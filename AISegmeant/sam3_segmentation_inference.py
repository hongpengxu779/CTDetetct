import os
import time
import numpy as np
import nibabel as nib
import torch


class Sam3PreSegmentationInference:
    """SAM3预分割推理（按2D切片自动掩膜并合成为3D体）"""

    def __init__(
        self,
        checkpoint_path,
        output_dir,
        model_type="vit_b",
        points_per_side=32,
        pred_iou_thresh=0.86,
        stability_score_thresh=0.92,
        min_mask_region_area=100,
        device=None,
    ):
        self.checkpoint_path = checkpoint_path
        self.output_dir = output_dir
        self.model_type = model_type
        self.points_per_side = points_per_side
        self.pred_iou_thresh = pred_iou_thresh
        self.stability_score_thresh = stability_score_thresh
        self.min_mask_region_area = min_mask_region_area
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu") if device is None else device

        os.makedirs(self.output_dir, exist_ok=True)
        self._initialize_sam()

    def _initialize_sam(self):
        try:
            from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
        except Exception as exc:
            raise ImportError(
                "未找到segment_anything，请先安装：pip install segment-anything"
            ) from exc

        if self.model_type not in sam_model_registry:
            available = ", ".join(list(sam_model_registry.keys()))
            raise ValueError(f"不支持的model_type: {self.model_type}，可选值：{available}")

        sam_model = sam_model_registry[self.model_type](checkpoint=self.checkpoint_path)
        sam_model.to(self.device)
        self.mask_generator = SamAutomaticMaskGenerator(
            model=sam_model,
            points_per_side=self.points_per_side,
            pred_iou_thresh=self.pred_iou_thresh,
            stability_score_thresh=self.stability_score_thresh,
            min_mask_region_area=self.min_mask_region_area,
        )

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
        masks = self.mask_generator.generate(rgb)
        if not masks:
            return np.zeros(slice_2d.shape, dtype=np.uint8)

        merged = np.zeros(slice_2d.shape, dtype=bool)
        for item in masks:
            seg = item.get("segmentation", None)
            if seg is not None:
                merged |= seg
        return merged.astype(np.uint8)

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
        print(f"SAM3预分割完成，耗时: {elapsed:.2f}秒")
        print(f"前景体素: {positive}/{output.size} ({ratio:.2f}%)")
        return output

    def save_result(self, output_np, affine, output_filename="sam3_preseg.nii.gz"):
        save_path = os.path.join(self.output_dir, output_filename)
        output_scaled = (output_np > 0).astype(np.uint8) * 255
        nib.save(nib.Nifti1Image(output_scaled, affine), save_path)
        return save_path

    def run(self, input_path, output_filename="sam3_preseg.nii.gz", progress_callback=None):
        volume_array, affine = self.preprocess(input_path)
        output_np = self.inference(volume_array, progress_callback=progress_callback)
        return self.save_result(output_np, affine, output_filename)

    def run_from_array(self, input_array, affine=None, output_filename="sam3_preseg.nii.gz", progress_callback=None):
        volume_array, affine = self.preprocess_array(input_array, affine=affine)
        output_np = self.inference(volume_array, progress_callback=progress_callback)
        return self.save_result(output_np, affine, output_filename)
