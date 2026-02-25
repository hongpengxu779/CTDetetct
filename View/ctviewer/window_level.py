"""
窗宽窗位控制功能
负责管理图像的窗宽窗位调整
"""

import numpy as np
from PyQt5 import QtWidgets, QtCore


class WindowLevelControl:
    """窗宽窗位控制类，作为Mixin使用"""

    def _apply_2d_lut(self, slice_array):
        """按当前2D设置对切片应用LUT/alpha LUT。"""
        if slice_array is None:
            return slice_array

        lut_name = 'grayscale'
        if hasattr(self, 'lut_2d_combo'):
            lut_name = str(self.lut_2d_combo.currentText()).lower()

        use_alpha_lut = bool(getattr(self, 'chk_use_alpha_lut', None) and self.chk_use_alpha_lut.isChecked())

        arr_u16 = slice_array.astype(np.uint16)
        if lut_name == 'grayscale':
            if use_alpha_lut:
                alpha = arr_u16.astype(np.float32) / 65535.0
                arr_u16 = np.clip(arr_u16.astype(np.float32) * alpha, 0, 65535).astype(np.uint16)
            return arr_u16

        norm = arr_u16.astype(np.float32) / 65535.0

        if lut_name == 'hot':
            r = np.clip(norm * 3.0, 0.0, 1.0)
            g = np.clip(norm * 3.0 - 1.0, 0.0, 1.0)
            b = np.clip(norm * 3.0 - 2.0, 0.0, 1.0)
        elif lut_name == 'bone':
            r = np.clip(0.8 * norm + 0.2, 0.0, 1.0)
            g = np.clip(0.85 * norm + 0.15, 0.0, 1.0)
            b = np.clip(norm, 0.0, 1.0)
        elif lut_name == 'jet':
            r = np.clip(1.5 - np.abs(4.0 * norm - 3.0), 0.0, 1.0)
            g = np.clip(1.5 - np.abs(4.0 * norm - 2.0), 0.0, 1.0)
            b = np.clip(1.5 - np.abs(4.0 * norm - 1.0), 0.0, 1.0)
        else:
            r = g = b = norm

        rgb = np.stack([r, g, b], axis=-1)
        if use_alpha_lut:
            rgb = rgb * norm[..., None]

        return np.clip(rgb * 255.0, 0, 255).astype(np.uint8)

    def apply_window_level_drag_delta(self, delta_x, delta_y):
        """在2D视图拖拽时调整窗宽窗位（左右改窗宽，上下改窗位）"""
        if self.raw_array is None:
            return
        if not hasattr(self, 'ww_slider') or not hasattr(self, 'wl_slider'):
            return

        if hasattr(self, 'histogram_data_range'):
            data_min, data_max = self.histogram_data_range
            data_span = max(1.0, float(data_max - data_min))
        else:
            data_span = max(1.0, float(self.raw_array.max() - self.raw_array.min()))

        sensitivity = max(1.0, data_span / 512.0)
        new_width = float(self.window_width) + float(delta_x) * sensitivity
        new_level = float(self.window_level) - float(delta_y) * sensitivity

        ww_min, ww_max = self.ww_slider.minimum(), self.ww_slider.maximum()
        wl_min, wl_max = self.wl_slider.minimum(), self.wl_slider.maximum()
        new_width = int(round(max(ww_min, min(ww_max, new_width))))
        new_level = int(round(max(wl_min, min(wl_max, new_level))))

        self.ww_slider.setValue(new_width)
        self.wl_slider.setValue(new_level)

    def apply_window_level_from_roi(self, view_type, slice_index, x0, y0, x1, y1):
        """根据2D视图ROI计算窗宽窗位并应用到当前数据集"""
        if self.array is None:
            return False
        if not hasattr(self, 'ww_slider') or not hasattr(self, 'wl_slider'):
            return False

        x_min, x_max = sorted((int(x0), int(x1)))
        y_min, y_max = sorted((int(y0), int(y1)))

        try:
            if view_type == 'axial':
                if not (0 <= slice_index < self.array.shape[0]):
                    return False
                x_min = max(0, min(self.array.shape[2] - 1, x_min))
                x_max = max(0, min(self.array.shape[2] - 1, x_max))
                y_min = max(0, min(self.array.shape[1] - 1, y_min))
                y_max = max(0, min(self.array.shape[1] - 1, y_max))
                roi = self.array[slice_index, y_min:y_max + 1, x_min:x_max + 1]

            elif view_type == 'sagittal':
                if not (0 <= slice_index < self.array.shape[2]):
                    return False
                x_min = max(0, min(self.array.shape[1] - 1, x_min))
                x_max = max(0, min(self.array.shape[1] - 1, x_max))
                y_min = max(0, min(self.array.shape[0] - 1, y_min))
                y_max = max(0, min(self.array.shape[0] - 1, y_max))
                roi = self.array[y_min:y_max + 1, x_min:x_max + 1, slice_index]

            elif view_type == 'coronal':
                if not (0 <= slice_index < self.array.shape[1]):
                    return False
                x_min = max(0, min(self.array.shape[2] - 1, x_min))
                x_max = max(0, min(self.array.shape[2] - 1, x_max))
                y_min = max(0, min(self.array.shape[0] - 1, y_min))
                y_max = max(0, min(self.array.shape[0] - 1, y_max))
                roi = self.array[y_min:y_max + 1, slice_index, x_min:x_max + 1]
            else:
                return False

            if roi.size == 0:
                return False

            roi_min = float(np.min(roi))
            roi_max = float(np.max(roi))
            if roi_max <= roi_min:
                return False

            new_width = roi_max - roi_min
            new_level = 0.5 * (roi_max + roi_min)

            ww_min, ww_max = self.ww_slider.minimum(), self.ww_slider.maximum()
            wl_min, wl_max = self.wl_slider.minimum(), self.wl_slider.maximum()
            width_int = int(round(max(ww_min, min(ww_max, new_width))))
            level_int = int(round(max(wl_min, min(wl_max, new_level))))

            self.ww_slider.setValue(width_int)
            self.wl_slider.setValue(level_int)

            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage(
                        f"ROI自动窗调平已应用: 窗宽={width_int}, 窗位={level_int}",
                    3500
                )
            return True

        except Exception as exc:
            print(f"ROI自动窗调平失败: {exc}")
            return False
    
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
             self.prop_window_label.setText(f"窗宽: {int(self.window_width)}, 窗位: {int(self.window_level)}")

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
             self.prop_window_label.setText(f"窗宽: {int(self.window_width)}, 窗位: {int(self.window_level)}")
        
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
        
        temp_slice = temp_slice.astype(np.uint16)
        return self._apply_2d_lut(temp_slice)
    
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
        
        temp_slice = temp_slice.astype(np.uint16)
        return self._apply_2d_lut(temp_slice)
    
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

