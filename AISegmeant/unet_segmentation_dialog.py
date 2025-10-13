# -*- coding: utf-8 -*-
"""UNet分割对话框"""

from PyQt5 import QtWidgets, QtCore
import os


class UnetSegmentationDialog(QtWidgets.QDialog):
    """UNet分割对话框 - 用于获取基线方法的参数"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("人工智能分割 - 基线方法 (UNet)")
        self.setMinimumWidth(700)
        self.setMinimumHeight(400)
        
        # 结果变量
        self.checkpoint_path = None
        self.output_dir = None
        self.input_file = None
        self.roi_size = (128, 128, 128)  # 滑窗尺寸
        self.sw_batch_size = 1  # 滑窗批量大小
        self.overlay_with_original = False  # 是否与原始图像融合显示
        
        # 创建主布局
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # 创建参数输入区域
        param_group = QtWidgets.QGroupBox("分割参数设置")
        param_layout = QtWidgets.QGridLayout()
        param_group.setLayout(param_layout)
        
        # 输入文件选择
        row = 0
        param_layout.addWidget(QtWidgets.QLabel("输入文件 (*.nii.gz):"), row, 0)
        self.input_file_edit = QtWidgets.QLineEdit()
        self.input_file_edit.setPlaceholderText("选择待分割的NIfTI文件...")
        param_layout.addWidget(self.input_file_edit, row, 1)
        
        browse_input_btn = QtWidgets.QPushButton("浏览...")
        browse_input_btn.clicked.connect(self.browse_input_file)
        param_layout.addWidget(browse_input_btn, row, 2)
        
        # 模型权重文件选择
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("模型权重文件 (*.pth):"), row, 0)
        self.checkpoint_edit = QtWidgets.QLineEdit()
        self.checkpoint_edit.setPlaceholderText("选择训练好的模型权重文件...")
        param_layout.addWidget(self.checkpoint_edit, row, 1)
        
        browse_checkpoint_btn = QtWidgets.QPushButton("浏览...")
        browse_checkpoint_btn.clicked.connect(self.browse_checkpoint)
        param_layout.addWidget(browse_checkpoint_btn, row, 2)
        
        # 输出目录选择
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("输出目录:"), row, 0)
        self.output_dir_edit = QtWidgets.QLineEdit()
        self.output_dir_edit.setPlaceholderText("选择分割结果保存目录...")
        param_layout.addWidget(self.output_dir_edit, row, 1)
        
        browse_output_btn = QtWidgets.QPushButton("浏览...")
        browse_output_btn.clicked.connect(self.browse_output_dir)
        param_layout.addWidget(browse_output_btn, row, 2)
        
        # 滑窗尺寸设置 (ROI Size)
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("滑窗尺寸 (ROI Size):"), row, 0)
        
        roi_layout = QtWidgets.QHBoxLayout()
        
        self.roi_x_input = QtWidgets.QSpinBox()
        self.roi_x_input.setRange(32, 512)
        self.roi_x_input.setValue(128)
        self.roi_x_input.setPrefix("X: ")
        roi_layout.addWidget(self.roi_x_input)
        
        self.roi_y_input = QtWidgets.QSpinBox()
        self.roi_y_input.setRange(32, 512)
        self.roi_y_input.setValue(128)
        self.roi_y_input.setPrefix("Y: ")
        roi_layout.addWidget(self.roi_y_input)
        
        self.roi_z_input = QtWidgets.QSpinBox()
        self.roi_z_input.setRange(32, 512)
        self.roi_z_input.setValue(128)
        self.roi_z_input.setPrefix("Z: ")
        roi_layout.addWidget(self.roi_z_input)
        
        roi_widget = QtWidgets.QWidget()
        roi_widget.setLayout(roi_layout)
        param_layout.addWidget(roi_widget, row, 1, 1, 2)
        
        # 滑窗批量大小设置
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("滑窗批量大小:"), row, 0)
        self.sw_batch_size_input = QtWidgets.QSpinBox()
        self.sw_batch_size_input.setRange(1, 8)
        self.sw_batch_size_input.setValue(1)
        self.sw_batch_size_input.setToolTip("滑窗推理的批量大小，增大可能提高速度但需要更多显存")
        param_layout.addWidget(self.sw_batch_size_input, row, 1)
        
        # 添加说明标签
        row += 1
        info_label = QtWidgets.QLabel(
            "说明: \n"
            "• 滑窗尺寸(ROI Size)应与训练时使用的patch尺寸一致，默认为(128, 128, 128)\n"
            "• 滑窗批量大小控制每次处理的滑窗数量，增大可能提高速度但需要更多显存\n"
            "• 使用滑窗推理可处理任意大小的图像，保持原始分辨率"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 9pt; padding: 10px;")
        param_layout.addWidget(info_label, row, 0, 1, 3)
        
        # 将参数区域添加到主布局
        main_layout.addWidget(param_group)
        
        # 显示选项组
        display_group = QtWidgets.QGroupBox("显示选项")
        display_layout = QtWidgets.QVBoxLayout()
        display_group.setLayout(display_layout)
        
        # 融合显示选项
        self.overlay_checkbox = QtWidgets.QCheckBox("与原始图像融合显示（推荐）")
        self.overlay_checkbox.setChecked(True)  # 默认勾选
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
        self.color_combo.setCurrentIndex(0)  # 默认红色
        overlay_params_layout.addWidget(self.color_combo)
        
        display_layout.addLayout(overlay_params_layout)
        
        # 添加说明
        overlay_info = QtWidgets.QLabel(
            "融合显示可以直观地看到分割区域在原始图像上的位置，\n"
            "适合验证分割效果和医学诊断。"
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
    
    def browse_input_file(self):
        """浏览输入文件"""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择输入文件",
            "",
            "NIfTI文件 (*.nii *.nii.gz);;所有文件 (*)"
        )
        if filename:
            self.input_file_edit.setText(filename)
    
    def browse_checkpoint(self):
        """浏览模型权重文件"""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择模型权重文件",
            "",
            "PyTorch模型文件 (*.pth *.pt);;所有文件 (*)"
        )
        if filename:
            self.checkpoint_edit.setText(filename)
    
    def browse_output_dir(self):
        """浏览输出目录"""
        dirname = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            ""
        )
        if dirname:
            self.output_dir_edit.setText(dirname)
    
    def validate_and_accept(self):
        """验证输入并接受对话框"""
        # 检查输入文件
        input_file = self.input_file_edit.text().strip()
        if not input_file:
            QtWidgets.QMessageBox.warning(
                self,
                "输入错误",
                "请选择输入文件！"
            )
            return
        
        if not os.path.exists(input_file):
            QtWidgets.QMessageBox.warning(
                self,
                "输入错误",
                f"输入文件不存在：\n{input_file}"
            )
            return
        
        # 检查模型权重文件
        checkpoint_path = self.checkpoint_edit.text().strip()
        if not checkpoint_path:
            QtWidgets.QMessageBox.warning(
                self,
                "输入错误",
                "请选择模型权重文件！"
            )
            return
        
        if not os.path.exists(checkpoint_path):
            QtWidgets.QMessageBox.warning(
                self,
                "输入错误",
                f"模型权重文件不存在：\n{checkpoint_path}"
            )
            return
        
        # 检查输出目录
        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            QtWidgets.QMessageBox.warning(
                self,
                "输入错误",
                "请选择输出目录！"
            )
            return
        
        # 保存参数
        self.input_file = input_file
        self.checkpoint_path = checkpoint_path
        self.output_dir = output_dir
        self.roi_size = (
            self.roi_x_input.value(),
            self.roi_y_input.value(),
            self.roi_z_input.value()
        )
        self.sw_batch_size = self.sw_batch_size_input.value()
        self.overlay_with_original = self.overlay_checkbox.isChecked()
        
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
            'input_file': self.input_file,
            'checkpoint_path': self.checkpoint_path,
            'output_dir': self.output_dir,
            'roi_size': self.roi_size,
            'sw_batch_size': self.sw_batch_size,
            'overlay_with_original': self.overlay_with_original,
            'overlay_alpha': self.alpha_slider.value() / 100.0,
            'overlay_color': color_map[self.color_combo.currentText()]
        }

