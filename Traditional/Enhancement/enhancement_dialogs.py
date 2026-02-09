"""
图像增强对话框
包含直方图均衡化、CLAHE、Retinex SSR、去雾的参数设置和预览对话框

预览功能：对整个3D数据执行增强处理后，通过滑块浏览任意切片的增强效果。
确认时若已预览则直接复用结果，否则再做一次全量处理。
"""

from PyQt5 import QtWidgets, QtCore, QtGui
import numpy as np
from .enhancement_ops import EnhancementOps


class _BaseEnhancementDialog(QtWidgets.QDialog):
    """增强对话框基类，提供3D预览功能"""

    def __init__(self, title, image_array, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(700, 550)

        self.image_array = image_array
        self.result_array = None
        self._preview_volume = None  # 预览用的增强后3D数据
        self.current_slice_idx = image_array.shape[0] // 2

        # 主布局
        main_layout = QtWidgets.QVBoxLayout(self)

        # 上部：预览区
        preview_layout = QtWidgets.QHBoxLayout()

        # 原始图标签
        self.label_original = QtWidgets.QLabel("原始")
        self.label_original.setAlignment(QtCore.Qt.AlignCenter)
        self.label_original.setMinimumSize(300, 300)
        self.label_original.setStyleSheet("border:1px solid #ccc; background:#000;")
        self.label_original.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

        # 预览图标签
        self.label_preview = QtWidgets.QLabel("预览")
        self.label_preview.setAlignment(QtCore.Qt.AlignCenter)
        self.label_preview.setMinimumSize(300, 300)
        self.label_preview.setStyleSheet("border:1px solid #ccc; background:#000;")
        self.label_preview.setSizePolicy(
            QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

        # 等比例拉伸，确保两侧大小始终一致
        preview_layout.addWidget(self.label_original, 1)
        preview_layout.addWidget(self.label_preview, 1)
        main_layout.addLayout(preview_layout)

        # 切片选择滑块
        slice_layout = QtWidgets.QHBoxLayout()
        slice_layout.addWidget(QtWidgets.QLabel("预览切片:"))
        self.slice_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slice_slider.setRange(0, image_array.shape[0] - 1)
        self.slice_slider.setValue(self.current_slice_idx)
        self.slice_slider.valueChanged.connect(self._on_slice_changed)
        slice_layout.addWidget(self.slice_slider)
        self.slice_label = QtWidgets.QLabel(f"{self.current_slice_idx}/{image_array.shape[0]-1}")
        slice_layout.addWidget(self.slice_label)
        main_layout.addLayout(slice_layout)

        # 参数区（子类填充）
        self.params_group = QtWidgets.QGroupBox("参数设置")
        self.params_layout = QtWidgets.QFormLayout(self.params_group)
        main_layout.addWidget(self.params_group)

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

    def _slice_to_pixmap(self, slice_2d: np.ndarray) -> QtGui.QPixmap:
        """将2D切片转换为QPixmap"""
        s = slice_2d.astype(np.float64)
        smin, smax = s.min(), s.max()
        if smax - smin > 1e-8:
            s = (s - smin) / (smax - smin) * 255.0
        u8 = s.astype(np.uint8)
        h, w = u8.shape
        u8 = np.ascontiguousarray(u8)
        qimg = QtGui.QImage(u8.data, w, h, w, QtGui.QImage.Format_Grayscale8)
        return QtGui.QPixmap.fromImage(qimg.copy())

    def _get_preview_size(self) -> QtCore.QSize:
        """获取预览区域的统一显示尺寸（取两个label中较小的那个）"""
        s1 = self.label_original.size()
        s2 = self.label_preview.size()
        w = min(s1.width(), s2.width())
        h = min(s1.height(), s2.height())
        return QtCore.QSize(max(w, 1), max(h, 1))

    def _show_original(self):
        pix = self._slice_to_pixmap(self.image_array[self.current_slice_idx])
        display_size = self._get_preview_size()
        self.label_original.setPixmap(
            pix.scaled(display_size, QtCore.Qt.KeepAspectRatio,
                       QtCore.Qt.SmoothTransformation)
        )

    def _on_slice_changed(self, val):
        self.current_slice_idx = val
        self.slice_label.setText(f"{val}/{self.image_array.shape[0]-1}")
        self._show_original()
        # 如果已有预览结果，更新预览切片
        if self._preview_volume is not None:
            self._show_preview_slice()

    def _show_preview_slice(self):
        """显示预览3D数据中当前切片"""
        if self._preview_volume is not None:
            pix = self._slice_to_pixmap(self._preview_volume[self.current_slice_idx])
            display_size = self._get_preview_size()
            self.label_preview.setPixmap(
                pix.scaled(display_size, QtCore.Qt.KeepAspectRatio,
                           QtCore.Qt.SmoothTransformation)
            )

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
                self.result_array = self._preview_volume
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

                self.result_array = self._process_volume(self.image_array, cb)
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
                self.result_array = self._preview_volume
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

                self.result_array = self._process_volume(self.image_array, cb)
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
                self.result_array = self._preview_volume
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

                self.result_array = self._process_volume(self.image_array, cb)
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
                self.result_array = self._preview_volume
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

                self.result_array = self._process_volume(self.image_array, cb)
                progress.setValue(100)
                progress.close()
            super().accept()
        except InterruptedError:
            progress.close()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", str(e))
