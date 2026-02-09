"""
图像增强操作功能
负责直方图均衡化、CLAHE、Retinex SSR、去雾、光照补偿模糊增强等3D图像增强处理
"""

from PyQt5 import QtWidgets
from Traditional.Enhancement.enhancement_dialogs import (
    HistogramEqualizationDialog,
    CLAHEDialog,
    RetinexSSRDialog,
    DehazeDialog,
)
from Traditional.Enhancement.fuzzy_enhancement_dialog import FuzzyEnhancementDialog


class EnhancementOperations:
    """图像增强操作类，作为Mixin使用"""

    def _run_enhancement_dialog(self, dialog_class, title):
        """通用的增强对话框调用逻辑"""
        if not hasattr(self, 'array') or self.array is None:
            QtWidgets.QMessageBox.warning(self, "警告", "请先加载数据")
            return

        try:
            dialog = dialog_class(self.array, parent=self)

            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                result = dialog.get_result()
                if result is not None:
                    self.array = result
                    QtWidgets.QMessageBox.information(
                        self, "成功", f"{title}处理完成，正在更新视图..."
                    )
                    QtWidgets.QApplication.processEvents()
                    self.update_viewers()
                    QtWidgets.QMessageBox.information(self, "成功", "视图已更新")
                else:
                    QtWidgets.QMessageBox.warning(self, "警告", "处理未返回结果")
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "错误", f"应用{title}时出错：{str(e)}"
            )

    def apply_histogram_equalization(self):
        """应用直方图均衡化"""
        self._run_enhancement_dialog(HistogramEqualizationDialog, "直方图均衡化")

    def apply_clahe(self):
        """应用限制对比度自适应直方图均衡化 (CLAHE)"""
        self._run_enhancement_dialog(CLAHEDialog, "CLAHE")

    def apply_retinex_ssr(self):
        """应用单尺度Retinex (SSR)"""
        self._run_enhancement_dialog(RetinexSSRDialog, "Retinex SSR")

    def apply_dehaze(self):
        """应用暗通道先验去雾"""
        self._run_enhancement_dialog(DehazeDialog, "去雾")

    def apply_fuzzy_enhancement(self):
        """应用基于光照补偿的模糊增强"""
        self._run_enhancement_dialog(FuzzyEnhancementDialog, "补偿模糊增强")
