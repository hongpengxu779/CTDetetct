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
from ..viewers import SliceViewer, VolumeViewer

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
        
        helical_ct_action = QtWidgets.QAction("CT螺旋重建", self)
        helical_ct_action.triggered.connect(self.run_helical_ct_reconstruction)
        ct_menu.addAction(helical_ct_action)
        
        circle_ct_action = QtWidgets.QAction("CT圆轨迹", self)
        circle_ct_action.triggered.connect(self.run_circle_ct_reconstruction)
        ct_menu.addAction(circle_ct_action)
        
        # 传统分割检测菜单
        traditional_seg_menu = self.menu_bar.addMenu("传统分割检测")
        region_growing_action = QtWidgets.QAction("区域生长", self)
        region_growing_action.triggered.connect(self.run_region_growing)
        traditional_seg_menu.addAction(region_growing_action)
        
        otsu_action = QtWidgets.QAction("OTSU阈值分割", self)
        otsu_action.triggered.connect(self.run_otsu_segmentation)
        traditional_seg_menu.addAction(otsu_action)
        
        threshold_action = QtWidgets.QAction("阈值分割", self)
        threshold_action.triggered.connect(self.run_threshold_segmentation)
        traditional_seg_menu.addAction(threshold_action)
        
        # 人工智能分割菜单
        ai_menu = self.menu_bar.addMenu("人工智能分割")
        unet_action = QtWidgets.QAction("基线方法", self)
        unet_action.triggered.connect(self.run_unet_segmentation)
        ai_menu.addAction(unet_action)
        
        # 配准菜单（占位）
        config_menu = self.menu_bar.addMenu("配准")
        
        # 测量菜单
        measure_menu = self.menu_bar.addMenu("人工标记测量")
        distance_action = QtWidgets.QAction("线段距离", self)
        distance_action.triggered.connect(self.measure_distance)
        measure_menu.addAction(distance_action)
        
        angle_action = QtWidgets.QAction("三点测角度", self)
        angle_action.triggered.connect(self.measure_angle)
        measure_menu.addAction(angle_action)

        # 表面积测定
        surface_area_action = QtWidgets.QAction("表面积测定", self)
        surface_area_action.triggered.connect(self.run_surface_area_measurement)
        measure_menu.addAction(surface_area_action)

        # 投影菜单（MIP / MinIP）
        proj_menu = self.menu_bar.addMenu("投影")

        mip_menu = proj_menu.addMenu("最大密度投影 (MIP)")
        mip_z = QtWidgets.QAction("沿 Z 轴 (Axial)", self)
        mip_z.triggered.connect(lambda: self.create_mip_projection(axis=0, use_roi=True))
        mip_menu.addAction(mip_z)
        mip_y = QtWidgets.QAction("沿 Y 轴 (Coronal)", self)
        mip_y.triggered.connect(lambda: self.create_mip_projection(axis=1, use_roi=True))
        mip_menu.addAction(mip_y)
        mip_x = QtWidgets.QAction("沿 X 轴 (Sagittal)", self)
        mip_x.triggered.connect(lambda: self.create_mip_projection(axis=2, use_roi=True))
        mip_menu.addAction(mip_x)

        minip_menu = proj_menu.addMenu("最小密度投影 (MinIP)")
        minip_z = QtWidgets.QAction("沿 Z 轴 (Axial)", self)
        minip_z.triggered.connect(lambda: self.create_minip_projection(axis=0, use_roi=True))
        minip_menu.addAction(minip_z)
        minip_y = QtWidgets.QAction("沿 Y 轴 (Coronal)", self)
        minip_y.triggered.connect(lambda: self.create_minip_projection(axis=1, use_roi=True))
        minip_menu.addAction(minip_y)
        minip_x = QtWidgets.QAction("沿 X 轴 (Sagittal)", self)
        minip_x.triggered.connect(lambda: self.create_minip_projection(axis=2, use_roi=True))
        minip_menu.addAction(minip_x)
        
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
        roi_group = QtWidgets.QGroupBox("3D 感兴趣区域")
        roi_group.setStyleSheet("QGroupBox { font-weight: bold; padding-top: 10px; }")
        roi_group_layout = QtWidgets.QVBoxLayout(roi_group)
        roi_group_layout.setSpacing(8)
        
        # 说明文本
        # roi_info_label = QtWidgets.QLabel("在Axial视图中绘制ROI，\n用下方滑动条控制Z范围")
        # roi_info_label.setStyleSheet("QLabel { font-weight: normal; font-size: 10pt; color: #666; }")
        # roi_group_layout.addWidget(roi_info_label)
        
        # 选取ROI按钮
        roi_select_btn = QtWidgets.QPushButton("选取感兴趣区域")
        roi_select_btn.setStyleSheet("QPushButton { font-weight: normal; padding: 8px; }")
        roi_select_btn.clicked.connect(self.roi_selection_start)
        roi_group_layout.addWidget(roi_select_btn)
        
        # 清除ROI按钮
        roi_clear_btn = QtWidgets.QPushButton("清除感兴趣区域")
        roi_clear_btn.setStyleSheet("QPushButton { font-weight: normal; padding: 8px; }")
        roi_clear_btn.clicked.connect(self.roi_selection_clear)
        roi_group_layout.addWidget(roi_clear_btn)
        
        # 动态深度范围控制（根据选取的视图动态改变含义）
        # roi_group_layout.addSpacing(5)
        # depth_range_label = QtWidgets.QLabel("深度范围:")
        # depth_range_label.setStyleSheet("QLabel { font-weight: bold; font-size: 10pt; color: #0066cc; }")
        # roi_group_layout.addWidget(depth_range_label)
        
        # 深度标签（会动态改变，显示当前是Z/X/Y）
        # self.roi_depth_label = QtWidgets.QLabel("（等待选取ROI）")
        # self.roi_depth_label.setStyleSheet("QLabel { font-weight: normal; font-style: italic; color: #666666; }")
        # roi_group_layout.addWidget(self.roi_depth_label)
        
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
        
        # 数据列表面板（上半部分） - 浅色风格
        data_list_panel = QtWidgets.QWidget()
        data_list_panel.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border: 1px solid #d0d0d0;
                border-radius: 2px;
            }
        """)
        data_list_layout = QtWidgets.QVBoxLayout(data_list_panel)
        data_list_layout.setContentsMargins(4, 4, 4, 4)
        data_list_layout.setSpacing(4)
        
        # 标题栏
        data_list_label = QtWidgets.QLabel("已导入数据列表")
        data_list_label.setStyleSheet("""
            QLabel {
                color: #424242; 
                font-size: 10pt; 
                font-weight: bold;
                background-color: transparent;
                border: none;
                padding: 4px;
            }
        """)
        data_list_label.setAlignment(QtCore.Qt.AlignCenter)
        data_list_layout.addWidget(data_list_label)
        
        # 创建列表控件
        self.data_list_widget = QtWidgets.QListWidget()
        self.data_list_widget.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 2px;
                padding: 2px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #e0e0e0;
            }
            QListWidget::item:hover {
                background-color: #e3f2fd;
            }
            QListWidget::item:selected {
                background-color: #bbdefb;
            }
        """)
        data_list_layout.addWidget(self.data_list_widget)
        
        # 添加提示标签
        # data_hint_label = QtWidgets.QLabel("✓ 勾选的数据将显示在视图中")
        # data_hint_label.setStyleSheet("""
        #     QLabel {
        #         color: #666666;
        #         font-size: 8pt;
        #         background-color: transparent;
        #         border: none;
        #         padding: 2px;
        #     }
        # """)
        # data_hint_label.setAlignment(QtCore.Qt.AlignCenter)
        # data_list_layout.addWidget(data_hint_label)
        
        # 添加按钮区域
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(4)
        
        # 删除选中数据按钮
        self.remove_data_btn = QtWidgets.QPushButton("删除")
        self.remove_data_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffebee;
                color: #c62828;
                border: 1px solid #ef9a9a;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #ffcdd2;
            }
            QPushButton:pressed {
                background-color: #ef9a9a;
            }
        """)
        self.remove_data_btn.clicked.connect(self.remove_selected_data)
        button_layout.addWidget(self.remove_data_btn)
        
        # 清空所有数据按钮
        self.clear_all_data_btn = QtWidgets.QPushButton("清空")
        self.clear_all_data_btn.setStyleSheet("""
            QPushButton {
                background-color: #fff3e0;
                color: #e65100;
                border: 1px solid #ffcc80;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #ffe0b2;
            }
            QPushButton:pressed {
                background-color: #ffcc80;
            }
        """)
        self.clear_all_data_btn.clicked.connect(self.clear_all_data)
        button_layout.addWidget(self.clear_all_data_btn)
        
        data_list_layout.addLayout(button_layout)
        
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
        
        # 隐藏所有坐标轴和刻度
        self.histogram_ax.set_xticks([])
        self.histogram_ax.set_yticks([])
        self.histogram_ax.spines['bottom'].set_visible(False)
        self.histogram_ax.spines['left'].set_visible(False)
        self.histogram_ax.spines['top'].set_visible(False)
        self.histogram_ax.spines['right'].set_visible(False)
        
        # 初始化可拖动的垂直线
        self.histogram_left_line = None
        self.histogram_right_line = None
        self.histogram_dragging_line = None
        self.histogram_data_range = (0, 65535)  # 数据范围
        self.histogram_temp_label = None  # 临时标签引用
        
        # 连接鼠标事件
        self.histogram_canvas.mpl_connect('button_press_event', self.on_histogram_mouse_press)
        self.histogram_canvas.mpl_connect('button_release_event', self.on_histogram_mouse_release)
        self.histogram_canvas.mpl_connect('motion_notify_event', self.on_histogram_mouse_move)
        
        self.histogram_canvas.draw()
        
        histogram_layout.addWidget(self.histogram_canvas, 1)  # 添加stretch factor让画布填充
        
        # 将两个面板添加到右侧布局（上下排列，各占50%）
        right_panel_layout.addWidget(data_list_panel, 1)
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
        
        # 创建状态栏
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #f0f0f0;
                border-top: 1px solid #d0d0d0;
                padding: 4px;
            }
            QStatusBar::item {
                border: none;
            }
        """)
        
        # 创建状态栏标签
        self.status_label = QtWidgets.QLabel("准备就绪")
        self.status_label.setStyleSheet("color: #424242; padding: 0 10px;")
        self.status_bar.addWidget(self.status_label, 1)  # stretch factor = 1
        
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
        更新灰度直方图显示 - 带可拖动线段
        
        参数
        ----
        data_array : np.ndarray
            要显示直方图的数组数据
        """
        if not hasattr(self, 'histogram_ax'):
            return
        
        try:
            # 如果传入 None，清除直方图并返回
            if data_array is None:
                self.histogram_ax.clear()
                self.histogram_ax.set_facecolor('white')
                self.histogram_figure.patch.set_facecolor('#f5f5f5')
                self.histogram_canvas.draw_idle()
                return

            from matplotlib.colors import LinearSegmentedColormap
            
            # 清除之前的直方图
            self.histogram_ax.clear()
            
            # 清除临时标签
            self.histogram_temp_label = None
            
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
            
            # 保存数据范围
            data_min = float(sampled_data.min())
            data_max = float(sampled_data.max())
            self.histogram_data_range = (data_min, data_max)
            
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
            
            # 隐藏所有坐标轴和刻度
            self.histogram_ax.set_xticks([])
            self.histogram_ax.set_yticks([])
            self.histogram_ax.spines['bottom'].set_visible(False)
            self.histogram_ax.spines['left'].set_visible(False)
            self.histogram_ax.spines['top'].set_visible(False)
            self.histogram_ax.spines['right'].set_visible(False)
            
            # 设置坐标轴范围
            self.histogram_ax.set_xlim(data_min, data_max)
            y_max = hist_values.max() * 1.1
            self.histogram_ax.set_ylim(0, y_max)
            
            # 保存直方图数据用于查询
            self.histogram_bin_centers = bin_centers
            self.histogram_values = hist_values
            
            # 添加可拖动的垂直线（默认在25%和75%位置）
            line_left_pos = data_min + (data_max - data_min) * 0.25
            line_right_pos = data_min + (data_max - data_min) * 0.75
            
            # 左线使用蓝色，右线使用红色
            self.histogram_left_line = self.histogram_ax.axvline(
                line_left_pos, color='blue', linewidth=2, linestyle='-', alpha=0.8
            )
            self.histogram_right_line = self.histogram_ax.axvline(
                line_right_pos, color='red', linewidth=2, linestyle='-', alpha=0.8
            )
            
            # 计算统计信息并更新到状态栏
            data_mean = float(sampled_data.mean())
            data_std = float(sampled_data.std())
            
            # 更新状态栏信息
            self._update_status_bar(data_min, data_max, data_mean, data_std)
            
            # 调整布局让图表填充满整个区域
            self.histogram_figure.tight_layout(pad=0.5)
            self.histogram_canvas.draw()
            
            print(f"直方图已更新: 数据范围 [{data_min:.0f}, {data_max:.0f}], 均值 {data_mean:.1f}")
            
        except Exception as e:
            print(f"更新直方图时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _get_histogram_value_at_position(self, x_pos):
        """
        获取指定X位置（灰度值）对应的直方图Y值（像素个数）
        
        参数
        ----
        x_pos : float
            X轴位置（灰度值）
        
        返回
        ----
        float : 对应的像素个数，如果找不到则返回0
        """
        if not hasattr(self, 'histogram_bin_centers') or not hasattr(self, 'histogram_values'):
            return 0
        
        # 找到最接近的bin
        distances = np.abs(self.histogram_bin_centers - x_pos)
        closest_idx = np.argmin(distances)
        
        return float(self.histogram_values[closest_idx])
    
    def on_histogram_mouse_press(self, event):
        """处理直方图的鼠标按下事件"""
        if event.inaxes != self.histogram_ax or event.xdata is None:
            return
        
        # 检查是否点击在某条线附近（容差5个数据单位）
        tolerance = (self.histogram_data_range[1] - self.histogram_data_range[0]) * 0.02
        
        if self.histogram_left_line:
            left_pos = self.histogram_left_line.get_xdata()[0]
            if abs(event.xdata - left_pos) < tolerance:
                self.histogram_dragging_line = 'left'
                return
        
        if self.histogram_right_line:
            right_pos = self.histogram_right_line.get_xdata()[0]
            if abs(event.xdata - right_pos) < tolerance:
                self.histogram_dragging_line = 'right'
                return
    
    def on_histogram_mouse_release(self, event):
        """处理直方图的鼠标释放事件"""
        if self.histogram_dragging_line:
            self.histogram_dragging_line = None
            # 重绘以清除临时标签
            self._redraw_histogram_lines()
    
    def on_histogram_mouse_move(self, event):
        """处理直方图的鼠标移动事件"""
        if event.inaxes != self.histogram_ax or event.xdata is None:
            return
        
        # 如果正在拖动线段
        if self.histogram_dragging_line:
            data_min, data_max = self.histogram_data_range
            new_pos = max(data_min, min(data_max, event.xdata))
            
            # 清除所有临时文本标签
            self._clear_histogram_temp_labels()
            
            if self.histogram_dragging_line == 'left' and self.histogram_left_line:
                # 确保左线不会超过右线
                if self.histogram_right_line:
                    right_pos = self.histogram_right_line.get_xdata()[0]
                    new_pos = min(new_pos, right_pos)
                
                self.histogram_left_line.set_xdata([new_pos, new_pos])
                
                # 获取当前灰度值位置对应的像素个数
                pixel_count = self._get_histogram_value_at_position(new_pos)
                
                # 显示 [像素个数, 像素值] - 蓝色边框，黑色文字
                label_text = f'[{pixel_count:.0f}, {new_pos:.0f}]'
                y_max = self.histogram_ax.get_ylim()[1]
                # 保存临时标签的引用
                self.histogram_temp_label = self.histogram_ax.text(
                    new_pos, y_max * 0.95, label_text,
                    ha='center', va='top',
                    fontsize=8, color='black',
                    bbox=dict(boxstyle='round,pad=0.3',
                             facecolor='white',
                             edgecolor='blue',
                             alpha=0.9))
            
            elif self.histogram_dragging_line == 'right' and self.histogram_right_line:
                # 确保右线不会超过左线
                if self.histogram_left_line:
                    left_pos = self.histogram_left_line.get_xdata()[0]
                    new_pos = max(new_pos, left_pos)
                
                self.histogram_right_line.set_xdata([new_pos, new_pos])
                
                # 获取当前灰度值位置对应的像素个数
                pixel_count = self._get_histogram_value_at_position(new_pos)
                
                # 显示 [像素个数, 像素值] - 红色边框，黑色文字
                label_text = f'[{pixel_count:.0f}, {new_pos:.0f}]'
                y_max = self.histogram_ax.get_ylim()[1]
                # 保存临时标签的引用
                self.histogram_temp_label = self.histogram_ax.text(
                    new_pos, y_max * 0.95, label_text,
                    ha='center', va='top',
                    fontsize=8, color='black',
                    bbox=dict(boxstyle='round,pad=0.3',
                             facecolor='white',
                             edgecolor='red',
                             alpha=0.9))
            
            # 使用blit加速重绘
            self.histogram_canvas.draw_idle()
    
    def _clear_histogram_temp_labels(self):
        """清除直方图上的所有临时标签"""
        # 如果有保存的临时标签引用，直接移除
        if hasattr(self, 'histogram_temp_label') and self.histogram_temp_label:
            try:
                self.histogram_temp_label.remove()
            except:
                pass
            self.histogram_temp_label = None
    
    def _redraw_histogram_lines(self):
        """重新绘制直方图的垂直线（不包括临时标签）"""
        # 清除所有临时标签
        self._clear_histogram_temp_labels()
        self.histogram_canvas.draw()
    
    def _update_status_bar(self, data_min, data_max, data_mean, data_std):
        """
        更新状态栏显示统计信息
        
        参数
        ----
        data_min : float
            数据最小值
        data_max : float
            数据最大值
        data_mean : float
            数据平均值
        data_std : float
            数据标准差
        """
        if hasattr(self, 'status_label'):
            stats_text = f"最小值: {data_min:.0f}  |  最大值: {data_max:.0f}  |  平均值: {data_mean:.1f}  |  标准差: {data_std:.1f}"
            self.status_label.setText(stats_text)
    
    def add_data_to_list(self, data_name, data_item):
        """
        向数据列表中添加新的数据项
        确保每次只有一个复选框被选中
        
        参数
        ----
        data_name : str
            数据的显示名称
        data_item : dict
            数据项，包含image, array, spacing等信息
        """
        # 临时断开信号，避免触发多次切换
        try:
            self.data_list_widget.itemChanged.disconnect(self.on_data_item_changed)
        except:
            pass  # 如果信号未连接，忽略错误
        
        # 取消所有现有项的选中状态（单选机制）
        for i in range(self.data_list_widget.count()):
            existing_item = self.data_list_widget.item(i)
            existing_item.setCheckState(QtCore.Qt.Unchecked)
        
        # 创建新列表项
        list_item = QtWidgets.QListWidgetItem()
        list_item.setFlags(list_item.flags() | QtCore.Qt.ItemIsUserCheckable)
        list_item.setCheckState(QtCore.Qt.Checked)  # 新添加的数据默认勾选
        list_item.setText(data_name)
        
        # 将数据信息存储到item中
        list_item.setData(QtCore.Qt.UserRole, data_item)
        
        # 添加到列表
        self.data_list_widget.addItem(list_item)
        
        # 重新连接信号
        self.data_list_widget.itemChanged.connect(self.on_data_item_changed)
        
        print(f"数据已添加到列表: {data_name} (已自动选中)")
    
    def on_data_item_changed(self, item):
        """
        当数据项的复选框状态改变时调用
        确保每次只能选中一个复选框
        
        参数
        ----
        item : QListWidgetItem
            状态改变的列表项
        """
        data_name = item.text()
        is_checked = item.checkState() == QtCore.Qt.Checked
        
        if is_checked:
            # 临时断开信号，避免递归调用
            self.data_list_widget.itemChanged.disconnect(self.on_data_item_changed)
            
            # 取消其他项的选中状态（单选机制）
            for i in range(self.data_list_widget.count()):
                other_item = self.data_list_widget.item(i)
                if other_item != item and other_item.checkState() == QtCore.Qt.Checked:
                    other_item.setCheckState(QtCore.Qt.Unchecked)
            
            # 重新连接信号
            self.data_list_widget.itemChanged.connect(self.on_data_item_changed)
            
            # 切换到选中的数据
            data_item = item.data(QtCore.Qt.UserRole)
            self.switch_to_data(data_item, data_name)
            print(f"切换到数据: {data_name}")
        
        else:
            # 如果试图取消选中当前项，检查是否还有其他选中项
            has_other_checked = False
            for i in range(self.data_list_widget.count()):
                other_item = self.data_list_widget.item(i)
                if other_item != item and other_item.checkState() == QtCore.Qt.Checked:
                    has_other_checked = True
                    break
            
            # 如果没有其他选中项，强制保持当前项选中（至少要有一个数据被选中）
            if not has_other_checked:
                # 临时断开信号，避免递归调用
                self.data_list_widget.itemChanged.disconnect(self.on_data_item_changed)
                item.setCheckState(QtCore.Qt.Checked)
                self.data_list_widget.itemChanged.connect(self.on_data_item_changed)
                print(f"至少需要选中一个数据项，保持 '{data_name}' 为选中状态")
    
    def switch_to_data(self, data_item, data_name):
        """
        切换显示的数据
        
        参数
        ----
        data_item : dict
            要显示的数据项
        data_name : str
            数据名称
        """
        try:
            # 切换数据时清除旧的种子点（坐标已不再适用于新数据）
            if hasattr(self, 'clear_region_growing_seed_points'):
                self.clear_region_growing_seed_points()
            
            # 清除现有视图
            self.clear_viewers()
            
            # 恢复数据（派生数据可能不包含SimpleITK image）
            self.image = data_item.get('image', None)
            self.array = data_item['array']
            self.depth_z, self.depth_y, self.depth_x = data_item.get('shape', self.array.shape)
            self.spacing = data_item['spacing']
            
            # 如果有RGB数组，也恢复
            if 'rgb_array' in data_item:
                self.rgb_array = data_item['rgb_array']
            else:
                self.rgb_array = None
            
            # 设置raw_array
            self.raw_array = self.array
            
            # 重新创建视图
            data_max = float(self.array.max())
            
            # 创建三个方向的切片视图
            if hasattr(self, 'rgb_array') and self.rgb_array is not None:
                # RGB图像的切片获取
                self.axial_viewer = SliceViewer("Axial (彩色)",
                                          lambda z: self.rgb_array[z, :, :, :],
                                          self.depth_z)
                self.sag_viewer = SliceViewer("Sagittal (彩色)",
                                        lambda x: self.rgb_array[:, :, x, :],
                                        self.depth_x)
                self.cor_viewer = SliceViewer("Coronal (彩色)",
                                        lambda y: self.rgb_array[:, y, :, :],
                                        self.depth_y)
            else:
                # 灰度图像的切片获取
                self.axial_viewer = SliceViewer("Axial",
                                          lambda z: self.apply_window_level_to_slice(self.array[z, :, :]),
                                          self.depth_z,
                                          parent_viewer=self)
                self.sag_viewer = SliceViewer("Sagittal",
                                        lambda x: self.apply_window_level_to_slice(self.array[:, :, x]),
                                        self.depth_x,
                                        parent_viewer=self)
                self.cor_viewer = SliceViewer("Coronal",
                                        lambda y: self.apply_window_level_to_slice(self.array[:, y, :]),
                                        self.depth_y,
                                        parent_viewer=self)
            
            # 更新ROI范围滑动条
            if hasattr(self, 'roi_z_min_slider'):
                self.roi_z_min_slider.setMaximum(self.depth_z - 1)
                self.roi_z_max_slider.setMaximum(self.depth_z - 1)
                self.roi_z_max_slider.setValue(min(50, self.depth_z - 1))
            
            if hasattr(self, 'roi_x_min_slider'):
                self.roi_x_min_slider.setMaximum(self.depth_x - 1)
                self.roi_x_max_slider.setMaximum(self.depth_x - 1)
                self.roi_x_max_slider.setValue(self.depth_x - 1)
            
            if hasattr(self, 'roi_y_min_slider'):
                self.roi_y_min_slider.setMaximum(self.depth_y - 1)
                self.roi_y_max_slider.setMaximum(self.depth_y - 1)
                self.roi_y_max_slider.setValue(self.depth_y - 1)
            
            # 只有在数据不全为0时才创建3D视图
            if data_max > 0:
                # 创建三维体渲染视图
                self.volume_viewer = VolumeViewer(self.array, self.spacing, simplified=True, downsample_factor=1)
                
                # 四宫格布局
                self.grid_layout.addWidget(self.axial_viewer, 0, 0)
                self.grid_layout.addWidget(self.sag_viewer, 0, 1)
                self.grid_layout.addWidget(self.cor_viewer, 1, 0)
                self.grid_layout.addWidget(self.volume_viewer, 1, 1)
            else:
                # 数据全为0，只显示2D视图
                self.grid_layout.addWidget(self.axial_viewer, 0, 0)
                self.grid_layout.addWidget(self.sag_viewer, 0, 1)
                self.grid_layout.addWidget(self.cor_viewer, 1, 0)
                
                # 在右下角显示提示信息
                info_label = QtWidgets.QLabel("3D视图不可用\n(数据全为0)")
                info_label.setAlignment(QtCore.Qt.AlignCenter)
                info_label.setStyleSheet("QLabel { background-color: #f0f0f0; color: #666; font-size: 14pt; }")
                self.grid_layout.addWidget(info_label, 1, 1)
            
            # 更新窗口标题
            self.setWindowTitle(f"CT Viewer - {data_name}")
            
            # 初始化窗宽窗位
            if hasattr(self, 'reset_window_level'):
                self.reset_window_level()
                
                # 如果是小范围的分割结果（如OTSU多阈值），自动调整窗宽窗位以便可见
                data_max = float(self.array.max())
                data_min = float(self.array.min())
                if data_max < 2000 and data_max > 0:  # 判断是否为分割结果
                    print(f"检测到分割结果（范围{data_min}-{data_max}），自动调整窗宽窗位以便可见")
                    self.window_width = int(data_max * 1.2)  # 稍微扩大一点范围
                    self.window_level = int(data_max / 2)
                    self.ww_slider.setValue(self.window_width)
                    self.wl_slider.setValue(self.window_level)
                    self.update_all_views()
            
            # 更新灰度直方图
            if hasattr(self, 'update_histogram'):
                self.update_histogram(self.array)
            
            print(f"成功切换到数据: {data_name}")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "错误", f"切换数据时出错：{str(e)}")
    
    def remove_selected_data(self):
        """删除当前高亮（选中行）的数据项"""
        current_item = self.data_list_widget.currentItem()
        if current_item is None:
            QtWidgets.QMessageBox.information(self, "提示", "请先在数据列表中选中要删除的项。")
            return

        data_name = current_item.text()
        is_checked = current_item.checkState() == QtCore.Qt.Checked  # 是否正在显示

        reply = QtWidgets.QMessageBox.question(
            self, '确认删除',
            f'确定要删除数据 "{data_name}" 吗？',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        row = self.data_list_widget.row(current_item)

        # 临时断开信号
        try:
            self.data_list_widget.itemChanged.disconnect(self.on_data_item_changed)
        except:
            pass

        # 删除项
        self.data_list_widget.takeItem(row)
        print(f"已删除数据: {data_name}")

        remaining = self.data_list_widget.count()

        if remaining > 0 and is_checked:
            # 删除的是当前显示的数据 → 自动切换到第一个
            for i in range(remaining):
                self.data_list_widget.item(i).setCheckState(QtCore.Qt.Unchecked)
            first_item = self.data_list_widget.item(0)
            first_item.setCheckState(QtCore.Qt.Checked)
            self.data_list_widget.itemChanged.connect(self.on_data_item_changed)
            data_item = first_item.data(QtCore.Qt.UserRole)
            self.switch_to_data(data_item, first_item.text())
        elif remaining > 0:
            # 删除的不是当前显示的数据 → 无需切换
            self.data_list_widget.itemChanged.connect(self.on_data_item_changed)
        else:
            # 列表已空 → 清理全部状态
            self.data_list_widget.itemChanged.connect(self.on_data_item_changed)
            self._reset_after_all_data_removed()

    def clear_all_data(self):
        """清空所有数据"""
        if self.data_list_widget.count() == 0:
            return

        reply = QtWidgets.QMessageBox.question(
            self, '确认清空',
            '确定要清空所有数据吗？',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        try:
            self.data_list_widget.itemChanged.disconnect(self.on_data_item_changed)
        except:
            pass

        self.data_list_widget.clear()

        self.data_list_widget.itemChanged.connect(self.on_data_item_changed)
        self._reset_after_all_data_removed()
        print("已清空所有数据")

    def _reset_after_all_data_removed(self):
        """列表清空后，重置所有关联状态"""
        # 清除种子点
        if hasattr(self, 'clear_region_growing_seed_points'):
            self.clear_region_growing_seed_points()

        # 清除视图
        self.clear_viewers()

        # 重置数据变量
        self.image = None
        self.array = None
        self.raw_array = None
        self.rgb_array = None

        # 重置窗口标题
        self.setWindowTitle("工业CT智能软件")

        # 清除灰度直方图
        if hasattr(self, 'update_histogram'):
            try:
                self.update_histogram(None)
            except:
                pass

        # 清除状态栏统计信息
        if hasattr(self, 'status_label'):
            self.status_label.setText("")

        print("所有数据已移除，状态已重置")

