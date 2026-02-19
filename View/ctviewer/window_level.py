"""
窗宽窗位控制功能
负责管理图像的窗宽窗位调整
"""

import numpy as np
from PyQt5 import QtWidgets, QtCore


class WindowLevelControl:
    """窗宽窗位控制类，作为Mixin使用"""
    
    def on_window_level_changed(self):
        """窗宽窗位改变时的处理"""
        if self.raw_array is None:
            return
        if getattr(self, '_syncing_histogram_window', False):
            return
        
        self.window_width = self.ww_slider.value()
        self.window_level = self.wl_slider.value()
        self.ww_value.setText(str(int(self.window_width)))
        self.wl_value.setText(str(int(self.window_level)))

        if hasattr(self, 'prop_window_label'):
            self.prop_window_label.setText(f"W: {int(self.window_width)}, L: {int(self.window_level)}")

        if hasattr(self, '_sync_histogram_lines_to_window_level'):
            self._sync_histogram_lines_to_window_level()
            if hasattr(self, 'histogram_canvas'):
                self.histogram_canvas.draw_idle()
        
        # 更新所有视图
        self.update_all_views()
    
    def reset_window_level(self):
        """重置窗宽窗位"""
        if self.raw_array is None:
            return
        
        # 计算数据范围
        data_min = float(self.raw_array.min())
        data_max = float(self.raw_array.max())
        
        # 重置为全范围
        self.window_width = int(data_max - data_min)
        self.window_level = int((data_max + data_min) / 2)

        if hasattr(self, 'prop_window_label'):
            self.prop_window_label.setText(f"W: {int(self.window_width)}, L: {int(self.window_level)}")
        
        self.ww_slider.setValue(self.window_width)
        self.wl_slider.setValue(self.window_level)

        if hasattr(self, '_sync_histogram_lines_to_window_level'):
            self._sync_histogram_lines_to_window_level()
            if hasattr(self, 'histogram_canvas'):
                self.histogram_canvas.draw_idle()
    
    def apply_window_level_to_slice(self, slice_array):
        """将窗宽窗位应用到单个切片（内存高效）"""
        if slice_array is None:
            return slice_array
        
        # 计算窗口的最小值和最大值
        ww_min = self.window_level - self.window_width / 2.0
        ww_max = self.window_level + self.window_width / 2.0
        
        # 检查窗宽是否为0，避免除零错误
        if ww_max - ww_min <= 0:
            return slice_array
        
        # 应用窗宽窗位到切片（内存高效）
        temp_slice = slice_array.astype(np.float32)
        temp_slice = (temp_slice - ww_min) / (ww_max - ww_min) * 65535.0
        np.clip(temp_slice, 0, 65535, out=temp_slice)
        
        return temp_slice.astype(np.uint16)
    
    def apply_segmentation_display(self, slice_array):
        """
        为分割结果应用优化的显示映射
        
        分割结果通常值范围很小（如0-255），直接显示会很暗淡。
        此函数将分割值映射到完整的显示范围，使其清晰可见。
        
        参数
        ----
        slice_array : np.ndarray
            分割结果的切片数组
            
        返回
        ----
        np.ndarray
            映射后的uint16数组，适合显示
        """
        if slice_array is None:
            return slice_array
        
        # 获取当前切片的数据范围
        slice_min = float(slice_array.min())
        slice_max = float(slice_array.max())
        
        # 如果切片全为0或没有变化，直接返回
        if slice_max - slice_min <= 0:
            return slice_array.astype(np.uint16)
        
        # 将分割值映射到完整的uint16范围 [0, 65535]
        # 这样可以确保分割结果清晰可见
        temp_slice = slice_array.astype(np.float32)
        temp_slice = (temp_slice - slice_min) / (slice_max - slice_min) * 65535.0
        
        return temp_slice.astype(np.uint16)
    
    def apply_window_level_to_data(self):
        """将窗宽窗位应用到整个数据集（已弃用，保留以兼容旧代码）"""
        # 此方法已弃用，不再使用，以避免大数据集的内存问题
        # 窗宽窗位现在在显示切片时实时应用
        pass
    
    def update_all_views(self):
        """更新所有2D视图"""
        if self.axial_viewer:
            self.axial_viewer.update_slice(self.axial_viewer.slider.value())
        if self.sag_viewer:
            self.sag_viewer.update_slice(self.sag_viewer.slider.value())
        if self.cor_viewer:
            self.cor_viewer.update_slice(self.cor_viewer.slider.value())

