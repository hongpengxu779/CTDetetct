"""
图像增强对话框
包含直方图均衡化、CLAHE、Retinex SSR、去雾的参数设置和预览对话框

预览功能：对整个3D数据执行增强处理后，通过滑块浏览任意切片的增强效果。
确认时若已预览则直接复用结果，否则再做一次全量处理。
"""

from PyQt5 import QtWidgets, QtCore, QtGui
import numpy as np
from .enhancement_ops import EnhancementOps


class _FullscreenSliceDialog(QtWidgets.QDialog):
    """全屏切片查看对话框（Esc退出，双击退出）"""

    def __init__(self, pixmap: QtGui.QPixmap, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._source_pixmap = pixmap

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.image_label = QtWidgets.QLabel()
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setStyleSheet("background:#000;")
        layout.addWidget(self.image_label)

        self.close_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Escape"), self)
        self.close_shortcut.activated.connect(self.close)

        self._update_display()

    def _update_display(self):
        if self._source_pixmap.isNull():
            return
        scaled = self._source_pixmap.scaled(
            self.image_label.size(),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_display()

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.close()


class _BaseEnhancementDialog(QtWidgets.QDialog):
    """增强对话框基类，提供3D预览功能"""

    def __init__(self, title, image_array, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(1100, 760)

        self.image_array = image_array
        self.result_array = None
        self._preview_volume = None  # 预览用的增强后3D数据
        self.preview_axis = 0  # 0: 轴位(Z), 1: 冠状(Y), 2: 矢状(X)
        self.current_slice_indices = {
            0: image_array.shape[0] // 2,
            1: image_array.shape[1] // 2,
            2: image_array.shape[2] // 2,
        }

        # 预览窗宽窗位（默认启用）
        self.preview_use_window_level = True
        data_min = float(np.min(self.image_array))
        data_max = float(np.max(self.image_array))
        data_range = data_max - data_min
        if data_range < 1e-6:
            data_range = 1.0
        self.preview_ww = max(1.0, data_range)
        self.preview_wl = (data_min + data_max) / 2.0
        self._wl_slider_scale = 100.0

        # 主布局
        main_layout = QtWidgets.QVBoxLayout(self)

        # 上部：预览区
        preview_layout = QtWidgets.QHBoxLayout()

        # 原始图标签
        self.label_original = QtWidgets.QLabel("原始")
        self.label_original.setAlignment(QtCore.Qt.AlignCenter)
        self.label_original.setMinimumSize(460, 460)
        self.label_original.setStyleSheet("border:1px solid #ccc; background:#000;")
        self.label_original.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

        # 预览图标签
        self.label_preview = QtWidgets.QLabel("预览")
        self.label_preview.setAlignment(QtCore.Qt.AlignCenter)
        self.label_preview.setMinimumSize(460, 460)
        self.label_preview.setStyleSheet("border:1px solid #ccc; background:#000;")
        self.label_preview.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.label_preview.setToolTip("双击全屏查看当前预览切片")
        self.label_preview.installEventFilter(self)

        # 等比例拉伸，确保两侧大小始终一致
        preview_layout.addWidget(self.label_original, 1)
        preview_layout.addWidget(self.label_preview, 1)
        main_layout.addLayout(preview_layout)

        # 预览方向选择
        axis_layout = QtWidgets.QHBoxLayout()
        axis_layout.addWidget(QtWidgets.QLabel("预览方向:"))
        self.axis_combo = QtWidgets.QComboBox()
        self.axis_combo.addItems(["轴位 (Z)", "冠状 (Y)", "矢状 (X)"])
        self.axis_combo.setCurrentIndex(self.preview_axis)
        self.axis_combo.currentIndexChanged.connect(self._on_axis_changed)
        axis_layout.addWidget(self.axis_combo)
        axis_layout.addStretch()
        main_layout.addLayout(axis_layout)

        # 切片选择滑块
        slice_layout = QtWidgets.QHBoxLayout()
        slice_layout.addWidget(QtWidgets.QLabel("预览切片:"))
        self.slice_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slice_slider.setRange(0, self._axis_size(self.preview_axis) - 1)
        self.slice_slider.setValue(self.current_slice_indices[self.preview_axis])
        self.slice_slider.valueChanged.connect(self._on_slice_changed)
        slice_layout.addWidget(self.slice_slider)
        self.slice_label = QtWidgets.QLabel(
            f"{self.current_slice_indices[self.preview_axis]}/{self._axis_size(self.preview_axis)-1}"
        )
        slice_layout.addWidget(self.slice_label)
        main_layout.addLayout(slice_layout)

        # 预览窗宽窗位控制
        wl_group = QtWidgets.QGroupBox("预览窗宽窗位")
        wl_layout = QtWidgets.QGridLayout(wl_group)

        self.chk_preview_wl = QtWidgets.QCheckBox("启用窗宽窗位")
        self.chk_preview_wl.setChecked(True)
        self.chk_preview_wl.toggled.connect(self._on_preview_wl_toggled)
        wl_layout.addWidget(self.chk_preview_wl, 0, 0, 1, 2)

        self.btn_wl_auto = QtWidgets.QPushButton("自动")
        self.btn_wl_auto.setFixedWidth(70)
        self.btn_wl_auto.clicked.connect(self._auto_set_preview_window_level)
        wl_layout.addWidget(self.btn_wl_auto, 0, 2)

        wl_layout.addWidget(QtWidgets.QLabel("窗宽(W):"), 1, 0)
        self.slider_preview_ww = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_preview_ww.setRange(1, max(10, int(data_range * self._wl_slider_scale)))
        self.slider_preview_ww.setValue(max(1, int(self.preview_ww * self._wl_slider_scale)))
        self.slider_preview_ww.valueChanged.connect(self._on_preview_ww_changed)
        wl_layout.addWidget(self.slider_preview_ww, 1, 1)
        self.lbl_preview_ww = QtWidgets.QLabel(f"{self.preview_ww:.1f}")
        wl_layout.addWidget(self.lbl_preview_ww, 1, 2)

        wl_layout.addWidget(QtWidgets.QLabel("窗位(L):"), 2, 0)
        self.slider_preview_wl = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        wl_min = int((data_min - data_range) * self._wl_slider_scale)
        wl_max = int((data_max + data_range) * self._wl_slider_scale)
        self.slider_preview_wl.setRange(wl_min, wl_max)
        self.slider_preview_wl.setValue(int(self.preview_wl * self._wl_slider_scale))
        self.slider_preview_wl.valueChanged.connect(self._on_preview_wl_changed)
        wl_layout.addWidget(self.slider_preview_wl, 2, 1)
        self.lbl_preview_wl = QtWidgets.QLabel(f"{self.preview_wl:.1f}")
        wl_layout.addWidget(self.lbl_preview_wl, 2, 2)

        main_layout.addWidget(wl_group)

        # 参数区（子类填充）
        self.params_group = QtWidgets.QGroupBox("参数设置")
        self.params_layout = QtWidgets.QFormLayout(self.params_group)
        main_layout.addWidget(self.params_group)

        # 融合选项区
        blend_group = QtWidgets.QGroupBox("结果融合选项")
        blend_layout = QtWidgets.QVBoxLayout(blend_group)

        self.blend_with_original_checkbox = QtWidgets.QCheckBox("处理结果与原始图像加权融合")
        self.blend_with_original_checkbox.setChecked(False)
        self.blend_with_original_checkbox.toggled.connect(self._on_blend_option_changed)
        blend_layout.addWidget(self.blend_with_original_checkbox)

        alpha_layout = QtWidgets.QHBoxLayout()
        alpha_layout.addWidget(QtWidgets.QLabel("增强结果权重:"))
        self.blend_alpha_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.blend_alpha_slider.setRange(0, 100)
        self.blend_alpha_slider.setValue(70)
        self.blend_alpha_slider.valueChanged.connect(self._on_blend_alpha_changed)
        alpha_layout.addWidget(self.blend_alpha_slider)
        self.blend_alpha_label = QtWidgets.QLabel("70%")
        alpha_layout.addWidget(self.blend_alpha_label)
        blend_layout.addLayout(alpha_layout)

        blend_info = QtWidgets.QLabel("输出 = 原图 × (1-权重) + 增强图 × 权重")
        blend_info.setStyleSheet("color: #666; font-size: 9pt;")
        blend_layout.addWidget(blend_info)

        main_layout.addWidget(blend_group)

        # 预览按钮 —— 对整个3D数据做增强后预览
        preview_btn = QtWidgets.QPushButton("预览增强效果（处理全部切片）")
        preview_btn.clicked.connect(self._preview_3d)
        main_layout.addWidget(preview_btn)

        # 底部按钮
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        # 显示原始切片
        self._show_original()

    def eventFilter(self, obj, event):
        if obj is self.label_preview and event.type() == QtCore.QEvent.MouseButtonDblClick:
            self._open_preview_fullscreen()
            return True
        return super().eventFilter(obj, event)

    def _open_preview_fullscreen(self):
        idx = self.current_slice_indices[self.preview_axis]
        if self._preview_volume is not None:
            preview_slice = self._extract_slice(self._preview_volume, self.preview_axis, idx)
            if self.blend_with_original_checkbox.isChecked():
                original_slice = self._extract_slice(self.image_array, self.preview_axis, idx)
                preview_slice = self._blend_with_original_slice(original_slice, preview_slice)
            pix = self._slice_to_pixmap(preview_slice)
        else:
            pix = self._slice_to_pixmap(self._extract_slice(self.image_array, self.preview_axis, idx))

        axis_name = ["轴位", "冠状", "矢状"][self.preview_axis]
        title = f"全屏预览 - {axis_name} 第 {idx} 层"
        dlg = _FullscreenSliceDialog(pix, title, self)
        dlg.showFullScreen()
        dlg.exec_()

    def _axis_size(self, axis: int) -> int:
        return self.image_array.shape[axis]

    def _extract_slice(self, volume: np.ndarray, axis: int, idx: int) -> np.ndarray:
        if axis == 0:
            return volume[idx, :, :]
        if axis == 1:
            return volume[:, idx, :]
        return volume[:, :, idx]

    def _slice_to_pixmap(self, slice_2d: np.ndarray) -> QtGui.QPixmap:
        """将2D切片转换为QPixmap"""
        s = slice_2d.astype(np.float64)
        if self.preview_use_window_level:
            low = self.preview_wl - self.preview_ww / 2.0
            high = self.preview_wl + self.preview_ww / 2.0
            if high <= low:
                high = low + 1e-6
            s = np.clip(s, low, high)
            s = (s - low) / (high - low) * 255.0
        else:
            smin, smax = s.min(), s.max()
            if smax - smin > 1e-8:
                s = (s - smin) / (smax - smin) * 255.0
        u8 = np.clip(s, 0, 255).astype(np.uint8)
        h, w = u8.shape
        u8 = np.ascontiguousarray(u8)
        qimg = QtGui.QImage(u8.data, w, h, w, QtGui.QImage.Format_Grayscale8)
        return QtGui.QPixmap.fromImage(qimg.copy())

    def _on_preview_wl_toggled(self, checked):
        self.preview_use_window_level = bool(checked)
        self.slider_preview_ww.setEnabled(checked)
        self.slider_preview_wl.setEnabled(checked)
        self.lbl_preview_ww.setEnabled(checked)
        self.lbl_preview_wl.setEnabled(checked)
        self._show_original()
        if self._preview_volume is not None:
            self._show_preview_slice()

    def _on_preview_ww_changed(self, value):
        self.preview_ww = max(1.0, value / self._wl_slider_scale)
        self.lbl_preview_ww.setText(f"{self.preview_ww:.1f}")
        if self.preview_use_window_level:
            self._show_original()
            if self._preview_volume is not None:
                self._show_preview_slice()

    def _on_preview_wl_changed(self, value):
        self.preview_wl = value / self._wl_slider_scale
        self.lbl_preview_wl.setText(f"{self.preview_wl:.1f}")
        if self.preview_use_window_level:
            self._show_original()
            if self._preview_volume is not None:
                self._show_preview_slice()

    def _auto_set_preview_window_level(self):
        idx = self.current_slice_indices[self.preview_axis]
        src_slice = self._extract_slice(self.image_array, self.preview_axis, idx).astype(np.float64)
        smin = float(np.min(src_slice))
        smax = float(np.max(src_slice))
        ww = max(1.0, smax - smin)
        wl = (smax + smin) / 2.0
        self.preview_ww = ww
        self.preview_wl = wl

        self.slider_preview_ww.blockSignals(True)
        ww_val = max(self.slider_preview_ww.minimum(), min(self.slider_preview_ww.maximum(), int(ww * self._wl_slider_scale)))
        self.slider_preview_ww.setValue(ww_val)
        self.slider_preview_ww.blockSignals(False)

        self.slider_preview_wl.blockSignals(True)
        wl_val = max(self.slider_preview_wl.minimum(), min(self.slider_preview_wl.maximum(), int(wl * self._wl_slider_scale)))
        self.slider_preview_wl.setValue(wl_val)
        self.slider_preview_wl.blockSignals(False)

        self.lbl_preview_ww.setText(f"{self.preview_ww:.1f}")
        self.lbl_preview_wl.setText(f"{self.preview_wl:.1f}")
        self._show_original()
        if self._preview_volume is not None:
            self._show_preview_slice()

    def _get_preview_size(self) -> QtCore.QSize:
        """获取预览区域的统一显示尺寸（取两个label中较小的那个）"""
        s1 = self.label_original.size()
        s2 = self.label_preview.size()
        w = min(s1.width(), s2.width())
        h = min(s1.height(), s2.height())
        return QtCore.QSize(max(w, 1), max(h, 1))

    def _show_original(self):
        idx = self.current_slice_indices[self.preview_axis]
        pix = self._slice_to_pixmap(self._extract_slice(self.image_array, self.preview_axis, idx))
        display_size = self._get_preview_size()
        self.label_original.setPixmap(
            pix.scaled(display_size, QtCore.Qt.KeepAspectRatio,
                       QtCore.Qt.SmoothTransformation)
        )

    def _on_axis_changed(self, axis_idx):
        self.preview_axis = axis_idx
        max_idx = self._axis_size(self.preview_axis) - 1
        current_idx = min(self.current_slice_indices[self.preview_axis], max_idx)
        self.current_slice_indices[self.preview_axis] = current_idx

        self.slice_slider.blockSignals(True)
        self.slice_slider.setRange(0, max_idx)
        self.slice_slider.setValue(current_idx)
        self.slice_slider.blockSignals(False)
        self.slice_label.setText(f"{current_idx}/{max_idx}")

        self._show_original()
        if self._preview_volume is not None:
            self._show_preview_slice()

    def _on_slice_changed(self, val):
        self.current_slice_indices[self.preview_axis] = val
        self.slice_label.setText(f"{val}/{self._axis_size(self.preview_axis)-1}")
        self._show_original()
        # 如果已有预览结果，更新预览切片
        if self._preview_volume is not None:
            self._show_preview_slice()

    def _show_preview_slice(self):
        """显示预览3D数据中当前切片"""
        if self._preview_volume is not None:
            idx = self.current_slice_indices[self.preview_axis]
            preview_slice = self._extract_slice(self._preview_volume, self.preview_axis, idx)
            if self.blend_with_original_checkbox.isChecked():
                original_slice = self._extract_slice(self.image_array, self.preview_axis, idx)
                preview_slice = self._blend_with_original_slice(original_slice, preview_slice)
            pix = self._slice_to_pixmap(preview_slice)
            display_size = self._get_preview_size()
            self.label_preview.setPixmap(
                pix.scaled(display_size, QtCore.Qt.KeepAspectRatio,
                           QtCore.Qt.SmoothTransformation)
            )

    def _blend_with_original_slice(self, original_slice: np.ndarray, enhanced_slice: np.ndarray) -> np.ndarray:
        alpha = self.blend_alpha_slider.value() / 100.0
        orig = original_slice.astype(np.float32)
        enh = enhanced_slice.astype(np.float32)
        blended = (1.0 - alpha) * orig + alpha * enh
        return self._cast_to_original_dtype(blended)

    def _cast_to_original_dtype(self, value_array: np.ndarray) -> np.ndarray:
        target_dtype = self.image_array.dtype
        if np.issubdtype(target_dtype, np.integer):
            info = np.iinfo(target_dtype)
            return np.clip(value_array, info.min, info.max).astype(target_dtype)
        if np.issubdtype(target_dtype, np.floating):
            return value_array.astype(target_dtype)
        return value_array.astype(self.image_array.dtype)

    def _apply_blend_if_enabled(self, enhanced_volume: np.ndarray) -> np.ndarray:
        if not self.blend_with_original_checkbox.isChecked():
            return enhanced_volume
        alpha = self.blend_alpha_slider.value() / 100.0
        orig = self.image_array.astype(np.float32)
        enh = enhanced_volume.astype(np.float32)
        blended = (1.0 - alpha) * orig + alpha * enh
        return self._cast_to_original_dtype(blended)

    def _on_blend_option_changed(self, checked):
        self.blend_alpha_slider.setEnabled(checked)
        if self._preview_volume is not None:
            self._show_preview_slice()

    def _on_blend_alpha_changed(self, value):
        self.blend_alpha_label.setText(f"{value}%")
        if self._preview_volume is not None and self.blend_with_original_checkbox.isChecked():
            self._show_preview_slice()

    def _preview_3d(self):
        """对整个3D数据执行增强，然后预览任意切片"""
        try:
            progress = QtWidgets.QProgressDialog(
                "正在预览增强效果（处理全部切片）...", "取消", 0, 100, self)
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.show()

            def cb(cur, total):
                progress.setValue(int(cur / total * 100))
                QtWidgets.QApplication.processEvents()
                if progress.wasCanceled():
                    raise InterruptedError("用户取消")

            self._preview_volume = self._process_volume(self.image_array, cb)
            progress.setValue(100)
            progress.close()
            self._show_preview_slice()
        except InterruptedError:
            progress.close()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "预览失败", str(e))

    def _process_volume(self, volume: np.ndarray, progress_callback=None) -> np.ndarray:
        """子类需要重写：对整个3D数据执行增强处理，用于预览和最终确认"""
        raise NotImplementedError

    def _on_param_changed(self):
        """参数变化时清除预览缓存，提示用户需要重新预览"""
        self._preview_volume = None
        self.label_preview.setText("参数已修改，请重新预览")

    def get_result(self) -> np.ndarray:
        return self.result_array

    def resizeEvent(self, event):
        """窗口大小改变时同步刷新两侧预览图"""
        super().resizeEvent(event)
        self._show_original()
        if self._preview_volume is not None:
            self._show_preview_slice()


# ===== 1. 直方图均衡化对话框 =====

class HistogramEqualizationDialog(_BaseEnhancementDialog):
    """直方图均衡化对话框"""

    def __init__(self, image_array, parent=None):
        super().__init__("直方图均衡化", image_array, parent)
        info_label = QtWidgets.QLabel("直方图均衡化无需额外参数，将自动拉伸对比度。")
        info_label.setWordWrap(True)
        self.params_layout.addRow(info_label)

    def _process_volume(self, volume, progress_callback=None):
        return EnhancementOps.histogram_equalization_3d(
            volume, progress_callback=progress_callback)

    def accept(self):
        try:
            if self._preview_volume is not None:
                self.result_array = self._apply_blend_if_enabled(self._preview_volume)
            else:
                progress = QtWidgets.QProgressDialog(
                    "正在进行直方图均衡化...", "取消", 0, 100, self)
                progress.setWindowModality(QtCore.Qt.WindowModal)
                progress.show()

                def cb(cur, total):
                    progress.setValue(int(cur / total * 100))
                    QtWidgets.QApplication.processEvents()
                    if progress.wasCanceled():
                        raise InterruptedError("用户取消")

                enhanced = self._process_volume(self.image_array, cb)
                self.result_array = self._apply_blend_if_enabled(enhanced)
                progress.setValue(100)
                progress.close()
            super().accept()
        except InterruptedError:
            progress.close()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", str(e))


# ===== 2. CLAHE 对话框 =====

class CLAHEDialog(_BaseEnhancementDialog):
    """限制对比度自适应直方图均衡化 (CLAHE) 对话框"""

    def __init__(self, image_array, parent=None):
        super().__init__("限制对比度直方图均衡化 (CLAHE)", image_array, parent)

        self.clip_limit_spin = QtWidgets.QDoubleSpinBox()
        self.clip_limit_spin.setRange(0.1, 40.0)
        self.clip_limit_spin.setSingleStep(0.5)
        self.clip_limit_spin.setValue(2.0)
        self.clip_limit_spin.valueChanged.connect(self._on_param_changed)
        self.params_layout.addRow("对比度限制 (clipLimit):", self.clip_limit_spin)

        self.tile_w_spin = QtWidgets.QSpinBox()
        self.tile_w_spin.setRange(2, 64)
        self.tile_w_spin.setValue(8)
        self.tile_w_spin.valueChanged.connect(self._on_param_changed)
        self.params_layout.addRow("网格宽度:", self.tile_w_spin)

        self.tile_h_spin = QtWidgets.QSpinBox()
        self.tile_h_spin.setRange(2, 64)
        self.tile_h_spin.setValue(8)
        self.tile_h_spin.valueChanged.connect(self._on_param_changed)
        self.params_layout.addRow("网格高度:", self.tile_h_spin)

    def _process_volume(self, volume, progress_callback=None):
        return EnhancementOps.clahe_3d(
            volume,
            clip_limit=self.clip_limit_spin.value(),
            tile_grid_size=(self.tile_w_spin.value(), self.tile_h_spin.value()),
            progress_callback=progress_callback
        )

    def accept(self):
        try:
            if self._preview_volume is not None:
                self.result_array = self._apply_blend_if_enabled(self._preview_volume)
            else:
                progress = QtWidgets.QProgressDialog(
                    "正在进行CLAHE处理...", "取消", 0, 100, self)
                progress.setWindowModality(QtCore.Qt.WindowModal)
                progress.show()

                def cb(cur, total):
                    progress.setValue(int(cur / total * 100))
                    QtWidgets.QApplication.processEvents()
                    if progress.wasCanceled():
                        raise InterruptedError("用户取消")

                enhanced = self._process_volume(self.image_array, cb)
                self.result_array = self._apply_blend_if_enabled(enhanced)
                progress.setValue(100)
                progress.close()
            super().accept()
        except InterruptedError:
            progress.close()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", str(e))


# ===== 3. Retinex SSR 对话框 =====

class RetinexSSRDialog(_BaseEnhancementDialog):
    """单尺度 Retinex (SSR) 对话框"""

    def __init__(self, image_array, parent=None):
        super().__init__("Retinex SSR 增强", image_array, parent)

        self.sigma_spin = QtWidgets.QDoubleSpinBox()
        self.sigma_spin.setRange(1.0, 500.0)
        self.sigma_spin.setSingleStep(10.0)
        self.sigma_spin.setValue(80.0)
        self.sigma_spin.valueChanged.connect(self._on_param_changed)
        self.params_layout.addRow("高斯sigma:", self.sigma_spin)

        sigma_info = QtWidgets.QLabel("较小的sigma强调细节增强，\n较大的sigma强调动态范围压缩。")
        sigma_info.setWordWrap(True)
        sigma_info.setStyleSheet("color: #666; font-size: 9pt;")
        self.params_layout.addRow(sigma_info)

    def _process_volume(self, volume, progress_callback=None):
        return EnhancementOps.retinex_ssr_3d(
            volume,
            sigma=self.sigma_spin.value(),
            progress_callback=progress_callback
        )

    def accept(self):
        try:
            if self._preview_volume is not None:
                self.result_array = self._apply_blend_if_enabled(self._preview_volume)
            else:
                progress = QtWidgets.QProgressDialog(
                    "正在进行Retinex SSR处理...", "取消", 0, 100, self)
                progress.setWindowModality(QtCore.Qt.WindowModal)
                progress.show()

                def cb(cur, total):
                    progress.setValue(int(cur / total * 100))
                    QtWidgets.QApplication.processEvents()
                    if progress.wasCanceled():
                        raise InterruptedError("用户取消")

                enhanced = self._process_volume(self.image_array, cb)
                self.result_array = self._apply_blend_if_enabled(enhanced)
                progress.setValue(100)
                progress.close()
            super().accept()
        except InterruptedError:
            progress.close()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", str(e))


# ===== 4. 去雾对话框 =====

class DehazeDialog(_BaseEnhancementDialog):
    """暗通道先验去雾对话框"""

    def __init__(self, image_array, parent=None):
        super().__init__("暗通道先验去雾", image_array, parent)

        self.omega_spin = QtWidgets.QDoubleSpinBox()
        self.omega_spin.setRange(0.1, 1.0)
        self.omega_spin.setSingleStep(0.05)
        self.omega_spin.setDecimals(2)
        self.omega_spin.setValue(0.95)
        self.omega_spin.valueChanged.connect(self._on_param_changed)
        self.params_layout.addRow("去雾程度 (omega):", self.omega_spin)

        self.t_min_spin = QtWidgets.QDoubleSpinBox()
        self.t_min_spin.setRange(0.01, 0.5)
        self.t_min_spin.setSingleStep(0.01)
        self.t_min_spin.setDecimals(2)
        self.t_min_spin.setValue(0.1)
        self.t_min_spin.valueChanged.connect(self._on_param_changed)
        self.params_layout.addRow("透射率下限 (t_min):", self.t_min_spin)

        self.patch_spin = QtWidgets.QSpinBox()
        self.patch_spin.setRange(3, 51)
        self.patch_spin.setSingleStep(2)
        self.patch_spin.setValue(15)
        self.patch_spin.valueChanged.connect(self._on_param_changed)
        self.params_layout.addRow("邻域大小 (patch):", self.patch_spin)

        dehaze_info = QtWidgets.QLabel("omega越大去雾越彻底；\npatch越大处理越平滑。")
        dehaze_info.setWordWrap(True)
        dehaze_info.setStyleSheet("color: #666; font-size: 9pt;")
        self.params_layout.addRow(dehaze_info)

    def _process_volume(self, volume, progress_callback=None):
        return EnhancementOps.dehaze_3d(
            volume,
            omega=self.omega_spin.value(),
            t_min=self.t_min_spin.value(),
            patch_size=self.patch_spin.value(),
            progress_callback=progress_callback
        )

    def accept(self):
        try:
            if self._preview_volume is not None:
                self.result_array = self._apply_blend_if_enabled(self._preview_volume)
            else:
                progress = QtWidgets.QProgressDialog(
                    "正在进行去雾处理...", "取消", 0, 100, self)
                progress.setWindowModality(QtCore.Qt.WindowModal)
                progress.show()

                def cb(cur, total):
                    progress.setValue(int(cur / total * 100))
                    QtWidgets.QApplication.processEvents()
                    if progress.wasCanceled():
                        raise InterruptedError("用户取消")

                enhanced = self._process_volume(self.image_array, cb)
                self.result_array = self._apply_blend_if_enabled(enhanced)
                progress.setValue(100)
                progress.close()
            super().accept()
        except InterruptedError:
            progress.close()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", str(e))


# ===== 5. mUSICA 对话框 =====

class MUSICADialog(_BaseEnhancementDialog):
    """mUSICA增强对话框 - 完全模拟导出切片→处理→重组的流程"""

    def __init__(self, image_array, parent=None):
        super().__init__("mUSICA 增强", image_array, parent)
        
        # 保存原始输入数据（未转换）
        self._original_input = image_array

        self.level_spin = QtWidgets.QSpinBox()
        self.level_spin.setRange(1, 8)
        self.level_spin.setValue(8)
        self.level_spin.valueChanged.connect(self._on_param_changed)
        self.params_layout.addRow("Level:", self.level_spin)

        self.strength_spin = QtWidgets.QSpinBox()
        self.strength_spin.setRange(0, 100)
        self.strength_spin.setValue(100)
        self.strength_spin.valueChanged.connect(self._on_param_changed)
        self.params_layout.addRow("Strength:", self.strength_spin)

        info = QtWidgets.QLabel(
            "完全模拟导出切片→mUSICA处理→重组的流程：\n"
            "1. 逐切片转换为 uint16（与导出TIFF一致）\n"
            "2. 调用 ImageMaster.dll 的 IM_MUSCIA_SSE 处理\n"
            "3. 重新组合为3D体数据\n"
            "Level 控制多尺度层数，Strength 控制增强强度。"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; font-size: 9pt;")
        self.params_layout.addRow(info)

    def _process_volume(self, volume, progress_callback=None):
        """
        完全模拟导出切片→处理→重组的流程
        
        流程：
        1. 逐切片: slice.astype(np.uint16) - 与 export_slices 中的转换完全一致
        2. 调用 DLL: _musica_slice_imagemaster(slice_u16, level, strength)
        3. 收集所有处理后的切片，组合成3D数组
        """
        level = self.level_spin.value()
        strength = self.strength_spin.value()
        
        depth = volume.shape[0]
        result_slices = []
        
        # 检查 DLL 是否可用
        dll_func = EnhancementOps._load_imagemaster_musica_func()
        use_dll = dll_func is not None
        
        print(f"[mUSICA模拟导出流程] 输入: dtype={volume.dtype}, shape={volume.shape}")
        print(f"[mUSICA模拟导出流程] 参数: Level={level}, Strength={strength}")
        print(f"[mUSICA模拟导出流程] 使用DLL: {'是' if use_dll else '否'}")
        
        for z in range(depth):
            # Step 1: 模拟导出 - 与 export_slices 中的 arr.astype(np.uint16) 完全一致
            slice_original = volume[z]
            slice_u16 = slice_original.astype(np.uint16)
            
            # Step 2: 调用 DLL 处理
            if use_dll:
                try:
                    slice_processed = EnhancementOps._musica_slice_imagemaster(
                        slice_u16, level, strength
                    )
                except Exception as e:
                    print(f"[mUSICA] 切片 {z} DLL失败，使用回退: {e}")
                    slice_processed = EnhancementOps._musica_slice_u16(
                        slice_u16, level, strength
                    )
            else:
                slice_processed = EnhancementOps._musica_slice_u16(
                    slice_u16, level, strength
                )
            
            result_slices.append(slice_processed)
            
            if progress_callback and z % max(1, depth // 20) == 0:
                progress_callback(z, depth)
        
        # Step 3: 重组为3D数组
        result = np.stack(result_slices, axis=0)
        print(f"[mUSICA模拟导出流程] 输出: dtype={result.dtype}, shape={result.shape}")
        print(f"[mUSICA模拟导出流程] 输出范围: [{result.min()}, {result.max()}]")
        
        return result

    def accept(self):
        try:
            if self._preview_volume is not None:
                self.result_array = self._apply_blend_if_enabled(self._preview_volume)
            else:
                progress = QtWidgets.QProgressDialog(
                    "正在进行mUSICA增强（模拟导出流程）...", "取消", 0, 100, self)
                progress.setWindowModality(QtCore.Qt.WindowModal)
                progress.show()

                def cb(cur, total):
                    progress.setValue(int(cur / total * 100))
                    QtWidgets.QApplication.processEvents()
                    if progress.wasCanceled():
                        raise InterruptedError("用户取消")

                enhanced = self._process_volume(self.image_array, cb)
                self.result_array = self._apply_blend_if_enabled(enhanced)
                progress.setValue(100)
                progress.close()
            super().accept()
        except InterruptedError:
            progress.close()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", str(e))
