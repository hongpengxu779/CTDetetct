"""
数据加载和管理功能
负责加载CT数据、重建数据等
"""

import os
import numpy as np
import SimpleITK as sitk
from PyQt5 import QtWidgets, QtCore
import json
import imageio
import re

from File.readData import CTImageData
from ..viewers import SliceViewer, VolumeViewer


class DataLoader:
    """数据加载和管理类，作为Mixin使用"""

    def _add_reconstructed_item_to_data_list(self, title, image, array):
        """将重建数据添加到数据列表，确保后续保存/导出可用。"""
        if not hasattr(self, 'data_list_widget') or self.data_list_widget is None:
            return
        if not hasattr(self, 'add_data_to_list'):
            return

        base_name = (title or "重建数据").strip() or "重建数据"
        existing = set()
        for i in range(self.data_list_widget.count()):
            item = self.data_list_widget.item(i)
            if item is not None:
                existing.add(item.text())

        name = base_name
        if name in existing:
            idx = 2
            while f"{base_name} ({idx})" in existing:
                idx += 1
            name = f"{base_name} ({idx})"

        spacing = tuple(image.GetSpacing()) if image is not None else tuple(getattr(self, 'spacing', (1.0, 1.0, 1.0)))
        data_item = {
            'image': image,
            'array': array,
            'shape': array.shape,
            'spacing': spacing,
            'data_type': 'image',
            'source': 'slice_reconstruction',
        }
        self.add_data_to_list(name, data_item)
    
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
                # 增强对话框：同时输入 raw 的维度 (Z,Y,X) 和体素大小 (spacing)
                dialog = QtWidgets.QDialog(self)
                dialog.setWindowTitle("输入RAW文件维度和体素大小")

                form_layout = QtWidgets.QFormLayout(dialog)

                # 体素维度输入
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

                # 体素大小输入（单位示例：mm）
                sx_input = QtWidgets.QDoubleSpinBox()
                sx_input.setRange(0.000001, 1000.0)
                sx_input.setDecimals(6)
                sx_input.setValue(1.0)
                sx_input.setSingleStep(0.001)
                sx_input.setToolTip("X方向体素大小（例如 mm）")
                form_layout.addRow("X 方向间距 (mm):", sx_input)

                sy_input = QtWidgets.QDoubleSpinBox()
                sy_input.setRange(0.000001, 1000.0)
                sy_input.setDecimals(6)
                sy_input.setValue(1.0)
                sy_input.setSingleStep(0.001)
                sy_input.setToolTip("Y方向体素大小（例如 mm）")
                form_layout.addRow("Y 方向间距 (mm):", sy_input)

                sz_input = QtWidgets.QDoubleSpinBox()
                sz_input.setRange(0.000001, 1000.0)
                sz_input.setDecimals(6)
                sz_input.setValue(1.0)
                sz_input.setSingleStep(0.001)
                sz_input.setToolTip("Z方向体素大小（例如 mm）")
                form_layout.addRow("Z 方向间距 (mm):", sz_input)

                # 确认按钮
                button_box = QtWidgets.QDialogButtonBox(
                    QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
                )
                button_box.accepted.connect(dialog.accept)
                button_box.rejected.connect(dialog.reject)
                form_layout.addRow(button_box)

                if dialog.exec_() == QtWidgets.QDialog.Accepted:
                    shape = (z_input.value(), y_input.value(), x_input.value())
                    spacing = (float(sx_input.value()), float(sy_input.value()), float(sz_input.value()))
                    # 将 spacing 传递给 load_data，保证后续 3D 显示使用正确的体素比例
                    self.load_data(filename, shape, spacing)
            else:
                # 对于其他格式，直接加载
                self.load_data(filename)
    
    def load_data(self, filename, shape=None, spacing=None, dtype=np.uint16):
        """加载CT数据并添加到数据列表"""
        try:
            # 读取CT数据
            CTdata = CTImageData(filename, shape, spacing)
            temp_image = CTdata.image
            temp_array = CTdata.array
            
            # 检查数据类型并获取尺寸
            original_dtype = temp_array.dtype
            print(f"原始数据类型: {original_dtype}, 形状: {temp_array.shape}")
            
            # 检查是否为RGB图像
            is_rgb = False
            temp_rgb_array = None
            
            if len(temp_array.shape) == 4:
                # 检查是否为 (Z, Y, X, 3/4) 格式
                if temp_array.shape[3] in [3, 4]:
                    is_rgb = True
                    print(f"检测到RGB图像（通道在最后）: {temp_array.shape}")
                    temp_rgb_array = temp_array.copy()
                    temp_depth_z, temp_depth_y, temp_depth_x = temp_array.shape[:3]
                # 检查是否为 (3/4, Z, Y, X) 格式（NIfTI常见格式）
                elif temp_array.shape[0] in [3, 4]:
                    is_rgb = True
                    print(f"检测到RGB图像（通道在最前）: {temp_array.shape}")
                    # 需要转置维度: (C, Z, Y, X) -> (Z, Y, X, C)
                    temp_rgb_array = np.transpose(temp_array, (1, 2, 3, 0))
                    print(f"转置后形状: {temp_rgb_array.shape}")
                    temp_depth_z, temp_depth_y, temp_depth_x = temp_rgb_array.shape[:3]
                else:
                    # 其他4D格式，按普通3D处理
                    is_rgb = False
                    temp_depth_z, temp_depth_y, temp_depth_x = temp_array.shape[:3]
            else:
                # 3D或其他维度
                is_rgb = False
                if len(temp_array.shape) == 3:
                    temp_depth_z, temp_depth_y, temp_depth_x = temp_array.shape
            
            # 获取spacing，确保只有3个值（x, y, z）
            spacing_raw = temp_image.GetSpacing()
            if len(spacing_raw) > 3:
                # RGB图像可能有4个spacing值，只取前3个（忽略颜色通道）
                temp_spacing = spacing_raw[:3]
                print(f"Spacing从{len(spacing_raw)}维调整为3维: {temp_spacing}")
            else:
                temp_spacing = spacing_raw
            
            if is_rgb:
                print(f"RGB数组形状: {temp_rgb_array.shape}")
                print(f"数据尺寸: Z={temp_depth_z}, Y={temp_depth_y}, X={temp_depth_x}")
                print(f"Spacing: {temp_spacing}")
                
                # RGB图像不是分割结果
                is_segmentation = False
                
                # 为了3D显示，将RGB转换为灰度
                if temp_rgb_array.shape[3] >= 3:
                    gray = (0.299 * temp_rgb_array[:,:,:,0] + 
                           0.587 * temp_rgb_array[:,:,:,1] + 
                           0.114 * temp_rgb_array[:,:,:,2])
                    # 转换为uint16以供VolumeViewer使用
                    if temp_rgb_array.dtype == np.uint8:
                        temp_array = (gray.astype(np.float32) * 257).astype(np.uint16)
                    else:
                        temp_array = gray.astype(np.uint16)
                    print(f"RGB已转换为灰度用于3D显示，范围: [{temp_array.min()}, {temp_array.max()}]")
            else:
                # 非RGB图像，保持原有逻辑
                temp_rgb_array = None
                
                # 在转换之前检测是否为分割结果
                # 分割结果的特征：
                # 1. 数据类型为uint8
                # 2. 数据范围较小（通常0-255或更小）
                # 3. 数据值只有少数几个离散值
                is_segmentation = False
                if temp_array.dtype == np.uint8:
                    # 检查唯一值数量
                    unique_values = np.unique(temp_array)
                    if len(unique_values) <= 20:  # 少于20个唯一值，可能是分割结果
                        is_segmentation = True
                        print(f"检测到分割结果，唯一值: {unique_values}")
                
                if temp_array.dtype == np.uint8:
                    # 将uint8转换为uint16，扩展到完整范围
                    if not is_segmentation:
                        # 普通uint8图像，扩展到完整范围
                        print("检测到uint8数据，转换为uint16以便3D显示")
                        temp_array = (temp_array.astype(np.float32) * 257).astype(np.uint16)
                    else:
                        # 分割结果，保持原始值但转换类型
                        print("检测到分割结果（uint8），转换为uint16但保持原始值")
                        temp_array = temp_array.astype(np.uint16)
                elif temp_array.dtype != np.uint16:
                    # 其他类型也转换为uint16
                    print(f"转换数据类型 {temp_array.dtype} -> uint16")
                    data_min = temp_array.min()
                    data_max = temp_array.max()
                    if data_max > data_min:
                        temp_array = ((temp_array - data_min) / (data_max - data_min) * 65535).astype(np.uint16)
                    else:
                        temp_array = temp_array.astype(np.uint16)
            
            # 检查数据范围，判断是否为分割结果
            data_min = float(temp_array.min())
            data_max = float(temp_array.max())
            print(f"转换后数据范围: [{data_min}, {data_max}]")
            
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
                if not is_rgb:  # 只有非RGB图像才标记为分割结果
                    is_segmentation = True
            
            # 创建数据项保存所有信息
            data_item = {
                'image': temp_image,
                'array': temp_array,
                'shape': (temp_depth_z, temp_depth_y, temp_depth_x),
                'spacing': temp_spacing,
                'rgb_array': temp_rgb_array,
                'is_segmentation': is_segmentation  # 添加分割结果标志
            }
            
            # 生成数据名称
            import os
            data_name = os.path.basename(filename)
            
            # 添加到数据列表
            if hasattr(self, 'add_data_to_list'):
                self.add_data_to_list(data_name, data_item)
            
            # 设置为当前数据（用于第一次加载或直接显示）
            self.image = temp_image
            self.array = temp_array
            self.depth_z, self.depth_y, self.depth_x = temp_depth_z, temp_depth_y, temp_depth_x
            self.spacing = temp_spacing
            self.rgb_array = temp_rgb_array
            self.raw_array = temp_array
            self.is_segmentation = is_segmentation  # 保存分割结果标志
            self.annotation_enabled = False
            self.annotation_mode = 'brush'
            self.annotation_volume = np.zeros(self.array.shape, dtype=np.uint16) if len(self.array.shape) == 3 else None
            self.annotation_drawn_mask = np.zeros(self.array.shape, dtype=bool) if len(self.array.shape) == 3 else None
            self.annotation_overlay_color = (255, 60, 60)
            self.annotation_overlay_alpha = 110
            self.annotation_label_colors = {}
            print(f"raw_array已设置，形状: {self.raw_array.shape}")

            if hasattr(self, 'prop_size_label'):
                self.prop_size_label.setText(f"{self.depth_x} x {self.depth_y} x {self.depth_z}")
            if hasattr(self, 'prop_spacing_label'):
                sx, sy, sz = self.spacing if self.spacing is not None else (1.0, 1.0, 1.0)
                self.prop_spacing_label.setText(f"{sx:.4f} x {sy:.4f} x {sz:.4f}")
                if hasattr(self, 'prop_spacing_xyz_label'):
                    self.prop_spacing_xyz_label.setText(f"{sx:.4f} x {sy:.4f} x {sz:.4f}")
            if hasattr(self, 'prop_type_label'):
                self.prop_type_label.setText(str(self.array.dtype))
            if hasattr(self, 'prop_width_label'):
                self.prop_width_label.setText(str(self.depth_x))
            if hasattr(self, 'prop_height_label'):
                self.prop_height_label.setText(str(self.depth_y))
            if hasattr(self, 'prop_slice_count_label'):
                self.prop_slice_count_label.setText(str(self.depth_z))
            if hasattr(self, 'prop_format_label'):
                self.prop_format_label.setText(os.path.splitext(filename)[1].lower().replace('.', '') or "体数据")
            if hasattr(self, '_update_basic_properties_table'):
                self._update_basic_properties_table()
            if is_segmentation:
                print("✓ 检测到分割结果，将不应用窗宽窗位")
            
            # 清除旧的视图组件
            self.clear_viewers()
            
            # 创建三个方向的切片视图
            if hasattr(self, 'rgb_array') and self.rgb_array is not None:
                # RGB图像的切片获取
                self.axial_viewer = SliceViewer("轴位 (彩色)",
                                          lambda z: self.rgb_array[z, :, :, :],
                                                                                    self.depth_z,
                                                                                    parent_viewer=self)
                self.sag_viewer = SliceViewer("矢状 (彩色)",
                                        lambda x: self.rgb_array[:, :, x, :],
                                                                                self.depth_x,
                                                                                parent_viewer=self)
                self.cor_viewer = SliceViewer("冠状 (彩色)",
                                        lambda y: self.rgb_array[:, y, :, :],
                                                                                self.depth_y,
                                                                                parent_viewer=self)
            else:
                # 灰度图像的切片获取
                # 如果是分割结果，使用优化的显示映射而不是窗宽窗位
                if is_segmentation:
                    print("创建分割结果视图（使用优化的显示映射）")
                    self.axial_viewer = SliceViewer("轴位 (分割)",
                                              lambda z: self.apply_segmentation_display(self.array[z, :, :]),
                                              self.depth_z,
                                              parent_viewer=self)
                    self.sag_viewer = SliceViewer("矢状 (分割)",
                                            lambda x: self.apply_segmentation_display(self.array[:, :, x]),
                                            self.depth_x,
                                            parent_viewer=self)
                    self.cor_viewer = SliceViewer("冠状 (分割)",
                                            lambda y: self.apply_segmentation_display(self.array[:, y, :]),
                                            self.depth_y,
                                            parent_viewer=self)
                else:
                    self.axial_viewer = SliceViewer("轴位",
                                              lambda z: self.apply_window_level_to_slice(self.array[z, :, :]),
                                              self.depth_z,
                                              parent_viewer=self)
                    self.sag_viewer = SliceViewer("矢状",
                                            lambda x: self.apply_window_level_to_slice(self.array[:, :, x]),
                                            self.depth_x,
                                            parent_viewer=self)
                    self.cor_viewer = SliceViewer("冠状",
                                            lambda y: self.apply_window_level_to_slice(self.array[:, y, :]),
                                            self.depth_y,
                                            parent_viewer=self)

                    self.active_view = 'axial'
            
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
                if hasattr(self.volume_viewer, 'set_background_color'):
                    self.volume_viewer.set_background_color((0.08, 0.08, 0.10))
                if hasattr(self, 'apply_current_3d_controls'):
                    self.apply_current_3d_controls()
                
                # 四宫格布局
                self.grid_layout.addWidget(self.volume_viewer, 0, 0)
                self.grid_layout.addWidget(self.cor_viewer, 0, 1)
                self.grid_layout.addWidget(self.axial_viewer, 1, 0)
                self.grid_layout.addWidget(self.sag_viewer, 1, 1)
            else:
                # 数据全为0，只显示2D视图
                print("数据全为0，跳过3D视图创建")
                self.grid_layout.addWidget(self.cor_viewer, 0, 1)
                self.grid_layout.addWidget(self.axial_viewer, 1, 0)
                self.grid_layout.addWidget(self.sag_viewer, 1, 1)
                
                # 在左上角显示提示信息
                info_label = QtWidgets.QLabel("三维视图不可用\n(数据全为0)")
                info_label.setAlignment(QtCore.Qt.AlignCenter)
                info_label.setStyleSheet("QLabel { background-color: #151515; border: 1px solid #3f3f3f; color: #d0d0d0; font-size: 14pt; }")
                self.grid_layout.addWidget(info_label, 0, 0)

            if hasattr(self, '_on_2d_viewers_created'):
                self._on_2d_viewers_created()
            
            # 更新显示
            self.setWindowTitle(f"工业CT智能软件 - {os.path.basename(filename)}")
            
            # 初始化窗宽窗位
            if hasattr(self, 'reset_window_level'):
                self.reset_window_level()
                
                # 如果是小范围的分割结果（如OTSU多阈值），自动调整窗宽窗位以便可见
                if data_max < 2000 and data_max > 0:  # 判断是否为分割结果
                    print(f"检测到分割结果（范围{data_min}-{data_max}），自动调整窗宽窗位以便可见")
                    self.window_width = int(data_max * 1.2)  # 稍微扩大一点范围
                    self.window_level = int(data_max / 2)
                    self.ww_slider.setValue(self.window_width)
                    self.wl_slider.setValue(self.window_level)
                    self.update_all_views()
            
            # 更新灰度直方图
            if hasattr(self, 'update_histogram'):
                self.update_histogram(self.array)

            if hasattr(self, '_refresh_preview_thumbnail'):
                self._refresh_preview_thumbnail()
            
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
        self.axial_viewer = SliceViewer("轴位",
                                  lambda z: self.apply_window_level_to_slice(self.array[z, :, :]),
                                  self.depth_z,
                                  parent_viewer=self)
        self.sag_viewer = SliceViewer("矢状",
                                lambda x: self.apply_window_level_to_slice(self.array[:, :, x]),
                                self.depth_x,
                                parent_viewer=self)
        self.cor_viewer = SliceViewer("冠状",
                                lambda y: self.apply_window_level_to_slice(self.array[:, y, :]),
                                self.depth_y,
                                parent_viewer=self)
        
        # 创建简化版3D体渲染视图（禁用降采样）
        self.volume_viewer = VolumeViewer(self.array, self.spacing, simplified=True, downsample_factor=1)
        if hasattr(self.volume_viewer, 'set_background_color'):
            self.volume_viewer.set_background_color((0.08, 0.08, 0.10))
        if hasattr(self, 'apply_current_3d_controls'):
            self.apply_current_3d_controls()
        
        # 应用与load_reconstructed_data相同的3D视图参数调整
        self.volume_viewer.adjust_contrast(opacity_scale=1.5)
        
        # 四视图布局
        self.grid_layout.addWidget(self.volume_viewer, 0, 0)
        self.grid_layout.addWidget(self.cor_viewer, 0, 1)
        self.grid_layout.addWidget(self.axial_viewer, 1, 0)
        self.grid_layout.addWidget(self.sag_viewer, 1, 1)

        if hasattr(self, '_on_2d_viewers_created'):
            self._on_2d_viewers_created()
        
        # 更新灰度直方图
        if hasattr(self, 'update_histogram'):
            self.update_histogram(self.array)

        if hasattr(self, '_refresh_preview_thumbnail'):
            self._refresh_preview_thumbnail()
    
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
            self.raw_array = self.array
            
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
            self.axial_viewer = SliceViewer("轴位",
                                      lambda z: self.apply_window_level_to_slice(self.array[z, :, :]),
                                      self.depth_z,
                                      parent_viewer=self)
            progress.setValue(1)
            QtWidgets.QApplication.processEvents()
            
            self.sag_viewer = SliceViewer("矢状",
                                    lambda x: self.apply_window_level_to_slice(self.array[:, :, x]),
                                    self.depth_x,
                                    parent_viewer=self)
            progress.setValue(2)
            QtWidgets.QApplication.processEvents()
            
            self.cor_viewer = SliceViewer("冠状",
                                    lambda y: self.apply_window_level_to_slice(self.array[:, y, :]),
                                    self.depth_y,
                                    parent_viewer=self)
            progress.setValue(3)
            QtWidgets.QApplication.processEvents()
            
            # 创建简化版3D体渲染视图（禁用降采样）
            self.volume_viewer = VolumeViewer(self.array, self.spacing, simplified=True, downsample_factor=1)
            
            # 针对重建数据特点自动调整3D视图参数
            self.volume_viewer.adjust_contrast(opacity_scale=1.5)
            if hasattr(self, 'apply_current_3d_controls'):
                self.apply_current_3d_controls()
            
            progress.setValue(4)
            QtWidgets.QApplication.processEvents()
            
            # 四视图布局
            self.grid_layout.addWidget(self.axial_viewer, 0, 0)
            self.grid_layout.addWidget(self.sag_viewer, 0, 1)
            self.grid_layout.addWidget(self.cor_viewer, 1, 0)
            self.grid_layout.addWidget(self.volume_viewer, 1, 1)

            if hasattr(self, '_on_2d_viewers_created'):
                self._on_2d_viewers_created()
            
            # 关闭进度对话框
            progress.close()
            
            # 更新窗口标题
            self.setWindowTitle(f"工业CT智能软件 - {title}")
            
            # 更新灰度直方图
            if hasattr(self, 'update_histogram'):
                self.update_histogram(self.array)

            # 加入数据列表（用于保存/导出/切换）
            self._add_reconstructed_item_to_data_list(title, self.image, self.array)
            
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
            self.axial_viewer = SliceViewer("轴位",
                                      lambda z: self.apply_window_level_to_slice(self.raw_array[z, :, :]),
                                      self.depth_z,
                                      parent_viewer=self)
            
            self.sag_viewer = SliceViewer("矢状",
                                    lambda x: self.apply_window_level_to_slice(self.raw_array[:, :, x]),
                                    self.depth_x,
                                    parent_viewer=self)
            
            self.cor_viewer = SliceViewer("冠状",
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
            if hasattr(self, 'apply_current_3d_controls'):
                self.apply_current_3d_controls()
            
            progress.setValue(95)
            progress.setLabelText("布局视图...")
            QtWidgets.QApplication.processEvents()
            
            # 四视图布局
            self.grid_layout.addWidget(self.axial_viewer, 0, 0)
            self.grid_layout.addWidget(self.sag_viewer, 0, 1)
            self.grid_layout.addWidget(self.cor_viewer, 1, 0)
            self.grid_layout.addWidget(self.volume_viewer, 1, 1)

            if hasattr(self, '_on_2d_viewers_created'):
                self._on_2d_viewers_created()
            
            progress.setValue(100)
            progress.close()
            
            # 更新窗口标题
            self.setWindowTitle(f"工业CT智能软件 - {title}")
            
            # 更新灰度直方图
            if hasattr(self, 'update_histogram'):
                self.update_histogram(self.raw_array)

            # 加入数据列表（用于保存/导出/切换）
            self._add_reconstructed_item_to_data_list(title, self.image, self.raw_array)
            
            print(f"成功加载 {title}")
            print(f"窗宽窗位控制已启用: WW={self.window_width}, WL={self.window_level}")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            if 'progress' in locals():
                progress.close()
            QtWidgets.QMessageBox.critical(self, "错误", f"加载重建数据时出错：{str(e)}")

    def export_slices_dialog(self):
        """通过对话框导出当前数据为按轴切片的uint16 TIFF序列并保存元数据（可逆）。"""
        if not hasattr(self, 'raw_array') or self.raw_array is None:
            QtWidgets.QMessageBox.warning(self, "导出失败", "没有可用的影像数据来导出。")
            return

        # 选择方向
        axes = {"Z (轴位)": 0, "Y (冠状)": 1, "X (矢状)": 2}
        items = list(axes.keys())
        item, ok = QtWidgets.QInputDialog.getItem(self, "选择导出方向", "沿哪个方向导出切片：", items, 0, False)
        if not ok:
            return
        axis = axes[item]

        # 选择输出目录
        out_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "选择保存切片的文件夹")
        if not out_dir:
            return

        # 文件名前缀
        prefix, ok = QtWidgets.QInputDialog.getText(self, "输入文件前缀", "每张切片的文件名前缀（例如 切片）：", text="切片")
        if not ok:
            return

        try:
            self.export_slices(axis=axis, out_dir=out_dir, prefix=prefix)
            QtWidgets.QMessageBox.information(self, "导出完成", f"已导出切片到：\n{out_dir}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "导出失败", str(e))

    def export_slices(self, axis, out_dir, prefix='slice'):
        """将当前原始数组沿指定轴导出为uint16 TIFF序列，并写出元数据用于可逆重建。

        参数
        ----
        axis: int
            导出轴 (0=Z,1=Y,2=X)
        out_dir: str
            输出文件夹
        prefix: str
            每个切片文件的前缀
        """
        # 优先从数据列表获取当前选中项的数据（与 mUSICA 一致）
        arr = None
        if hasattr(self, 'data_list_widget') and self.data_list_widget is not None:
            from PyQt5 import QtCore
            current_item = self.data_list_widget.currentItem()
            if current_item is not None:
                data_item = current_item.data(QtCore.Qt.UserRole)
                if isinstance(data_item, dict) and 'array' in data_item:
                    arr = data_item['array']
                    print(f"[导出切片] 从数据列表获取: dtype={arr.dtype}, shape={arr.shape}")
        
        # 回退到 self.raw_array
        if arr is None:
            arr = self.raw_array
            if arr is not None:
                print(f"[导出切片] 使用 self.raw_array: dtype={arr.dtype}, shape={arr.shape}")
        
        if arr is None:
            raise RuntimeError('没有原始数组可导出')

        # 确保为 uint16
        arr_uint16 = arr.astype(np.uint16)

        num_slices = arr_uint16.shape[axis]

        # 创建元数据
        metadata = {
            'axis': int(axis),
            'shape': tuple(int(x) for x in arr_uint16.shape),
            'spacing': tuple(float(x) for x in (self.spacing if self.spacing is not None else (1.0, 1.0, 1.0))),
            'dtype': 'uint16',
            'prefix': prefix,
            'file_pattern': f"{prefix}_%0{max(4, len(str(num_slices)))}d.tiff",
            'count': int(num_slices)
        }

        # 保存元数据
        meta_path = os.path.join(out_dir, 'export_metadata.json')
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        # 进度对话框
        progress = QtWidgets.QProgressDialog("正在导出切片...", "取消", 0, num_slices, self)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.show()
        QtWidgets.QApplication.processEvents()

        for i in range(num_slices):
            if progress.wasCanceled():
                break

            # 取出指定轴的切片
            if axis == 0:
                slice2d = arr_uint16[i, :, :]
            elif axis == 1:
                slice2d = arr_uint16[:, i, :]
            else:
                slice2d = arr_uint16[:, :, i]

            filename = os.path.join(out_dir, f"{prefix}_{i:0{max(4, len(str(num_slices))) }d}.tiff")

            # 使用 imageio 保存 uint16 TIFF
            imageio.imwrite(filename, slice2d.astype(np.uint16))

            progress.setValue(i + 1)
            QtWidgets.QApplication.processEvents()

        progress.close()

    def import_slices_dialog(self):
        """通过对话框从保存的切片文件夹或metadata.json重建体数据并加载到应用中。"""
        # 选择包含切片的目录
        in_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "选择包含切片的文件夹")
        if not in_dir:
            return

        try:
            volume_image, volume_array, metadata = self.import_slices(in_dir)
            # 使用已有的加载函数将重建数据加载入视图
            self.load_reconstructed_data(volume_image, volume_array, title=os.path.basename(in_dir))
            QtWidgets.QMessageBox.information(self, "导入完成", f"已从切片重建并加载：\n{in_dir}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "导入失败", str(e))

    def import_slices(self, in_dir):
        """从某个目录读取uint16 TIFF序列（优先使用export_metadata.json），并重建3D numpy数组和SimpleITK图像。

        返回 (sitk.Image, np.ndarray, metadata)
        """
        meta_path = os.path.join(in_dir, 'export_metadata.json')
        metadata = None
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

        # 列出所有 tiff/tif 文件
        files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.tif', '.tiff'))]
        if not files:
            raise RuntimeError('未在目录中找到 TIFF 文件')

        # 自然数值排序函数
        def natural_key(s):
            nums = re.findall(r"\d+", s)
            if nums:
                return int(nums[-1])
            return s

        files = sorted(files, key=natural_key)

        # 读取所有切片为 uint16
        slices = []
        progress = QtWidgets.QProgressDialog("正在读取切片...", "取消", 0, len(files), self)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.show()
        for i, fname in enumerate(files):
            if progress.wasCanceled():
                break
            path = os.path.join(in_dir, fname)
            img = imageio.imread(path)
            # 强制为 uint16
            img = np.asarray(img).astype(np.uint16)
            slices.append(img)
            progress.setValue(i + 1)
            QtWidgets.QApplication.processEvents()
        progress.close()

        # 堆叠为 (N, H, W)
        stack = np.stack(slices, axis=0)

        if metadata is not None:
            axis = int(metadata.get('axis', 0))
            shape = tuple(metadata.get('shape', stack.shape))
            spacing = tuple(metadata.get('spacing', (1.0, 1.0, 1.0)))

            # 根据导出轴将 stack 放回原始形状
            if axis == 0:
                vol = stack
            elif axis == 1:
                # stack currently (N, H, W) where N was Y slices -> need (Z,Y,X)
                # original shape = (Z,Y,X)
                # We received slices along Y: each slice has shape (Z,X) if exported along Y. But our export always saved 2D arrays with consistent orientation.
                vol = np.transpose(stack, (1, 0, 2))
            else:
                vol = np.transpose(stack, (1, 2, 0))

            # Ensure final shape matches metadata
            if vol.shape != shape:
                try:
                    vol = vol.reshape(shape)
                except Exception:
                    # 如果形状不匹配，尽量调整
                    pass

            sitk_image = sitk.GetImageFromArray(vol)
            sitk_image.SetSpacing(spacing)
            return sitk_image, vol.astype(np.uint16), metadata
        else:
            # 未找到 metadata，默认认为沿 Z 堆叠
            sitk_image = sitk.GetImageFromArray(stack)
            sitk_image.SetSpacing((1.0, 1.0, 1.0))
            return sitk_image, stack.astype(np.uint16), {'axis': 0, 'shape': stack.shape, 'spacing': (1.0,1.0,1.0)}

