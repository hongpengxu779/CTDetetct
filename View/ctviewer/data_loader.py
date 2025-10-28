"""
数据加载和管理功能
负责加载CT数据、重建数据等
"""

import os
import numpy as np
import SimpleITK as sitk
from PyQt5 import QtWidgets, QtCore

from File.readData import CTImageData
from ..viewers import SliceViewer, VolumeViewer


class DataLoader:
    """数据加载和管理类，作为Mixin使用"""
    
    def import_file(self):
        """导入文件对话框"""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 
            "选择医学影像文件", 
            "", 
            "医学影像文件 (*.nii *.nii.gz *.mhd *.dcm *.raw);;所有文件 (*)"
        )
        
        if filename:
            # 如果选择了.raw文件，则需要询问维度
            if filename.endswith('.raw'):
                dialog = QtWidgets.QDialog(self)
                dialog.setWindowTitle("输入RAW文件维度")
                
                form_layout = QtWidgets.QFormLayout(dialog)
                
                z_input = QtWidgets.QSpinBox()
                z_input.setRange(1, 2000)
                z_input.setValue(512)
                form_layout.addRow("Z 维度:", z_input)
                
                y_input = QtWidgets.QSpinBox()
                y_input.setRange(1, 2000)
                y_input.setValue(512)
                form_layout.addRow("Y 维度:", y_input)
                
                x_input = QtWidgets.QSpinBox()
                x_input.setRange(1, 2000)
                x_input.setValue(512)
                form_layout.addRow("X 维度:", x_input)
                
                button_box = QtWidgets.QDialogButtonBox(
                    QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
                )
                button_box.accepted.connect(dialog.accept)
                button_box.rejected.connect(dialog.reject)
                form_layout.addRow(button_box)
                
                if dialog.exec_() == QtWidgets.QDialog.Accepted:
                    shape = (z_input.value(), y_input.value(), x_input.value())
                    self.load_data(filename, shape)
            else:
                # 对于其他格式，直接加载
                self.load_data(filename)
    
    def load_data(self, filename, shape=None, spacing=None, dtype=np.uint16):
        """加载CT数据并更新视图"""
        try:
            # 清除旧的视图组件
            self.clear_viewers()
            
            # 读取CT数据
            CTdata = CTImageData(filename, shape, spacing)
            self.image = CTdata.image
            self.array = CTdata.array
            
            # 检查数据类型并获取尺寸
            original_dtype = self.array.dtype
            print(f"原始数据类型: {original_dtype}, 形状: {self.array.shape}")
            
            # 检查是否为RGB图像
            is_rgb = False
            
            if len(self.array.shape) == 4:
                # 检查是否为 (Z, Y, X, 3/4) 格式
                if self.array.shape[3] in [3, 4]:
                    is_rgb = True
                    print(f"检测到RGB图像（通道在最后）: {self.array.shape}")
                    self.rgb_array = self.array.copy()
                    self.depth_z, self.depth_y, self.depth_x = self.array.shape[:3]
                # 检查是否为 (3/4, Z, Y, X) 格式（NIfTI常见格式）
                elif self.array.shape[0] in [3, 4]:
                    is_rgb = True
                    print(f"检测到RGB图像（通道在最前）: {self.array.shape}")
                    # 需要转置维度: (C, Z, Y, X) -> (Z, Y, X, C)
                    self.rgb_array = np.transpose(self.array, (1, 2, 3, 0))
                    print(f"转置后形状: {self.rgb_array.shape}")
                    self.depth_z, self.depth_y, self.depth_x = self.rgb_array.shape[:3]
                else:
                    # 其他4D格式，按普通3D处理
                    is_rgb = False
                    self.depth_z, self.depth_y, self.depth_x = self.array.shape[:3]
            else:
                # 3D或其他维度
                is_rgb = False
                if len(self.array.shape) == 3:
                    self.depth_z, self.depth_y, self.depth_x = self.array.shape
            
            # 获取spacing，确保只有3个值（x, y, z）
            spacing_raw = self.image.GetSpacing()
            if len(spacing_raw) > 3:
                # RGB图像可能有4个spacing值，只取前3个（忽略颜色通道）
                self.spacing = spacing_raw[:3]
                print(f"Spacing从{len(spacing_raw)}维调整为3维: {self.spacing}")
            else:
                self.spacing = spacing_raw
            
            if is_rgb:
                print(f"RGB数组形状: {self.rgb_array.shape}")
                print(f"数据尺寸: Z={self.depth_z}, Y={self.depth_y}, X={self.depth_x}")
                print(f"Spacing: {self.spacing}")
                
                # 为了3D显示，将RGB转换为灰度
                if self.rgb_array.shape[3] >= 3:
                    gray = (0.299 * self.rgb_array[:,:,:,0] + 
                           0.587 * self.rgb_array[:,:,:,1] + 
                           0.114 * self.rgb_array[:,:,:,2])
                    # 转换为uint16以供VolumeViewer使用
                    if self.rgb_array.dtype == np.uint8:
                        self.array = (gray.astype(np.float32) * 257).astype(np.uint16)
                    else:
                        self.array = gray.astype(np.uint16)
                    print(f"RGB已转换为灰度用于3D显示，范围: [{self.array.min()}, {self.array.max()}]")
            else:
                # 非RGB图像，保持原有逻辑
                self.rgb_array = None
                
                if self.array.dtype == np.uint8:
                    # 将uint8转换为uint16，扩展到完整范围
                    print("检测到uint8数据，转换为uint16以便3D显示")
                    self.array = (self.array.astype(np.float32) * 257).astype(np.uint16)
                elif self.array.dtype != np.uint16:
                    # 其他类型也转换为uint16
                    print(f"转换数据类型 {self.array.dtype} -> uint16")
                    data_min = self.array.min()
                    data_max = self.array.max()
                    if data_max > data_min:
                        self.array = ((self.array - data_min) / (data_max - data_min) * 65535).astype(np.uint16)
                    else:
                        self.array = self.array.astype(np.uint16)
            
            # 检查数据范围，判断是否为分割结果
            data_min = float(self.array.min())
            data_max = float(self.array.max())
            print(f"转换后数据范围: [{data_min}, {data_max}]")
            
            # 设置raw_array用于ROI 3D预览（必须在创建视图之前！）
            self.raw_array = self.array
            print(f"raw_array已设置，形状: {self.raw_array.shape}")
            
            # 如果数据范围很小或全为0，可能是分割结果且没有检测到目标
            if data_max == 0 or (data_max - data_min) < 1:
                QtWidgets.QMessageBox.warning(
                    self,
                    "数据警告",
                    f"加载的数据范围异常: [{data_min}, {data_max}]\n\n"
                    "这可能是分割结果但未检测到任何目标区域。\n"
                    "建议检查：\n"
                    "1. 输入数据是否正确\n"
                    "2. 模型权重是否匹配\n"
                    "3. 分割阈值是否需要调整"
                )
            
            # 创建三个方向的切片视图
            if hasattr(self, 'rgb_array') and self.rgb_array is not None:
                # RGB图像的切片获取
                self.axial_viewer = SliceViewer("Axial (彩色)",
                                          lambda z: self.rgb_array[z, :, :, :],
                                          self.depth_z)
                self.sag_viewer = SliceViewer("Sagittal (彩色)",
                                        lambda x: self.rgb_array[:, :, x, :],
                                        self.depth_x)
                self.cor_viewer = SliceViewer("Coronal (彩色)",
                                        lambda y: self.rgb_array[:, y, :, :],
                                        self.depth_y)
            else:
                # 灰度图像的切片获取
                self.axial_viewer = SliceViewer("Axial",
                                          lambda z: self.array[z, :, :],
                                          self.depth_z)
                self.sag_viewer = SliceViewer("Sagittal",
                                        lambda x: self.array[:, :, x],
                                        self.depth_x)
                self.cor_viewer = SliceViewer("Coronal",
                                        lambda y: self.array[:, y, :],
                                        self.depth_y)
            
            # 更新ROI Z范围滑动条
            if hasattr(self, 'roi_z_min_slider'):
                self.roi_z_min_slider.setMaximum(self.depth_z - 1)
                self.roi_z_max_slider.setMaximum(self.depth_z - 1)
                self.roi_z_max_slider.setValue(min(50, self.depth_z - 1))  # 默认范围设为50层或最大值
                
                print(f"ROI Z范围滑动条已更新: 0 - {self.depth_z - 1}")
            
            # 更新ROI X范围滑动条
            if hasattr(self, 'roi_x_min_slider'):
                self.roi_x_min_slider.setMaximum(self.depth_x - 1)
                self.roi_x_max_slider.setMaximum(self.depth_x - 1)
                self.roi_x_max_slider.setValue(self.depth_x - 1)  # 默认设为最大值
                
                print(f"ROI X范围滑动条已更新: 0 - {self.depth_x - 1}")
            
            # 更新ROI Y范围滑动条
            if hasattr(self, 'roi_y_min_slider'):
                self.roi_y_min_slider.setMaximum(self.depth_y - 1)
                self.roi_y_max_slider.setMaximum(self.depth_y - 1)
                self.roi_y_max_slider.setValue(self.depth_y - 1)  # 默认设为最大值
                
                print(f"ROI Y范围滑动条已更新: 0 - {self.depth_y - 1}")
            
            # 只有在数据不全为0时才创建3D视图
            if data_max > 0:
                # 创建三维体渲染视图（禁用降采样）
                self.volume_viewer = VolumeViewer(self.array, self.spacing, simplified=True, downsample_factor=1)
                
                # 四宫格布局
                self.grid_layout.addWidget(self.axial_viewer, 0, 0)
                self.grid_layout.addWidget(self.sag_viewer, 0, 1)
                self.grid_layout.addWidget(self.cor_viewer, 1, 0)
                self.grid_layout.addWidget(self.volume_viewer, 1, 1)
            else:
                # 数据全为0，只显示2D视图
                print("数据全为0，跳过3D视图创建")
                self.grid_layout.addWidget(self.axial_viewer, 0, 0)
                self.grid_layout.addWidget(self.sag_viewer, 0, 1)
                self.grid_layout.addWidget(self.cor_viewer, 1, 0)
                
                # 在右下角显示提示信息
                info_label = QtWidgets.QLabel("3D视图不可用\n(数据全为0)")
                info_label.setAlignment(QtCore.Qt.AlignCenter)
                info_label.setStyleSheet("QLabel { background-color: #f0f0f0; color: #666; font-size: 14pt; }")
                self.grid_layout.addWidget(info_label, 1, 1)
            
            # 更新显示
            self.setWindowTitle(f"CT Viewer - {os.path.basename(filename)}")
            
            # 更新灰度直方图
            if hasattr(self, 'update_histogram'):
                self.update_histogram(self.array)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "错误", f"加载文件时出错：{str(e)}")
    
    def clear_viewers(self):
        """清除现有的视图组件"""
        # 清除grid_layout中的所有widget
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 重置视图引用
        self.axial_viewer = None
        self.sag_viewer = None
        self.cor_viewer = None
        self.volume_viewer = None
    
    def update_viewers(self):
        """更新所有视图"""
        # 清除现有的视图组件
        self.clear_viewers()
        
        # 重新创建视图组件
        self.axial_viewer = SliceViewer("Axial",
                                  lambda z: self.array[z, :, :],
                                  self.depth_z)
        self.sag_viewer = SliceViewer("Sagittal",
                                lambda x: self.array[:, :, x],
                                self.depth_x)
        self.cor_viewer = SliceViewer("Coronal",
                                lambda y: self.array[:, y, :],
                                self.depth_y)
        
        # 创建简化版3D体渲染视图（禁用降采样）
        self.volume_viewer = VolumeViewer(self.array, self.spacing, simplified=True, downsample_factor=1)
        
        # 应用与load_reconstructed_data相同的3D视图参数调整
        self.volume_viewer.adjust_contrast(opacity_scale=1.5)
        
        # 四视图布局
        self.grid_layout.addWidget(self.axial_viewer, 0, 0)
        self.grid_layout.addWidget(self.sag_viewer, 0, 1)
        self.grid_layout.addWidget(self.cor_viewer, 1, 0)
        self.grid_layout.addWidget(self.volume_viewer, 1, 1)
        
        # 更新灰度直方图
        if hasattr(self, 'update_histogram'):
            self.update_histogram(self.array)
    
    def load_reconstructed_data(self, image, array, title="重建数据"):
        """
        加载CT重建的数据并在四视图中显示
        
        参数
        ----
        image : sitk.Image
            SimpleITK图像对象
        array : np.ndarray
            原始三维数组，形状为(z, y, x)
        title : str
            窗口标题
        """
        try:
            # 清除现有的视图组件
            self.clear_viewers()
            
            # 打印调试信息
            print(f"加载重建数据: 形状={array.shape}, 类型={array.dtype}")
            print(f"数据范围: 最小值={array.min()}, 最大值={array.max()}")
            
            # 保存图像数据
            self.image = image
            
            # 处理数组数据用于显示
            processed_array = array.copy()
            
            # 负值处理
            if processed_array.min() < 0:
                processed_array = processed_array - processed_array.min()
            
            # 归一化并缩放到uint16范围
            if processed_array.max() > 0:
                scale_factor = 65535.0 / processed_array.max()
                processed_array = (processed_array * scale_factor).astype(np.uint16)
            else:
                processed_array = processed_array.astype(np.uint16)
            
            # 保存处理后的数组
            self.array = processed_array
            
            # 获取尺寸信息
            self.depth_z, self.depth_y, self.depth_x = self.array.shape
            self.spacing = self.image.GetSpacing()
            
            print(f"处理后数据: 形状={self.array.shape}, 类型={self.array.dtype}")
            print(f"处理后范围: 最小值={self.array.min()}, 最大值={self.array.max()}")
            
            # 创建进度对话框
            progress = QtWidgets.QProgressDialog("正在创建视图...", "取消", 0, 4, self)
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.setValue(0)
            progress.show()
            QtWidgets.QApplication.processEvents()
            
            # 重新创建视图组件
            self.axial_viewer = SliceViewer("Axial",
                                      lambda z: self.array[z, :, :],
                                      self.depth_z)
            progress.setValue(1)
            QtWidgets.QApplication.processEvents()
            
            self.sag_viewer = SliceViewer("Sagittal",
                                    lambda x: self.array[:, :, x],
                                    self.depth_x)
            progress.setValue(2)
            QtWidgets.QApplication.processEvents()
            
            self.cor_viewer = SliceViewer("Coronal",
                                    lambda y: self.array[:, y, :],
                                    self.depth_y)
            progress.setValue(3)
            QtWidgets.QApplication.processEvents()
            
            # 创建简化版3D体渲染视图（禁用降采样）
            self.volume_viewer = VolumeViewer(self.array, self.spacing, simplified=True, downsample_factor=1)
            
            # 针对重建数据特点自动调整3D视图参数
            self.volume_viewer.adjust_contrast(opacity_scale=1.5)
            
            progress.setValue(4)
            QtWidgets.QApplication.processEvents()
            
            # 四视图布局
            self.grid_layout.addWidget(self.axial_viewer, 0, 0)
            self.grid_layout.addWidget(self.sag_viewer, 0, 1)
            self.grid_layout.addWidget(self.cor_viewer, 1, 0)
            self.grid_layout.addWidget(self.volume_viewer, 1, 1)
            
            # 关闭进度对话框
            progress.close()
            
            # 更新窗口标题
            self.setWindowTitle(f"CT Viewer - {title}")
            
            # 更新灰度直方图
            if hasattr(self, 'update_histogram'):
                self.update_histogram(self.array)
            
            # 显示成功消息
            QtWidgets.QMessageBox.information(self, "成功", f"已加载{title}")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "错误", f"加载重建数据时出错：{str(e)}")
    
    def load_reconstructed_data_no_copy(self, data_array, spacing, title="重建数据"):
        """
        加载CT重建的数据并在四视图中显示（内存优化版本，不创建数据副本）
        
        参数
        ----
        data_array : np.ndarray
            LEAP重建的原始数组（直接引用，不会复制）
        spacing : tuple
            体素间距，形式为(sx, sy, sz)
        title : str
            窗口标题
        """
        try:
            # 清除现有的视图组件
            self.clear_viewers()
            
            # 打印调试信息
            print(f"加载重建数据（无副本模式）: 形状={data_array.shape}, 类型={data_array.dtype}")
            print(f"原始数据范围: 最小值={np.min(data_array)}, 最大值={np.max(data_array)}")
            
            # 创建进度对话框
            progress = QtWidgets.QProgressDialog("正在处理重建数据...", "取消", 0, 100, self)
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.setValue(0)
            progress.show()
            QtWidgets.QApplication.processEvents()
            
            # 获取数据统计信息（不创建副本）
            data_min = float(np.min(data_array))
            data_max = float(np.max(data_array))
            
            progress.setValue(10)
            progress.setLabelText("计算归一化参数...")
            QtWidgets.QApplication.processEvents()
            
            # 计算归一化参数
            if data_min < 0:
                offset = -data_min
            else:
                offset = 0.0
            
            if data_max + offset > 0:
                scale = 65535.0 / (data_max + offset)
            else:
                scale = 1.0
            
            print(f"归一化参数: offset={offset}, scale={scale}")
            
            progress.setValue(20)
            progress.setLabelText("创建SimpleITK图像...")
            QtWidgets.QApplication.processEvents()
            
            # 创建SimpleITK图像
            sitk_array = np.ascontiguousarray(data_array, dtype=np.float32)
            sitk_image = sitk.GetImageFromArray(sitk_array)
            sitk_image.SetSpacing(spacing)
            self.image = sitk_image
            
            # 设置spacing和尺寸
            self.spacing = spacing
            self.depth_z, self.depth_y, self.depth_x = data_array.shape
            
            progress.setValue(30)
            progress.setLabelText("准备显示数据...")
            QtWidgets.QApplication.processEvents()
            
            # 对于显示，我们需要uint16格式的数据
            print("开始转换为uint16格式...")
            
            # 分配uint16数组
            display_array = np.empty(data_array.shape, dtype=np.uint16)
            
            # 分块处理，减少内存峰值
            chunk_size = 100  # 每次处理100个切片
            num_slices = data_array.shape[0]
            
            for start_z in range(0, num_slices, chunk_size):
                end_z = min(start_z + chunk_size, num_slices)
                
                # 处理当前块
                chunk = data_array[start_z:end_z, :, :]
                
                # 原地处理：偏移和缩放
                if offset != 0:
                    chunk = chunk + offset
                if scale != 1.0:
                    chunk = chunk * scale
                
                # 裁剪到uint16范围并转换
                np.clip(chunk, 0, 65535, out=chunk)
                display_array[start_z:end_z, :, :] = chunk.astype(np.uint16)
                
                # 更新进度
                progress_val = 30 + int(50 * (end_z / num_slices))
                progress.setValue(progress_val)
                QtWidgets.QApplication.processEvents()
                
                print(f"已处理 {end_z}/{num_slices} 切片")
            
            # 保存原始数据
            self.raw_array = display_array
            self.array = self.raw_array
            
            print(f"转换完成: 形状={self.raw_array.shape}, 类型={self.raw_array.dtype}")
            print(f"显示数据范围: 最小值={self.raw_array.min()}, 最大值={self.raw_array.max()}")
            
            # 初始化窗宽窗位控制
            data_min = int(self.raw_array.min())
            data_max = int(self.raw_array.max())
            self.window_width = data_max - data_min
            self.window_level = (data_max + data_min) // 2
            
            # 更新滑动条范围和值
            self.ww_slider.setMaximum(data_max)
            self.ww_slider.setValue(self.window_width)
            self.wl_slider.setMaximum(data_max)
            self.wl_slider.setValue(self.window_level)
            self.ww_value.setText(str(self.window_width))
            self.wl_value.setText(str(self.window_level))
            
            # 显示窗宽窗位控制面板
            self.ww_wl_panel.show()
            
            progress.setValue(85)
            progress.setLabelText("创建2D视图...")
            QtWidgets.QApplication.processEvents()
            
            # 重新创建视图组件
            self.axial_viewer = SliceViewer("Axial",
                                      lambda z: self.apply_window_level_to_slice(self.raw_array[z, :, :]),
                                      self.depth_z,
                                      parent_viewer=self)
            
            self.sag_viewer = SliceViewer("Sagittal",
                                    lambda x: self.apply_window_level_to_slice(self.raw_array[:, :, x]),
                                    self.depth_x,
                                    parent_viewer=self)
            
            self.cor_viewer = SliceViewer("Coronal",
                                    lambda y: self.apply_window_level_to_slice(self.raw_array[:, y, :]),
                                    self.depth_y,
                                    parent_viewer=self)
            
            progress.setValue(90)
            progress.setLabelText("创建3D视图（这可能需要较长时间）...")
            QtWidgets.QApplication.processEvents()
            
            # 创建简化版3D体渲染视图（禁用降采样）
            self.volume_viewer = VolumeViewer(self.raw_array, self.spacing, simplified=True, downsample_factor=1)
            
            # 针对重建数据特点自动调整3D视图参数
            self.volume_viewer.adjust_contrast(opacity_scale=1.5)
            
            progress.setValue(95)
            progress.setLabelText("布局视图...")
            QtWidgets.QApplication.processEvents()
            
            # 四视图布局
            self.grid_layout.addWidget(self.axial_viewer, 0, 0)
            self.grid_layout.addWidget(self.sag_viewer, 0, 1)
            self.grid_layout.addWidget(self.cor_viewer, 1, 0)
            self.grid_layout.addWidget(self.volume_viewer, 1, 1)
            
            progress.setValue(100)
            progress.close()
            
            # 更新窗口标题
            self.setWindowTitle(f"CT Viewer - {title}")
            
            # 更新灰度直方图
            if hasattr(self, 'update_histogram'):
                self.update_histogram(self.raw_array)
            
            print(f"成功加载 {title}")
            print(f"窗宽窗位控制已启用: WW={self.window_width}, WL={self.window_level}")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            if 'progress' in locals():
                progress.close()
            QtWidgets.QMessageBox.critical(self, "错误", f"加载重建数据时出错：{str(e)}")

