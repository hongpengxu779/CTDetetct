# -*- coding: utf-8 -*-
"""区域生长对话框"""

from PyQt5 import QtWidgets, QtCore


class RegionGrowingDialog(QtWidgets.QDialog):
    """区域生长对话框 - 用于获取区域生长的参数
    
    改进的工作流：
    - 点击"从主界面选择种子点"时对话框最小化而非关闭
    - 在主界面右键添加种子点后，对话框实时更新显示
    - 用户可随时切换回对话框继续操作
    """
    
    def __init__(self, parent=None, current_data=None):
        super().__init__(parent)
        self.parent_viewer = parent
        self.current_data = current_data  # 当前已加载的数据
        self.setWindowTitle("传统分割检测 - 区域生长")
        self.setMinimumWidth(650)
        self.setMinimumHeight(500)
        
        # 允许对话框最小化（添加窗口按钮）
        self.setWindowFlags(
            self.windowFlags()
            | QtCore.Qt.WindowMinimizeButtonHint
            | QtCore.Qt.WindowMaximizeButtonHint
        )
        
        # 结果变量
        self.use_current_data = True  # 默认使用当前数据
        self.seed_points = []  # 种子点列表
        self.lower_threshold = 0.0
        self.upper_threshold = 255.0
        self.multiplier = 2.5
        self.number_of_iterations = 5
        self.replace_value = 255
        self._is_selecting_seeds = False  # 是否正在选择种子点
        
        # 创建主布局
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # 创建参数输入区域
        param_group = QtWidgets.QGroupBox("区域生长参数设置")
        param_layout = QtWidgets.QGridLayout()
        param_group.setLayout(param_layout)
        
        row = 0
        
        # 数据来源提示
        if current_data is not None:
            data_info = QtWidgets.QLabel("将对当前已加载的数据进行区域生长分割")
            data_info.setStyleSheet("color: #2196F3; font-weight: bold; padding: 5px;")
            param_layout.addWidget(data_info, row, 0, 1, 3)
            row += 1
        else:
            data_info = QtWidgets.QLabel("请先在主界面加载数据")
            data_info.setStyleSheet("color: #F44336; font-weight: bold; padding: 5px;")
            param_layout.addWidget(data_info, row, 0, 1, 3)
            row += 1
        
        # 算法选择
        param_layout.addWidget(QtWidgets.QLabel("算法类型:"), row, 0)
        self.algorithm_combo = QtWidgets.QComboBox()
        self.algorithm_combo.addItems([
            "ConnectedThreshold（连通阈值）",
            "ConfidenceConnected（置信连接）",
            "NeighborhoodConnected（邻域连接）"
        ])
        self.algorithm_combo.currentIndexChanged.connect(self.on_algorithm_changed)
        param_layout.addWidget(self.algorithm_combo, row, 1, 1, 2)
        row += 1
        
        # 种子点设置说明
        seed_label = QtWidgets.QLabel("种子点:")
        seed_label.setToolTip("在主界面的切片视图中右键点击选择种子点")
        param_layout.addWidget(seed_label, row, 0)
        
        seed_layout = QtWidgets.QVBoxLayout()
        
        self.seed_display = QtWidgets.QTextEdit()
        self.seed_display.setReadOnly(True)
        self.seed_display.setMaximumHeight(100)
        self.seed_display.setPlaceholderText(
            "点击下方按钮后，在主界面切片视图中右键点击选择种子点\n"
            "可以选择多个种子点，对话框会实时更新"
        )
        seed_layout.addWidget(self.seed_display)
        
        # 添加种子点操作按钮
        seed_button_layout = QtWidgets.QHBoxLayout()
        
        self.select_seed_btn = QtWidgets.QPushButton("📌 从主界面选择种子点")
        self.select_seed_btn.setStyleSheet(
            "QPushButton { background-color: #E8F5E9; color: #2E7D32; font-weight: bold; padding: 6px; }"
            "QPushButton:hover { background-color: #C8E6C9; }"
        )
        self.select_seed_btn.clicked.connect(self.start_seed_selection)
        seed_button_layout.addWidget(self.select_seed_btn)
        
        self.clear_seed_btn = QtWidgets.QPushButton("🗑 清除种子点")
        self.clear_seed_btn.setStyleSheet(
            "QPushButton { background-color: #FFEBEE; color: #C62828; padding: 6px; }"
            "QPushButton:hover { background-color: #FFCDD2; }"
        )
        self.clear_seed_btn.clicked.connect(self.clear_seeds)
        seed_button_layout.addWidget(self.clear_seed_btn)
        
        seed_layout.addLayout(seed_button_layout)
        
        # 种子点选择模式提示
        self.seed_mode_label = QtWidgets.QLabel("")
        self.seed_mode_label.setStyleSheet(
            "color: #FF6F00; font-weight: bold; padding: 4px; "
            "background-color: #FFF8E1; border-radius: 3px;"
        )
        self.seed_mode_label.setVisible(False)
        seed_layout.addWidget(self.seed_mode_label)
        
        seed_widget = QtWidgets.QWidget()
        seed_widget.setLayout(seed_layout)
        param_layout.addWidget(seed_widget, row, 1, 1, 2)
        row += 1
        
        # 阈值范围 - ConnectedThreshold算法使用
        param_layout.addWidget(QtWidgets.QLabel("下阈值:"), row, 0)
        self.lower_threshold_input = QtWidgets.QDoubleSpinBox()
        self.lower_threshold_input.setRange(-10000, 10000)
        self.lower_threshold_input.setValue(0)
        self.lower_threshold_input.setDecimals(1)
        self.lower_threshold_input.setToolTip("连通阈值算法的下阈值")
        param_layout.addWidget(self.lower_threshold_input, row, 1, 1, 2)
        row += 1
        
        param_layout.addWidget(QtWidgets.QLabel("上阈值:"), row, 0)
        self.upper_threshold_input = QtWidgets.QDoubleSpinBox()
        self.upper_threshold_input.setRange(-10000, 10000)
        self.upper_threshold_input.setValue(255)
        self.upper_threshold_input.setDecimals(1)
        self.upper_threshold_input.setToolTip("连通阈值算法的上阈值")
        param_layout.addWidget(self.upper_threshold_input, row, 1, 1, 2)
        row += 1
        
        # ConfidenceConnected参数
        param_layout.addWidget(QtWidgets.QLabel("倍增因子:"), row, 0)
        self.multiplier_input = QtWidgets.QDoubleSpinBox()
        self.multiplier_input.setRange(0.1, 10.0)
        self.multiplier_input.setValue(2.5)
        self.multiplier_input.setSingleStep(0.1)
        self.multiplier_input.setDecimals(1)
        self.multiplier_input.setToolTip("置信连接算法的倍增因子（控制阈值范围）")
        param_layout.addWidget(self.multiplier_input, row, 1, 1, 2)
        row += 1
        
        param_layout.addWidget(QtWidgets.QLabel("迭代次数:"), row, 0)
        self.iterations_input = QtWidgets.QSpinBox()
        self.iterations_input.setRange(1, 20)
        self.iterations_input.setValue(5)
        self.iterations_input.setToolTip("置信连接和邻域连接算法的迭代次数")
        param_layout.addWidget(self.iterations_input, row, 1, 1, 2)
        row += 1
        
        # 替换值
        param_layout.addWidget(QtWidgets.QLabel("替换值:"), row, 0)
        self.replace_value_input = QtWidgets.QSpinBox()
        self.replace_value_input.setRange(0, 65535)
        self.replace_value_input.setValue(255)
        self.replace_value_input.setToolTip("分割区域将被设置为此值")
        param_layout.addWidget(self.replace_value_input, row, 1, 1, 2)
        row += 1
        
        # 添加算法说明
        self.algorithm_info = QtWidgets.QLabel()
        self.algorithm_info.setWordWrap(True)
        self.algorithm_info.setStyleSheet("color: #666; font-size: 9pt; padding: 10px; background-color: #f5f5f5; border-radius: 4px;")
        param_layout.addWidget(self.algorithm_info, row, 0, 1, 3)
        row += 1
        
        # 根据初始算法设置界面
        self.on_algorithm_changed(0)
        
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
            "适合验证分割效果。"
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
    
    def on_algorithm_changed(self, index):
        """当算法选择改变时，更新界面和说明"""
        algorithm_name = self.algorithm_combo.currentText()
        
        if "ConnectedThreshold" in algorithm_name:
            self.lower_threshold_input.setEnabled(True)
            self.upper_threshold_input.setEnabled(True)
            self.multiplier_input.setEnabled(False)
            self.iterations_input.setEnabled(False)
            
            self.algorithm_info.setText(
                "连通阈值算法说明:\n"
                "• 从种子点开始，生长包含灰度值在[下阈值, 上阈值]范围内的邻接像素\n"
                "• 需要手动设置阈值范围\n"
                "• 适合目标区域灰度值相对均匀的情况\n"
                "• 推荐先观察直方图确定合适的阈值范围"
            )
        elif "ConfidenceConnected" in algorithm_name:
            self.lower_threshold_input.setEnabled(False)
            self.upper_threshold_input.setEnabled(False)
            self.multiplier_input.setEnabled(True)
            self.iterations_input.setEnabled(True)
            
            self.algorithm_info.setText(
                "置信连接算法说明:\n"
                "• 自动计算阈值范围：均值 ± 倍增因子 × 标准差\n"
                "• 通过多次迭代逐步扩展分割区域\n"
                "• 不需要手动设置阈值，更加自适应\n"
                "• 倍增因子越大，分割区域越大；迭代次数越多，边界越精细"
            )
        else:  # NeighborhoodConnected
            self.lower_threshold_input.setEnabled(True)
            self.upper_threshold_input.setEnabled(True)
            self.multiplier_input.setEnabled(False)
            self.iterations_input.setEnabled(True)
            
            self.algorithm_info.setText(
                "邻域连接算法说明:\n"
                "• 基于种子点邻域的统计信息进行生长\n"
                "• 结合阈值范围和邻域一致性\n"
                "• 通过多次迭代细化分割边界\n"
                "• 适合处理有一定噪声的图像"
            )
    
    def set_seed_points(self, seed_points):
        """设置种子点（从主界面或 slice_viewer 实时调用）
        
        参数
        ----
        seed_points : list
            种子点列表，每个元素为 (z, y, x) 元组
        """
        self.seed_points = list(seed_points)
        self.update_seed_display()
    
    def update_seed_display(self):
        """更新种子点显示"""
        if self.seed_points:
            seed_text = f"已设置 {len(self.seed_points)} 个种子点:\n"
            for i, point in enumerate(self.seed_points):
                seed_text += f"  点{i+1}: (z={point[0]}, y={point[1]}, x={point[2]})\n"
            self.seed_display.setText(seed_text)
            
            # 如果正在选择模式，更新提示
            if self._is_selecting_seeds:
                self.seed_mode_label.setText(
                    f"🔴 种子点选择中... 已选 {len(self.seed_points)} 个 | "
                    f"在主界面右键继续添加，完成后点击此窗口"
                )
        else:
            self.seed_display.clear()
    
    def start_seed_selection(self):
        """开始选择种子点 — 最小化对话框而非关闭"""
        self._is_selecting_seeds = True
        
        # 更新UI提示
        self.seed_mode_label.setText(
            "🔴 种子点选择模式已开启 | 在主界面切片视图中右键点击添加种子点"
        )
        self.seed_mode_label.setVisible(True)
        self.select_seed_btn.setText("📌 继续选择种子点...")
        self.select_seed_btn.setStyleSheet(
            "QPushButton { background-color: #FFF3E0; color: #E65100; font-weight: bold; padding: 6px; }"
            "QPushButton:hover { background-color: #FFE0B2; }"
        )
        
        # 在主界面状态栏提示
        if self.parent_viewer and hasattr(self.parent_viewer, 'status_label'):
            self.parent_viewer.status_label.setText(
                "📌 种子点选择模式：在切片视图中右键点击 → 选择\"添加区域生长种子点\" | "
                "完成后切换回区域生长对话框"
            )
        
        # 最小化对话框而不是关闭，这样用户可以方便地切换回来
        self.showMinimized()
    
    def changeEvent(self, event):
        """处理窗口状态变化事件"""
        super().changeEvent(event)
        if event.type() == QtCore.QEvent.WindowStateChange:
            # 当对话框从最小化恢复时
            if not self.isMinimized() and self._is_selecting_seeds:
                self._is_selecting_seeds = False
                self.select_seed_btn.setText("📌 从主界面选择种子点")
                self.select_seed_btn.setStyleSheet(
                    "QPushButton { background-color: #E8F5E9; color: #2E7D32; font-weight: bold; padding: 6px; }"
                    "QPushButton:hover { background-color: #C8E6C9; }"
                )
                
                # 从父窗口同步最新的种子点
                if self.parent_viewer and hasattr(self.parent_viewer, 'region_growing_seed_points'):
                    self.set_seed_points(self.parent_viewer.region_growing_seed_points)
                
                if self.seed_points:
                    self.seed_mode_label.setText(
                        f"✅ 已完成选择，共 {len(self.seed_points)} 个种子点"
                    )
                    self.seed_mode_label.setStyleSheet(
                        "color: #2E7D32; font-weight: bold; padding: 4px; "
                        "background-color: #E8F5E9; border-radius: 3px;"
                    )
                else:
                    self.seed_mode_label.setVisible(False)
    
    def clear_seeds(self):
        """清除所有种子点"""
        self.seed_points = []
        self.update_seed_display()
        self.seed_mode_label.setVisible(False)
        
        # 同时清除主界面的种子点和标记
        if self.parent_viewer and hasattr(self.parent_viewer, 'clear_region_growing_seed_points'):
            self.parent_viewer.clear_region_growing_seed_points()
        
        QtWidgets.QMessageBox.information(self, "已清除", "所有种子点已清除")
    
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
        
        # 从父窗口同步最新的种子点（确保拿到最新的）
        if self.parent_viewer and hasattr(self.parent_viewer, 'region_growing_seed_points'):
            self.seed_points = list(self.parent_viewer.region_growing_seed_points)
        
        # 检查种子点
        if not self.seed_points or len(self.seed_points) == 0:
            QtWidgets.QMessageBox.warning(
                self,
                "输入错误",
                "请先设置种子点！\n\n"
                "点击\"从主界面选择种子点\"按钮，\n"
                "然后在切片视图中右键点击选择种子点。"
            )
            return
        
        # 保存参数
        self.lower_threshold = self.lower_threshold_input.value()
        self.upper_threshold = self.upper_threshold_input.value()
        self.multiplier = self.multiplier_input.value()
        self.number_of_iterations = self.iterations_input.value()
        self.replace_value = self.replace_value_input.value()
        
        # 验证阈值
        if self.algorithm_combo.currentIndex() == 0:  # ConnectedThreshold
            if self.lower_threshold >= self.upper_threshold:
                QtWidgets.QMessageBox.warning(
                    self,
                    "参数错误",
                    "下阈值必须小于上阈值！"
                )
                return
        
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
        
        # 算法类型映射
        algorithm_map = {
            0: "ConnectedThreshold",
            1: "ConfidenceConnected",
            2: "NeighborhoodConnected"
        }
        
        return {
            'current_data': self.current_data,
            'algorithm': algorithm_map[self.algorithm_combo.currentIndex()],
            'seed_points': self.seed_points,
            'lower_threshold': self.lower_threshold,
            'upper_threshold': self.upper_threshold,
            'multiplier': self.multiplier,
            'number_of_iterations': self.number_of_iterations,
            'replace_value': self.replace_value,
            'overlay_with_original': self.overlay_checkbox.isChecked(),
            'overlay_alpha': self.alpha_slider.value() / 100.0,
            'overlay_color': color_map[self.color_combo.currentText()]
        }

