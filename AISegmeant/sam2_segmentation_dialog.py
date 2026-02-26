# -*- coding: utf-8 -*-
"""SAM预分割对话框（兼容 SAM2 / segment-anything）"""

from PyQt5 import QtWidgets, QtCore
import os


class Sam2SegmentationDialog(QtWidgets.QDialog):
    """SAM预分割参数对话框"""

    def __init__(self, parent=None, current_data=None):
        super().__init__(parent)
        self.parent = parent
        self.current_data = current_data
        self.setWindowTitle("人工智能分割 - SAM预分割")
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
        self.segmentation_mode = "volume_auto"
        self.slice_index = 0
        self.prompt_type = "none"
        self.point_x = 0
        self.point_y = 0
        self.point_label = 1
        self.box_x1 = 0
        self.box_y1 = 0
        self.box_x2 = 0
        self.box_y2 = 0
        self.interactive_prompt_state = None

        main_layout = QtWidgets.QVBoxLayout(self)

        param_group = QtWidgets.QGroupBox("SAM 预分割参数")
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
        param_layout.addWidget(QtWidgets.QLabel("SAM模型权重 (*.pt/*.pth):"), row, 0)
        self.checkpoint_edit = QtWidgets.QLineEdit()
        self.checkpoint_edit.setPlaceholderText("选择SAM模型权重文件（SAM1或SAM2）...")
        param_layout.addWidget(self.checkpoint_edit, row, 1)
        browse_checkpoint_btn = QtWidgets.QPushButton("浏览...")
        browse_checkpoint_btn.clicked.connect(self.browse_checkpoint)
        param_layout.addWidget(browse_checkpoint_btn, row, 2)

        row += 1
        param_layout.addWidget(QtWidgets.QLabel("输出目录（可选）:"), row, 0)
        self.output_dir_edit = QtWidgets.QLineEdit()
        self.output_dir_edit.setPlaceholderText("可留空，默认自动保存到输入同级目录")
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
        param_layout.addWidget(QtWidgets.QLabel("分割模式:"), row, 0)
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItem("整卷自动预分割", "volume_auto")
        self.mode_combo.addItem("单切片 + 点提示", "single_point")
        self.mode_combo.addItem("单切片 + 矩形框提示", "single_box")
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        param_layout.addWidget(self.mode_combo, row, 1, 1, 2)

        row += 1
        param_layout.addWidget(QtWidgets.QLabel("切片索引 (Z):"), row, 0)
        self.slice_index_spin = QtWidgets.QSpinBox()
        max_z = 9999
        if isinstance(current_data, dict) and 'array' in current_data and current_data['array'] is not None:
            try:
                max_z = max(0, int(current_data['array'].shape[0]) - 1)
            except Exception:
                max_z = 9999
        self.slice_index_spin.setRange(0, max_z)
        self.slice_index_spin.setValue(0)
        param_layout.addWidget(self.slice_index_spin, row, 1, 1, 2)

        row += 1
        param_layout.addWidget(QtWidgets.QLabel("点提示 (x,y):"), row, 0)
        point_row = QtWidgets.QHBoxLayout()
        self.point_x_spin = QtWidgets.QSpinBox()
        self.point_x_spin.setRange(0, 10000)
        self.point_y_spin = QtWidgets.QSpinBox()
        self.point_y_spin.setRange(0, 10000)
        self.point_label_combo = QtWidgets.QComboBox()
        self.point_label_combo.addItem("前景点", 1)
        self.point_label_combo.addItem("背景点", 0)
        point_row.addWidget(QtWidgets.QLabel("x"))
        point_row.addWidget(self.point_x_spin)
        point_row.addWidget(QtWidgets.QLabel("y"))
        point_row.addWidget(self.point_y_spin)
        point_row.addWidget(self.point_label_combo)
        point_widget = QtWidgets.QWidget()
        point_widget.setLayout(point_row)
        param_layout.addWidget(point_widget, row, 1, 1, 2)

        row += 1
        param_layout.addWidget(QtWidgets.QLabel("框提示 (x1,y1,x2,y2):"), row, 0)
        box_row = QtWidgets.QHBoxLayout()
        self.box_x1_spin = QtWidgets.QSpinBox(); self.box_x1_spin.setRange(0, 10000)
        self.box_y1_spin = QtWidgets.QSpinBox(); self.box_y1_spin.setRange(0, 10000)
        self.box_x2_spin = QtWidgets.QSpinBox(); self.box_x2_spin.setRange(0, 10000)
        self.box_y2_spin = QtWidgets.QSpinBox(); self.box_y2_spin.setRange(0, 10000)
        box_row.addWidget(QtWidgets.QLabel("x1")); box_row.addWidget(self.box_x1_spin)
        box_row.addWidget(QtWidgets.QLabel("y1")); box_row.addWidget(self.box_y1_spin)
        box_row.addWidget(QtWidgets.QLabel("x2")); box_row.addWidget(self.box_x2_spin)
        box_row.addWidget(QtWidgets.QLabel("y2")); box_row.addWidget(self.box_y2_spin)
        box_widget = QtWidgets.QWidget()
        box_widget.setLayout(box_row)
        param_layout.addWidget(box_widget, row, 1, 1, 2)

        self._point_prompt_widget = point_widget
        self._box_prompt_widget = box_widget

        row += 1
        prompt_sync_row = QtWidgets.QHBoxLayout()
        self.prompt_sync_label = QtWidgets.QLabel("标注联动提示：未读取")
        self.prompt_sync_label.setStyleSheet("color: #666;")
        prompt_sync_row.addWidget(self.prompt_sync_label)
        prompt_sync_row.addStretch()
        refresh_prompt_btn = QtWidgets.QPushButton("读取标注提示")
        refresh_prompt_btn.clicked.connect(self.refresh_interactive_prompt_state)
        prompt_sync_row.addWidget(refresh_prompt_btn)
        prompt_sync_widget = QtWidgets.QWidget()
        prompt_sync_widget.setLayout(prompt_sync_row)
        param_layout.addWidget(prompt_sync_widget, row, 0, 1, 3)

        row += 1
        info_label = QtWidgets.QLabel(
            "说明:\n"
            "• 支持整卷自动预分割，或对单切片使用点/框提示分割。\n"
            "• 优先使用SAM2；若不可用则自动回退到SAM1（segment-anything）。\n"
            "• 该结果定位为预分割，可作为后续编辑与精修的初稿。\n"
            "• 按官方示例，仅需模型权重（checkpoint）；无需手动选择SAM2配置文件。"
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
        self.refresh_interactive_prompt_state()
        self.on_mode_changed()

    def on_source_changed(self):
        use_file = self.use_file_radio.isChecked()
        self.input_file_edit.setEnabled(use_file)
        self.browse_input_btn.setEnabled(use_file)

    def on_mode_changed(self):
        mode = self.mode_combo.currentData()
        is_single = mode in ("single_point", "single_box")
        self.slice_index_spin.setEnabled(is_single)
        self._point_prompt_widget.setVisible(mode == "single_point")
        self._box_prompt_widget.setVisible(mode == "single_box")

    def refresh_interactive_prompt_state(self):
        state = None
        if self.parent is not None and hasattr(self.parent, 'get_sam_prompt_state'):
            try:
                state = self.parent.get_sam_prompt_state()
            except Exception:
                state = None

        if not isinstance(state, dict):
            state = {'point': None, 'box': None}

        self.interactive_prompt_state = state

        point_state = state.get('point')
        box_state = state.get('box')

        if isinstance(point_state, dict):
            self.slice_index_spin.setValue(int(point_state.get('slice_index', 0)))
            self.point_x_spin.setValue(int(point_state.get('x', 0)))
            self.point_y_spin.setValue(int(point_state.get('y', 0)))
            lbl = int(point_state.get('point_label', 1))
            idx = self.point_label_combo.findData(lbl)
            if idx >= 0:
                self.point_label_combo.setCurrentIndex(idx)

        if isinstance(box_state, dict):
            self.slice_index_spin.setValue(int(box_state.get('slice_index', 0)))
            self.box_x1_spin.setValue(int(box_state.get('x1', 0)))
            self.box_y1_spin.setValue(int(box_state.get('y1', 0)))
            self.box_x2_spin.setValue(int(box_state.get('x2', 0)))
            self.box_y2_spin.setValue(int(box_state.get('y2', 0)))

        summary = []
        if isinstance(point_state, dict):
            summary.append(
                f"点(Z={int(point_state.get('slice_index', 0))}, x={int(point_state.get('x', 0))}, y={int(point_state.get('y', 0))})"
            )
        if isinstance(box_state, dict):
            summary.append(
                f"框(Z={int(box_state.get('slice_index', 0))}, {int(box_state.get('x1', 0))},{int(box_state.get('y1', 0))},{int(box_state.get('x2', 0))},{int(box_state.get('y2', 0))})"
            )

        if summary:
            self.prompt_sync_label.setText("标注联动提示：" + "；".join(summary))
        else:
            self.prompt_sync_label.setText("标注联动提示：未采集到点/框")

    def browse_input_file(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择输入文件", "", "NIfTI文件 (*.nii *.nii.gz);;所有文件 (*)"
        )
        if filename:
            self.input_file_edit.setText(filename)

    def browse_checkpoint(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择SAM模型权重文件", "", "PyTorch模型文件 (*.pth *.pt);;所有文件 (*)"
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

        model_cfg = self.model_cfg

        checkpoint_path = self.checkpoint_edit.text().strip()
        if not checkpoint_path:
            QtWidgets.QMessageBox.warning(self, "输入错误", "请选择SAM模型权重文件。")
            return
        if not os.path.exists(checkpoint_path):
            QtWidgets.QMessageBox.warning(self, "输入错误", f"模型权重文件不存在：\n{checkpoint_path}")
            return

        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            if self.use_current_data:
                output_dir = os.path.join(os.getcwd(), "sam_preseg_output")
            else:
                output_dir = os.path.join(os.path.dirname(self.input_file), "sam_preseg_output")

        os.makedirs(output_dir, exist_ok=True)

        self.model_cfg = model_cfg
        self.checkpoint_path = checkpoint_path
        self.output_dir = output_dir
        self.points_per_side = self.points_per_side_spin.value()
        self.pred_iou_thresh = self.pred_iou_spin.value()
        self.stability_score_thresh = self.stability_spin.value()
        self.min_mask_region_area = self.min_area_spin.value()
        self.segmentation_mode = self.mode_combo.currentData()
        self.slice_index = int(self.slice_index_spin.value())
        state = self.interactive_prompt_state if isinstance(self.interactive_prompt_state, dict) else {}
        if self.segmentation_mode == "single_point":
            self.prompt_type = "point"
            point_state = state.get('point') if isinstance(state, dict) else None
            if isinstance(point_state, dict):
                self.slice_index = int(point_state.get('slice_index', self.slice_index))
                self.point_x = int(point_state.get('x', self.point_x_spin.value()))
                self.point_y = int(point_state.get('y', self.point_y_spin.value()))
                self.point_label = int(point_state.get('point_label', self.point_label_combo.currentData()))
            else:
                self.point_x = int(self.point_x_spin.value())
                self.point_y = int(self.point_y_spin.value())
                self.point_label = int(self.point_label_combo.currentData())
        elif self.segmentation_mode == "single_box":
            self.prompt_type = "box"
            box_state = state.get('box') if isinstance(state, dict) else None
            if isinstance(box_state, dict):
                self.slice_index = int(box_state.get('slice_index', self.slice_index))
                self.box_x1 = int(box_state.get('x1', self.box_x1_spin.value()))
                self.box_y1 = int(box_state.get('y1', self.box_y1_spin.value()))
                self.box_x2 = int(box_state.get('x2', self.box_x2_spin.value()))
                self.box_y2 = int(box_state.get('y2', self.box_y2_spin.value()))
            else:
                self.box_x1 = int(self.box_x1_spin.value())
                self.box_y1 = int(self.box_y1_spin.value())
                self.box_x2 = int(self.box_x2_spin.value())
                self.box_y2 = int(self.box_y2_spin.value())
            if self.box_x2 <= self.box_x1 or self.box_y2 <= self.box_y1:
                QtWidgets.QMessageBox.warning(self, "输入错误", "矩形框必须满足 x2>x1 且 y2>y1。")
                return
        else:
            self.prompt_type = "none"
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
            "segmentation_mode": self.segmentation_mode,
            "slice_index": self.slice_index,
            "prompt_type": self.prompt_type,
            "point_xy": (self.point_x, self.point_y),
            "point_label": self.point_label,
            "box_xyxy": (self.box_x1, self.box_y1, self.box_x2, self.box_y2),
            "overlay_with_original": self.overlay_with_original,
            "overlay_alpha": self.alpha_slider.value() / 100.0,
            "overlay_color": color_map[self.color_combo.currentText()]
        }
