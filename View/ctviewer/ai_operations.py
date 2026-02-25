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
from AISegmeant.image_overlay import create_overlay_from_files


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
        """运行SAM2预分割"""
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

            progress = QtWidgets.QProgressDialog("正在执行SAM2预分割，请稍候...", None, 0, 100, self)
            progress.setWindowTitle("SAM2预分割进度")
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
                if params['use_current_data']:
                    data = params['current_data']
                    output_filename = "current_data_sam2_preseg.nii.gz"
                    affine_matrix = self._build_affine_from_sitk_image(data['image'])
                    result_path = inferencer.run_from_array(
                        data['array'],
                        affine=affine_matrix,
                        output_filename=output_filename,
                        progress_callback=on_progress,
                    )
                else:
                    output_filename = self._derive_nifti_output_name(params['input_file'], '_sam2_preseg')
                    result_path = inferencer.run(
                        params['input_file'],
                        output_filename=output_filename,
                        progress_callback=on_progress,
                    )

                progress.setValue(100)
                progress.close()

                if params['overlay_with_original']:
                    try:
                        if params['use_current_data']:
                            overlay_filename = "current_data_sam2_overlay.nii.gz"
                        else:
                            overlay_filename = self._derive_nifti_output_name(params['input_file'], '_sam2_overlay')
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
                            "SAM2预分割完成",
                            f"SAM2预分割完成！\n\n"
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
                            "SAM2预分割完成",
                            f"SAM2预分割完成！结果已保存到：\n{result_path}\n\n是否加载预分割结果？",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                        )
                        if reply == QtWidgets.QMessageBox.Yes:
                            self.load_data(result_path)
                else:
                    reply = QtWidgets.QMessageBox.question(
                        self,
                        "SAM2预分割完成",
                        f"SAM2预分割完成！结果已保存到：\n{result_path}\n\n是否加载预分割结果？",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                    )
                    if reply == QtWidgets.QMessageBox.Yes:
                        self.load_data(result_path)

            except Exception as e:
                progress.close()
                QtWidgets.QMessageBox.critical(
                    self,
                    "SAM2预分割错误",
                    f"执行SAM2预分割时出错：{str(e)}\n\n请检查：\n"
                    f"1. SAM2配置文件与checkpoint是否匹配\n"
                    f"2. 输入数据格式是否正确\n"
                    f"3. 是否安装了依赖包(sam2, torch, torchvision, hydra-core)"
                )

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"运行SAM2预分割时出错：{str(e)}")

