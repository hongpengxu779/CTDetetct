"""
AI分割操作功能
负责各种AI分割相关的操作
"""

import os
import tempfile
import SimpleITK as sitk
from PyQt5 import QtWidgets, QtCore

from AISegmeant.unet_segmentation_dialog import UnetSegmentationDialog
from AISegmeant.segmentation_inference import UnetSegmentationInference
from AISegmeant.sam2_segmentation_dialog import Sam2SegmentationDialog
from AISegmeant.sam2_segmentation_inference import Sam2PreSegmentationInference
from AISegmeant.image_overlay import create_overlay_from_files, overlay_segmentation


class AIOperations:
    """AI分割操作类，作为Mixin使用"""

    @staticmethod
    def _build_affine_from_sitk_image(sitk_image):
        if sitk_image is None:
            return None
        import numpy as np
        direction = sitk_image.GetDirection()
        spacing_data = sitk_image.GetSpacing()
        origin = sitk_image.GetOrigin()
        affine_matrix = np.eye(4)
        for i in range(3):
            for j in range(3):
                affine_matrix[i, j] = direction[i * 3 + j] * spacing_data[j]
        affine_matrix[:3, 3] = origin
        return affine_matrix

    @staticmethod
    def _derive_nifti_output_name(input_file, suffix):
        base = os.path.basename(input_file)
        if base.endswith('.nii.gz'):
            stem = base[:-7]
            return f"{stem}{suffix}.nii.gz"
        if base.endswith('.nii'):
            stem = base[:-4]
            return f"{stem}{suffix}.nii"
        stem, ext = os.path.splitext(base)
        return f"{stem}{suffix}{ext if ext else '.nii.gz'}"
    
    def run_unet_segmentation(self):
        """运行UNet分割程序"""
        try:
            # 准备当前数据
            current_data = None
            if hasattr(self, 'image') and self.image is not None and hasattr(self, 'array') and self.array is not None:
                # 包含图像和数组数据
                current_data = {
                    'image': self.image,
                    'array': self.array,
                    'spacing': self.spacing if hasattr(self, 'spacing') else (1.0, 1.0, 1.0)
                }
            
            # 创建UNet分割对话框，传递当前数据
            dialog = UnetSegmentationDialog(self, current_data=current_data)
            
            # 如果用户点击了确定
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                # 获取用户输入的参数
                params = dialog.get_parameters()
                
                # 显示进度对话框
                progress = QtWidgets.QProgressDialog(
                    "正在进行分割，请稍候...", 
                    "取消", 
                    0, 
                    0, 
                    self
                )
                progress.setWindowTitle("AI分割进度")
                progress.setWindowModality(QtCore.Qt.WindowModal)
                progress.setCancelButton(None)  # 禁用取消按钮
                progress.show()
                QtWidgets.QApplication.processEvents()
                
                try:
                    # 初始化推理器（使用滑窗推理）
                    inferencer = UnetSegmentationInference(
                        checkpoint_path=params['checkpoint_path'],
                        output_dir=params['output_dir'],
                        roi_size=params['roi_size'],
                        sw_batch_size=params['sw_batch_size']
                    )
                    
                    # 执行分割 - 根据是否使用当前数据选择不同的方法
                    if params['use_current_data']:
                        # 使用当前数据进行分割
                        data = params['current_data']
                        output_filename = "current_data_segmented.nii.gz"
                        
                        # 获取affine矩阵
                        affine_matrix = None
                        if data['image'] is not None:
                            # 从SimpleITK图像获取affine
                            direction = data['image'].GetDirection()
                            spacing_data = data['image'].GetSpacing()
                            origin = data['image'].GetOrigin()
                            
                            # 构建affine矩阵
                            import numpy as np
                            affine_matrix = np.eye(4)
                            # 设置旋转和缩放部分
                            for i in range(3):
                                for j in range(3):
                                    affine_matrix[i, j] = direction[i*3 + j] * spacing_data[j]
                            # 设置平移部分
                            affine_matrix[:3, 3] = origin
                        
                        result_path = inferencer.run_from_array(
                            data['array'], 
                            affine=affine_matrix,
                            output_filename=output_filename
                        )
                    else:
                        # 从文件加载进行分割
                        output_filename = os.path.basename(params['input_file']).replace('.nii', '_segmented.nii')
                        result_path = inferencer.run(params['input_file'], output_filename)
                    
                    progress.close()
                    
                    # 如果选择了融合显示，创建融合图像
                    if params['overlay_with_original']:
                        try:
                            # 创建融合图像
                            if params['use_current_data']:
                                overlay_filename = "current_data_overlay.nii.gz"
                            else:
                                overlay_filename = os.path.basename(params['input_file']).replace('.nii', '_overlay.nii')
                            overlay_path = os.path.join(params['output_dir'], overlay_filename)
                            
                            # 显示融合进度
                            overlay_progress = QtWidgets.QProgressDialog(
                                "正在创建融合图像...", 
                                None, 
                                0, 
                                0, 
                                self
                            )
                            overlay_progress.setWindowTitle("图像融合")
                            overlay_progress.setWindowModality(QtCore.Qt.WindowModal)
                            overlay_progress.show()
                            QtWidgets.QApplication.processEvents()
                            
                            # 根据是否使用当前数据选择不同的方法
                            if params['use_current_data']:
                                # 使用当前数据创建融合图像
                                # 先将当前数据保存为临时文件，然后调用融合函数
                                temp_input = tempfile.NamedTemporaryFile(suffix='.nii.gz', delete=False)
                                temp_input.close()
                                
                                # 保存当前数据为NIfTI文件
                                # 注意：使用array而不是image，以保持与推理输出相同的维度顺序 (Z, Y, X)
                                import nibabel as nib
                                import numpy as np
                                temp_nii = nib.Nifti1Image(params['current_data']['array'], affine_matrix if affine_matrix is not None else np.eye(4))
                                nib.save(temp_nii, temp_input.name)
                                
                                # 创建融合图像
                                create_overlay_from_files(
                                    temp_input.name,
                                    result_path,
                                    overlay_path,
                                    color=params['overlay_color'],
                                    alpha=params['overlay_alpha']
                                )
                                
                                # 删除临时文件
                                os.unlink(temp_input.name)
                            else:
                                # 从文件创建融合图像
                                create_overlay_from_files(
                                    params['input_file'],
                                    result_path,
                                    overlay_path,
                                    color=params['overlay_color'],
                                    alpha=params['overlay_alpha']
                                )
                            
                            overlay_progress.close()
                            
                            # 询问用户加载哪个结果
                            reply = QtWidgets.QMessageBox.question(
                                self,
                                "分割完成",
                                f"分割完成！\n\n"
                                f"• 分割结果: {result_path}\n"
                                f"• 融合图像: {overlay_path}\n\n"
                                f"选择要加载的图像：\n"
                                f"- 是(Y)：加载融合图像（推荐）\n"
                                f"- 否(N)：加载纯分割结果",
                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel
                            )
                            
                            if reply == QtWidgets.QMessageBox.Yes:
                                # 加载融合图像
                                self.load_data(overlay_path)
                            elif reply == QtWidgets.QMessageBox.No:
                                # 加载纯分割结果
                                self.load_data(result_path)
                            # Cancel则不加载任何图像
                            
                        except Exception as e:
                            QtWidgets.QMessageBox.warning(
                                self,
                                "融合警告",
                                f"创建融合图像时出错：{str(e)}\n\n将显示纯分割结果"
                            )
                            # 如果融合失败，仍然可以显示分割结果
                            reply = QtWidgets.QMessageBox.question(
                                self,
                                "分割完成",
                                f"分割完成！结果已保存到：\n{result_path}\n\n是否加载分割结果？",
                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                            )
                            if reply == QtWidgets.QMessageBox.Yes:
                                self.load_data(result_path)
                    else:
                        # 不使用融合，直接询问是否加载分割结果
                        reply = QtWidgets.QMessageBox.question(
                            self,
                            "分割完成",
                            f"分割完成！结果已保存到：\n{result_path}\n\n是否加载分割结果？",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                        )
                        
                        if reply == QtWidgets.QMessageBox.Yes:
                            # 加载并显示分割结果
                            self.load_data(result_path)
                        
                except Exception as e:
                    progress.close()
                    QtWidgets.QMessageBox.critical(
                        self, 
                        "分割错误", 
                        f"执行分割时出错：{str(e)}\n\n请检查：\n"
                        f"1. 模型权重文件是否正确\n"
                        f"2. 输入文件格式是否正确\n"
                        f"3. 是否安装了所需的依赖包(torch, monai等)"
                    )
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"运行UNet分割程序时出错：{str(e)}")

    def run_sam2_presegmentation(self):
        """运行SAM预分割（优先SAM2，回退SAM1）"""
        try:
            current_data = None
            if hasattr(self, 'image') and self.image is not None and hasattr(self, 'array') and self.array is not None:
                current_data = {
                    'image': self.image,
                    'array': self.array,
                    'spacing': self.spacing if hasattr(self, 'spacing') else (1.0, 1.0, 1.0)
                }

            dialog = Sam2SegmentationDialog(self, current_data=current_data)
            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                return

            params = dialog.get_parameters()
            self.sam_quick_config = {
                'checkpoint_path': params['checkpoint_path'],
                'output_dir': params['output_dir'],
                'model_cfg': params['model_cfg'],
                'points_per_side': params['points_per_side'],
                'pred_iou_thresh': params['pred_iou_thresh'],
                'stability_score_thresh': params['stability_score_thresh'],
                'min_mask_region_area': params['min_mask_region_area'],
                'use_current_data': True,
            }
            self.sam_quick_runtime = None

            progress = QtWidgets.QProgressDialog("正在执行SAM预分割，请稍候...", None, 0, 100, self)
            progress.setWindowTitle("SAM预分割进度")
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.setCancelButton(None)
            progress.setValue(0)
            progress.show()
            QtWidgets.QApplication.processEvents()

            try:
                inferencer = Sam2PreSegmentationInference(
                    checkpoint_path=params['checkpoint_path'],
                    output_dir=params['output_dir'],
                    model_cfg=params['model_cfg'],
                    points_per_side=params['points_per_side'],
                    pred_iou_thresh=params['pred_iou_thresh'],
                    stability_score_thresh=params['stability_score_thresh'],
                    min_mask_region_area=params['min_mask_region_area'],
                )

                def on_progress(value):
                    progress.setValue(value)
                    QtWidgets.QApplication.processEvents()

                affine_matrix = None
                seg_mode = params.get('segmentation_mode', 'volume_auto')
                is_single_slice = seg_mode in ('single_point', 'single_box')
                prompt_type = params.get('prompt_type', 'none')
                slice_index = int(params.get('slice_index', 0))
                point_xy = params.get('point_xy', None)
                point_label = int(params.get('point_label', 1))
                box_xyxy = params.get('box_xyxy', None)

                if params['use_current_data']:
                    data = params['current_data']
                    affine_matrix = self._build_affine_from_sitk_image(data['image'])
                    if is_single_slice:
                        output_filename = f"current_data_sam_slice_{slice_index:04d}.nii.gz"
                        result_path = inferencer.run_single_slice_from_array(
                            data['array'],
                            slice_index=slice_index,
                            affine=affine_matrix,
                            output_filename=output_filename,
                            prompt_type=prompt_type,
                            point_xy=point_xy,
                            point_label=point_label,
                            box_xyxy=box_xyxy,
                            progress_callback=on_progress,
                        )
                    else:
                        output_filename = "current_data_sam_preseg.nii.gz"
                        result_path = inferencer.run_from_array(
                            data['array'],
                            affine=affine_matrix,
                            output_filename=output_filename,
                            progress_callback=on_progress,
                        )
                else:
                    if is_single_slice:
                        output_filename = self._derive_nifti_output_name(
                            params['input_file'], f'_sam_slice_{slice_index:04d}'
                        )
                        result_path = inferencer.run_single_slice(
                            params['input_file'],
                            slice_index=slice_index,
                            output_filename=output_filename,
                            prompt_type=prompt_type,
                            point_xy=point_xy,
                            point_label=point_label,
                            box_xyxy=box_xyxy,
                            progress_callback=on_progress,
                        )
                    else:
                        output_filename = self._derive_nifti_output_name(params['input_file'], '_sam_preseg')
                        result_path = inferencer.run(
                            params['input_file'],
                            output_filename=output_filename,
                            progress_callback=on_progress,
                        )

                progress.setValue(100)
                progress.close()

                if params['overlay_with_original'] and not is_single_slice:
                    try:
                        if params['use_current_data']:
                            overlay_filename = "current_data_sam_overlay.nii.gz"
                        else:
                            overlay_filename = self._derive_nifti_output_name(params['input_file'], '_sam_overlay')
                        overlay_path = os.path.join(params['output_dir'], overlay_filename)

                        overlay_progress = QtWidgets.QProgressDialog("正在创建融合图像...", None, 0, 0, self)
                        overlay_progress.setWindowTitle("图像融合")
                        overlay_progress.setWindowModality(QtCore.Qt.WindowModal)
                        overlay_progress.show()
                        QtWidgets.QApplication.processEvents()

                        if params['use_current_data']:
                            temp_input = tempfile.NamedTemporaryFile(suffix='.nii.gz', delete=False)
                            temp_input.close()

                            import nibabel as nib
                            import numpy as np
                            temp_nii = nib.Nifti1Image(
                                params['current_data']['array'],
                                affine_matrix if affine_matrix is not None else np.eye(4)
                            )
                            nib.save(temp_nii, temp_input.name)

                            create_overlay_from_files(
                                temp_input.name,
                                result_path,
                                overlay_path,
                                color=params['overlay_color'],
                                alpha=params['overlay_alpha']
                            )
                            os.unlink(temp_input.name)
                        else:
                            create_overlay_from_files(
                                params['input_file'],
                                result_path,
                                overlay_path,
                                color=params['overlay_color'],
                                alpha=params['overlay_alpha']
                            )

                        overlay_progress.close()

                        reply = QtWidgets.QMessageBox.question(
                            self,
                            "SAM预分割完成",
                            f"SAM预分割完成！\n\n"
                            f"• 预分割结果: {result_path}\n"
                            f"• 融合图像: {overlay_path}\n\n"
                            f"选择要加载的图像：\n"
                            f"- 是(Y)：加载融合图像（推荐）\n"
                            f"- 否(N)：加载纯预分割结果",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel
                        )

                        if reply == QtWidgets.QMessageBox.Yes:
                            self.load_data(overlay_path)
                        elif reply == QtWidgets.QMessageBox.No:
                            self.load_data(result_path)

                    except Exception as e:
                        QtWidgets.QMessageBox.warning(
                            self,
                            "融合警告",
                            f"创建融合图像时出错：{str(e)}\n\n将显示纯预分割结果"
                        )
                        reply = QtWidgets.QMessageBox.question(
                            self,
                            "SAM预分割完成",
                            f"SAM预分割完成！结果已保存到：\n{result_path}\n\n是否加载预分割结果？",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                        )
                        if reply == QtWidgets.QMessageBox.Yes:
                            self.load_data(result_path)
                else:
                    reply = QtWidgets.QMessageBox.question(
                        self,
                        "SAM预分割完成",
                        f"SAM预分割完成！结果已保存到：\n{result_path}\n\n是否加载预分割结果？",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                    )
                    if reply == QtWidgets.QMessageBox.Yes:
                        self.load_data(result_path)

            except Exception as e:
                progress.close()
                QtWidgets.QMessageBox.critical(
                    self,
                    "SAM预分割错误",
                    f"执行SAM预分割时出错：{str(e)}\n\n请检查：\n"
                    f"1. 若使用SAM2，配置文件与checkpoint是否匹配\n"
                    f"2. 输入数据格式是否正确\n"
                    f"3. 是否安装了依赖包(segment-anything 或 sam2, torch, torchvision)"
                )

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"运行SAM预分割时出错：{str(e)}")

    def _sam_apply_overlay_to_viewers(self, runtime, color_rgb, point_xy, slice_index, view_type):
        """刷新2D视图（SAM结果通过标注overlay显示，与画笔/橡皮擦同一套），并更新3D体渲染mask overlay。

        2D切片视图不再替换 get_slice，SAM掩码已写入 annotation_volume，
        由标注系统的 annotation_overlay_item 负责渲染，使画笔/橡皮擦可直接编辑。
        """
        accum_mask = runtime['accum_mask']

        # --- 2D viewer：SAM 结果已写入 annotation_volume，刷新标注 overlay 即可 ---
        for viewer_attr in ('axial_viewer', 'cor_viewer', 'sag_viewer'):
            viewer = getattr(self, viewer_attr, None)
            if viewer is None:
                continue
            viewer._refresh_current_slice()

        # --- 3D viewer 更新（在原始体数据上叠加一个独立的 mask volume actor）---
        vol_viewer = getattr(self, 'volume_viewer', None)
        if vol_viewer is not None and hasattr(vol_viewer, 'update_mask_overlay'):
            spacing = getattr(self, 'spacing', (1.0, 1.0, 1.0))
            try:
                vol_viewer.update_mask_overlay(accum_mask, spacing=spacing, color_rgb=color_rgb, alpha=0.55)
            except Exception as e:
                print(f"3D mask overlay 更新失败: {e}")

        # --- 恢复十字线到点击位置 ---
        try:
            if point_xy is not None and hasattr(self, 'sync_crosshair_from_view'):
                self.sync_crosshair_from_view(
                    str(view_type), int(point_xy[0]), int(point_xy[1]), int(slice_index))
        except Exception:
            pass

    def _sam_import_to_annotation(self, mask_2d, view_type_str, slice_index, color_rgb=(0, 255, 0)):
        """将 SAM 分割结果（2D mask）写入标注系统（annotation_volume / annotation_drawn_mask）。

        写入时使用当前标注标签号；若标签为 0 则自动用标签 1。
        同时将 color_rgb 写入 annotation_label_colors，使 2D overlay 与 3D VTK overlay 颜色一致。
        返回实际写入的 label 值（int）。
        """
        import numpy as np

        # 确保 annotation_volume / annotation_drawn_mask 已初始化
        if not hasattr(self, '_prepare_annotation_environment'):
            return 0
        if not self._prepare_annotation_environment():
            return 0

        # 获取当前标注标签号；若为 0（默认/背景），自动使用标签 1
        if hasattr(self, 'get_current_annotation_label'):
            label = int(self.get_current_annotation_label())
        else:
            label = 1
        if label <= 0:
            label = 1  # 标签 0 为背景，SAM 结果默认归入标签 1

        # 同步标注颜色表，确保 2D overlay 与 3D VTK overlay 颜色一致
        if hasattr(self, 'annotation_label_colors'):
            self.annotation_label_colors[label] = tuple(int(c) for c in color_rgb)

        av = self.annotation_volume          # uint16 (Z, Y, X)
        dm = self.annotation_drawn_mask      # bool   (Z, Y, X)
        z_dim, y_dim, x_dim = av.shape

        mask_bool = mask_2d > 0
        s_idx = int(slice_index)

        if view_type_str == 'coronal':
            # 冠状面：slice_index 对应 Y 轴，图像维度 (Z, X)
            if 0 <= s_idx < y_dim:
                h = min(z_dim, mask_bool.shape[0])
                w = min(x_dim, mask_bool.shape[1])
                av[:h, s_idx, :w][mask_bool[:h, :w]] = label
                dm[:h, s_idx, :w][mask_bool[:h, :w]] = True
        elif view_type_str == 'sagittal':
            # 矢状面：slice_index 对应 X 轴，图像维度 (Z, Y)
            if 0 <= s_idx < x_dim:
                h = min(z_dim, mask_bool.shape[0])
                w = min(y_dim, mask_bool.shape[1])
                av[:h, :w, s_idx][mask_bool[:h, :w]] = label
                dm[:h, :w, s_idx][mask_bool[:h, :w]] = True
        else:  # axial
            # 轴位：slice_index 对应 Z 轴，图像维度 (Y, X)
            if 0 <= s_idx < z_dim:
                h = min(y_dim, mask_bool.shape[0])
                w = min(x_dim, mask_bool.shape[1])
                av[s_idx, :h, :w][mask_bool[:h, :w]] = label
                dm[s_idx, :h, :w][mask_bool[:h, :w]] = True

        # 刷新三个 viewer 的标注覆盖层
        if hasattr(self, 'refresh_annotation_overlays'):
            self.refresh_annotation_overlays()

        return label

    def _sam_register_annotation_in_data_list(self, label, color_rgb):
        """将当前 annotation_volume 作为标签数据项注册到数据列表。

        直接操作 data_list_widget，不调用 add_data_to_list / switch_to_data，
        避免触发 on_data_selection_changed 重建 viewer 和重置切片位置。
        """
        import SimpleITK as sitk
        from PyQt5 import QtCore, QtWidgets

        if not hasattr(self, 'data_list_widget') or not hasattr(self, 'annotation_volume'):
            return

        # 移除旧的 SAM 标注条目
        rows_to_remove = []
        for i in range(self.data_list_widget.count()):
            item = self.data_list_widget.item(i)
            if item is None:
                continue
            d = item.data(QtCore.Qt.UserRole)
            if isinstance(d, dict) and d.get('label_source') == 'sam_annotation':
                rows_to_remove.append(i)
        for row in reversed(rows_to_remove):
            self.data_list_widget.takeItem(row)

        try:
            label_image = sitk.GetImageFromArray(self.annotation_volume.astype('uint16'))
            if hasattr(self, 'image') and self.image is not None:
                label_image.CopyInformation(self.image)
        except Exception:
            label_image = None

        unique_vals = sorted(set(int(v) for v in self.annotation_volume.flat if v > 0))
        color_map = {int(label): tuple(int(c) for c in color_rgb)}

        data_item = {
            'image': label_image,
            'array': self.annotation_volume.astype('uint16').copy(),
            'shape': self.annotation_volume.shape,
            'spacing': getattr(self, 'spacing', (1.0, 1.0, 1.0)),
            'rgb_array': None,
            'is_segmentation': True,
            'data_type': 'label',
            'label_source': 'sam_annotation',
            'label_values': unique_vals,
            'label_color_map': color_map,
            'label_path': None,
            'annotation_drawn_mask': (
                self.annotation_drawn_mask.copy()
                if hasattr(self, 'annotation_drawn_mask') else None
            ),
        }

        dataset_name = f"SAM分割 [标签{label}]"

        # 直接向列表插入条目，不触发 currentItemChanged / switch_to_data
        list_item = QtWidgets.QListWidgetItem(dataset_name)
        list_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        list_item.setData(QtCore.Qt.UserRole, data_item)
        list_item.setData(QtCore.Qt.UserRole + 1, True)  # visible

        # 暂时断开 currentItemChanged 信号，避免 switch_to_data 被触发
        try:
            self.data_list_widget.currentItemChanged.disconnect(self.on_data_selection_changed)
        except Exception:
            pass

        self.data_list_widget.addItem(list_item)

        if hasattr(self, '_build_dataset_list_item_widget'):
            item_widget = self._build_dataset_list_item_widget(list_item, dataset_name)
            list_item.setSizeHint(item_widget.sizeHint())
            self.data_list_widget.setItemWidget(list_item, item_widget)

        # 重新连接信号
        try:
            self.data_list_widget.currentItemChanged.connect(self.on_data_selection_changed)
        except Exception:
            pass

    def run_sam_prompt_quick(self, prompt_type, slice_index, point_xy=None, point_label=1, box_xyxy=None, view_type='axial'):
        """使用最近一次SAM参数进行快速单切片提示分割（无需重复弹参数对话框）。"""
        import numpy as np  # 确保整个函数都能使用np

        cfg = getattr(self, 'sam_quick_config', None)
        if not isinstance(cfg, dict):
            current_data = None
            if hasattr(self, 'image') and self.image is not None and hasattr(self, 'array') and self.array is not None:
                current_data = {
                    'image': self.image,
                    'array': self.array,
                    'spacing': self.spacing if hasattr(self, 'spacing') else (1.0, 1.0, 1.0)
                }

            dialog = Sam2SegmentationDialog(self, current_data=current_data)
            dialog.setWindowTitle("SAM快速分割 - 首次参数配置")
            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                return

            params = dialog.get_parameters()
            cfg = {
                'checkpoint_path': params['checkpoint_path'],
                'output_dir': params['output_dir'],
                'model_cfg': params['model_cfg'],
                'points_per_side': params['points_per_side'],
                'pred_iou_thresh': params['pred_iou_thresh'],
                'stability_score_thresh': params['stability_score_thresh'],
                'min_mask_region_area': params['min_mask_region_area'],
                'use_current_data': True,
            }
            self.sam_quick_config = cfg
            self.sam_quick_runtime = None

        if not hasattr(self, 'array') or self.array is None:
            QtWidgets.QMessageBox.warning(self, "SAM快速分割", "当前没有可用的体数据。")
            return

        # ---------- 初始化/验证 runtime（保存原始数据副本） ----------
        runtime = getattr(self, 'sam_quick_runtime', None)
        try:
            array_shape = tuple(self.array.shape)
        except Exception:
            array_shape = None

        # 若 runtime 中的 base_array 是从 overlay 加载的（shape 不同或不存在），重新初始化
        # 始终以当前加载的原始数据为基准（首次分割时取 self.array）
        if not isinstance(runtime, dict) or runtime.get('base_array') is None:
            runtime = None
        elif array_shape is None or tuple(runtime.get('base_array').shape) != array_shape:
            runtime = None

        if runtime is None:
            base_array = np.asarray(self.array, dtype=np.float32).copy()
            base_affine = self._build_affine_from_sitk_image(getattr(self, 'image', None))
            if base_affine is None:
                base_affine = np.eye(4, dtype=np.float64)
            else:
                base_affine = np.array(base_affine, dtype=np.float64, copy=True)
            runtime = {
                'base_array': base_array,
                'base_affine': base_affine,
                'accum_mask': np.zeros(base_array.shape, dtype=np.uint8),
            }
            self.sam_quick_runtime = runtime

        # ---------- 进度框 ----------
        progress = QtWidgets.QProgressDialog("正在执行SAM快速分割...", None, 0, 100, self)
        progress.setWindowTitle("SAM快速分割")
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setCancelButton(None)
        progress.setValue(0)
        progress.show()
        QtWidgets.QApplication.processEvents()

        try:
            # ---------- 复用已缓存的 inferencer ----------
            _inferencer_key = (
                cfg['checkpoint_path'],
                cfg.get('model_cfg', 'configs/sam2.1/sam2.1_hiera_l.yaml'),
                int(cfg.get('points_per_side', 32)),
                float(cfg.get('pred_iou_thresh', 0.8)),
                float(cfg.get('stability_score_thresh', 0.95)),
                int(cfg.get('min_mask_region_area', 100)),
            )
            cached = getattr(self, 'sam_quick_inferencer', None)
            if cached is None or getattr(self, '_sam_quick_inferencer_key', None) != _inferencer_key:
                inferencer = Sam2PreSegmentationInference(
                    checkpoint_path=cfg['checkpoint_path'],
                    output_dir=cfg['output_dir'],
                    model_cfg=cfg.get('model_cfg', 'configs/sam2.1/sam2.1_hiera_l.yaml'),
                    points_per_side=int(cfg.get('points_per_side', 32)),
                    pred_iou_thresh=float(cfg.get('pred_iou_thresh', 0.8)),
                    stability_score_thresh=float(cfg.get('stability_score_thresh', 0.95)),
                    min_mask_region_area=int(cfg.get('min_mask_region_area', 100)),
                )
                self.sam_quick_inferencer = inferencer
                self._sam_quick_inferencer_key = _inferencer_key
            else:
                inferencer = cached
                inferencer.output_dir = cfg['output_dir']
                os.makedirs(inferencer.output_dir, exist_ok=True)

            def on_progress(value):
                progress.setValue(int(value))
                QtWidgets.QApplication.processEvents()

            # ---------- 按视图轴提取2D切片，封装为伪3D ----------
            base_array = runtime['base_array']
            view_type_str = str(view_type)
            if view_type_str == 'coronal':
                slice_2d = base_array[:, int(slice_index), :]   # (Z, X)
            elif view_type_str == 'sagittal':
                slice_2d = base_array[:, :, int(slice_index)]   # (Z, Y)
            else:  # axial
                slice_2d = base_array[int(slice_index), :, :]   # (Y, X)

            # 归一化为 float32 3D(1,H,W) 传给 inferencer
            pseudo_volume = np.expand_dims(slice_2d.astype(np.float32), axis=0)

            # ---------- 直接推理得到2D mask（不写文件） ----------
            proc_volume, _ = inferencer.preprocess_array(pseudo_volume)
            mask_2d = inferencer.inference_single_slice(
                proc_volume,
                slice_index=0,
                prompt_type=str(prompt_type),
                point_xy=point_xy,
                point_label=int(point_label),
                box_xyxy=box_xyxy,
                progress_callback=on_progress,
            )  # shape(H,W), uint8, values 0 or 1

            progress.setValue(100)
            progress.close()

            # ---------- 将 mask 累积写入 accum_mask ----------
            mask_3d   = runtime['accum_mask']
            mask_bool = (mask_2d > 0).astype(np.uint8) * 255
            s_idx = int(slice_index)
            if view_type_str == 'coronal':
                if 0 <= s_idx < mask_3d.shape[1]:
                    h = min(mask_3d.shape[0], mask_bool.shape[0])
                    w = min(mask_3d.shape[2], mask_bool.shape[1])
                    mask_3d[:h, s_idx, :w] = np.maximum(mask_3d[:h, s_idx, :w], mask_bool[:h, :w])
            elif view_type_str == 'sagittal':
                if 0 <= s_idx < mask_3d.shape[2]:
                    h = min(mask_3d.shape[0], mask_bool.shape[0])
                    w = min(mask_3d.shape[1], mask_bool.shape[1])
                    mask_3d[:h, :w, s_idx] = np.maximum(mask_3d[:h, :w, s_idx], mask_bool[:h, :w])
            else:  # axial
                if 0 <= s_idx < mask_3d.shape[0]:
                    h = min(mask_3d.shape[1], mask_bool.shape[0])
                    w = min(mask_3d.shape[2], mask_bool.shape[1])
                    mask_3d[s_idx, :h, :w] = np.maximum(mask_3d[s_idx, :h, :w], mask_bool[:h, :w])

            # ---------- 更新 viewer get_slice 函数并刷新（不重建viewer） ----------
            color_rgb = (0, 255, 0) if str(prompt_type) == 'point' else (255, 0, 255)

            # ---------- 联动：将 SAM mask 写入标注系统（annotation_volume） ----------
            _used_label = 1
            try:
                _used_label = self._sam_import_to_annotation(
                    mask_2d, view_type_str, s_idx, color_rgb=color_rgb) or 1
            except Exception as _e:
                print(f"SAM 掩码写入标注系统失败（不影响显示）: {_e}")

            # ---------- 将 annotation_volume 注册到数据列表 ----------
            try:
                self._sam_register_annotation_in_data_list(_used_label, color_rgb)
            except Exception as _e:
                print(f"SAM 标注注册数据列表失败（不影响显示）: {_e}")

            self._sam_apply_overlay_to_viewers(runtime, color_rgb, point_xy, slice_index, view_type)

            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage(
                    f"SAM快速分割完成：{view_type_str} 切片={s_idx}，结果已写入标注层，可用画笔/橡皮擦继续编辑",
                    5000,
                )

        except Exception as e:
            progress.close()
            QtWidgets.QMessageBox.critical(self, "SAM快速分割错误", str(e))

