"""
基于光照补偿的模糊增强对话框

提供参数设置和3D预览功能，允许用户交互式调整以下参数：
- 形态学结构元素大小
- 高斯低通滤波σ
- Prewitt双阈值
- 光照补偿σ及补偿强度
"""

from PyQt5 import QtWidgets, QtCore
import numpy as np
from .enhancement_dialogs import _BaseEnhancementDialog
from .fuzzy_enhancement_ops import FuzzyEnhancementOps


class FuzzyEnhancementDialog(_BaseEnhancementDialog):
    """基于光照补偿的模糊增强对话框"""

    def __init__(self, image_array, parent=None):
        super().__init__("基于光照补偿的模糊增强", image_array, parent)

        # ---- 形态学参数 ----
        self.morph_kernel_spin = QtWidgets.QSpinBox()
        self.morph_kernel_spin.setRange(3, 21)
        self.morph_kernel_spin.setSingleStep(2)
        self.morph_kernel_spin.setValue(5)
        self.morph_kernel_spin.valueChanged.connect(self._on_param_changed)
        self.params_layout.addRow("形态学核大小 (奇数):", self.morph_kernel_spin)

        # ---- 高斯低通参数 ----
        self.gauss_sigma_spin = QtWidgets.QDoubleSpinBox()
        self.gauss_sigma_spin.setRange(0.5, 10.0)
        self.gauss_sigma_spin.setSingleStep(0.5)
        self.gauss_sigma_spin.setValue(1.5)
        self.gauss_sigma_spin.valueChanged.connect(self._on_param_changed)
        self.params_layout.addRow("高斯滤波σ (噪点抑制):", self.gauss_sigma_spin)

        # ---- Prewitt 双阈值参数 ----
        self.prewitt_low_spin = QtWidgets.QDoubleSpinBox()
        self.prewitt_low_spin.setRange(0.01, 0.5)
        self.prewitt_low_spin.setSingleStep(0.01)
        self.prewitt_low_spin.setDecimals(2)
        self.prewitt_low_spin.setValue(0.05)
        self.prewitt_low_spin.valueChanged.connect(self._on_param_changed)
        self.params_layout.addRow("Prewitt低阈值:", self.prewitt_low_spin)

        self.prewitt_high_spin = QtWidgets.QDoubleSpinBox()
        self.prewitt_high_spin.setRange(0.05, 0.8)
        self.prewitt_high_spin.setSingleStep(0.01)
        self.prewitt_high_spin.setDecimals(2)
        self.prewitt_high_spin.setValue(0.15)
        self.prewitt_high_spin.valueChanged.connect(self._on_param_changed)
        self.params_layout.addRow("Prewitt高阈值:", self.prewitt_high_spin)

        # ---- 光照补偿参数 ----
        self.comp_sigma_spin = QtWidgets.QDoubleSpinBox()
        self.comp_sigma_spin.setRange(5.0, 200.0)
        self.comp_sigma_spin.setSingleStep(5.0)
        self.comp_sigma_spin.setValue(30.0)
        self.comp_sigma_spin.valueChanged.connect(self._on_param_changed)
        self.params_layout.addRow("光照补偿σ (场效应范围):", self.comp_sigma_spin)

        self.comp_strength_spin = QtWidgets.QDoubleSpinBox()
        self.comp_strength_spin.setRange(0.0, 1.0)
        self.comp_strength_spin.setSingleStep(0.05)
        self.comp_strength_spin.setDecimals(2)
        self.comp_strength_spin.setValue(0.5)
        self.comp_strength_spin.valueChanged.connect(self._on_param_changed)
        self.params_layout.addRow("补偿强度:", self.comp_strength_spin)

        # ---- 说明信息 ----
        info = QtWidgets.QLabel(
            "基于光照补偿的模糊增强方法：\n"
            "① 形态学顶帽/底帽变换锐化细节\n"
            "② 三角形隶属度函数映射到模糊域\n"
            "③ 高斯低通 + Prewitt边缘 + 非极大值抑制\n"
            "④ 场效应估计与光照补偿\n"
            "⑤ 反模糊化映射回空间域\n\n"
            "形态学核越大，锐化效果越强；\n"
            "补偿σ越大，校正越大范围的光照不均匀；\n"
            "补偿强度控制补偿程度。"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; font-size: 9pt;")
        self.params_layout.addRow(info)

    def _process_volume(self, volume, progress_callback=None):
        # 确保形态学核大小为奇数
        morph_k = self.morph_kernel_spin.value()
        if morph_k % 2 == 0:
            morph_k += 1

        return FuzzyEnhancementOps.fuzzy_enhancement_3d(
            volume,
            morph_kernel_size=morph_k,
            gauss_sigma=self.gauss_sigma_spin.value(),
            prewitt_low=self.prewitt_low_spin.value(),
            prewitt_high=self.prewitt_high_spin.value(),
            comp_sigma=self.comp_sigma_spin.value(),
            comp_strength=self.comp_strength_spin.value(),
            progress_callback=progress_callback,
        )

    def accept(self):
        try:
            if self._preview_volume is not None:
                self.result_array = self._apply_blend_if_enabled(self._preview_volume)
            else:
                progress = QtWidgets.QProgressDialog(
                    "正在进行补偿模糊增强...", "取消", 0, 100, self)
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
