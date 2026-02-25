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
from Traditional.Segmentation.threshold_segmentation_dialog import ThresholdSegmentationDialog
from Traditional.Segmentation.ml_segmentation_dialog import MLSegmentationDialog
from AISegmeant.image_overlay import create_overlay_from_files, create_multi_label_overlay_from_files


class TraditionalSegmentationOperations:
    """传统分割操作类，作为Mixin使用"""
    
    def __init__(self):
        """初始化"""
        self.region_growing_seed_points = []  # 存储种子点
        self.last_otsu_threshold = None  # 存储上次OTSU计算的阈值
        self._region_growing_dialog = None  # 区域生长对话框引用
    
    def run_region_growing(self):
        """运行区域生长分割"""
        try:
            # 检查是否有 SimpleITK 图像（区域生长需要 SimpleITK Image）
            if not hasattr(self, 'image') or self.image is None:
                QtWidgets.QMessageBox.warning(
                    self,
                    "数据不可用",
                    "当前没有可用的 SimpleITK 图像数据。\n\n"
                    "可能的原因：\n"
                    "• 尚未加载任何数据\n"
                    "• 当前显示的是投影结果等派生数据\n\n"
                    "请先加载原始 CT 数据再执行区域生长。"
                )
                return
            
            # 准备当前数据
            current_data = None
            if hasattr(self, 'array') and self.array is not None:
                current_data = {
                    'image': self.image,
                    'array': self.array,
                    'spacing': self.spacing if hasattr(self, 'spacing') else (1.0, 1.0, 1.0)
                }
            
            # 创建区域生长对话框，传递当前数据
            dialog = RegionGrowingDialog(self, current_data=current_data)
            
            # 保存对话框引用，以便 slice_viewer 实时更新种子点
            self._region_growing_dialog = dialog
            
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
            
            # 对话框关闭后清除引用
            self._region_growing_dialog = None
            
        except Exception as e:
            self._region_growing_dialog = None
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
        
        # 转换种子点格式 - 从numpy数组索引(z, y, x)转换为SimpleITK索引(x, y, z)
        # 注意：SimpleITK的SetSeedList()接受的是索引坐标（index），不是物理坐标
        seed_list = []
        for seed in seed_points:
            # seed是(z, y, x)格式的numpy数组索引
            # SimpleITK期望(x, y, z)格式的索引
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
                for mark in viewer.seed_point_marks:
                    try:
                        items = mark[:3]  # h_line, v_line, circle
                        for item in items:
                            viewer.scene.removeItem(item)
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

    # ====================================================================
    # 阈值分割
    # ====================================================================
    def run_threshold_segmentation(self):
        """运行手动阈值分割"""
        try:
            # 检查数据
            if not hasattr(self, 'array') or self.array is None:
                QtWidgets.QMessageBox.warning(
                    self,
                    "数据不可用",
                    "当前没有可用的图像数据。\n请先加载 CT 数据再执行阈值分割。"
                )
                return

            current_data = {
                'image': self.image if hasattr(self, 'image') else None,
                'array': self.array,
                'spacing': self.spacing if hasattr(self, 'spacing') else (1.0, 1.0, 1.0),
            }

            dialog = ThresholdSegmentationDialog(self, current_data=current_data)

            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                return

            params = dialog.get_parameters()

            # 进度提示
            progress = QtWidgets.QProgressDialog(
                "正在进行阈值分割，请稍候...", None, 0, 0, self)
            progress.setWindowTitle("阈值分割")
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.show()
            QtWidgets.QApplication.processEvents()

            try:
                result_image = self.perform_threshold_segmentation(params)

                # 保存结果
                temp_dir = tempfile.gettempdir()
                result_path = os.path.join(temp_dir, "threshold_seg_result.nii.gz")
                sitk.WriteImage(result_image, result_path)

                progress.close()

                if params['overlay_with_original'] and current_data.get('image') is not None:
                    try:
                        overlay_path = os.path.join(temp_dir, "threshold_seg_overlay.nii.gz")
                        overlay_progress = QtWidgets.QProgressDialog(
                            "正在创建融合图像...", None, 0, 0, self)
                        overlay_progress.setWindowTitle("图像融合")
                        overlay_progress.setWindowModality(QtCore.Qt.WindowModal)
                        overlay_progress.show()
                        QtWidgets.QApplication.processEvents()

                        temp_input = tempfile.NamedTemporaryFile(suffix='.nii.gz', delete=False)
                        temp_input.close()
                        sitk.WriteImage(current_data['image'], temp_input.name)

                        create_overlay_from_files(
                            temp_input.name,
                            result_path,
                            overlay_path,
                            color=params['overlay_color'],
                            alpha=params['overlay_alpha'],
                        )
                        os.unlink(temp_input.name)
                        overlay_progress.close()

                        reply = QtWidgets.QMessageBox.question(
                            self,
                            "分割完成",
                            f"阈值分割完成！\n\n"
                            f"• 分割结果: {result_path}\n"
                            f"• 融合图像: {overlay_path}\n\n"
                            f"选择要加载的图像：\n"
                            f"- 是(Y)：加载融合图像（推荐）\n"
                            f"- 否(N)：加载纯分割结果",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel,
                        )
                        if reply == QtWidgets.QMessageBox.Yes:
                            self.load_data(overlay_path)
                        elif reply == QtWidgets.QMessageBox.No:
                            self.load_data(result_path)
                    except Exception as e:
                        QtWidgets.QMessageBox.warning(
                            self, "融合警告",
                            f"创建融合图像时出错：{str(e)}\n\n将显示纯分割结果")
                        reply = QtWidgets.QMessageBox.question(
                            self, "分割完成",
                            f"阈值分割完成！\n结果已保存到：\n{result_path}\n\n是否加载？",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                        if reply == QtWidgets.QMessageBox.Yes:
                            self.load_data(result_path)
                else:
                    reply = QtWidgets.QMessageBox.question(
                        self, "分割完成",
                        f"阈值分割完成！\n结果已保存到：\n{result_path}\n\n是否加载分割结果？",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                    if reply == QtWidgets.QMessageBox.Yes:
                        self.load_data(result_path)

            except Exception as e:
                progress.close()
                import traceback
                traceback.print_exc()
                QtWidgets.QMessageBox.critical(
                    self, "分割错误",
                    f"执行阈值分割时出错：{str(e)}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "错误", f"运行阈值分割时出错：{str(e)}")

    def perform_threshold_segmentation(self, params):
        """
        执行阈值分割（基于 numpy 矢量化操作，高效）

        参数
        ----
        params : dict
            包含 lower_threshold, upper_threshold, foreground_value, background_value, current_data

        返回
        ----
        sitk.Image : 二值分割结果
        """
        array = params['current_data']['array']
        lower = params['lower_threshold']
        upper = params['upper_threshold']
        fg = params['foreground_value']
        bg = params['background_value']

        print(f"阈值分割: 模式={params['mode']}, 范围=[{lower:.1f}, {upper:.1f}], 前景={fg}, 背景={bg}")

        # numpy 矢量化操作 — 整个 3D 体数据一步完成
        mask = (array >= lower) & (array <= upper)
        result_array = np.where(mask, fg, bg).astype(np.uint16)

        selected = int(mask.sum())
        print(f"阈值分割完成: 选中体素 {selected:,} / {array.size:,} ({selected/array.size*100:.2f}%)")

        # 转换为 SimpleITK Image 以保留空间信息
        result_image = sitk.GetImageFromArray(result_array)

        # 如果有原始 SimpleITK 图像，拷贝空间信息
        src_image = params['current_data'].get('image')
        if src_image is not None:
            result_image.CopyInformation(src_image)

        return result_image

    # ====================================================================
    # 机器学习分割（KNN + 集成方法）
    # ====================================================================
    def run_ml_segmentation(self):
        """运行机器学习分割"""
        try:
            current_data = None
            if hasattr(self, 'array') and self.array is not None:
                current_data = {
                    'image': self.image if hasattr(self, 'image') else None,
                    'array': self.array,
                    'spacing': self.spacing if hasattr(self, 'spacing') else (1.0, 1.0, 1.0),
                }

            dialog = MLSegmentationDialog(self, current_data=current_data)
            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                return

            params = dialog.get_parameters()

            progress = QtWidgets.QProgressDialog(
                "正在进行机器学习分割，请稍候...",
                None,
                0,
                0,
                self,
            )
            progress.setWindowTitle("机器学习分割")
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.show()
            QtWidgets.QApplication.processEvents()

            try:
                result_image, result_stats = self.perform_ml_segmentation(params)

                output_dir = params['output_dir'] if params['output_dir'] else tempfile.gettempdir()
                os.makedirs(output_dir, exist_ok=True)
                result_path = os.path.join(output_dir, "ml_segmentation_result.nii.gz")
                sitk.WriteImage(result_image, result_path)

                progress.close()

                summary_text = (
                    f"算法: {params['algorithm']}\n"
                    f"训练范围: {'仅标注切片' if params.get('train_scope') == 'annotated_slices' else '全三维'}\n"
                    f"推理范围: {('按切片方向全部切片' if params.get('predict_scope') == 'directional_slices' else ('仅标注切片' if params.get('predict_scope') == 'annotated_slices' else '全三维'))}\n"
                    f"类别数: {result_stats['num_classes']}\n"
                    f"前景体素占比: {result_stats['foreground_ratio']:.2f}%"
                )

                if params['overlay_with_original'] and result_stats['can_overlay']:
                    try:
                        overlay_progress = QtWidgets.QProgressDialog(
                            "正在创建融合图像...",
                            None,
                            0,
                            0,
                            self,
                        )
                        overlay_progress.setWindowTitle("图像融合")
                        overlay_progress.setWindowModality(QtCore.Qt.WindowModal)
                        overlay_progress.show()
                        QtWidgets.QApplication.processEvents()

                        overlay_path = os.path.join(output_dir, "ml_segmentation_overlay.nii.gz")
                        temp_input = tempfile.NamedTemporaryFile(suffix='.nii.gz', delete=False)
                        temp_input.close()
                        sitk.WriteImage(result_stats['source_image'], temp_input.name)

                        if result_stats['num_classes'] > 2:
                            create_multi_label_overlay_from_files(
                                temp_input.name,
                                result_path,
                                overlay_path,
                                color_map=None,
                                alpha=params['overlay_alpha'],
                            )
                        else:
                            create_overlay_from_files(
                                temp_input.name,
                                result_path,
                                overlay_path,
                                color=params['overlay_color'],
                                alpha=params['overlay_alpha'],
                            )

                        os.unlink(temp_input.name)
                        overlay_progress.close()

                        reply = QtWidgets.QMessageBox.question(
                            self,
                            "分割完成",
                            f"机器学习分割完成！\n\n{summary_text}\n\n"
                            f"• 分割结果: {result_path}\n"
                            f"• 融合图像: {overlay_path}\n\n"
                            f"选择要加载的图像：\n"
                            f"- 是(Y)：加载融合图像（推荐）\n"
                            f"- 否(N)：加载纯分割结果",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel,
                        )
                        if reply == QtWidgets.QMessageBox.Yes:
                            self.load_data(overlay_path)
                        elif reply == QtWidgets.QMessageBox.No:
                            self.load_data(result_path)
                    except Exception as e:
                        QtWidgets.QMessageBox.warning(
                            self,
                            "融合警告",
                            f"创建融合图像时出错：{str(e)}\n\n将显示纯分割结果",
                        )
                        reply = QtWidgets.QMessageBox.question(
                            self,
                            "分割完成",
                            f"机器学习分割完成！\n\n{summary_text}\n\n"
                            f"结果已保存到：\n{result_path}\n\n是否加载分割结果？",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                        )
                        if reply == QtWidgets.QMessageBox.Yes:
                            self.load_data(result_path)
                else:
                    reply = QtWidgets.QMessageBox.question(
                        self,
                        "分割完成",
                        f"机器学习分割完成！\n\n{summary_text}\n\n"
                        f"结果已保存到：\n{result_path}\n\n是否加载分割结果？",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    )
                    if reply == QtWidgets.QMessageBox.Yes:
                        self.load_data(result_path)

            except Exception as e:
                progress.close()
                import traceback
                traceback.print_exc()
                QtWidgets.QMessageBox.critical(
                    self,
                    "分割错误",
                    f"执行机器学习分割时出错：{str(e)}\n\n"
                    f"请检查：\n"
                    f"1. 是否安装 scikit-learn\n"
                    f"2. 标签文件与输入影像尺寸是否一致\n"
                    f"3. 标签值是否合理（建议0为背景，1..N为类别）",
                )

        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "错误", f"运行机器学习分割时出错：{str(e)}")

    def perform_ml_segmentation(self, params):
        """执行机器学习分割"""
        try:
            from sklearn.neighbors import KNeighborsClassifier
            from sklearn.ensemble import (
                AdaBoostClassifier,
                BaggingClassifier,
                ExtraTreesClassifier,
                GradientBoostingClassifier,
                RandomForestClassifier,
            )
            from sklearn.tree import DecisionTreeClassifier
        except Exception as e:
            raise RuntimeError(f"导入scikit-learn失败：{str(e)}")

        if params['use_current_data']:
            source_array = params['current_data']['array']
            source_image = params['current_data'].get('image')
        else:
            input_img = sitk.ReadImage(params['input_file'])
            source_array = sitk.GetArrayFromImage(input_img)
            source_image = input_img

        label_img = sitk.ReadImage(params['label_file'])
        label_array = sitk.GetArrayFromImage(label_img)

        if source_array.shape != label_array.shape:
            raise ValueError(
                f"输入影像与标签尺寸不一致：{source_array.shape} vs {label_array.shape}"
            )

        source_array = source_array.astype(np.float32)
        label_array = label_array.astype(np.int32)

        train_scope = params.get('train_scope', 'annotated_slices')
        predict_scope = params.get('predict_scope', 'directional_slices')
        predict_view_type = params.get('predict_view_type', 'axial')

        view_axis_map = {
            'axial': 0,
            'coronal': 1,
            'sagittal': 2,
        }

        def _build_slice_scope_mask(base_mask, axis):
            mask = np.zeros_like(base_mask, dtype=bool)
            if axis == 0:
                annotated = np.any(base_mask, axis=(1, 2))
                mask[annotated, :, :] = True
            elif axis == 1:
                annotated = np.any(base_mask, axis=(0, 2))
                mask[:, annotated, :] = True
            else:
                annotated = np.any(base_mask, axis=(0, 1))
                mask[:, :, annotated] = True
            return mask

        drawn_mask = None
        label_dataset_info = params.get('label_dataset_info')
        annotation_view_type = predict_view_type
        if isinstance(label_dataset_info, dict):
            ds_drawn_mask = label_dataset_info.get('annotation_drawn_mask', None)
            if ds_drawn_mask is not None:
                ds_drawn_mask = np.asarray(ds_drawn_mask, dtype=bool)
                if ds_drawn_mask.shape == source_array.shape:
                    drawn_mask = ds_drawn_mask
            ds_view_type = label_dataset_info.get('annotation_view_type', None)
            if ds_view_type in view_axis_map:
                annotation_view_type = ds_view_type

        if annotation_view_type not in view_axis_map:
            annotation_view_type = 'axial'
        direction_axis = view_axis_map[annotation_view_type]

        fallback_label_mask = label_array != 0
        if drawn_mask is not None:
            annotation_scope_mask = drawn_mask
        else:
            annotation_scope_mask = _build_slice_scope_mask(fallback_label_mask, direction_axis)

        full_scope_mask = np.ones_like(annotation_scope_mask, dtype=bool)
        train_scope_mask = annotation_scope_mask if train_scope == 'annotated_slices' else full_scope_mask
        if predict_scope == 'annotated_slices':
            predict_scope_mask = annotation_scope_mask
        elif predict_scope == 'directional_slices':
            predict_scope_mask = _build_slice_scope_mask(np.ones_like(annotation_scope_mask, dtype=bool), direction_axis)
        else:
            predict_scope_mask = full_scope_mask

        flat_intensity = source_array.reshape(-1)
        if flat_intensity.max() > flat_intensity.min():
            flat_intensity = (flat_intensity - flat_intensity.min()) / (flat_intensity.max() - flat_intensity.min())
        else:
            flat_intensity = np.zeros_like(flat_intensity, dtype=np.float32)

        feature_list = [flat_intensity.reshape(-1, 1)]
        if params['use_coordinates']:
            z, y, x = source_array.shape
            zz, yy, xx = np.indices((z, y, x), dtype=np.float32)
            if z > 1:
                zz /= (z - 1)
            if y > 1:
                yy /= (y - 1)
            if x > 1:
                xx /= (x - 1)
            coords = np.stack([zz.reshape(-1), yy.reshape(-1), xx.reshape(-1)], axis=1)
            feature_list.append(coords)

        feature_matrix = np.concatenate(feature_list, axis=1)
        labels = label_array.reshape(-1)
        train_scope_mask_flat = train_scope_mask.reshape(-1)
        predict_scope_mask_flat = predict_scope_mask.reshape(-1)

        if params['ignore_background']:
            train_label_mask = labels > 0
        else:
            train_label_mask = labels >= 0

        train_mask = train_scope_mask_flat & train_label_mask

        train_indices = np.flatnonzero(train_mask)
        if train_indices.size < 100:
            raise ValueError("可用训练样本过少（<100），请检查标签文件")

        if train_indices.size > params['max_train_samples']:
            rng = np.random.default_rng(42)
            sampled_indices = []
            selected_labels = labels[train_indices]
            unique_classes = np.unique(selected_labels)
            for class_id in unique_classes:
                class_indices = train_indices[selected_labels == class_id]
                class_quota = max(1, int(params['max_train_samples'] * (class_indices.size / train_indices.size)))
                if class_indices.size > class_quota:
                    class_indices = rng.choice(class_indices, size=class_quota, replace=False)
                sampled_indices.append(class_indices)
            train_indices = np.concatenate(sampled_indices)

        x_train = feature_matrix[train_indices]
        y_train = labels[train_indices]

        algorithm = params['algorithm']
        max_depth = params['max_depth']

        if algorithm == "K-Nearest":
            classifier = KNeighborsClassifier(
                n_neighbors=params['k_neighbors'],
                weights='distance',
                n_jobs=-1,
            )
        elif algorithm == "AdaBoost":
            classifier = AdaBoostClassifier(
                n_estimators=params['n_estimators'],
                random_state=42,
            )
        elif algorithm == "Bagging":
            classifier = BaggingClassifier(
                estimator=DecisionTreeClassifier(max_depth=max_depth, random_state=42),
                n_estimators=params['n_estimators'],
                random_state=42,
                n_jobs=-1,
            )
        elif algorithm == "Extra Trees":
            classifier = ExtraTreesClassifier(
                n_estimators=params['n_estimators'],
                max_depth=max_depth,
                random_state=42,
                n_jobs=-1,
                class_weight='balanced',
            )
        elif algorithm == "Gradient Boosting":
            classifier = GradientBoostingClassifier(
                n_estimators=params['n_estimators'],
                learning_rate=params['learning_rate'],
                max_depth=max_depth if max_depth is not None else 3,
                random_state=42,
            )
        elif algorithm == "Random Forest":
            classifier = RandomForestClassifier(
                n_estimators=params['n_estimators'],
                max_depth=max_depth,
                random_state=42,
                n_jobs=-1,
                class_weight='balanced',
            )
        else:
            raise ValueError(f"不支持的机器学习算法：{algorithm}")

        classifier.fit(x_train, y_train)

        batch_size = params['predict_batch_size']
        pred = np.zeros(feature_matrix.shape[0], dtype=np.int32)
        if predict_scope == 'directional_slices':
            z, y, x = source_array.shape
            feat_dim = feature_matrix.shape[1]
            feature_volume = feature_matrix.reshape(z, y, x, feat_dim)
            pred_volume = pred.reshape(z, y, x)
            if direction_axis == 0:
                num_slices = z
                for slice_idx in range(num_slices):
                    slice_feat = feature_volume[slice_idx, :, :, :].reshape(-1, feat_dim)
                    slice_pred = np.zeros(slice_feat.shape[0], dtype=np.int32)
                    for start in range(0, slice_feat.shape[0], batch_size):
                        end = min(start + batch_size, slice_feat.shape[0])
                        slice_pred[start:end] = classifier.predict(slice_feat[start:end])
                    pred_volume[slice_idx, :, :] = slice_pred.reshape(y, x)
            elif direction_axis == 1:
                num_slices = y
                for slice_idx in range(num_slices):
                    slice_feat = feature_volume[:, slice_idx, :, :].reshape(-1, feat_dim)
                    slice_pred = np.zeros(slice_feat.shape[0], dtype=np.int32)
                    for start in range(0, slice_feat.shape[0], batch_size):
                        end = min(start + batch_size, slice_feat.shape[0])
                        slice_pred[start:end] = classifier.predict(slice_feat[start:end])
                    pred_volume[:, slice_idx, :] = slice_pred.reshape(z, x)
            else:
                num_slices = x
                for slice_idx in range(num_slices):
                    slice_feat = feature_volume[:, :, slice_idx, :].reshape(-1, feat_dim)
                    slice_pred = np.zeros(slice_feat.shape[0], dtype=np.int32)
                    for start in range(0, slice_feat.shape[0], batch_size):
                        end = min(start + batch_size, slice_feat.shape[0])
                        slice_pred[start:end] = classifier.predict(slice_feat[start:end])
                    pred_volume[:, :, slice_idx] = slice_pred.reshape(z, y)
        else:
            predict_indices = np.flatnonzero(predict_scope_mask_flat)
            if predict_indices.size == 0:
                raise ValueError("推理范围内没有可用体素，请检查标签覆盖范围")

            for start in range(0, predict_indices.size, batch_size):
                end = min(start + batch_size, predict_indices.size)
                batch_indices = predict_indices[start:end]
                pred[batch_indices] = classifier.predict(feature_matrix[batch_indices])

        pred_array = pred.reshape(source_array.shape).astype(np.uint16)

        result_image = sitk.GetImageFromArray(pred_array)
        if source_image is not None:
            result_image.CopyInformation(source_image)
        else:
            result_image.CopyInformation(label_img)

        unique_pred = np.unique(pred_array)
        foreground_ratio = 100.0 * float(np.count_nonzero(pred_array > 0)) / float(pred_array.size)
        result_stats = {
            'num_classes': int(unique_pred.size),
            'foreground_ratio': foreground_ratio,
            'can_overlay': source_image is not None,
            'source_image': source_image,
        }

        return result_image, result_stats

    def run_label_file_creator(self):
        """菜单入口：交互式创建标签文件"""
        path = self.create_label_file_interactive()
        if path:
            QtWidgets.QMessageBox.information(
                self,
                "标签创建完成",
                f"标签文件已创建：\n{path}",
            )

    def create_label_file_interactive(self, input_file=None, suggested_output_path=None):
        """通过手工标注交互创建标签文件，并返回输出路径（失败/取消返回None）"""
        if hasattr(self, 'create_label_file_from_annotation'):
            return self.create_label_file_from_annotation(suggested_output_path=suggested_output_path)

        QtWidgets.QMessageBox.warning(
            self,
            "功能不可用",
            "当前界面未启用手工标注导出能力，请先在主界面标注后再保存标签。",
        )
        return None

