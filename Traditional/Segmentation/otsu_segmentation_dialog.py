# -*- coding: utf-8 -*-
"""OTSU阈值分割对话框"""

from PyQt5 import QtWidgets, QtCore


class OtsuSegmentationDialog(QtWidgets.QDialog):
    """OTSU阈值分割对话框 - 自动阈值分割"""
    
    def __init__(self, parent=None, current_data=None):
        super().__init__(parent)
        self.parent = parent
        self.current_data = current_data  # 当前已加载的数据
        self.setWindowTitle("传统分割检测 - OTSU阈值分割")
        self.setMinimumWidth(650)
        self.setMinimumHeight(450)
        
        # 结果变量
        self.number_of_histogram_bins = 128
        self.mask_output = True
        self.mask_value = 255
        self.outside_value = 0
        self.inside_value = 255
        
        # 创建主布局
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # 创建参数输入区域
        param_group = QtWidgets.QGroupBox("OTSU分割参数设置")
        param_layout = QtWidgets.QGridLayout()
        param_group.setLayout(param_layout)
        
        row = 0
        
        # 数据来源提示
        if current_data is not None:
            data_info = QtWidgets.QLabel("将对当前已加载的数据进行OTSU阈值分割")
            data_info.setStyleSheet("color: #2196F3; font-weight: bold; padding: 5px;")
            param_layout.addWidget(data_info, row, 0, 1, 3)
            row += 1
        else:
            data_info = QtWidgets.QLabel("请先在主界面加载数据")
            data_info.setStyleSheet("color: #F44336; font-weight: bold; padding: 5px;")
            param_layout.addWidget(data_info, row, 0, 1, 3)
            row += 1
        
        # 算法说明
        algo_info = QtWidgets.QLabel(
            "OTSU算法说明：\n"
            "• 自动计算最佳阈值，无需手动设置\n"
            "• 基于图像灰度直方图的类间方差最大化\n"
            "• 适合前景和背景灰度分布清晰的图像\n"
            "• 不需要种子点，全局自动分割"
        )
        algo_info.setWordWrap(True)
        algo_info.setStyleSheet(
            "color: #666; font-size: 9pt; padding: 10px; "
            "background-color: #E3F2FD; border-radius: 4px; border-left: 4px solid #2196F3;"
        )
        param_layout.addWidget(algo_info, row, 0, 1, 3)
        row += 1
        
        # 添加分隔线
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        param_layout.addWidget(line, row, 0, 1, 3)
        row += 1
        
        # 直方图bins数量
        param_layout.addWidget(QtWidgets.QLabel("直方图bins数量:"), row, 0)
        self.bins_input = QtWidgets.QSpinBox()
        self.bins_input.setRange(8, 512)
        self.bins_input.setValue(128)
        self.bins_input.setSingleStep(8)
        self.bins_input.setToolTip("计算阈值时使用的直方图bins数量（通常128或256）")
        param_layout.addWidget(self.bins_input, row, 1, 1, 2)
        row += 1
        
        # 输出模式选择
        param_layout.addWidget(QtWidgets.QLabel("输出模式:"), row, 0)
        self.output_mode_combo = QtWidgets.QComboBox()
        self.output_mode_combo.addItems([
            "二值掩码输出（推荐）",
            "保留原始灰度值"
        ])
        self.output_mode_combo.currentIndexChanged.connect(self.on_output_mode_changed)
        param_layout.addWidget(self.output_mode_combo, row, 1, 1, 2)
        row += 1
        
        # 二值掩码模式的参数
        self.mask_params_label = QtWidgets.QLabel("掩码参数:")
        param_layout.addWidget(self.mask_params_label, row, 0)
        
        mask_layout = QtWidgets.QHBoxLayout()
        mask_layout.addWidget(QtWidgets.QLabel("前景值:"))
        self.inside_value_input = QtWidgets.QSpinBox()
        self.inside_value_input.setRange(0, 65535)
        self.inside_value_input.setValue(255)
        self.inside_value_input.setToolTip("分割区域（前景）的像素值")
        mask_layout.addWidget(self.inside_value_input)
        
        mask_layout.addWidget(QtWidgets.QLabel("  背景值:"))
        self.outside_value_input = QtWidgets.QSpinBox()
        self.outside_value_input.setRange(0, 65535)
        self.outside_value_input.setValue(0)
        self.outside_value_input.setToolTip("非分割区域（背景）的像素值")
        mask_layout.addWidget(self.outside_value_input)
        
        mask_widget = QtWidgets.QWidget()
        mask_widget.setLayout(mask_layout)
        param_layout.addWidget(mask_widget, row, 1, 1, 2)
        row += 1
        
        # 多阈值选项（可选，用于多类别分割）
        param_layout.addWidget(QtWidgets.QLabel("阈值数量:"), row, 0)
        threshold_layout = QtWidgets.QHBoxLayout()
        
        self.single_threshold_radio = QtWidgets.QRadioButton("单阈值（二分类）")
        self.single_threshold_radio.setChecked(True)
        self.single_threshold_radio.toggled.connect(self.on_threshold_mode_changed)
        threshold_layout.addWidget(self.single_threshold_radio)
        
        self.multi_threshold_radio = QtWidgets.QRadioButton("多阈值")
        threshold_layout.addWidget(self.multi_threshold_radio)
        
        self.num_thresholds_input = QtWidgets.QSpinBox()
        self.num_thresholds_input.setRange(2, 5)
        self.num_thresholds_input.setValue(2)
        self.num_thresholds_input.setEnabled(False)
        self.num_thresholds_input.setToolTip("多阈值分割的类别数量")
        threshold_layout.addWidget(self.num_thresholds_input)
        
        threshold_widget = QtWidgets.QWidget()
        threshold_widget.setLayout(threshold_layout)
        param_layout.addWidget(threshold_widget, row, 1, 1, 2)
        row += 1
        
        # 添加说明
        info_label = QtWidgets.QLabel(
            "说明：\n"
            "• 单阈值：将图像分为前景和背景两类（使用单一颜色）\n"
            "• 多阈值：将图像分为多个类别，融合显示时每个类别使用不同颜色\n"
            "  （例如：标签1=红色，标签2=绿色，标签3=蓝色...）\n"
            "• bins数量越大，阈值计算越精确，但计算时间也越长\n"
            "• OTSU算法会自动寻找最佳阈值，无需手动调整"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 9pt; padding: 10px;")
        param_layout.addWidget(info_label, row, 0, 1, 3)
        row += 1
        
        # 将参数区域添加到主布局
        main_layout.addWidget(param_group)
        
        # 显示选项组
        display_group = QtWidgets.QGroupBox("显示选项")
        display_layout = QtWidgets.QVBoxLayout()
        display_group.setLayout(display_layout)
        
        # 融合显示选项
        self.overlay_checkbox = QtWidgets.QCheckBox("与原始图像融合显示（推荐）")
        self.overlay_checkbox.setChecked(True)
        self.overlay_checkbox.setToolTip("将分割结果以彩色半透明方式叠加在原始图像上")
        display_layout.addWidget(self.overlay_checkbox)
        
        # 融合参数设置
        overlay_params_layout = QtWidgets.QHBoxLayout()
        
        overlay_params_layout.addWidget(QtWidgets.QLabel("透明度:"))
        self.alpha_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.alpha_slider.setRange(10, 100)
        self.alpha_slider.setValue(50)
        self.alpha_slider.setToolTip("分割区域的透明度（10-100%）")
        overlay_params_layout.addWidget(self.alpha_slider)
        
        self.alpha_label = QtWidgets.QLabel("50%")
        self.alpha_slider.valueChanged.connect(lambda v: self.alpha_label.setText(f"{v}%"))
        overlay_params_layout.addWidget(self.alpha_label)
        
        overlay_params_layout.addWidget(QtWidgets.QLabel("  颜色:"))
        self.color_combo = QtWidgets.QComboBox()
        self.color_combo.addItems(["红色", "绿色", "蓝色", "黄色", "青色", "品红"])
        self.color_combo.setCurrentIndex(1)  # 默认绿色
        overlay_params_layout.addWidget(self.color_combo)
        
        display_layout.addLayout(overlay_params_layout)
        
        # 添加说明
        overlay_info = QtWidgets.QLabel(
            "融合显示可以直观地看到分割区域在原始图像上的位置。\n"
            "注意：多阈值模式下会自动为不同类别使用不同颜色（红、绿、蓝等），上方的颜色选择将被忽略。"
        )
        overlay_info.setWordWrap(True)
        overlay_info.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        display_layout.addWidget(overlay_info)
        
        main_layout.addWidget(display_group)
        
        # 添加弹性空间
        main_layout.addStretch()
        
        # 按钮区域
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        
        self.run_button = QtWidgets.QPushButton("开始分割")
        self.run_button.setMinimumWidth(100)
        self.run_button.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(self.run_button)
        
        self.cancel_button = QtWidgets.QPushButton("取消")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(button_layout)
    
    def on_output_mode_changed(self, index):
        """当输出模式改变时"""
        is_mask_mode = (index == 0)
        self.mask_params_label.setEnabled(is_mask_mode)
        self.inside_value_input.setEnabled(is_mask_mode)
        self.outside_value_input.setEnabled(is_mask_mode)
    
    def on_threshold_mode_changed(self):
        """当阈值模式改变时"""
        is_multi = self.multi_threshold_radio.isChecked()
        self.num_thresholds_input.setEnabled(is_multi)
    
    def validate_and_accept(self):
        """验证输入并接受对话框"""
        # 检查是否有数据
        if self.current_data is None:
            QtWidgets.QMessageBox.warning(
                self,
                "输入错误",
                "当前没有已加载的数据！请先在主界面加载数据。"
            )
            return
        
        # 保存参数
        self.number_of_histogram_bins = self.bins_input.value()
        self.mask_output = (self.output_mode_combo.currentIndex() == 0)
        self.inside_value = self.inside_value_input.value()
        self.outside_value = self.outside_value_input.value()
        
        # 接受对话框
        self.accept()
    
    def get_parameters(self):
        """获取用户输入的参数"""
        # 颜色映射
        color_map = {
            "红色": (255, 0, 0),
            "绿色": (0, 255, 0),
            "蓝色": (0, 0, 255),
            "黄色": (255, 255, 0),
            "青色": (0, 255, 255),
            "品红": (255, 0, 255)
        }
        
        return {
            'current_data': self.current_data,
            'number_of_histogram_bins': self.number_of_histogram_bins,
            'mask_output': self.mask_output,
            'inside_value': self.inside_value,
            'outside_value': self.outside_value,
            'use_multi_threshold': self.multi_threshold_radio.isChecked(),
            'num_thresholds': self.num_thresholds_input.value() if self.multi_threshold_radio.isChecked() else 1,
            'overlay_with_original': self.overlay_checkbox.isChecked(),
            'overlay_alpha': self.alpha_slider.value() / 100.0,
            'overlay_color': color_map[self.color_combo.currentText()]
        }

