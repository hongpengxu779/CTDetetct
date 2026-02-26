import os
import time
import numpy as np
import nibabel as nib
import torch


class Sam2PreSegmentationInference:
    """SAM2预分割推理（按2D切片自动掩膜并合成为3D体）"""

    def __init__(
        self,
        checkpoint_path,
        output_dir,
        model_cfg="configs/sam2.1/sam2.1_hiera_l.yaml",
        points_per_side=32,
        pred_iou_thresh=0.8,
        stability_score_thresh=0.95,
        min_mask_region_area=100,
        device=None,
    ):
        self.checkpoint_path = checkpoint_path
        self.output_dir = output_dir
        self.model_cfg = model_cfg
        self.points_per_side = points_per_side
        self.pred_iou_thresh = pred_iou_thresh
        self.stability_score_thresh = stability_score_thresh
        self.min_mask_region_area = min_mask_region_area
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu") if device is None else device
        self.backend = None
        self.sam_model = None
        self.sam_predictor = None

        os.makedirs(self.output_dir, exist_ok=True)
        self._initialize_sam2()

    def _initialize_sam2(self):
        # 优先使用 SAM2；若环境不满足（如 Python<3.10）则自动回退到 SAM1（segment-anything）
        try:
            from sam2.build_sam import build_sam2
            from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
            from sam2.sam2_image_predictor import SAM2ImagePredictor

            sam2_model = build_sam2(
                config_file=self.model_cfg,
                ckpt_path=self.checkpoint_path,
                device=str(self.device),
                mode="eval",
                apply_postprocessing=True,
            )
            self.mask_generator = SAM2AutomaticMaskGenerator(
                model=sam2_model,
                points_per_side=self.points_per_side,
                pred_iou_thresh=self.pred_iou_thresh,
                stability_score_thresh=self.stability_score_thresh,
                min_mask_region_area=self.min_mask_region_area,
                output_mode="binary_mask",
                use_m2m=False,
            )
            # 同时创建 SAM2ImagePredictor，用于点/框提示分割
            self.sam_predictor = SAM2ImagePredictor(sam2_model)
            self.backend = "sam2"
            return
        except Exception:
            pass

        try:
            from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
        except Exception as exc:
            raise ImportError(
                "未找到可用的SAM后端。请安装以下任一方案：\n"
                "1) SAM2（Python>=3.10）：pip install -e ./sam2\n"
                "2) SAM1（Python>=3.8）：pip install git+https://github.com/facebookresearch/segment-anything.git"
            ) from exc

        ckpt_name = os.path.basename(str(self.checkpoint_path)).lower()
        if "vit_h" in ckpt_name or "hiera" in ckpt_name:
            model_type = "vit_h"
        elif "vit_l" in ckpt_name:
            model_type = "vit_l"
        else:
            model_type = "vit_b"

        sam_model = sam_model_registry[model_type](checkpoint=self.checkpoint_path)
        sam_model.to(device=str(self.device))
        sam_model.eval()
        self.sam_model = sam_model

        try:
            from segment_anything import SamPredictor
            self.sam_predictor = SamPredictor(sam_model)
        except Exception:
            self.sam_predictor = None

        self.mask_generator = SamAutomaticMaskGenerator(
            model=sam_model,
            points_per_side=self.points_per_side,
            pred_iou_thresh=self.pred_iou_thresh,
            stability_score_thresh=self.stability_score_thresh,
            min_mask_region_area=self.min_mask_region_area,
            output_mode="binary_mask",
        )
        self.backend = "sam1"

    @staticmethod
    def _normalize_slice_to_rgb(slice_2d):
        finite_mask = np.isfinite(slice_2d)
        if not np.any(finite_mask):
            normalized = np.zeros_like(slice_2d, dtype=np.uint8)
            return np.stack([normalized, normalized, normalized], axis=-1)

        valid_values = slice_2d[finite_mask]
        low = np.percentile(valid_values, 1)
        high = np.percentile(valid_values, 99)
        if high <= low:
            low = float(valid_values.min())
            high = float(valid_values.max())

        if high > low:
            clipped = np.clip(slice_2d, low, high)
            norm = (clipped - low) / (high - low)
        else:
            norm = np.zeros_like(slice_2d, dtype=np.float32)

        norm = np.nan_to_num(norm, nan=0.0, posinf=1.0, neginf=0.0)
        gray_u8 = (norm * 255.0).astype(np.uint8)
        return np.stack([gray_u8, gray_u8, gray_u8], axis=-1)

    def _segment_slice(self, slice_2d):
        rgb = self._normalize_slice_to_rgb(slice_2d)
        anns = self.mask_generator.generate(rgb)
        if not anns:
            return np.zeros(slice_2d.shape, dtype=np.uint8)

        merged = np.zeros(slice_2d.shape, dtype=bool)
        for ann in anns:
            seg = ann.get("segmentation", None)
            if seg is not None:
                merged |= np.asarray(seg, dtype=bool)
        return merged.astype(np.uint8)

    def _segment_slice_with_prompt(self, slice_2d, prompt_type, point_xy=None, point_label=1, box_xyxy=None):
        if self.sam_predictor is None:
            raise RuntimeError("点/框提示分割需要 SAM predictor，初始化失败。")

        rgb = self._normalize_slice_to_rgb(slice_2d)

        if self.backend == "sam2":
            import torch
            with torch.inference_mode():
                self.sam_predictor.set_image(rgb)
                if prompt_type == "point":
                    if point_xy is None:
                        raise ValueError("点提示缺少坐标")
                    point_coords = np.array([[float(point_xy[0]), float(point_xy[1])]], dtype=np.float32)
                    point_labels = np.array([int(point_label)], dtype=np.int32)
                    masks, scores, _ = self.sam_predictor.predict(
                        point_coords=point_coords,
                        point_labels=point_labels,
                        multimask_output=True,
                    )
                    # 选得分最高的 mask
                    best = int(np.argmax(scores))
                    result = np.asarray(masks[best], dtype=np.uint8)
                elif prompt_type == "box":
                    if box_xyxy is None:
                        raise ValueError("框提示缺少坐标")
                    box = np.array([float(v) for v in box_xyxy], dtype=np.float32)
                    masks, scores, _ = self.sam_predictor.predict(
                        box=box,
                        multimask_output=False,
                    )
                    result = np.asarray(masks[0], dtype=np.uint8)
                else:
                    raise ValueError(f"不支持的提示类型: {prompt_type}")
            return result
        else:  # sam1
            self.sam_predictor.set_image(rgb)
            if prompt_type == "point":
                if point_xy is None:
                    raise ValueError("点提示缺少坐标")
                point_coords = np.array([[float(point_xy[0]), float(point_xy[1])]], dtype=np.float32)
                point_labels = np.array([int(point_label)], dtype=np.int32)
                masks, _, _ = self.sam_predictor.predict(
                    point_coords=point_coords,
                    point_labels=point_labels,
                    multimask_output=False,
                )
            elif prompt_type == "box":
                if box_xyxy is None:
                    raise ValueError("框提示缺少坐标")
                box = np.array([float(v) for v in box_xyxy], dtype=np.float32)
                masks, _, _ = self.sam_predictor.predict(
                    box=box,
                    multimask_output=False,
                )
            else:
                raise ValueError(f"不支持的提示类型: {prompt_type}")
            if masks is None or len(masks) == 0:
                return np.zeros(slice_2d.shape, dtype=np.uint8)
            return np.asarray(masks[0], dtype=np.uint8)

    def preprocess(self, input_path):
        nii = nib.load(input_path)
        array = nii.get_fdata().astype(np.float32)
        affine = nii.affine
        return array, affine

    def preprocess_array(self, input_array, affine=None):
        array = np.asarray(input_array, dtype=np.float32)
        if array.ndim != 3:
            raise ValueError(f"输入数组必须是3D (Z,Y,X)，当前形状: {array.shape}")
        if affine is None:
            affine = np.eye(4)
        return array, affine

    def inference(self, volume_array, progress_callback=None):
        depth = volume_array.shape[0]
        output = np.zeros(volume_array.shape, dtype=np.uint8)
        start_time = time.time()

        for z in range(depth):
            output[z] = self._segment_slice(volume_array[z])
            if progress_callback is not None:
                progress = int((z + 1) * 100 / max(depth, 1))
                progress_callback(progress)

        elapsed = time.time() - start_time
        positive = int(np.sum(output > 0))
        ratio = positive / output.size * 100 if output.size > 0 else 0.0
        backend_name = "SAM2" if self.backend == "sam2" else "SAM1"
        print(f"{backend_name}预分割完成，耗时: {elapsed:.2f}秒")
        print(f"前景体素: {positive}/{output.size} ({ratio:.2f}%)")
        return output

    def inference_single_slice(
        self,
        volume_array,
        slice_index,
        prompt_type="none",
        point_xy=None,
        point_label=1,
        box_xyxy=None,
        progress_callback=None,
    ):
        depth = volume_array.shape[0]
        if slice_index < 0 or slice_index >= depth:
            raise ValueError(f"slice_index 超出范围: {slice_index}, depth={depth}")

        if prompt_type in ("point", "box"):
            output_2d = self._segment_slice_with_prompt(
                volume_array[slice_index],
                prompt_type=prompt_type,
                point_xy=point_xy,
                point_label=point_label,
                box_xyxy=box_xyxy,
            )
        else:
            output_2d = self._segment_slice(volume_array[slice_index])

        if progress_callback is not None:
            progress_callback(100)
        return np.asarray(output_2d, dtype=np.uint8)

    @staticmethod
    def _single_slice_affine(affine, slice_index):
        affine_new = np.array(affine, dtype=np.float64, copy=True)
        affine_new[:3, 3] = affine_new[:3, 3] + affine_new[:3, 2] * float(slice_index)
        return affine_new

    def save_single_slice_result(self, output_2d, affine, slice_index, output_filename="sam_single_slice_preseg.nii.gz"):
        save_path = os.path.join(self.output_dir, output_filename)
        output_scaled = (np.asarray(output_2d, dtype=np.uint8) > 0).astype(np.uint8) * 255
        output_3d = output_scaled[np.newaxis, ...]
        nib.save(nib.Nifti1Image(output_3d, self._single_slice_affine(affine, slice_index)), save_path)
        return save_path

    def save_result(self, output_np, affine, output_filename="sam2_preseg.nii.gz"):
        save_path = os.path.join(self.output_dir, output_filename)
        output_scaled = (output_np > 0).astype(np.uint8) * 255
        nib.save(nib.Nifti1Image(output_scaled, affine), save_path)
        return save_path

    def run(self, input_path, output_filename="sam2_preseg.nii.gz", progress_callback=None):
        volume_array, affine = self.preprocess(input_path)
        output_np = self.inference(volume_array, progress_callback=progress_callback)
        return self.save_result(output_np, affine, output_filename)

    def run_from_array(self, input_array, affine=None, output_filename="sam2_preseg.nii.gz", progress_callback=None):
        volume_array, affine = self.preprocess_array(input_array, affine=affine)
        output_np = self.inference(volume_array, progress_callback=progress_callback)
        return self.save_result(output_np, affine, output_filename)

    def run_single_slice_from_array(
        self,
        input_array,
        slice_index,
        affine=None,
        output_filename="sam_single_slice_preseg.nii.gz",
        prompt_type="none",
        point_xy=None,
        point_label=1,
        box_xyxy=None,
        progress_callback=None,
    ):
        volume_array, affine = self.preprocess_array(input_array, affine=affine)
        output_np = self.inference_single_slice(
            volume_array,
            slice_index=slice_index,
            prompt_type=prompt_type,
            point_xy=point_xy,
            point_label=point_label,
            box_xyxy=box_xyxy,
            progress_callback=progress_callback,
        )
        return self.save_single_slice_result(output_np, affine, slice_index, output_filename)

    def run_single_slice(
        self,
        input_path,
        slice_index,
        output_filename="sam_single_slice_preseg.nii.gz",
        prompt_type="none",
        point_xy=None,
        point_label=1,
        box_xyxy=None,
        progress_callback=None,
    ):
        volume_array, affine = self.preprocess(input_path)
        output_np = self.inference_single_slice(
            volume_array,
            slice_index=slice_index,
            prompt_type=prompt_type,
            point_xy=point_xy,
            point_label=point_label,
            box_xyxy=box_xyxy,
            progress_callback=progress_callback,
        )
        return self.save_single_slice_result(output_np, affine, slice_index, output_filename)
