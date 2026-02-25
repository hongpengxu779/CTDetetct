# -*- coding: utf-8 -*-
"""交互式标签文件创建对话框"""

import os
from PyQt5 import QtWidgets


class LabelFileCreationDialog(QtWidgets.QDialog):
    """用于创建机器学习训练标签文件的参数对话框"""

    def __init__(self, parent=None, data_min=0.0, data_max=1.0, default_output_path=""):
        super().__init__(parent)
        self._data_min = float(data_min)
        self._data_max = float(data_max)
        self._default_output_path = default_output_path

        self.setWindowTitle("创建标签文件")
        self.setMinimumWidth(700)
        self.setMinimumHeight(460)

        self._build_ui()
        self._on_method_changed()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        info_group = QtWidgets.QGroupBox("输入数据")
        info_layout = QtWidgets.QVBoxLayout(info_group)
        info_label = QtWidgets.QLabel(
            f"当前灰度范围: [{self._data_min:.2f}, {self._data_max:.2f}]\n"
            "说明：创建结果将保存为标签文件（0为背景，1..N为类别）。"
        )
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        main_layout.addWidget(info_group)

        param_group = QtWidgets.QGroupBox("标签生成方式")
        grid = QtWidgets.QGridLayout(param_group)
        row = 0

        grid.addWidget(QtWidgets.QLabel("方式:"), row, 0)
        self.method_combo = QtWidgets.QComboBox()
        self.method_combo.addItems([
            "阈值二值标签",
            "多阈值OTSU标签",
            "非零区域转单标签",
        ])
        self.method_combo.currentIndexChanged.connect(self._on_method_changed)
        grid.addWidget(self.method_combo, row, 1, 1, 2)

        row += 1
        grid.addWidget(QtWidgets.QLabel("下阈值:"), row, 0)
        self.lower_spin = QtWidgets.QDoubleSpinBox()
        self.lower_spin.setRange(self._data_min, self._data_max)
        self.lower_spin.setDecimals(2)
        self.lower_spin.setValue(self._data_min + (self._data_max - self._data_min) * 0.3)
        grid.addWidget(self.lower_spin, row, 1)

        row += 1
        grid.addWidget(QtWidgets.QLabel("上阈值:"), row, 0)
        self.upper_spin = QtWidgets.QDoubleSpinBox()
        self.upper_spin.setRange(self._data_min, self._data_max)
        self.upper_spin.setDecimals(2)
        self.upper_spin.setValue(self._data_min + (self._data_max - self._data_min) * 0.7)
        grid.addWidget(self.upper_spin, row, 1)

        row += 1
        grid.addWidget(QtWidgets.QLabel("标签值:"), row, 0)
        self.label_value_spin = QtWidgets.QSpinBox()
        self.label_value_spin.setRange(1, 255)
        self.label_value_spin.setValue(1)
        grid.addWidget(self.label_value_spin, row, 1)

        row += 1
        grid.addWidget(QtWidgets.QLabel("OTSU阈值数量:"), row, 0)
        self.otsu_num_spin = QtWidgets.QSpinBox()
        self.otsu_num_spin.setRange(2, 8)
        self.otsu_num_spin.setValue(3)
        grid.addWidget(self.otsu_num_spin, row, 1)

        row += 1
        grid.addWidget(QtWidgets.QLabel("OTSU直方图bins:"), row, 0)
        self.otsu_bins_spin = QtWidgets.QSpinBox()
        self.otsu_bins_spin.setRange(32, 1024)
        self.otsu_bins_spin.setValue(128)
        grid.addWidget(self.otsu_bins_spin, row, 1)

        row += 1
        self.keep_existing_cb = QtWidgets.QCheckBox("若输出文件已存在，则在其基础上叠加新标签（新标签覆盖冲突区域）")
        self.keep_existing_cb.setChecked(False)
        grid.addWidget(self.keep_existing_cb, row, 0, 1, 3)

        row += 1
        self.method_info = QtWidgets.QLabel()
        self.method_info.setWordWrap(True)
        self.method_info.setStyleSheet("color:#666; font-size:9pt; padding:6px;")
        grid.addWidget(self.method_info, row, 0, 1, 3)

        main_layout.addWidget(param_group)

        output_group = QtWidgets.QGroupBox("输出标签文件")
        output_grid = QtWidgets.QGridLayout(output_group)
        output_grid.addWidget(QtWidgets.QLabel("标签文件路径:"), 0, 0)
        self.output_edit = QtWidgets.QLineEdit()
        self.output_edit.setPlaceholderText("选择保存路径（*.nii.gz）")
        self.output_edit.setText(self._default_output_path)
        output_grid.addWidget(self.output_edit, 0, 1)
        browse_btn = QtWidgets.QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_output)
        output_grid.addWidget(browse_btn, 0, 2)
        main_layout.addWidget(output_group)

        main_layout.addStretch()

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QtWidgets.QPushButton("生成标签文件")
        ok_btn.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(ok_btn)
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)

    def _on_method_changed(self):
        method = self.method_combo.currentText()
        is_threshold = method == "阈值二值标签"
        is_otsu = method == "多阈值OTSU标签"

        self.lower_spin.setEnabled(is_threshold)
        self.upper_spin.setEnabled(is_threshold)
        self.otsu_num_spin.setEnabled(is_otsu)
        self.otsu_bins_spin.setEnabled(is_otsu)

        if is_threshold:
            text = "阈值二值标签：将灰度在[下阈值, 上阈值]内的体素赋值为“标签值”，其余为0。"
        elif is_otsu:
            text = "多阈值OTSU标签：自动分成多个类别，输出标签为0..N（自动多类标注）。"
        else:
            text = "非零区域转单标签：将灰度>0的区域统一赋值为“标签值”，适合已有粗分割数据。"
        self.method_info.setText(text)

    def _browse_output(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "保存标签文件",
            self.output_edit.text().strip(),
            "NIfTI文件 (*.nii.gz *.nii);;所有文件 (*)",
        )
        if path:
            if not (path.endswith(".nii.gz") or path.endswith(".nii")):
                path += ".nii.gz"
            self.output_edit.setText(path)

    def _validate_and_accept(self):
        output_path = self.output_edit.text().strip()
        if not output_path:
            QtWidgets.QMessageBox.warning(self, "输入错误", "请设置标签文件输出路径。")
            return

        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            QtWidgets.QMessageBox.warning(self, "输入错误", f"输出目录不存在：\n{output_dir}")
            return

        if self.lower_spin.value() >= self.upper_spin.value() and self.method_combo.currentText() == "阈值二值标签":
            QtWidgets.QMessageBox.warning(self, "输入错误", "阈值设置无效：下阈值必须小于上阈值。")
            return

        self.accept()

    def get_parameters(self):
        return {
            'method': self.method_combo.currentText(),
            'lower_threshold': self.lower_spin.value(),
            'upper_threshold': self.upper_spin.value(),
            'label_value': self.label_value_spin.value(),
            'otsu_num_thresholds': self.otsu_num_spin.value(),
            'otsu_bins': self.otsu_bins_spin.value(),
            'keep_existing': self.keep_existing_cb.isChecked(),
            'output_path': self.output_edit.text().strip(),
        }
