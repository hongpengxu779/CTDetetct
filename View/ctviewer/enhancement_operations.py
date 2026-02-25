"""
图像增强操作功能
负责直方图均衡化、CLAHE、Retinex SSR、去雾、光照补偿模糊增强等3D图像增强处理
"""

import numpy as np
from PyQt5 import QtWidgets, QtCore
from Traditional.Enhancement.enhancement_dialogs import (
    HistogramEqualizationDialog,
    CLAHEDialog,
    RetinexSSRDialog,
    DehazeDialog,
    MUSICADialog,
)
from Traditional.Enhancement.fuzzy_enhancement_dialog import FuzzyEnhancementDialog


class EnhancementOperations:
    """图像增强操作类，作为Mixin使用"""

    def _generate_unique_data_name(self, base_name):
        if not hasattr(self, 'data_list_widget') or self.data_list_widget is None:
            return base_name

        existing_names = {
            self.data_list_widget.item(i).text()
            for i in range(self.data_list_widget.count())
        }
        if base_name not in existing_names:
            return base_name

        idx = 1
        while True:
            candidate = f"{base_name}_{idx}"
            if candidate not in existing_names:
                return candidate
            idx += 1

    def _create_enhanced_data_item(self, result_array, title):
        current_name = "当前数据"
        source_item = None
        if hasattr(self, 'data_list_widget') and self.data_list_widget is not None:
            current_item = self.data_list_widget.currentItem()
            if current_item is not None:
                current_name = current_item.text()
                source_item = current_item.data(QtCore.Qt.UserRole)

        base_name = current_name.replace(" [标签]", "")
        new_name = self._generate_unique_data_name(f"{base_name}_{title}")

        spacing = getattr(self, 'spacing', (1.0, 1.0, 1.0))
        image = getattr(self, 'image', None)
        if isinstance(source_item, dict):
            spacing = source_item.get('spacing', spacing)
            image = source_item.get('image', image)

        data_item = {
            'image': image,
            'array': np.asarray(result_array).copy(),
            'shape': tuple(result_array.shape),
            'spacing': spacing,
            'rgb_array': None,
            'is_segmentation': False,
            'data_type': 'image',
            'source_operation': title,
        }
        return new_name, data_item

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
                    if hasattr(self, 'add_data_to_list'):
                        data_name, data_item = self._create_enhanced_data_item(result, title)
                        self.add_data_to_list(data_name, data_item)
                        QtWidgets.QMessageBox.information(
                            self,
                            "成功",
                            f"{title}处理完成，已生成新数据：\n{data_name}\n\n原始图像保持不变。"
                        )
                    else:
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

    def apply_musica_enhancement(self):
        """应用mUSICA增强 - 完全模拟导出切片→处理→重组的流程"""
        # 从数据列表获取当前选中项的原始数据
        source_array = None
        
        if hasattr(self, 'data_list_widget') and self.data_list_widget is not None:
            current_item = self.data_list_widget.currentItem()
            if current_item is not None:
                data_item = current_item.data(QtCore.Qt.UserRole)
                if isinstance(data_item, dict) and 'array' in data_item:
                    source_array = data_item['array']
                    print(f"[mUSICA入口] 从数据列表获取: dtype={source_array.dtype}, shape={source_array.shape}")
        
        # 回退到 self.array
        if source_array is None:
            if hasattr(self, 'array') and self.array is not None:
                source_array = self.array
                print(f"[mUSICA入口] 使用 self.array: dtype={source_array.dtype}, shape={source_array.shape}")
        
        if source_array is None:
            QtWidgets.QMessageBox.warning(self, "警告", "请先加载数据")
            return

        try:
            # 直接传入原始数据，对话框内部会模拟导出流程进行处理
            dialog = MUSICADialog(source_array, parent=self)

            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                result = dialog.get_result()
                if result is not None:
                    if hasattr(self, 'add_data_to_list'):
                        data_name, data_item = self._create_enhanced_data_item(result, "mUSICA增强")
                        self.add_data_to_list(data_name, data_item)
                        QtWidgets.QMessageBox.information(
                            self,
                            "成功",
                            f"mUSICA增强处理完成，已生成新数据：\n{data_name}\n\n原始图像保持不变。"
                        )
                    else:
                        self.array = result
                        QtWidgets.QMessageBox.information(
                            self, "成功", "mUSICA增强处理完成，正在更新视图..."
                        )
                        QtWidgets.QApplication.processEvents()
                        self.update_viewers()
                        QtWidgets.QMessageBox.information(self, "成功", "视图已更新")
                else:
                    QtWidgets.QMessageBox.warning(self, "警告", "处理未返回结果")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(
                self, "错误", f"应用mUSICA增强时出错：{str(e)}"
            )
