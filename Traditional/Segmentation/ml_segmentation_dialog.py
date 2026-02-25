# -*- coding: utf-8 -*-
"""机器学习分割对话框"""

import os
from PyQt5 import QtWidgets, QtCore


class MLSegmentationDialog(QtWidgets.QDialog):
    """机器学习分割参数对话框（KNN + 集成方法）"""

    def __init__(self, parent=None, current_data=None):
        super().__init__(parent)
        self.parent_viewer = parent
        self.current_data = current_data

        self.setWindowTitle("机器学习分割")
        self.setMinimumWidth(760)
        self.setMinimumHeight(620)

        self.use_current_data = current_data is not None
        self.input_file = None
        self.label_file = None
        self.output_dir = None
        self.selected_label_dataset = None

        self._build_ui()
        self._on_data_source_changed()
        self._on_algorithm_changed()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        param_group = QtWidgets.QGroupBox("机器学习分割参数")
        grid = QtWidgets.QGridLayout(param_group)
        row = 0

        grid.addWidget(QtWidgets.QLabel("数据来源:"), row, 0)
        source_layout = QtWidgets.QHBoxLayout()
        self.use_current_radio = QtWidgets.QRadioButton("使用当前已加载数据")
        self.use_file_radio = QtWidgets.QRadioButton("从文件加载影像")
        if self.current_data is not None:
            self.use_current_radio.setChecked(True)
        else:
            self.use_file_radio.setChecked(True)
            self.use_current_radio.setEnabled(False)
        self.use_current_radio.toggled.connect(self._on_data_source_changed)
        source_layout.addWidget(self.use_current_radio)
        source_layout.addWidget(self.use_file_radio)
        source_layout.addStretch()
        source_widget = QtWidgets.QWidget()
        source_widget.setLayout(source_layout)
        grid.addWidget(source_widget, row, 1, 1, 2)

        row += 1
        grid.addWidget(QtWidgets.QLabel("输入影像 (*.nii.gz):"), row, 0)
        self.input_file_edit = QtWidgets.QLineEdit()
        self.input_file_edit.setPlaceholderText("选择待分割的CT体数据")
        grid.addWidget(self.input_file_edit, row, 1)
        self.input_browse_btn = QtWidgets.QPushButton("浏览...")
        self.input_browse_btn.clicked.connect(self._browse_input_file)
        grid.addWidget(self.input_browse_btn, row, 2)

        row += 1
        grid.addWidget(QtWidgets.QLabel("标签文件 (*.nii.gz):"), row, 0)
        self.label_file_edit = QtWidgets.QLineEdit()
        self.label_file_edit.setPlaceholderText("选择训练标签（0为背景，1..N为类别）")
        grid.addWidget(self.label_file_edit, row, 1)
        label_btn_widget = QtWidgets.QWidget()
        label_btn_layout = QtWidgets.QHBoxLayout(label_btn_widget)
        label_btn_layout.setContentsMargins(0, 0, 0, 0)
        label_btn_layout.setSpacing(4)
        label_browse_btn = QtWidgets.QPushButton("浏览...")
        label_browse_btn.clicked.connect(self._browse_label_file)
        label_btn_layout.addWidget(label_browse_btn)
        list_label_btn = QtWidgets.QPushButton("数据列表")
        list_label_btn.clicked.connect(self._pick_label_from_data_list)
        label_btn_layout.addWidget(list_label_btn)
        create_label_btn = QtWidgets.QPushButton("从标注区生成")
        create_label_btn.clicked.connect(self._create_label_file_interactive)
        label_btn_layout.addWidget(create_label_btn)
        grid.addWidget(label_btn_widget, row, 2)

        row += 1
        manual_tip = QtWidgets.QLabel("提示：交互创建将使用“标注区-画笔/橡皮擦”的手工标注结果导出标签文件。")
        manual_tip.setStyleSheet("color:#666; font-size:9pt;")
        manual_tip.setWordWrap(True)
        grid.addWidget(manual_tip, row, 0, 1, 3)

        row += 1
        grid.addWidget(QtWidgets.QLabel("输出目录:"), row, 0)
        self.output_dir_edit = QtWidgets.QLineEdit()
        self.output_dir_edit.setPlaceholderText("可选，留空默认保存到系统临时目录")
        grid.addWidget(self.output_dir_edit, row, 1)
        output_browse_btn = QtWidgets.QPushButton("浏览...")
        output_browse_btn.clicked.connect(self._browse_output_dir)
        grid.addWidget(output_browse_btn, row, 2)

        row += 1
        grid.addWidget(QtWidgets.QLabel("算法:"), row, 0)
        self.algorithm_combo = QtWidgets.QComboBox()
        self.algorithm_combo.addItems([
            "K-Nearest",
            "AdaBoost",
            "Bagging",
            "Extra Trees",
            "Gradient Boosting",
            "Random Forest",
        ])
        self.algorithm_combo.currentIndexChanged.connect(self._on_algorithm_changed)
        grid.addWidget(self.algorithm_combo, row, 1, 1, 2)

        row += 1
        grid.addWidget(QtWidgets.QLabel("K值(KNN):"), row, 0)
        self.k_input = QtWidgets.QSpinBox()
        self.k_input.setRange(1, 100)
        self.k_input.setValue(7)
        grid.addWidget(self.k_input, row, 1)

        row += 1
        grid.addWidget(QtWidgets.QLabel("树数量(集成):"), row, 0)
        self.n_estimators_input = QtWidgets.QSpinBox()
        self.n_estimators_input.setRange(10, 1000)
        self.n_estimators_input.setValue(200)
        self.n_estimators_input.setSingleStep(10)
        grid.addWidget(self.n_estimators_input, row, 1)

        row += 1
        grid.addWidget(QtWidgets.QLabel("最大深度(0=不限制):"), row, 0)
        self.max_depth_input = QtWidgets.QSpinBox()
        self.max_depth_input.setRange(0, 100)
        self.max_depth_input.setValue(18)
        grid.addWidget(self.max_depth_input, row, 1)

        row += 1
        grid.addWidget(QtWidgets.QLabel("学习率(GB):"), row, 0)
        self.learning_rate_input = QtWidgets.QDoubleSpinBox()
        self.learning_rate_input.setRange(0.001, 1.0)
        self.learning_rate_input.setSingleStep(0.01)
        self.learning_rate_input.setValue(0.1)
        self.learning_rate_input.setDecimals(3)
        grid.addWidget(self.learning_rate_input, row, 1)

        row += 1
        self.use_coords_cb = QtWidgets.QCheckBox("使用坐标特征 (x,y,z)")
        self.use_coords_cb.setChecked(True)
        grid.addWidget(self.use_coords_cb, row, 0, 1, 2)

        row += 1
        self.ignore_bg_cb = QtWidgets.QCheckBox("训练时忽略背景标签(0)")
        self.ignore_bg_cb.setChecked(False)
        grid.addWidget(self.ignore_bg_cb, row, 0, 1, 2)

        row += 1
        grid.addWidget(QtWidgets.QLabel("训练范围:"), row, 0)
        self.train_scope_combo = QtWidgets.QComboBox()
        self.train_scope_combo.addItems([
            "仅标注切片(推荐)",
            "全三维",
        ])
        grid.addWidget(self.train_scope_combo, row, 1, 1, 2)

        row += 1
        grid.addWidget(QtWidgets.QLabel("推理范围:"), row, 0)
        self.predict_scope_combo = QtWidgets.QComboBox()
        self.predict_scope_combo.addItems([
            "按切片方向全部切片(推荐)",
            "仅标注切片",
            "全三维",
        ])
        grid.addWidget(self.predict_scope_combo, row, 1, 1, 2)

        row += 1
        grid.addWidget(QtWidgets.QLabel("最大训练样本数:"), row, 0)
        self.max_samples_input = QtWidgets.QSpinBox()
        self.max_samples_input.setRange(1000, 5000000)
        self.max_samples_input.setSingleStep(10000)
        self.max_samples_input.setValue(300000)
        grid.addWidget(self.max_samples_input, row, 1)

        row += 1
        grid.addWidget(QtWidgets.QLabel("预测批大小:"), row, 0)
        self.predict_batch_input = QtWidgets.QSpinBox()
        self.predict_batch_input.setRange(10000, 5000000)
        self.predict_batch_input.setSingleStep(50000)
        self.predict_batch_input.setValue(500000)
        grid.addWidget(self.predict_batch_input, row, 1)

        row += 1
        self.alg_info = QtWidgets.QLabel()
        self.alg_info.setWordWrap(True)
        self.alg_info.setStyleSheet("color:#666; font-size:9pt; padding:8px;")
        grid.addWidget(self.alg_info, row, 0, 1, 3)

        main_layout.addWidget(param_group)

        display_group = QtWidgets.QGroupBox("结果显示")
        display_layout = QtWidgets.QVBoxLayout(display_group)

        self.overlay_checkbox = QtWidgets.QCheckBox("与原图融合显示")
        self.overlay_checkbox.setChecked(True)
        display_layout.addWidget(self.overlay_checkbox)

        overlay_param_layout = QtWidgets.QHBoxLayout()
        overlay_param_layout.addWidget(QtWidgets.QLabel("透明度:"))
        self.alpha_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.alpha_slider.setRange(10, 100)
        self.alpha_slider.setValue(50)
        overlay_param_layout.addWidget(self.alpha_slider)

        self.alpha_label = QtWidgets.QLabel("50%")
        self.alpha_slider.valueChanged.connect(lambda v: self.alpha_label.setText(f"{v}%"))
        overlay_param_layout.addWidget(self.alpha_label)

        overlay_param_layout.addWidget(QtWidgets.QLabel("颜色:"))
        self.color_combo = QtWidgets.QComboBox()
        self.color_combo.addItems(["红色", "绿色", "蓝色", "黄色", "青色", "品红"])
        overlay_param_layout.addWidget(self.color_combo)
        display_layout.addLayout(overlay_param_layout)

        main_layout.addWidget(display_group)
        main_layout.addStretch()

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        run_btn = QtWidgets.QPushButton("开始分割")
        run_btn.setMinimumWidth(110)
        run_btn.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(run_btn)

        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.setMinimumWidth(90)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)

    def _on_data_source_changed(self):
        use_file = self.use_file_radio.isChecked()
        self.input_file_edit.setEnabled(use_file)
        self.input_browse_btn.setEnabled(use_file)

    def _on_algorithm_changed(self):
        name = self.algorithm_combo.currentText()
        is_knn = name == "K-Nearest"
        is_gb = name == "Gradient Boosting"
        is_ensemble = not is_knn

        self.k_input.setEnabled(is_knn)
        self.n_estimators_input.setEnabled(is_ensemble)
        self.max_depth_input.setEnabled(name in ("Extra Trees", "Gradient Boosting", "Random Forest"))
        self.learning_rate_input.setEnabled(is_gb)

        infos = {
            "K-Nearest": "KNN：基于邻域投票，边界细腻，速度受样本规模影响较大。",
            "AdaBoost": "AdaBoost：逐步关注难分样本，适合中小规模训练样本。",
            "Bagging": "Bagging：并行集成弱学习器，稳定性好，抗过拟合能力较强。",
            "Extra Trees": "Extra Trees：随机化更强，训练快，常用于高维特征。",
            "Gradient Boosting": "Gradient Boosting：逐步优化损失，精度高但训练相对慢。",
            "Random Forest": "Random Forest：工业中最常用的树集成方法之一，鲁棒性好。",
        }
        self.alg_info.setText(infos.get(name, ""))

    def _browse_input_file(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择输入影像",
            "",
            "NIfTI文件 (*.nii *.nii.gz);;所有文件 (*)",
        )
        if filename:
            self.input_file_edit.setText(filename)

    def _browse_label_file(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择标签文件",
            "",
            "NIfTI文件 (*.nii *.nii.gz);;所有文件 (*)",
        )
        if filename:
            self.label_file_edit.setText(filename)
            self.selected_label_dataset = None

    def _pick_label_from_data_list(self):
        if self.parent_viewer is None or not hasattr(self.parent_viewer, 'get_available_label_datasets'):
            QtWidgets.QMessageBox.warning(self, "功能不可用", "当前主界面未提供数据列表标签接口。")
            return

        datasets = self.parent_viewer.get_available_label_datasets()
        if not datasets:
            QtWidgets.QMessageBox.information(self, "没有可用标签", "数据列表中没有可用的标签图层，请先手工标注并生成标签。")
            return

        option_texts = []
        mapping = {}
        for ds in datasets:
            info = ds.get('label_info', '')
            text = f"{ds['name']}  |  {info}" if info else ds['name']
            option_texts.append(text)
            mapping[text] = ds

        choice, ok = QtWidgets.QInputDialog.getItem(
            self,
            "选择数据列表标签",
            "请选择一个标签图层作为训练标签：",
            option_texts,
            0,
            False,
        )
        if not ok or not choice:
            return

        selected = mapping[choice]
        self.label_file_edit.setText(selected['path'])
        self.selected_label_dataset = selected

    def _create_label_file_interactive(self):
        if self.parent_viewer is None or not hasattr(self.parent_viewer, 'create_label_file_from_annotation'):
            QtWidgets.QMessageBox.warning(self, "功能不可用", "当前主界面未提供标签创建接口。")
            return

        suggested_path = self.label_file_edit.text().strip() if self.label_file_edit.text().strip() else None
        created_path = self.parent_viewer.create_label_file_from_annotation(suggested_output_path=suggested_path)
        if created_path:
            self.label_file_edit.setText(created_path)
            self.selected_label_dataset = None

    def _browse_output_dir(self):
        dirname = QtWidgets.QFileDialog.getExistingDirectory(self, "选择输出目录", "")
        if dirname:
            self.output_dir_edit.setText(dirname)

    def _validate_and_accept(self):
        self.use_current_data = self.use_current_radio.isChecked()

        if self.use_current_data:
            if self.current_data is None or self.current_data.get('array') is None:
                QtWidgets.QMessageBox.warning(self, "输入错误", "当前没有可用数据，请先加载CT影像。")
                return
            self.input_file = None
        else:
            input_file = self.input_file_edit.text().strip()
            if not input_file:
                QtWidgets.QMessageBox.warning(self, "输入错误", "请选择输入影像文件。")
                return
            if not os.path.exists(input_file):
                QtWidgets.QMessageBox.warning(self, "输入错误", f"输入影像不存在：\n{input_file}")
                return
            self.input_file = input_file

        label_file = self.label_file_edit.text().strip()
        if not label_file:
            QtWidgets.QMessageBox.warning(self, "输入错误", "请选择标签文件。")
            return
        if not os.path.exists(label_file):
            QtWidgets.QMessageBox.warning(self, "输入错误", f"标签文件不存在：\n{label_file}")
            return
        self.label_file = label_file
        if self.selected_label_dataset and self.selected_label_dataset.get('path') != self.label_file:
            self.selected_label_dataset = None

        output_dir = self.output_dir_edit.text().strip()
        self.output_dir = output_dir if output_dir else None
        if self.output_dir and not os.path.isdir(self.output_dir):
            QtWidgets.QMessageBox.warning(self, "输入错误", f"输出目录不存在：\n{self.output_dir}")
            return

        self.accept()

    def get_parameters(self):
        color_map = {
            "红色": (255, 0, 0),
            "绿色": (0, 255, 0),
            "蓝色": (0, 0, 255),
            "黄色": (255, 255, 0),
            "青色": (0, 255, 255),
            "品红": (255, 0, 255),
        }

        max_depth = self.max_depth_input.value()
        max_depth = None if max_depth == 0 else max_depth
        train_scope_map = {
            "仅标注切片(推荐)": "annotated_slices",
            "全三维": "full_volume",
        }
        predict_scope_map = {
            "按切片方向全部切片(推荐)": "directional_slices",
            "仅标注切片": "annotated_slices",
            "全三维": "full_volume",
        }

        predict_view_type = None
        if isinstance(self.selected_label_dataset, dict):
            predict_view_type = self.selected_label_dataset.get('annotation_view_type')
        if not predict_view_type and self.parent_viewer is not None:
            predict_view_type = getattr(self.parent_viewer, 'active_view', None)
        if not predict_view_type:
            predict_view_type = 'axial'

        return {
            'use_current_data': self.use_current_data,
            'current_data': self.current_data if self.use_current_data else None,
            'input_file': self.input_file,
            'label_file': self.label_file,
            'label_dataset_info': self.selected_label_dataset,
            'output_dir': self.output_dir,
            'algorithm': self.algorithm_combo.currentText(),
            'k_neighbors': self.k_input.value(),
            'n_estimators': self.n_estimators_input.value(),
            'max_depth': max_depth,
            'learning_rate': self.learning_rate_input.value(),
            'use_coordinates': self.use_coords_cb.isChecked(),
            'ignore_background': self.ignore_bg_cb.isChecked(),
            'train_scope': train_scope_map[self.train_scope_combo.currentText()],
            'predict_scope': predict_scope_map[self.predict_scope_combo.currentText()],
            'predict_view_type': predict_view_type,
            'max_train_samples': self.max_samples_input.value(),
            'predict_batch_size': self.predict_batch_input.value(),
            'overlay_with_original': self.overlay_checkbox.isChecked(),
            'overlay_alpha': self.alpha_slider.value() / 100.0,
            'overlay_color': color_map[self.color_combo.currentText()],
        }
