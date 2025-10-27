"""
CT查看器UI组件
包含样式表、菜单、工具栏等UI相关功能
"""

from PyQt5 import QtWidgets, QtCore


class UIComponents:
    """UI组件管理类，作为Mixin使用"""
    
    def apply_stylesheet(self):
        """应用样式表以美化界面"""
        stylesheet = """
        QMainWindow {
            background-color: #f5f5f5;
        }
        
        QWidget {
            background-color: #f5f5f5;
        }
        
        QMenuBar {
            background-color: #ffffff;
            border-bottom: 1px solid #d0d0d0;
            padding: 2px 4px;
            min-height: 28px;
            spacing: 3px;
        }
        
        QMenuBar::item {
            background-color: transparent;
            padding: 6px 12px;
            border-radius: 4px;
            margin: 0px;
        }
        
        QMenuBar::item:selected {
            background-color: #e3f2fd;
        }
        
        QMenuBar::item:pressed {
            background-color: #bbdefb;
        }
        
        QMenu {
            background-color: #ffffff;
            border: 1px solid #d0d0d0;
            border-radius: 4px;
        }
        
        QMenu::item {
            padding: 6px 25px;
        }
        
        QMenu::item:selected {
            background-color: #e3f2fd;
        }
        
        QGroupBox {
            background-color: #ffffff;
            border: 1px solid #d0d0d0;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 4px 8px;
            background-color: #ffffff;
            border-radius: 3px;
        }
        
        QPushButton {
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 6px 16px;
            font-weight: 500;
        }
        
        QPushButton:hover {
            background-color: #1976D2;
        }
        
        QPushButton:pressed {
            background-color: #0D47A1;
        }
        
        QPushButton:disabled {
            background-color: #BDBDBD;
        }
        
        QSlider::groove:horizontal {
            border: 1px solid #BDBDBD;
            height: 6px;
            background: #E0E0E0;
            border-radius: 3px;
        }
        
        QSlider::handle:horizontal {
            background: #2196F3;
            border: 1px solid #1976D2;
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 8px;
        }
        
        QSlider::handle:horizontal:hover {
            background: #1976D2;
        }
        
        QLabel {
            color: #424242;
        }
        
        QLineEdit {
            background-color: #ffffff;
            border: 1px solid #BDBDBD;
            border-radius: 4px;
            padding: 6px;
        }
        
        QLineEdit:focus {
            border: 2px solid #2196F3;
        }
        
        QSpinBox, QDoubleSpinBox {
            background-color: #ffffff;
            border: 1px solid #BDBDBD;
            border-radius: 4px;
            padding: 4px;
        }
        
        QSpinBox:focus, QDoubleSpinBox:focus {
            border: 2px solid #2196F3;
        }
        
        QRadioButton {
            spacing: 8px;
        }
        
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
        }
        
        QCheckBox {
            spacing: 8px;
        }
        
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
        }
        """
        self.setStyleSheet(stylesheet)
    
    def create_menu(self):
        """创建菜单栏"""
        # 创建菜单栏
        self.menu_bar = QtWidgets.QMenuBar()
        self.menu_bar.setNativeMenuBar(False)  # 禁用原生菜单栏，确保菜单栏始终显示
        
        # 文件菜单
        file_menu = self.menu_bar.addMenu("文件")
        import_action = QtWidgets.QAction("导入文件", self)
        import_action.triggered.connect(self.import_file)
        file_menu.addAction(import_action)
          
        # 滤波菜单
        filter_menu = self.menu_bar.addMenu("滤波")
        aniso_action = QtWidgets.QAction("各向异性平滑", self)
        aniso_action.triggered.connect(self.apply_anisotropic_filter)
        filter_menu.addAction(aniso_action)
        
        curvature_action = QtWidgets.QAction("曲率流去噪", self)
        curvature_action.triggered.connect(self.apply_curvature_flow_filter)
        filter_menu.addAction(curvature_action)
        
        median_action = QtWidgets.QAction("中值", self)
        median_action.triggered.connect(self.apply_median_filter)
        filter_menu.addAction(median_action)
        
        gaussian_action = QtWidgets.QAction("高斯", self)
        gaussian_action.triggered.connect(self.apply_gaussian_filter)
        filter_menu.addAction(gaussian_action)
        
        bilateral_action = QtWidgets.QAction("双边", self)
        bilateral_action.triggered.connect(self.apply_bilateral_filter)
        filter_menu.addAction(bilateral_action)
        
        # CT重建菜单
        ct_menu = self.menu_bar.addMenu("CT重建")
        ball_phantom_action = QtWidgets.QAction("多球标定", self)
        ball_phantom_action.triggered.connect(self.run_ball_phantom_calibration)
        ct_menu.addAction(ball_phantom_action)
        
        helical_ct_action = QtWidgets.QAction("CT螺旋重建", self)
        helical_ct_action.triggered.connect(self.run_helical_ct_reconstruction)
        ct_menu.addAction(helical_ct_action)
        
        circle_ct_action = QtWidgets.QAction("CT圆轨迹", self)
        circle_ct_action.triggered.connect(self.run_circle_ct_reconstruction)
        ct_menu.addAction(circle_ct_action)
        
        # 人工智能分割菜单
        ai_menu = self.menu_bar.addMenu("人工智能分割")
        unet_action = QtWidgets.QAction("基线方法", self)
        unet_action.triggered.connect(self.run_unet_segmentation)
        ai_menu.addAction(unet_action)
        
        # 配准菜单（占位）
        config_menu = self.menu_bar.addMenu("配准")
        
        # 使用QMainWindow的setMenuBar方法，菜单栏会自动显示在窗口顶部
        self.setMenuBar(self.menu_bar)
    
    def init_ui(self):
        """初始化界面布局"""
        # 创建主水平分割器：左侧工具栏 | 中间视图 | 右侧面板
        main_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        
        # 创建左侧工具栏（垂直布局）
        self.left_toolbar = QtWidgets.QWidget()
        self.left_toolbar.setMaximumWidth(220)
        self.left_toolbar.setMinimumWidth(180)
        self.left_toolbar.setStyleSheet("""
            QWidget {
                background-color: #eceff1;
            }
        """)
        toolbar_layout = QtWidgets.QVBoxLayout(self.left_toolbar)
        toolbar_layout.setContentsMargins(8, 8, 8, 8)
        toolbar_layout.setSpacing(10)
        
        # 创建窗宽窗位分组框
        ww_wl_group = QtWidgets.QGroupBox("窗宽窗位")
        ww_wl_group.setStyleSheet("QGroupBox { font-weight: bold; padding-top: 10px; }")
        ww_wl_group_layout = QtWidgets.QVBoxLayout(ww_wl_group)
        ww_wl_group_layout.setSpacing(8)
        
        # 窗宽控制
        ww_label = QtWidgets.QLabel("窗宽:")
        ww_label.setStyleSheet("font-weight: normal;")
        ww_wl_group_layout.addWidget(ww_label)
        
        self.ww_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.ww_slider.setMinimum(1)
        self.ww_slider.setMaximum(65535)
        self.ww_slider.setValue(65535)
        self.ww_slider.valueChanged.connect(self.on_window_level_changed)
        ww_wl_group_layout.addWidget(self.ww_slider)
        
        self.ww_value = QtWidgets.QLabel("65535")
        self.ww_value.setAlignment(QtCore.Qt.AlignCenter)
        self.ww_value.setStyleSheet("QLabel { font-weight: normal; background-color: #e8f4f8; padding: 5px; border: 1px solid #b0d4e3; border-radius: 3px; }")
        ww_wl_group_layout.addWidget(self.ww_value)
        
        ww_wl_group_layout.addSpacing(5)
        
        # 窗位控制
        wl_label = QtWidgets.QLabel("窗位:")
        wl_label.setStyleSheet("font-weight: normal;")
        ww_wl_group_layout.addWidget(wl_label)
        
        self.wl_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.wl_slider.setMinimum(0)
        self.wl_slider.setMaximum(65535)
        self.wl_slider.setValue(32767)
        self.wl_slider.valueChanged.connect(self.on_window_level_changed)
        ww_wl_group_layout.addWidget(self.wl_slider)
        
        self.wl_value = QtWidgets.QLabel("32767")
        self.wl_value.setAlignment(QtCore.Qt.AlignCenter)
        self.wl_value.setStyleSheet("QLabel { font-weight: normal; background-color: #e8f4f8; padding: 5px; border: 1px solid #b0d4e3; border-radius: 3px; }")
        ww_wl_group_layout.addWidget(self.wl_value)
        
        ww_wl_group_layout.addSpacing(5)
        
        # 重置按钮
        reset_btn = QtWidgets.QPushButton("重置")
        reset_btn.setStyleSheet("QPushButton { font-weight: normal; padding: 5px; }")
        reset_btn.clicked.connect(self.reset_window_level)
        ww_wl_group_layout.addWidget(reset_btn)
        
        # 将分组框添加到工具栏
        toolbar_layout.addWidget(ww_wl_group)
        toolbar_layout.addStretch()
        
        # 将左侧工具栏添加到主分割器
        main_splitter.addWidget(self.left_toolbar)
        
        # 保存引用（兼容旧代码）
        self.ww_wl_panel = self.left_toolbar
        
        # 创建中间视图区域
        self.grid_widget = QtWidgets.QWidget()
        self.grid_widget.setStyleSheet("background-color: #ffffff;")
        self.grid_layout = QtWidgets.QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(2)
        self.grid_layout.setContentsMargins(2, 2, 2, 2)
        
        # 将中间视图区域添加到主分割器
        main_splitter.addWidget(self.grid_widget)
        
        # 创建右侧面板（垂直分割成上下两部分）
        self.right_panel = QtWidgets.QWidget()
        self.right_panel.setMaximumWidth(280)
        self.right_panel.setMinimumWidth(200)
        self.right_panel.setStyleSheet("background-color: #eceff1;")  # 浅灰色背景
        right_panel_layout = QtWidgets.QVBoxLayout(self.right_panel)
        right_panel_layout.setContentsMargins(5, 5, 5, 5)
        right_panel_layout.setSpacing(10)  # 增加两个面板之间的间距
        
        # 热磁图层面板（上半部分）
        heatmap_panel = QtWidgets.QWidget()
        heatmap_panel.setStyleSheet("""
            QWidget {
                background-color: #b0bec5;
                border: 2px solid #78909c;
                border-radius: 6px;
            }
        """)
        heatmap_layout = QtWidgets.QVBoxLayout(heatmap_panel)
        heatmap_layout.setContentsMargins(10, 10, 10, 10)
        heatmap_label = QtWidgets.QLabel("热磁图层")
        heatmap_label.setStyleSheet("""
            QLabel {
                color: #37474f; 
                font-size: 12pt; 
                font-weight: bold;
                background-color: transparent;
                border: none;
            }
        """)
        heatmap_label.setAlignment(QtCore.Qt.AlignCenter)
        heatmap_layout.addWidget(heatmap_label)
        heatmap_layout.addStretch()
        
        # 灰度直方图面板（下半部分）
        histogram_panel = QtWidgets.QWidget()
        histogram_panel.setStyleSheet("""
            QWidget {
                background-color: #b0bec5;
                border: 2px solid #78909c;
                border-radius: 6px;
            }
        """)
        histogram_layout = QtWidgets.QVBoxLayout(histogram_panel)
        histogram_layout.setContentsMargins(10, 10, 10, 10)
        histogram_label = QtWidgets.QLabel("灰度直方图")
        histogram_label.setStyleSheet("""
            QLabel {
                color: #37474f; 
                font-size: 12pt; 
                font-weight: bold;
                background-color: transparent;
                border: none;
            }
        """)
        histogram_label.setAlignment(QtCore.Qt.AlignCenter)
        histogram_layout.addWidget(histogram_label)
        histogram_layout.addStretch()
        
        # 将两个面板添加到右侧布局（上下排列，各占50%）
        right_panel_layout.addWidget(heatmap_panel, 1)
        right_panel_layout.addWidget(histogram_panel, 1)
        
        # 将右侧面板添加到主分割器
        main_splitter.addWidget(self.right_panel)
        
        # 设置分割器的初始尺寸比例（左侧固定，中间自适应，右侧固定）
        main_splitter.setStretchFactor(0, 0)  # 左侧工具栏
        main_splitter.setStretchFactor(1, 1)  # 中间视图区域
        main_splitter.setStretchFactor(2, 0)  # 右侧面板
        
        # 使用QMainWindow的setCentralWidget方法设置中心部件
        self.setCentralWidget(main_splitter)
        
        # 初始时显示空白占位符
        self.axial_viewer = None
        self.sag_viewer = None
        self.cor_viewer = None
        self.volume_viewer = None
        
        # 创建初始占位符
        self.create_placeholder_views()
        
        # 数据相关变量
        self.raw_array = None  # 原始数据（uint16）
        self.window_width = 65535
        self.window_level = 32767
    
    def create_placeholder_views(self):
        """创建占位符视图"""
        placeholder_style = """
            QLabel {
                background-color: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 8px;
                color: #6c757d;
                font-size: 14pt;
                font-weight: 500;
            }
        """
        
        # 左上：Axial
        axial_placeholder = QtWidgets.QLabel("Axial\n横断面")
        axial_placeholder.setAlignment(QtCore.Qt.AlignCenter)
        axial_placeholder.setStyleSheet(placeholder_style)
        self.grid_layout.addWidget(axial_placeholder, 0, 0)
        
        # 右上：Sagittal
        sagittal_placeholder = QtWidgets.QLabel("Sagittal\n矢状面")
        sagittal_placeholder.setAlignment(QtCore.Qt.AlignCenter)
        sagittal_placeholder.setStyleSheet(placeholder_style)
        self.grid_layout.addWidget(sagittal_placeholder, 0, 1)
        
        # 左下：Coronal
        coronal_placeholder = QtWidgets.QLabel("Coronal\n冠状面")
        coronal_placeholder.setAlignment(QtCore.Qt.AlignCenter)
        coronal_placeholder.setStyleSheet(placeholder_style)
        self.grid_layout.addWidget(coronal_placeholder, 1, 0)
        
        # 右下：3D View
        view3d_placeholder = QtWidgets.QLabel("3D View\n三维视图")
        view3d_placeholder.setAlignment(QtCore.Qt.AlignCenter)
        view3d_placeholder.setStyleSheet(placeholder_style)
        self.grid_layout.addWidget(view3d_placeholder, 1, 1)

