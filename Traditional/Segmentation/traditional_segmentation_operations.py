"""
传统分割操作功能
负责各种传统分割相关的操作，包括区域生长等
"""

import os
import tempfile
import SimpleITK as sitk
import numpy as np
from PyQt5 import QtWidgets, QtCore

from Traditional.Segmentation.region_growing_dialog import RegionGrowingDialog
from Traditional.Segmentation.otsu_segmentation_dialog import OtsuSegmentationDialog
from AISegmeant.image_overlay import create_overlay_from_files, create_multi_label_overlay_from_files


class TraditionalSegmentationOperations:
    """传统分割操作类，作为Mixin使用"""
    
    def __init__(self):
        """初始化"""
        self.region_growing_seed_points = []  # 存储种子点
        self.last_otsu_threshold = None  # 存储上次OTSU计算的阈值
    
    def run_region_growing(self):
        """运行区域生长分割"""
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
            
            # 创建区域生长对话框，传递当前数据
            dialog = RegionGrowingDialog(self, current_data=current_data)
            
            # 如果已经有种子点，设置到对话框中
            if hasattr(self, 'region_growing_seed_points') and self.region_growing_seed_points:
                dialog.set_seed_points(self.region_growing_seed_points)
            
            # 如果用户点击了确定
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                # 获取用户输入的参数
                params = dialog.get_parameters()
                
                # 显示进度对话框
                progress = QtWidgets.QProgressDialog(
                    "正在进行区域生长分割，请稍候...", 
                    "取消", 
                    0, 
                    0, 
                    self
                )
                progress.setWindowTitle("区域生长进度")
                progress.setWindowModality(QtCore.Qt.WindowModal)
                progress.setCancelButton(None)  # 禁用取消按钮
                progress.show()
                QtWidgets.QApplication.processEvents()
                
                try:
                    # 执行区域生长分割
                    result_image = self.perform_region_growing(params)
                    
                    # 保存结果到临时文件
                    temp_dir = tempfile.gettempdir()
                    result_filename = "region_growing_result.nii.gz"
                    result_path = os.path.join(temp_dir, result_filename)
                    sitk.WriteImage(result_image, result_path)
                    
                    progress.close()
                    
                    # 如果选择了融合显示，创建融合图像
                    if params['overlay_with_original']:
                        try:
                            # 创建融合图像
                            overlay_filename = "region_growing_overlay.nii.gz"
                            overlay_path = os.path.join(temp_dir, overlay_filename)
                            
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
                            
                            # 保存原始图像到临时文件
                            temp_input = tempfile.NamedTemporaryFile(suffix='.nii.gz', delete=False)
                            temp_input.close()
                            sitk.WriteImage(params['current_data']['image'], temp_input.name)
                            
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
                            
                            overlay_progress.close()
                            
                            # 询问用户加载哪个结果
                            reply = QtWidgets.QMessageBox.question(
                                self,
                                "分割完成",
                                f"区域生长分割完成！\n\n"
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
                                f"区域生长分割完成！结果已保存到：\n{result_path}\n\n是否加载分割结果？",
                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                            )
                            if reply == QtWidgets.QMessageBox.Yes:
                                self.load_data(result_path)
                    else:
                        # 不使用融合，直接询问是否加载分割结果
                        reply = QtWidgets.QMessageBox.question(
                            self,
                            "分割完成",
                            f"区域生长分割完成！结果已保存到：\n{result_path}\n\n是否加载分割结果？",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                        )
                        
                        if reply == QtWidgets.QMessageBox.Yes:
                            # 加载并显示分割结果
                            self.load_data(result_path)
                        
                except Exception as e:
                    progress.close()
                    import traceback
                    traceback.print_exc()
                    QtWidgets.QMessageBox.critical(
                        self, 
                        "分割错误", 
                        f"执行区域生长分割时出错：{str(e)}\n\n请检查：\n"
                        f"1. 种子点是否正确\n"
                        f"2. 参数设置是否合理\n"
                        f"3. 输入数据是否有效"
                    )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "错误", f"运行区域生长分割时出错：{str(e)}")
    
    def perform_region_growing(self, params):
        """
        执行区域生长算法
        
        参数
        ----
        params : dict
            包含算法参数的字典
        
        返回
        ----
        sitk.Image : 分割结果图像
        """
        # 获取原始图像
        input_image = params['current_data']['image']
        algorithm = params['algorithm']
        seed_points = params['seed_points']
        
        # 转换种子点格式 - 从numpy数组索引(z, y, x)转换为ITK物理坐标
        seed_list = []
        for seed in seed_points:
            # seed是(z, y, x)格式的数组索引
            # ITK期望(x, y, z)格式的索引
            if len(seed) == 3:
                # 转换为ITK索引格式 (x, y, z)
                itk_seed = [int(seed[2]), int(seed[1]), int(seed[0])]
                seed_list.append(itk_seed)
            else:
                print(f"警告：种子点格式不正确: {seed}")
        
        print(f"使用算法: {algorithm}")
        print(f"种子点数量: {len(seed_list)}")
        print(f"种子点: {seed_list}")
        
        # 根据算法类型执行不同的区域生长
        if algorithm == "ConnectedThreshold":
            # 连通阈值区域生长
            seg_filter = sitk.ConnectedThresholdImageFilter()
            seg_filter.SetLower(params['lower_threshold'])
            seg_filter.SetUpper(params['upper_threshold'])
            seg_filter.SetReplaceValue(params['replace_value'])
            seg_filter.SetSeedList(seed_list)
            
            print(f"连通阈值参数: 下阈值={params['lower_threshold']}, 上阈值={params['upper_threshold']}")
            
            result_image = seg_filter.Execute(input_image)
            
        elif algorithm == "ConfidenceConnected":
            # 置信连接区域生长
            seg_filter = sitk.ConfidenceConnectedImageFilter()
            seg_filter.SetMultiplier(params['multiplier'])
            seg_filter.SetNumberOfIterations(params['number_of_iterations'])
            seg_filter.SetReplaceValue(params['replace_value'])
            seg_filter.SetSeedList(seed_list)
            
            print(f"置信连接参数: 倍增因子={params['multiplier']}, 迭代次数={params['number_of_iterations']}")
            
            result_image = seg_filter.Execute(input_image)
            
        elif algorithm == "NeighborhoodConnected":
            # 邻域连接区域生长
            seg_filter = sitk.NeighborhoodConnectedImageFilter()
            seg_filter.SetLower(params['lower_threshold'])
            seg_filter.SetUpper(params['upper_threshold'])
            seg_filter.SetReplaceValue(params['replace_value'])
            seg_filter.SetSeedList(seed_list)
            
            # 设置邻域半径（默认为1）
            radius = [1, 1, 1]
            seg_filter.SetRadius(radius)
            
            print(f"邻域连接参数: 下阈值={params['lower_threshold']}, 上阈值={params['upper_threshold']}, 半径={radius}")
            
            result_image = seg_filter.Execute(input_image)
        else:
            raise ValueError(f"不支持的算法类型: {algorithm}")
        
        print("区域生长执行完成")
        
        return result_image
    
    def add_region_growing_seed_point(self, point):
        """
        添加区域生长的种子点
        
        参数
        ----
        point : tuple or list
            种子点坐标 (z, y, x)
        """
        if not hasattr(self, 'region_growing_seed_points'):
            self.region_growing_seed_points = []
        
        self.region_growing_seed_points.append(point)
        print(f"已添加种子点: {point}，当前共有 {len(self.region_growing_seed_points)} 个种子点")
    
    def clear_region_growing_seed_points(self):
        """清除所有区域生长的种子点"""
        if hasattr(self, 'region_growing_seed_points'):
            self.region_growing_seed_points = []
            print("已清除所有种子点")
        
        # 清除所有视图中的种子点标记
        self._clear_seed_marks_from_all_viewers()
    
    def _clear_seed_marks_from_all_viewers(self):
        """清除所有视图中的种子点标记"""
        for viewer in [getattr(self, 'axial_viewer', None), 
                      getattr(self, 'sag_viewer', None), 
                      getattr(self, 'cor_viewer', None)]:
            if viewer and hasattr(viewer, 'seed_point_marks'):
                for h_line, v_line, circle in viewer.seed_point_marks:
                    try:
                        viewer.scene.removeItem(h_line)
                        viewer.scene.removeItem(v_line)
                        viewer.scene.removeItem(circle)
                    except:
                        pass
                viewer.seed_point_marks = []
    
    def run_otsu_segmentation(self):
        """运行OTSU阈值分割"""
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
            
            # 创建OTSU分割对话框，传递当前数据
            dialog = OtsuSegmentationDialog(self, current_data=current_data)
            
            # 如果用户点击了确定
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                # 获取用户输入的参数
                params = dialog.get_parameters()
                
                # 显示进度对话框
                progress = QtWidgets.QProgressDialog(
                    "正在进行OTSU阈值分割，请稍候...", 
                    "取消", 
                    0, 
                    0, 
                    self
                )
                progress.setWindowTitle("OTSU分割进度")
                progress.setWindowModality(QtCore.Qt.WindowModal)
                progress.setCancelButton(None)  # 禁用取消按钮
                progress.show()
                QtWidgets.QApplication.processEvents()
                
                try:
                    # 执行OTSU阈值分割
                    result_image = self.perform_otsu_segmentation(params)
                    
                    # 如果是多阈值分割，将标签值映射到可见范围
                    if params['use_multi_threshold']:
                        # 获取标签图像的数组
                        label_array = sitk.GetArrayFromImage(result_image)
                        unique_labels = np.unique(label_array)
                        print(f"多阈值分割标签值: {unique_labels}")
                        
                        # 将标签值映射到0, 255, 510, 765...（间隔255）
                        # 这样在灰度图中可以清晰看到不同的标签
                        mapped_array = np.zeros_like(label_array, dtype=np.uint16)
                        for i, label in enumerate(unique_labels):
                            if label > 0:  # 跳过背景
                                mapped_array[label_array == label] = i * 255
                        
                        print(f"标签映射后范围: [{mapped_array.min()}, {mapped_array.max()}]")
                        
                        # 创建新的ITK图像
                        result_image_display = sitk.GetImageFromArray(mapped_array)
                        result_image_display.CopyInformation(result_image)
                        
                        # 保存映射后的结果用于显示
                        temp_dir = tempfile.gettempdir()
                        result_filename = "otsu_segmentation_result.nii.gz"
                        result_path = os.path.join(temp_dir, result_filename)
                        sitk.WriteImage(result_image_display, result_path)
                        
                        # 同时保存原始标签图像（用于融合）
                        label_filename = "otsu_segmentation_labels.nii.gz"
                        label_path = os.path.join(temp_dir, label_filename)
                        sitk.WriteImage(result_image, label_path)
                        
                        # 更新result_image为原始标签图像，用于后续融合
                        result_image_for_overlay = label_path
                    else:
                        # 单阈值分割，正常保存
                        temp_dir = tempfile.gettempdir()
                        result_filename = "otsu_segmentation_result.nii.gz"
                        result_path = os.path.join(temp_dir, result_filename)
                        sitk.WriteImage(result_image, result_path)
                        result_image_for_overlay = result_path
                    
                    progress.close()
                    
                    # 显示计算得到的阈值信息
                    threshold_info = ""
                    if self.last_otsu_threshold is not None:
                        if isinstance(self.last_otsu_threshold, (list, tuple)):
                            threshold_info = f"\n计算得到的阈值: {[f'{t:.2f}' for t in self.last_otsu_threshold]}"
                        else:
                            threshold_info = f"\n计算得到的阈值: {self.last_otsu_threshold:.2f}"
                    
                    # 如果选择了融合显示，创建融合图像
                    if params['overlay_with_original']:
                        try:
                            # 创建融合图像
                            overlay_filename = "otsu_segmentation_overlay.nii.gz"
                            overlay_path = os.path.join(temp_dir, overlay_filename)
                            
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
                            
                            # 保存原始图像到临时文件
                            temp_input = tempfile.NamedTemporaryFile(suffix='.nii.gz', delete=False)
                            temp_input.close()
                            sitk.WriteImage(params['current_data']['image'], temp_input.name)
                            
                            # 根据是否为多阈值选择融合方式
                            if params['use_multi_threshold']:
                                # 多阈值：使用多颜色融合（使用原始标签图像）
                                create_multi_label_overlay_from_files(
                                    temp_input.name,
                                    result_image_for_overlay,  # 使用原始标签图像
                                    overlay_path,
                                    color_map=None,  # 使用默认颜色方案
                                    alpha=params['overlay_alpha']
                                )
                            else:
                                # 单阈值：使用单颜色融合
                                create_overlay_from_files(
                                    temp_input.name,
                                    result_image_for_overlay,
                                    overlay_path,
                                    color=params['overlay_color'],
                                    alpha=params['overlay_alpha']
                                )
                            
                            # 删除临时文件
                            os.unlink(temp_input.name)
                            
                            overlay_progress.close()
                            
                            # 询问用户加载哪个结果
                            reply = QtWidgets.QMessageBox.question(
                                self,
                                "分割完成",
                                f"OTSU阈值分割完成！{threshold_info}\n\n"
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
                                f"OTSU阈值分割完成！{threshold_info}\n\n"
                                f"结果已保存到：\n{result_path}\n\n是否加载分割结果？",
                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                            )
                            if reply == QtWidgets.QMessageBox.Yes:
                                self.load_data(result_path)
                    else:
                        # 不使用融合，直接询问是否加载分割结果
                        reply = QtWidgets.QMessageBox.question(
                            self,
                            "分割完成",
                            f"OTSU阈值分割完成！{threshold_info}\n\n"
                            f"结果已保存到：\n{result_path}\n\n是否加载分割结果？",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                        )
                        
                        if reply == QtWidgets.QMessageBox.Yes:
                            # 加载并显示分割结果
                            self.load_data(result_path)
                        
                except Exception as e:
                    progress.close()
                    import traceback
                    traceback.print_exc()
                    QtWidgets.QMessageBox.critical(
                        self, 
                        "分割错误", 
                        f"执行OTSU阈值分割时出错：{str(e)}\n\n请检查：\n"
                        f"1. 输入数据是否有效\n"
                        f"2. 参数设置是否合理\n"
                        f"3. 图像是否适合OTSU分割（需要有明显的前景和背景）"
                    )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "错误", f"运行OTSU阈值分割时出错：{str(e)}")
    
    def perform_otsu_segmentation(self, params):
        """
        执行OTSU阈值分割
        
        参数
        ----
        params : dict
            包含算法参数的字典
        
        返回
        ----
        sitk.Image : 分割结果图像
        """
        # 获取原始图像
        input_image = params['current_data']['image']
        
        print(f"OTSU分割参数:")
        print(f"  直方图bins: {params['number_of_histogram_bins']}")
        print(f"  掩码输出: {params['mask_output']}")
        print(f"  多阈值: {params['use_multi_threshold']}")
        
        if params['use_multi_threshold']:
            # 多阈值OTSU分割
            otsu_filter = sitk.OtsuMultipleThresholdsImageFilter()
            otsu_filter.SetNumberOfHistogramBins(params['number_of_histogram_bins'])
            otsu_filter.SetNumberOfThresholds(params['num_thresholds'])
            
            # 执行分割
            result_image = otsu_filter.Execute(input_image)
            
            # 获取计算的阈值
            thresholds = otsu_filter.GetThresholds()
            self.last_otsu_threshold = list(thresholds)
            print(f"  计算得到的阈值: {self.last_otsu_threshold}")
            
            # 如果需要掩码输出且不需要融合显示，将标签图像转换为二值掩码
            # 如果需要融合显示，保留标签图像以便使用多颜色显示
            if params['mask_output'] and not params['overlay_with_original']:
                # 只在不需要融合显示时才转换为二值掩码
                threshold_filter = sitk.BinaryThresholdImageFilter()
                threshold_filter.SetLowerThreshold(1)
                threshold_filter.SetUpperThreshold(params['num_thresholds'])
                threshold_filter.SetInsideValue(params['inside_value'])
                threshold_filter.SetOutsideValue(params['outside_value'])
                result_image = threshold_filter.Execute(result_image)
            else:
                # 保留标签图像（0, 1, 2, 3...）用于多颜色融合显示
                print(f"  保留多标签图像用于多颜色融合显示")
        else:
            # 单阈值OTSU分割
            otsu_filter = sitk.OtsuThresholdImageFilter()
            otsu_filter.SetNumberOfHistogramBins(params['number_of_histogram_bins'])
            
            if params['mask_output']:
                # 输出二值掩码
                otsu_filter.SetInsideValue(params['inside_value'])
                otsu_filter.SetOutsideValue(params['outside_value'])
            
            # 执行分割
            result_image = otsu_filter.Execute(input_image)
            
            # 获取计算的阈值
            threshold = otsu_filter.GetThreshold()
            self.last_otsu_threshold = threshold
            print(f"  计算得到的阈值: {threshold:.2f}")
        
        print("OTSU分割执行完成")
        
        return result_image

