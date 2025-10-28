"""
CT查看器UI组件
包含样式表、菜单、工具栏等UI相关功能
"""

from PyQt5 import QtWidgets, QtCore
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib
import platform

# 设置matplotlib中文字体支持
if platform.system() == 'Windows':
    matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun']
elif platform.system() == 'Darwin':  # macOS
    matplotlib.rcParams['font.sans-serif'] = ['PingFang SC', 'STHeiti', 'Arial Unicode MS']
else:  # Linux
    matplotlib.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题


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
            background-color: #E3F2FD;
            color: #212121;
            border: 1px solid #BBDEFB;
            border-radius: 4px;
            padding: 6px 16px;
            font-weight: 500;
        }
        
        QPushButton:hover {
            background-color: #BBDEFB;
            color: #000000;
        }
        
        QPushButton:pressed {
            background-color: #90CAF9;
            color: #000000;
        }
        
        QPushButton:disabled {
            background-color: #F5F5F5;
            color: #9E9E9E;
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
        
        # 测量菜单
        measure_menu = self.menu_bar.addMenu("测量")
        distance_action = QtWidgets.QAction("距离", self)
        distance_action.triggered.connect(self.measure_distance)
        measure_menu.addAction(distance_action)
        
        angle_action = QtWidgets.QAction("角度", self)
        angle_action.triggered.connect(self.measure_angle)
        measure_menu.addAction(angle_action)
        
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
        
        # 创建ROI分组框
        roi_group = QtWidgets.QGroupBox("ROI工具")
        roi_group.setStyleSheet("QGroupBox { font-weight: bold; padding-top: 10px; }")
        roi_group_layout = QtWidgets.QVBoxLayout(roi_group)
        roi_group_layout.setSpacing(8)
        
        # 说明文本
        roi_info_label = QtWidgets.QLabel("在Axial视图中绘制ROI，\n用下方滑动条控制Z范围")
        roi_info_label.setStyleSheet("QLabel { font-weight: normal; font-size: 10pt; color: #666; }")
        roi_group_layout.addWidget(roi_info_label)
        
        # 选取ROI按钮
        roi_select_btn = QtWidgets.QPushButton("选取ROI")
        roi_select_btn.setStyleSheet("QPushButton { font-weight: normal; padding: 8px; }")
        roi_select_btn.clicked.connect(self.roi_selection_start)
        roi_group_layout.addWidget(roi_select_btn)
        
        # 清除ROI按钮
        roi_clear_btn = QtWidgets.QPushButton("清除ROI")
        roi_clear_btn.setStyleSheet("QPushButton { font-weight: normal; padding: 8px; }")
        roi_clear_btn.clicked.connect(self.roi_selection_clear)
        roi_group_layout.addWidget(roi_clear_btn)
        
        # 动态深度范围控制（根据选取的视图动态改变含义）
        roi_group_layout.addSpacing(5)
        depth_range_label = QtWidgets.QLabel("深度范围:")
        depth_range_label.setStyleSheet("QLabel { font-weight: bold; font-size: 10pt; color: #0066cc; }")
        roi_group_layout.addWidget(depth_range_label)
        
        # 深度标签（会动态改变，显示当前是Z/X/Y）
        self.roi_depth_label = QtWidgets.QLabel("（等待选取ROI）")
        self.roi_depth_label.setStyleSheet("QLabel { font-weight: normal; font-style: italic; color: #666666; }")
        roi_group_layout.addWidget(self.roi_depth_label)
        
        # 深度最小值滑动条
        depth_min_layout = QtWidgets.QHBoxLayout()
        depth_min_text = QtWidgets.QLabel("Min:")
        depth_min_text.setStyleSheet("QLabel { font-weight: normal; }")
        depth_min_layout.addWidget(depth_min_text)
        
        self.roi_depth_min_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.roi_depth_min_slider.setMinimum(0)
        self.roi_depth_min_slider.setMaximum(1000)
        self.roi_depth_min_slider.setValue(0)
        self.roi_depth_min_slider.setToolTip("深度最小值")
        depth_min_layout.addWidget(self.roi_depth_min_slider)
        
        self.roi_depth_min_value = QtWidgets.QLabel("0")
        self.roi_depth_min_value.setAlignment(QtCore.Qt.AlignCenter)
        self.roi_depth_min_value.setStyleSheet("QLabel { font-weight: normal; background-color: #e6f2ff; padding: 2px; border: 1px solid #99ccff; border-radius: 3px; min-width: 40px; }")
        self.roi_depth_min_slider.valueChanged.connect(lambda v: self.roi_depth_min_value.setText(str(v)))
        depth_min_layout.addWidget(self.roi_depth_min_value)
        
        roi_group_layout.addLayout(depth_min_layout)
        
        # 深度最大值滑动条
        depth_max_layout = QtWidgets.QHBoxLayout()
        depth_max_text = QtWidgets.QLabel("Max:")
        depth_max_text.setStyleSheet("QLabel { font-weight: normal; }")
        depth_max_layout.addWidget(depth_max_text)
        
        self.roi_depth_max_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.roi_depth_max_slider.setMinimum(0)
        self.roi_depth_max_slider.setMaximum(1000)
        self.roi_depth_max_slider.setValue(100)
        self.roi_depth_max_slider.setToolTip("深度最大值")
        depth_max_layout.addWidget(self.roi_depth_max_slider)
        
        self.roi_depth_max_value = QtWidgets.QLabel("100")
        self.roi_depth_max_value.setAlignment(QtCore.Qt.AlignCenter)
        self.roi_depth_max_value.setStyleSheet("QLabel { font-weight: normal; background-color: #e6f2ff; padding: 2px; border: 1px solid #99ccff; border-radius: 3px; min-width: 40px; }")
        self.roi_depth_max_slider.valueChanged.connect(lambda v: self.roi_depth_max_value.setText(str(v)))
        depth_max_layout.addWidget(self.roi_depth_max_value)
        
        roi_group_layout.addLayout(depth_max_layout)
        
        # 3D预览按钮
        roi_3d_btn = QtWidgets.QPushButton("3D预览")
        roi_3d_btn.setStyleSheet("QPushButton { font-weight: normal; padding: 8px; }")
        roi_3d_btn.clicked.connect(self.preview_roi_3d)
        roi_group_layout.addWidget(roi_3d_btn)
        
        # 导出/导入按钮
        roi_io_layout = QtWidgets.QHBoxLayout()
        
        roi_export_btn = QtWidgets.QPushButton("导出")
        roi_export_btn.setStyleSheet("QPushButton { font-weight: normal; padding: 6px; }")
        roi_export_btn.clicked.connect(self.on_export_roi)
        roi_io_layout.addWidget(roi_export_btn)
        
        roi_import_btn = QtWidgets.QPushButton("导入")
        roi_import_btn.setStyleSheet("QPushButton { font-weight: normal; padding: 6px; }")
        roi_import_btn.clicked.connect(self.on_import_roi)
        roi_io_layout.addWidget(roi_import_btn)
        
        roi_group_layout.addLayout(roi_io_layout)
        
        # 将ROI分组框添加到工具栏
        toolbar_layout.insertWidget(1, roi_group)
        
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
        self.right_panel.setMaximumWidth(350)
        self.right_panel.setMinimumWidth(280)
        self.right_panel.setStyleSheet("background-color: #eceff1;")  # 浅灰色背景
        right_panel_layout = QtWidgets.QVBoxLayout(self.right_panel)
        right_panel_layout.setContentsMargins(8, 8, 8, 8)
        right_panel_layout.setSpacing(10)  # 增加两个面板之间的间距
        
        # 热磁图层面板（上半部分） - 浅色风格
        heatmap_panel = QtWidgets.QWidget()
        heatmap_panel.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border: 1px solid #d0d0d0;
                border-radius: 2px;
            }
        """)
        heatmap_layout = QtWidgets.QVBoxLayout(heatmap_panel)
        heatmap_layout.setContentsMargins(2, 2, 2, 2)
        heatmap_layout.setSpacing(2)
        
        # 标题栏
        heatmap_label = QtWidgets.QLabel("热力图层叠加")
        heatmap_label.setStyleSheet("""
            QLabel {
                color: #424242; 
                font-size: 10pt; 
                background-color: transparent;
                border: none;
                padding: 4px;
            }
        """)
        heatmap_label.setAlignment(QtCore.Qt.AlignCenter)
        heatmap_layout.addWidget(heatmap_label)
        
        # 提示信息
        heatmap_info = QtWidgets.QLabel("功能开发中")
        heatmap_info.setStyleSheet("""
            QLabel {
                color: #999999;
                font-size: 10pt;
                background-color: transparent;
                border: none;
            }
        """)
        heatmap_info.setAlignment(QtCore.Qt.AlignCenter)
        heatmap_layout.addWidget(heatmap_info)
        
        heatmap_layout.addStretch()
        
        # 灰度直方图面板（下半部分） - 浅色背景风格
        histogram_panel = QtWidgets.QWidget()
        histogram_panel.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border: 1px solid #d0d0d0;
                border-radius: 2px;
            }
        """)
        histogram_layout = QtWidgets.QVBoxLayout(histogram_panel)
        histogram_layout.setContentsMargins(2, 2, 2, 2)
        histogram_layout.setSpacing(2)
        
        # 标题栏 - 简洁风格
        histogram_label = QtWidgets.QLabel("灰度直方图")
        histogram_label.setStyleSheet("""
            QLabel {
                color: #424242; 
                font-size: 10pt; 
                background-color: transparent;
                border: none;
                padding: 4px;
            }
        """)
        histogram_label.setAlignment(QtCore.Qt.AlignCenter)
        histogram_layout.addWidget(histogram_label)
        
        # 创建matplotlib图形用于显示直方图 - 浅色背景
        self.histogram_figure = Figure(facecolor='#f5f5f5')
        self.histogram_canvas = FigureCanvas(self.histogram_figure)
        self.histogram_canvas.setStyleSheet("background-color: #f5f5f5;")
        self.histogram_ax = self.histogram_figure.add_subplot(111)
        
        # 初始化空直方图 - 浅色背景
        self.histogram_ax.set_facecolor('white')
        self.histogram_ax.text(0.5, 0.5, '等待数据导入', 
                              transform=self.histogram_ax.transAxes,
                              ha='center', va='center',
                              fontsize=10, color='#999999')
        self.histogram_ax.tick_params(labelsize=8, colors='#666666')
        
        # 设置坐标轴颜色为浅色主题
        self.histogram_ax.spines['bottom'].set_color('#cccccc')
        self.histogram_ax.spines['left'].set_color('#cccccc')
        self.histogram_ax.spines['top'].set_visible(False)
        self.histogram_ax.spines['right'].set_visible(False)
        
        self.histogram_canvas.draw()
        
        histogram_layout.addWidget(self.histogram_canvas, 1)  # 添加stretch factor让画布填充
        
        # 将两个面板添加到右侧布局（上下排列，各占50%）
        right_panel_layout.addWidget(heatmap_panel, 1)
        right_panel_layout.addWidget(histogram_panel, 1)
        
        # 将右侧面板添加到主分割器
        main_splitter.addWidget(self.right_panel)
        
        # 设置分割器的初始尺寸比例（左侧固定，中间自适应，右侧固定）
        main_splitter.setStretchFactor(0, 0)  # 左侧工具栏 - 不拉伸
        main_splitter.setStretchFactor(1, 3)  # 中间视图区域 - 主要区域，拉伸因子为3
        main_splitter.setStretchFactor(2, 0)  # 右侧面板 - 不拉伸
        
        # 设置初始分割比例
        total_width = 1600  # 假设的总宽度
        main_splitter.setSizes([200, 1050, 350])  # 左侧:中间:右侧 的比例
        
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
    
    def on_export_roi(self):
        """处理ROI导出"""
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出ROI信息", "", "ROI文件 (*.roi.json)"
        )
        if filepath:
            if not filepath.endswith('.roi.json'):
                filepath += '.roi.json'
            self.export_roi_info(filepath)
    
    def on_import_roi(self):
        """处理ROI导入"""
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "导入ROI信息", "", "ROI文件 (*.roi.json)"
        )
        if filepath:
            self.import_roi_info(filepath)
    
    def update_histogram(self, data_array):
        """
        更新灰度直方图显示 - VGStudio风格
        
        参数
        ----
        data_array : np.ndarray
            要显示直方图的数组数据
        """
        if not hasattr(self, 'histogram_ax'):
            return
        
        try:
            from matplotlib.colors import LinearSegmentedColormap
            
            # 清除之前的直方图
            self.histogram_ax.clear()
            
            # 对于大数据集，使用采样以加快计算
            if data_array.size > 1e7:  # 如果数据量大于1000万像素
                # 随机采样10%的数据
                sample_size = int(data_array.size * 0.1)
                flat_data = data_array.flatten()
                sample_indices = np.random.choice(flat_data.size, sample_size, replace=False)
                sampled_data = flat_data[sample_indices]
            else:
                sampled_data = data_array.flatten()
            
            # 计算直方图（使用256个bins）
            hist_values, bin_edges = np.histogram(sampled_data, bins=256)
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            
            # VGStudio风格：使用灰度渐变填充
            # 创建灰度渐变colormap - 从深灰到浅灰
            colors = [(0.15, 0.15, 0.15), (0.5, 0.5, 0.5), (0.85, 0.85, 0.85)]
            n_bins = len(bin_centers)
            cmap = LinearSegmentedColormap.from_list('grayscale', colors, N=n_bins)
            
            # 为每个bin生成对应的颜色
            bar_colors = [cmap(i / n_bins) for i in range(n_bins)]
            
            # 一次性绘制所有柱状图（更高效）
            bar_width = bin_edges[1] - bin_edges[0]
            self.histogram_ax.bar(bin_centers, hist_values, 
                                 width=bar_width * 0.95,  # 稍微缩小避免重叠
                                 color=bar_colors,
                                 edgecolor='none')
            
            # 设置浅色背景
            self.histogram_ax.set_facecolor('white')
            self.histogram_figure.patch.set_facecolor('#f5f5f5')
            
            # 不显示坐标轴标签
            self.histogram_ax.set_xlabel('')
            self.histogram_ax.set_ylabel('')
            self.histogram_ax.tick_params(labelsize=8, colors='#666666')
            
            # 设置坐标轴样式 - 浅色主题
            self.histogram_ax.spines['bottom'].set_color('#cccccc')
            self.histogram_ax.spines['left'].set_color('#cccccc')
            self.histogram_ax.spines['top'].set_visible(False)
            self.histogram_ax.spines['right'].set_visible(False)
            
            # 添加统计信息 - 浅色主题版本
            data_min = float(sampled_data.min())
            data_max = float(sampled_data.max())
            data_mean = float(sampled_data.mean())
            data_std = float(sampled_data.std())
            
            stats_text = f'最小值: {data_min:.0f}\n最大值: {data_max:.0f}\n平均值: {data_mean:.1f}\n标准差: {data_std:.1f}'
            
            self.histogram_ax.text(0.98, 0.97, stats_text, 
                                  transform=self.histogram_ax.transAxes,
                                  verticalalignment='top', 
                                  horizontalalignment='right',
                                  fontsize=7.5,
                                  color='#424242',
                                  bbox=dict(boxstyle='round,pad=0.5', 
                                           facecolor='white', 
                                           edgecolor='#d0d0d0',
                                           alpha=0.9,
                                           linewidth=1))
            
            # 调整布局让图表填充满整个区域
            self.histogram_figure.tight_layout(pad=0.5)
            self.histogram_canvas.draw()
            
            print(f"直方图已更新: 数据范围 [{data_min:.0f}, {data_max:.0f}], 均值 {data_mean:.1f}")
            
        except Exception as e:
            print(f"更新直方图时出错: {str(e)}")
            import traceback
            traceback.print_exc()

