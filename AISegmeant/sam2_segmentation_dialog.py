# -*- coding: utf-8 -*-
"""SAM2预分割对话框"""

from PyQt5 import QtWidgets, QtCore
import os


class Sam2SegmentationDialog(QtWidgets.QDialog):
    """SAM2预分割参数对话框"""

    def __init__(self, parent=None, current_data=None):
        super().__init__(parent)
        self.parent = parent
        self.current_data = current_data
        self.setWindowTitle("人工智能分割 - SAM2预分割")
        self.setMinimumWidth(760)
        self.setMinimumHeight(540)

        self.checkpoint_path = None
        self.model_cfg = "configs/sam2.1/sam2.1_hiera_l.yaml"
        self.output_dir = None
        self.input_file = None
        self.use_current_data = False
        self.points_per_side = 32
        self.pred_iou_thresh = 0.8
        self.stability_score_thresh = 0.95
        self.min_mask_region_area = 100
        self.overlay_with_original = True

        main_layout = QtWidgets.QVBoxLayout(self)

        param_group = QtWidgets.QGroupBox("SAM2 预分割参数")
        param_layout = QtWidgets.QGridLayout()
        param_group.setLayout(param_layout)

        row = 0
        param_layout.addWidget(QtWidgets.QLabel("数据来源:"), row, 0)
        source_layout = QtWidgets.QHBoxLayout()
        self.use_current_radio = QtWidgets.QRadioButton("使用当前已加载数据")
        self.use_file_radio = QtWidgets.QRadioButton("从文件加载")
        if current_data is not None:
            self.use_current_radio.setChecked(True)
        else:
            self.use_current_radio.setEnabled(False)
            self.use_file_radio.setChecked(True)
        source_layout.addWidget(self.use_current_radio)
        source_layout.addWidget(self.use_file_radio)
        source_layout.addStretch()
        source_widget = QtWidgets.QWidget()
        source_widget.setLayout(source_layout)
        param_layout.addWidget(source_widget, row, 1, 1, 2)

        row += 1
        param_layout.addWidget(QtWidgets.QLabel("输入文件 (*.nii.gz):"), row, 0)
        self.input_file_edit = QtWidgets.QLineEdit()
        self.input_file_edit.setPlaceholderText("选择待分割的NIfTI文件...")
        param_layout.addWidget(self.input_file_edit, row, 1)
        self.browse_input_btn = QtWidgets.QPushButton("浏览...")
        self.browse_input_btn.clicked.connect(self.browse_input_file)
        param_layout.addWidget(self.browse_input_btn, row, 2)

        self.use_current_radio.toggled.connect(self.on_source_changed)
        self.use_file_radio.toggled.connect(self.on_source_changed)
        self.on_source_changed()

        row += 1
        param_layout.addWidget(QtWidgets.QLabel("SAM2配置文件 (yaml):"), row, 0)
        self.model_cfg_edit = QtWidgets.QLineEdit()
        self.model_cfg_edit.setText(self.model_cfg)
        self.model_cfg_edit.setPlaceholderText("例如: configs/sam2.1/sam2.1_hiera_l.yaml")
        param_layout.addWidget(self.model_cfg_edit, row, 1)
        self.browse_cfg_btn = QtWidgets.QPushButton("浏览...")
        self.browse_cfg_btn.clicked.connect(self.browse_model_cfg)
        param_layout.addWidget(self.browse_cfg_btn, row, 2)

        row += 1
        param_layout.addWidget(QtWidgets.QLabel("SAM2模型权重 (*.pt/*.pth):"), row, 0)
        self.checkpoint_edit = QtWidgets.QLineEdit()
        self.checkpoint_edit.setPlaceholderText("选择SAM2模型权重文件...")
        param_layout.addWidget(self.checkpoint_edit, row, 1)
        browse_checkpoint_btn = QtWidgets.QPushButton("浏览...")
        browse_checkpoint_btn.clicked.connect(self.browse_checkpoint)
        param_layout.addWidget(browse_checkpoint_btn, row, 2)

        row += 1
        param_layout.addWidget(QtWidgets.QLabel("输出目录:"), row, 0)
        self.output_dir_edit = QtWidgets.QLineEdit()
        self.output_dir_edit.setPlaceholderText("选择分割结果保存目录...")
        param_layout.addWidget(self.output_dir_edit, row, 1)
        browse_output_btn = QtWidgets.QPushButton("浏览...")
        browse_output_btn.clicked.connect(self.browse_output_dir)
        param_layout.addWidget(browse_output_btn, row, 2)

        row += 1
        param_layout.addWidget(QtWidgets.QLabel("points_per_side:"), row, 0)
        self.points_per_side_spin = QtWidgets.QSpinBox()
        self.points_per_side_spin.setRange(4, 128)
        self.points_per_side_spin.setValue(32)
        param_layout.addWidget(self.points_per_side_spin, row, 1)

        row += 1
        param_layout.addWidget(QtWidgets.QLabel("pred_iou_thresh:"), row, 0)
        self.pred_iou_spin = QtWidgets.QDoubleSpinBox()
        self.pred_iou_spin.setRange(0.1, 0.99)
        self.pred_iou_spin.setDecimals(2)
        self.pred_iou_spin.setSingleStep(0.01)
        self.pred_iou_spin.setValue(0.80)
        param_layout.addWidget(self.pred_iou_spin, row, 1)

        row += 1
        param_layout.addWidget(QtWidgets.QLabel("stability_score_thresh:"), row, 0)
        self.stability_spin = QtWidgets.QDoubleSpinBox()
        self.stability_spin.setRange(0.1, 0.99)
        self.stability_spin.setDecimals(2)
        self.stability_spin.setSingleStep(0.01)
        self.stability_spin.setValue(0.95)
        param_layout.addWidget(self.stability_spin, row, 1)

        row += 1
        param_layout.addWidget(QtWidgets.QLabel("min_mask_region_area:"), row, 0)
        self.min_area_spin = QtWidgets.QSpinBox()
        self.min_area_spin.setRange(0, 50000)
        self.min_area_spin.setValue(100)
        param_layout.addWidget(self.min_area_spin, row, 1)

        row += 1
        info_label = QtWidgets.QLabel(
            "说明:\n"
            "• 当前实现按切片执行SAM2自动掩膜，再融合为3D二值体。\n"
            "• 该结果定位为预分割，可作为后续编辑与精修的初稿。\n"
            "• 需先安装 sam2 官方库并准备 cfg + checkpoint。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 9pt; padding: 10px;")
        param_layout.addWidget(info_label, row, 0, 1, 3)

        main_layout.addWidget(param_group)

        display_group = QtWidgets.QGroupBox("显示选项")
        display_layout = QtWidgets.QVBoxLayout()
        display_group.setLayout(display_layout)
        self.overlay_checkbox = QtWidgets.QCheckBox("与原始图像融合显示（推荐）")
        self.overlay_checkbox.setChecked(True)
        display_layout.addWidget(self.overlay_checkbox)

        overlay_params_layout = QtWidgets.QHBoxLayout()
        overlay_params_layout.addWidget(QtWidgets.QLabel("透明度:"))
        self.alpha_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.alpha_slider.setRange(10, 100)
        self.alpha_slider.setValue(50)
        overlay_params_layout.addWidget(self.alpha_slider)
        self.alpha_label = QtWidgets.QLabel("50%")
        self.alpha_slider.valueChanged.connect(lambda v: self.alpha_label.setText(f"{v}%"))
        overlay_params_layout.addWidget(self.alpha_label)
        overlay_params_layout.addWidget(QtWidgets.QLabel("  颜色:"))
        self.color_combo = QtWidgets.QComboBox()
        self.color_combo.addItems(["红色", "绿色", "蓝色", "黄色", "青色", "品红"])
        self.color_combo.setCurrentIndex(0)
        overlay_params_layout.addWidget(self.color_combo)
        display_layout.addLayout(overlay_params_layout)
        main_layout.addWidget(display_group)

        main_layout.addStretch()
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        run_button = QtWidgets.QPushButton("开始预分割")
        run_button.setMinimumWidth(110)
        run_button.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(run_button)
        cancel_button = QtWidgets.QPushButton("取消")
        cancel_button.setMinimumWidth(100)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)

    def on_source_changed(self):
        use_file = self.use_file_radio.isChecked()
        self.input_file_edit.setEnabled(use_file)
        self.browse_input_btn.setEnabled(use_file)

    def browse_input_file(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择输入文件", "", "NIfTI文件 (*.nii *.nii.gz);;所有文件 (*)"
        )
        if filename:
            self.input_file_edit.setText(filename)

    def browse_model_cfg(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择SAM2配置文件", "", "YAML文件 (*.yaml *.yml);;所有文件 (*)"
        )
        if filename:
            self.model_cfg_edit.setText(filename)

    def browse_checkpoint(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择SAM2模型权重文件", "", "PyTorch模型文件 (*.pth *.pt);;所有文件 (*)"
        )
        if filename:
            self.checkpoint_edit.setText(filename)

    def browse_output_dir(self):
        dirname = QtWidgets.QFileDialog.getExistingDirectory(self, "选择输出目录", "")
        if dirname:
            self.output_dir_edit.setText(dirname)

    def validate_and_accept(self):
        self.use_current_data = self.use_current_radio.isChecked()

        if self.use_current_data:
            if self.current_data is None:
                QtWidgets.QMessageBox.warning(self, "输入错误", "当前没有已加载的数据，请先在主界面加载数据。")
                return
            self.input_file = None
        else:
            input_file = self.input_file_edit.text().strip()
            if not input_file:
                QtWidgets.QMessageBox.warning(self, "输入错误", "请选择输入文件。")
                return
            if not os.path.exists(input_file):
                QtWidgets.QMessageBox.warning(self, "输入错误", f"输入文件不存在：\n{input_file}")
                return
            self.input_file = input_file

        model_cfg = self.model_cfg_edit.text().strip()
        if not model_cfg:
            QtWidgets.QMessageBox.warning(self, "输入错误", "请填写SAM2配置文件路径。")
            return

        checkpoint_path = self.checkpoint_edit.text().strip()
        if not checkpoint_path:
            QtWidgets.QMessageBox.warning(self, "输入错误", "请选择SAM2模型权重文件。")
            return
        if not os.path.exists(checkpoint_path):
            QtWidgets.QMessageBox.warning(self, "输入错误", f"模型权重文件不存在：\n{checkpoint_path}")
            return

        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            QtWidgets.QMessageBox.warning(self, "输入错误", "请选择输出目录。")
            return

        self.model_cfg = model_cfg
        self.checkpoint_path = checkpoint_path
        self.output_dir = output_dir
        self.points_per_side = self.points_per_side_spin.value()
        self.pred_iou_thresh = self.pred_iou_spin.value()
        self.stability_score_thresh = self.stability_spin.value()
        self.min_mask_region_area = self.min_area_spin.value()
        self.overlay_with_original = self.overlay_checkbox.isChecked()
        self.accept()

    def get_parameters(self):
        color_map = {
            "红色": (255, 0, 0),
            "绿色": (0, 255, 0),
            "蓝色": (0, 0, 255),
            "黄色": (255, 255, 0),
            "青色": (0, 255, 255),
            "品红": (255, 0, 255)
        }

        return {
            "use_current_data": self.use_current_data,
            "current_data": self.current_data if self.use_current_data else None,
            "input_file": self.input_file,
            "checkpoint_path": self.checkpoint_path,
            "model_cfg": self.model_cfg,
            "output_dir": self.output_dir,
            "points_per_side": self.points_per_side,
            "pred_iou_thresh": self.pred_iou_thresh,
            "stability_score_thresh": self.stability_score_thresh,
            "min_mask_region_area": self.min_mask_region_area,
            "overlay_with_original": self.overlay_with_original,
            "overlay_alpha": self.alpha_slider.value() / 100.0,
            "overlay_color": color_map[self.color_combo.currentText()]
        }
