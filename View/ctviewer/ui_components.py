"""
CT查看器UI组件
包含样式表、菜单、工具栏等UI相关功能
"""

from PyQt5 import QtWidgets, QtCore, QtGui
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
            background-color: #2a2a2a;
            font-size: 9pt;
        }
        
        QWidget {
            background-color: #2a2a2a;
            color: #d8d8d8;
            font-size: 9pt;
        }
        
        QMenuBar {
            background-color: #383838;
            border-bottom: 1px solid #1e1e1e;
            padding: 1px 4px;
            min-height: 24px;
            spacing: 3px;
            color: #e6e6e6;
            font-size: 9pt;
        }
        
        QMenuBar::item {
            background-color: transparent;
            padding: 4px 10px;
            border-radius: 4px;
            margin: 0px;
        }
        
        QMenuBar::item:selected {
            background-color: #505050;
        }
        
        QMenuBar::item:pressed {
            background-color: #5d5d5d;
        }
        
        QMenu {
            background-color: #3a3a3a;
            border: 1px solid #4a4a4a;
            border-radius: 4px;
            color: #f0f0f0;
        }
        
        QMenu::item {
            padding: 5px 20px;
        }
        
        QMenu::item:selected {
            background-color: #5d5d5d;
        }

        QToolBar {
            background-color: #343434;
            border-bottom: 1px solid #222;
            spacing: 2px;
            padding: 2px;
            min-height: 26px;
        }

        QToolButton {
            background-color: #474747;
            color: #f2f2f2;
            border: 1px solid #5d5d5d;
            border-radius: 3px;
            padding: 1px 4px;
            min-height: 18px;
            min-width: 20px;
            font-size: 8.5pt;
        }

        QToolButton:hover {
            background-color: #5a5a5a;
        }

        QToolButton:pressed {
            background-color: #676767;
        }

        QTabWidget::pane {
            border: 1px solid #444;
            background: #2d2d2d;
        }

        QTabBar::tab {
            background: #3a3a3a;
            border: 1px solid #505050;
            padding: 4px 8px;
            margin-right: 1px;
            color: #d8d8d8;
        }

        QTabBar::tab:selected {
            background: #505050;
            color: #f3f3f3;
        }

        QToolBox::tab {
            background: #3b3b3b;
            border: 1px solid #4f4f4f;
            padding: 4px 6px;
            color: #e2e2e2;
            font-weight: bold;
        }

        QToolBox::tab:selected {
            background: #505050;
        }

        QScrollArea {
            border: none;
            background: #2f2f2f;
        }
        
        QGroupBox {
            background-color: #323232;
            border: 1px solid #4d4d4d;
            border-radius: 6px;
            margin-top: 7px;
            padding-top: 7px;
            font-weight: bold;
            color: #e8e8e8;
            font-size: 8.8pt;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 2px 6px;
            background-color: #323232;
            border-radius: 3px;
        }
        
        QPushButton {
            background-color: #4b4b4b;
            color: #f1f1f1;
            border: 1px solid #666;
            border-radius: 4px;
            padding: 3px 8px;
            font-weight: 500;
            min-height: 20px;
            font-size: 8.8pt;
        }
        
        QPushButton:hover {
            background-color: #5b5b5b;
            color: #ffffff;
        }
        
        QPushButton:pressed {
            background-color: #676767;
            color: #ffffff;
        }
        
        QPushButton:disabled {
            background-color: #3a3a3a;
            color: #8e8e8e;
        }
        
        QSlider::groove:horizontal {
            border: 1px solid #555;
            height: 5px;
            background: #2d2d2d;
            border-radius: 3px;
        }
        
        QSlider::handle:horizontal {
            background: #909090;
            border: 1px solid #b0b0b0;
            width: 16px;
            height: 14px;
            margin: -5px 0;
            border-radius: 8px;
        }
        
        QSlider::handle:horizontal:hover {
            background: #b0b0b0;
        }
        
        QLabel {
            color: #d8d8d8;
            font-size: 8.8pt;
        }
        
        QLineEdit {
            background-color: #2c2c2c;
            border: 1px solid #666;
            border-radius: 4px;
            padding: 6px;
            color: #e8e8e8;
        }
        
        QLineEdit:focus {
            border: 2px solid #9a9a9a;
        }
        
        QSpinBox, QDoubleSpinBox {
            background-color: #2c2c2c;
            border: 1px solid #666;
            border-radius: 4px;
            padding: 2px;
            color: #f0f0f0;
            min-height: 20px;
        }
        
        QSpinBox:focus, QDoubleSpinBox:focus {
            border: 2px solid #9a9a9a;
        }

        QListWidget {
            background-color: #2a2a2a;
            border: 1px solid #4c4c4c;
        }

        QListWidget::item:selected {
            background-color: #5d5d5d;
        }

        QStatusBar {
            background-color: #333;
            color: #d6d6d6;
            border-top: 1px solid #1d1d1d;
            font-size: 8.8pt;
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

    def create_top_toolbars(self):
        """创建顶部紧凑工具条（单行优先，避免挤压主视图区）"""
        style = self.style()

        # Manipulate 工具组（Track / Pan / Cine / Zoom + Fit / Reset）
        manipulate_toolbar = QtWidgets.QToolBar("Manipulate", self)
        manipulate_toolbar.setMovable(False)
        manipulate_toolbar.setIconSize(QtCore.QSize(16, 16))
        manipulate_toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.addToolBar(QtCore.Qt.TopToolBarArea, manipulate_toolbar)

        self.manipulate_action_group = QtWidgets.QActionGroup(self)
        self.manipulate_action_group.setExclusive(True)

        self.track_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_DialogYesButton), "Track", self)
        self.track_action.setToolTip("Track（十字线联动）")
        self.track_action.setCheckable(True)
        self.track_action.triggered.connect(self.set_track_mode)
        self.manipulate_action_group.addAction(self.track_action)
        manipulate_toolbar.addAction(self.track_action)

        self.pan_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_ArrowLeft), "Pan", self)
        self.pan_action.setToolTip("Pan（平移）")
        self.pan_action.setCheckable(True)
        self.pan_action.triggered.connect(self.set_pan_mode)
        self.manipulate_action_group.addAction(self.pan_action)
        manipulate_toolbar.addAction(self.pan_action)

        self.cine_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_MediaPlay), "Cine", self)
        self.cine_action.setToolTip("Cine（自动滚片）")
        self.cine_action.setCheckable(True)
        self.cine_action.toggled.connect(self.set_cine_mode)
        self.manipulate_action_group.addAction(self.cine_action)
        manipulate_toolbar.addAction(self.cine_action)

        self.zoom_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_ArrowUp), "Zoom", self)
        self.zoom_action.setToolTip("Zoom（缩放）")
        self.zoom_action.setCheckable(True)
        self.zoom_action.triggered.connect(self.set_zoom_mode)
        self.manipulate_action_group.addAction(self.zoom_action)
        manipulate_toolbar.addAction(self.zoom_action)

        manipulate_toolbar.addSeparator()

        self.fit_view_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_TitleBarMaxButton), "Fit", self)
        self.fit_view_action.setToolTip("Fit to View")
        self.fit_view_action.triggered.connect(self.fit_all_views)
        manipulate_toolbar.addAction(self.fit_view_action)

        self.reset_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_BrowserReload), "Reset", self)
        self.reset_action.setToolTip("Reset")
        self.reset_action.triggered.connect(self.reset_view_transform)
        manipulate_toolbar.addAction(self.reset_action)

        self.track_action.setChecked(True)

        self.cine_timer = QtCore.QTimer(self)
        self.cine_timer.setInterval(90)
        self.cine_timer.timeout.connect(self._cine_tick)

        self.stop_cine_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Esc"), self)
        self.stop_cine_shortcut.activated.connect(self.stop_cine_via_shortcut)

        # 第一组：基础文件操作
        primary_toolbar = QtWidgets.QToolBar("主工具栏", self)
        primary_toolbar.setMovable(False)
        primary_toolbar.setIconSize(QtCore.QSize(16, 16))
        primary_toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.addToolBar(QtCore.Qt.TopToolBarArea, primary_toolbar)

        open_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_DialogOpenButton), "打开", self)
        open_action.setToolTip("打开")
        open_action.triggered.connect(self.import_file)
        primary_toolbar.addAction(open_action)

        save_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_DialogSaveButton), "保存", self)
        save_action.setToolTip("保存")
        save_action.triggered.connect(self.save_current_session)
        primary_toolbar.addAction(save_action)

        import_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon), "导入", self)
        import_action.setToolTip("导入")
        import_action.triggered.connect(self.import_file)
        primary_toolbar.addAction(import_action)

        export_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_DialogSaveButton), "导出", self)
        export_action.setToolTip("导出")
        export_action.triggered.connect(self.export_current_layer)
        primary_toolbar.addAction(export_action)

        reset_view_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_BrowserReload), "重置窗宽窗位", self)
        reset_view_action.setToolTip("重置窗宽窗位")
        reset_view_action.triggered.connect(self.reset_window_level)
        primary_toolbar.addAction(reset_view_action)

        primary_toolbar.addSeparator()

        roi_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_DirIcon), "ROI", self)
        roi_action.setToolTip("ROI")
        roi_action.triggered.connect(self.roi_selection_start)
        primary_toolbar.addAction(roi_action)

        roi_clear_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_TrashIcon), "清除ROI", self)
        roi_clear_action.setToolTip("清除ROI")
        roi_clear_action.triggered.connect(self.roi_selection_clear)
        primary_toolbar.addAction(roi_clear_action)

        primary_toolbar.addSeparator()

        segment_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_ArrowForward), "U-Net分割", self)
        segment_action.setToolTip("U-Net分割")
        segment_action.triggered.connect(self.run_unet_segmentation)
        primary_toolbar.addAction(segment_action)

        # 视图/测量快捷（与第一组同排）
        secondary_toolbar = QtWidgets.QToolBar("显示工具栏", self)
        secondary_toolbar.setMovable(False)
        secondary_toolbar.setIconSize(QtCore.QSize(16, 16))
        secondary_toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.addToolBar(QtCore.Qt.TopToolBarArea, secondary_toolbar)

        pan_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_ArrowLeft), "平移", self)
        pan_action.setToolTip("平移")
        pan_action.triggered.connect(self.set_pan_mode)
        secondary_toolbar.addAction(pan_action)

        zoom_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_ArrowUp), "缩放", self)
        zoom_action.setToolTip("缩放")
        zoom_action.triggered.connect(self.set_zoom_mode)
        secondary_toolbar.addAction(zoom_action)

        rotate_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_BrowserReload), "旋转", self)
        rotate_action.setToolTip("旋转")
        rotate_action.triggered.connect(self.set_rotate_mode)
        secondary_toolbar.addAction(rotate_action)

        secondary_toolbar.addSeparator()

        distance_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_LineEditClearButton), "距离", self)
        distance_action.setToolTip("距离测量")
        distance_action.triggered.connect(self.measure_distance)
        secondary_toolbar.addAction(distance_action)

        angle_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView), "角度", self)
        angle_action.setToolTip("角度测量")
        angle_action.triggered.connect(self.measure_angle)
        secondary_toolbar.addAction(angle_action)

        secondary_toolbar.addSeparator()

        mip_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_ComputerIcon), "MIP(Z)", self)
        mip_action.setToolTip("MIP")
        mip_action.triggered.connect(lambda: self.create_mip_projection(axis=0, use_roi=True))
        secondary_toolbar.addAction(mip_action)

        minip_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_TitleBarShadeButton), "MinIP(Z)", self)
        minip_action.setToolTip("MinIP")
        minip_action.triggered.connect(lambda: self.create_minip_projection(axis=0, use_roi=True))
        secondary_toolbar.addAction(minip_action)

        # 开关与步进（与前两组同排）
        tertiary_toolbar = QtWidgets.QToolBar("交互工具栏", self)
        tertiary_toolbar.setMovable(False)
        tertiary_toolbar.setIconSize(QtCore.QSize(16, 16))
        tertiary_toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.addToolBar(QtCore.Qt.TopToolBarArea, tertiary_toolbar)

        link_views_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_CommandLink), "联动", self)
        link_views_action.setToolTip("视图联动")
        link_views_action.setCheckable(True)
        link_views_action.setChecked(True)
        tertiary_toolbar.addAction(link_views_action)

        show_cross_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_DialogYesButton), "十字线", self)
        show_cross_action.setToolTip("十字线")
        show_cross_action.setCheckable(True)
        show_cross_action.setChecked(True)
        show_cross_action.triggered.connect(lambda checked: self.chk_show_crosshair.setChecked(checked) if hasattr(self, 'chk_show_crosshair') else None)
        tertiary_toolbar.addAction(show_cross_action)

        tertiary_toolbar.addSeparator()
        tertiary_toolbar.addWidget(QtWidgets.QLabel("步进"))
        self.slice_step_spin = QtWidgets.QSpinBox()
        self.slice_step_spin.setRange(1, 50)
        self.slice_step_spin.setValue(1)
        self.slice_step_spin.setFixedWidth(52)
        tertiary_toolbar.addWidget(self.slice_step_spin)
    
    def create_menu(self):
        """创建菜单栏"""
        # 创建菜单栏
        self.menu_bar = QtWidgets.QMenuBar()
        self.menu_bar.setNativeMenuBar(False)  # 禁用原生菜单栏，确保菜单栏始终显示
        
        # 文件菜单
        file_menu = self.menu_bar.addMenu("文件")
        import_action = QtWidgets.QAction("打开影像...", self)
        import_action.triggered.connect(self.import_file)
        file_menu.addAction(import_action)

        save_session_action = QtWidgets.QAction("保存会话...", self)
        save_session_action.triggered.connect(self.save_current_session)
        file_menu.addAction(save_session_action)

        file_menu.addSeparator()

        import_dicom_action = QtWidgets.QAction("导入 DICOM...", self)
        import_dicom_action.triggered.connect(self.import_dicom_series)
        file_menu.addAction(import_dicom_action)

        export_dicom_action = QtWidgets.QAction("导出 DICOM...", self)
        export_dicom_action.triggered.connect(self.export_dicom_series)
        file_menu.addAction(export_dicom_action)

        # 新增：导出切片为 TIFF（无符号16位）
        export_slices_action = QtWidgets.QAction("导出切片为TIFF...", self)
        export_slices_action.triggered.connect(lambda: getattr(self, 'export_slices_dialog', lambda: None)())
        file_menu.addAction(export_slices_action)

        # 新增：从切片重建体数据
        import_slices_action = QtWidgets.QAction("从切片重建...", self)
        import_slices_action.triggered.connect(lambda: getattr(self, 'import_slices_dialog', lambda: None)())
        file_menu.addAction(import_slices_action)

        file_menu.addSeparator()
        new_session_action = QtWidgets.QAction("新建会话", self)
        new_session_action.triggered.connect(self.start_new_session)
        file_menu.addAction(new_session_action)

        # 工具菜单
        tools_menu = self.menu_bar.addMenu("工具")

        # 滤波子菜单
        filter_menu = tools_menu.addMenu("滤波")
        
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
        
        # 图像增强菜单
        enhance_menu = tools_menu.addMenu("图像增强")
        
        hist_eq_action = QtWidgets.QAction("直方图均衡化", self)
        hist_eq_action.triggered.connect(self.apply_histogram_equalization)
        enhance_menu.addAction(hist_eq_action)
        
        clahe_action = QtWidgets.QAction("限制对比度直方图均衡化 (CLAHE)", self)
        clahe_action.triggered.connect(self.apply_clahe)
        enhance_menu.addAction(clahe_action)
        
        retinex_action = QtWidgets.QAction("Retinex SSR", self)
        retinex_action.triggered.connect(self.apply_retinex_ssr)
        enhance_menu.addAction(retinex_action)
        
        dehaze_action = QtWidgets.QAction("去雾", self)
        dehaze_action.triggered.connect(self.apply_dehaze)
        enhance_menu.addAction(dehaze_action)
        
        fuzzy_enhance_action = QtWidgets.QAction("补偿模糊增强", self)
        fuzzy_enhance_action.triggered.connect(self.apply_fuzzy_enhancement)
        enhance_menu.addAction(fuzzy_enhance_action)
        
        # CT重建菜单
        ct_menu = tools_menu.addMenu("CT重建")
        
        helical_ct_action = QtWidgets.QAction("CT螺旋重建", self)
        helical_ct_action.triggered.connect(self.run_helical_ct_reconstruction)
        ct_menu.addAction(helical_ct_action)
        
        circle_ct_action = QtWidgets.QAction("CT圆轨迹", self)
        circle_ct_action.triggered.connect(self.run_circle_ct_reconstruction)
        ct_menu.addAction(circle_ct_action)
        
        # 传统分割检测菜单
        traditional_seg_menu = tools_menu.addMenu("传统分割检测")
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
        ai_menu = tools_menu.addMenu("人工智能分割")
        unet_action = QtWidgets.QAction("基线方法", self)
        unet_action.triggered.connect(self.run_unet_segmentation)
        ai_menu.addAction(unet_action)
        
        # 配准菜单（占位）
        config_menu = tools_menu.addMenu("配准")
        
        # 测量菜单
        measure_menu = tools_menu.addMenu("人工标记测量")
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
        proj_menu = tools_menu.addMenu("投影")

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

        # 开发者工具
        dev_menu = self.menu_bar.addMenu("开发者工具")
        python_console_action = QtWidgets.QAction("Python脚本控制台", self)
        python_console_action.triggered.connect(self.open_python_console)
        dev_menu.addAction(python_console_action)

        macro_action = QtWidgets.QAction("宏录制", self)
        macro_action.triggered.connect(self.toggle_macro_recording)
        dev_menu.addAction(macro_action)

        debug_action = QtWidgets.QAction("调试接口", self)
        debug_action.triggered.connect(self.open_debug_interface)
        dev_menu.addAction(debug_action)

        # 帮助菜单
        help_menu = self.menu_bar.addMenu("帮助")
        docs_action = QtWidgets.QAction("文档", self)
        docs_action.triggered.connect(self.open_help_docs)
        help_menu.addAction(docs_action)

        version_action = QtWidgets.QAction("版本信息", self)
        version_action.triggered.connect(self.show_version_info)
        help_menu.addAction(version_action)

        support_action = QtWidgets.QAction("技术支持", self)
        support_action.triggered.connect(self.contact_support)
        help_menu.addAction(support_action)
        
        # 使用QMainWindow的setMenuBar方法，菜单栏会自动显示在窗口顶部
        self.setMenuBar(self.menu_bar)
    
    def init_ui(self):
        """初始化界面布局"""
        # 创建主水平分割器：左侧工具栏 | 中间视图 | 右侧面板
        main_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        main_splitter.setChildrenCollapsible(False)
        main_splitter.setHandleWidth(2)
        
        # 创建左侧工具栏（垂直布局）
        self.left_toolbar = QtWidgets.QWidget()
        self.left_toolbar.setMaximumWidth(230)
        self.left_toolbar.setMinimumWidth(190)
        self.left_toolbar.setStyleSheet("""
            QWidget {
                background-color: #303030;
                border-right: 1px solid #1f1f1f;
            }
        """)
        toolbar_layout = QtWidgets.QVBoxLayout(self.left_toolbar)
        toolbar_layout.setContentsMargins(4, 4, 4, 4)
        toolbar_layout.setSpacing(4)

        # 左侧标签页：主控台 / 图像分割
        left_tabs = QtWidgets.QTabWidget()
        left_tabs.setDocumentMode(True)
        left_tabs.setTabPosition(QtWidgets.QTabWidget.North)

        # ------------------------ 主控台标签页 ------------------------
        main_console = QtWidgets.QWidget()
        main_console_layout = QtWidgets.QVBoxLayout(main_console)
        main_console_layout.setContentsMargins(2, 2, 2, 2)
        main_console_layout.setSpacing(4)

        # 操作区
        ops_group = QtWidgets.QGroupBox("操作区")
        ops_layout = QtWidgets.QGridLayout(ops_group)
        ops_layout.setSpacing(4)
        ops_buttons = [
            ("平移", self.set_pan_mode),
            ("缩放", self.set_zoom_mode),
            ("旋转", self.set_rotate_mode),
            ("翻转", self.flip_current_view),
            ("重置视图", self.reset_view_transform),
            ("定位十字线", self.enable_crosshair_mode),
            ("上一切片", self.goto_prev_slice),
            ("下一切片", self.goto_next_slice),
        ]
        for idx, (text, callback) in enumerate(ops_buttons):
            btn = QtWidgets.QToolButton()
            btn.setText(text)
            btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
            btn.clicked.connect(callback)
            btn.setMinimumHeight(20)
            btn.setMinimumWidth(44)
            ops_layout.addWidget(btn, idx // 4, idx % 4)
        main_console_layout.addWidget(ops_group)

        # 翻转/旋转面板
        flip_rotate_group = QtWidgets.QGroupBox("翻转/旋转")
        flip_rotate_layout = QtWidgets.QGridLayout(flip_rotate_group)
        flip_rotate_layout.setSpacing(4)

        flip_h_btn = QtWidgets.QToolButton()
        flip_h_btn.setText("水平翻转")
        flip_h_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        flip_h_btn.clicked.connect(self.flip_current_view_horizontal)
        flip_rotate_layout.addWidget(flip_h_btn, 0, 0)

        flip_v_btn = QtWidgets.QToolButton()
        flip_v_btn.setText("垂直翻转")
        flip_v_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        flip_v_btn.clicked.connect(self.flip_current_view_vertical)
        flip_rotate_layout.addWidget(flip_v_btn, 0, 1)

        rot_cw_90_btn = QtWidgets.QToolButton()
        rot_cw_90_btn.setText("旋转+90°")
        rot_cw_90_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        rot_cw_90_btn.clicked.connect(self.rotate_current_view_cw_90)
        flip_rotate_layout.addWidget(rot_cw_90_btn, 1, 0)

        rot_ccw_90_btn = QtWidgets.QToolButton()
        rot_ccw_90_btn.setText("旋转-90°")
        rot_ccw_90_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        rot_ccw_90_btn.clicked.connect(self.rotate_current_view_ccw_90)
        flip_rotate_layout.addWidget(rot_ccw_90_btn, 1, 1)

        angle_label = QtWidgets.QLabel("角度")
        flip_rotate_layout.addWidget(angle_label, 2, 0)
        self.rotate_step_spin = QtWidgets.QSpinBox()
        self.rotate_step_spin.setRange(1, 180)
        self.rotate_step_spin.setValue(10)
        self.rotate_step_spin.setSuffix("°")
        flip_rotate_layout.addWidget(self.rotate_step_spin, 2, 1)

        rot_cw_btn = QtWidgets.QToolButton()
        rot_cw_btn.setText("顺时针")
        rot_cw_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        rot_cw_btn.clicked.connect(lambda: self.rotate_current_view_by_step(True))
        flip_rotate_layout.addWidget(rot_cw_btn, 3, 0)

        rot_ccw_btn = QtWidgets.QToolButton()
        rot_ccw_btn.setText("逆时针")
        rot_ccw_btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        rot_ccw_btn.clicked.connect(lambda: self.rotate_current_view_by_step(False))
        flip_rotate_layout.addWidget(rot_ccw_btn, 3, 1)

        main_console_layout.addWidget(flip_rotate_group)

        sep1 = QtWidgets.QFrame()
        sep1.setFrameShape(QtWidgets.QFrame.HLine)
        sep1.setStyleSheet("color:#4a4a4a;")
        main_console_layout.addWidget(sep1)
        
        # 窗位/窗宽
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
        self.ww_value.setStyleSheet("QLabel { font-weight: normal; background-color: #252525; color: #dcdcdc; padding: 3px; border: 1px solid #555; border-radius: 2px; }")
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
        self.wl_value.setStyleSheet("QLabel { font-weight: normal; background-color: #252525; color: #dcdcdc; padding: 3px; border: 1px solid #555; border-radius: 2px; }")
        ww_wl_group_layout.addWidget(self.wl_value)
        
        ww_wl_group_layout.addSpacing(5)
        
        # 重置按钮
        reset_btn = QtWidgets.QPushButton("重置")
        reset_btn.setStyleSheet("QPushButton { font-weight: normal; padding: 5px; }")
        reset_btn.clicked.connect(self.reset_window_level)
        ww_wl_group_layout.addWidget(reset_btn)
        
        main_console_layout.addWidget(ww_wl_group)

        # 标注区
        annotation_group = QtWidgets.QGroupBox("标注区")
        annotation_layout = QtWidgets.QGridLayout(annotation_group)
        annotation_layout.setSpacing(4)
        annotation_buttons = [
            ("画笔", self.start_brush_annotation),
            ("橡皮擦", self.start_eraser_annotation),
            ("ROI绘制", self.roi_selection_start),
            ("长度", self.measure_distance),
            ("角度", self.measure_angle),
            ("面积", self.measure_area_placeholder),
            ("体积", self.measure_volume_placeholder),
            ("文本", self.add_text_annotation),
        ]
        for idx, (text, callback) in enumerate(annotation_buttons):
            btn = QtWidgets.QToolButton()
            btn.setText(text)
            btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
            btn.clicked.connect(callback)
            btn.setMinimumHeight(20)
            btn.setMinimumWidth(44)
            annotation_layout.addWidget(btn, idx // 4, idx % 4)
        main_console_layout.addWidget(annotation_group)

        sep2 = QtWidgets.QFrame()
        sep2.setFrameShape(QtWidgets.QFrame.HLine)
        sep2.setStyleSheet("color:#4a4a4a;")
        main_console_layout.addWidget(sep2)

        # 移动区
        move_group = QtWidgets.QGroupBox("移动区")
        move_layout = QtWidgets.QVBoxLayout(move_group)
        self.chk_dynamic_refresh = QtWidgets.QCheckBox("动态刷新")
        self.chk_dynamic_refresh.setChecked(True)
        self.chk_interactive_probe = QtWidgets.QCheckBox("探头定位")
        move_layout.addWidget(self.chk_dynamic_refresh)
        move_layout.addWidget(self.chk_interactive_probe)
        main_console_layout.addWidget(move_group)

        sep3 = QtWidgets.QFrame()
        sep3.setFrameShape(QtWidgets.QFrame.HLine)
        sep3.setStyleSheet("color:#4a4a4a;")
        main_console_layout.addWidget(sep3)

        # 场景视图属性
        scene_group = QtWidgets.QGroupBox("场景视图属性")
        scene_layout = QtWidgets.QVBoxLayout(scene_group)
        self.chk_show_scale = QtWidgets.QCheckBox("显示比例尺")
        self.chk_show_scale.setChecked(True)
        self.chk_show_legend = QtWidgets.QCheckBox("显示图例")
        self.chk_show_annotations = QtWidgets.QCheckBox("显示文字注释")
        self.chk_show_annotations.setChecked(True)
        self.chk_show_crosshair = QtWidgets.QCheckBox("显示十字线")
        self.chk_show_crosshair.setChecked(True)
        self.chk_orthogonal_projection = QtWidgets.QCheckBox("正交投影")
        self.chk_reduce_quality_during_op = QtWidgets.QCheckBox("操作时降低画质")
        self.chk_best_quality = QtWidgets.QCheckBox("最优质量")
        self.chk_best_quality.setChecked(True)
        self.chk_show_orientation = QtWidgets.QCheckBox("显示方向信息")
        self.chk_show_orientation.setChecked(True)
        for widget in [
            self.chk_show_scale, self.chk_show_legend, self.chk_show_annotations,
            self.chk_show_crosshair, self.chk_orthogonal_projection,
            self.chk_reduce_quality_during_op, self.chk_best_quality,
            self.chk_show_orientation
        ]:
            scene_layout.addWidget(widget)

        mode_row = QtWidgets.QHBoxLayout()
        mode_row.addWidget(QtWidgets.QLabel("视图模式:"))
        self.view_mode_combo = QtWidgets.QComboBox()
        self.view_mode_combo.addItems(["2D", "3D", "2D+3D"])
        mode_row.addWidget(self.view_mode_combo)
        scene_layout.addLayout(mode_row)

        render_row = QtWidgets.QHBoxLayout()
        render_row.addWidget(QtWidgets.QLabel("渲染模式:"))
        self.render_mode_combo = QtWidgets.QComboBox()
        self.render_mode_combo.addItems(["默认", "MIP", "MinIP", "表面渲染", "体渲染"])
        self.render_mode_combo.currentTextChanged.connect(self.on_render_mode_changed)
        render_row.addWidget(self.render_mode_combo)
        scene_layout.addLayout(render_row)

        bg_btn = QtWidgets.QPushButton("背景颜色")
        bg_btn.clicked.connect(self.change_background_color)
        scene_layout.addWidget(bg_btn)
        main_console_layout.addWidget(scene_group)

        # 光照设置
        light_group = QtWidgets.QGroupBox("光照设置")
        light_form = QtWidgets.QFormLayout(light_group)
        self.light_pos_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.light_pos_slider.setRange(0, 100)
        self.light_pos_slider.setValue(50)
        self.light_intensity_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.light_intensity_slider.setRange(0, 100)
        self.light_intensity_slider.setValue(60)
        self.shadow_strength_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.shadow_strength_slider.setRange(0, 100)
        self.shadow_strength_slider.setValue(40)
        self.shadow_alpha_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.shadow_alpha_slider.setRange(0, 100)
        self.shadow_alpha_slider.setValue(50)
        self.brightness_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.setValue(50)
        self.spot_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.spot_slider.setRange(0, 100)
        self.spot_slider.setValue(30)
        self.specular_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.specular_slider.setRange(0, 100)
        self.specular_slider.setValue(35)
        self.scatter_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.scatter_slider.setRange(0, 100)
        self.scatter_slider.setValue(45)
        light_form.addRow("光源位置", self.light_pos_slider)
        light_form.addRow("光线照明", self.light_intensity_slider)
        light_form.addRow("阴影强度", self.shadow_strength_slider)
        light_form.addRow("阴影透明度", self.shadow_alpha_slider)
        light_form.addRow("光亮", self.brightness_slider)
        light_form.addRow("聚光灯", self.spot_slider)
        light_form.addRow("镜面反光", self.specular_slider)
        light_form.addRow("散射", self.scatter_slider)
        main_console_layout.addWidget(light_group)

        # 聚焦
        focus_group = QtWidgets.QGroupBox("聚焦")
        focus_layout = QtWidgets.QFormLayout(focus_group)
        self.chk_auto_focus = QtWidgets.QCheckBox("自动对焦")
        self.chk_auto_focus.setChecked(True)
        self.focus_distance_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.focus_distance_slider.setRange(0, 100)
        self.focus_distance_slider.setValue(40)
        self.depth_of_field_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.depth_of_field_slider.setRange(0, 100)
        self.depth_of_field_slider.setValue(30)
        focus_layout.addRow(self.chk_auto_focus)
        focus_layout.addRow("焦距", self.focus_distance_slider)
        focus_layout.addRow("景深", self.depth_of_field_slider)
        main_console_layout.addWidget(focus_group)

        # 单位与导出
        unit_group = QtWidgets.QGroupBox("单位与导出")
        unit_layout = QtWidgets.QVBoxLayout(unit_group)
        unit_row = QtWidgets.QHBoxLayout()
        unit_row.addWidget(QtWidgets.QLabel("长度单位"))
        self.unit_combo = QtWidgets.QComboBox()
        self.unit_combo.addItems(["mm", "cm", "μm"])
        unit_row.addWidget(self.unit_combo)
        unit_layout.addLayout(unit_row)
        export_screen_btn = QtWidgets.QPushButton("导出截屏")
        export_screen_btn.clicked.connect(self.export_screenshot)
        unit_layout.addWidget(export_screen_btn)
        main_console_layout.addWidget(unit_group)

        # 2D视图
        view2d_group = QtWidgets.QGroupBox("2D视图")
        view2d_layout = QtWidgets.QGridLayout(view2d_group)
        view2d_layout.setSpacing(4)
        side_btn = QtWidgets.QToolButton(); side_btn.setText("侧视图"); side_btn.clicked.connect(lambda: self.switch_2d_view("side"))
        front_btn = QtWidgets.QToolButton(); front_btn.setText("正视图"); front_btn.clicked.connect(lambda: self.switch_2d_view("front"))
        back_btn = QtWidgets.QToolButton(); back_btn.setText("后视图"); back_btn.clicked.connect(lambda: self.switch_2d_view("back"))
        plane_btn = QtWidgets.QToolButton(); plane_btn.setText("可视平面"); plane_btn.clicked.connect(self.configure_visible_plane)
        view2d_layout.addWidget(side_btn, 0, 0)
        view2d_layout.addWidget(front_btn, 0, 1)
        view2d_layout.addWidget(back_btn, 1, 0)
        view2d_layout.addWidget(plane_btn, 1, 1)
        main_console_layout.addWidget(view2d_group)
        
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
        self.roi_depth_min_value.setStyleSheet("QLabel { font-weight: normal; background-color: #252525; color: #dcdcdc; padding: 2px; border: 1px solid #555; border-radius: 2px; min-width: 40px; }")
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
        self.roi_depth_max_value.setStyleSheet("QLabel { font-weight: normal; background-color: #252525; color: #dcdcdc; padding: 2px; border: 1px solid #555; border-radius: 2px; min-width: 40px; }")
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
        
        # 主控台补充ROI设置
        main_console_layout.addWidget(roi_group)
        main_console_layout.addStretch()

        # 滚动容器（主控台控件较多）
        main_scroll = QtWidgets.QScrollArea()
        main_scroll.setWidget(main_console)
        main_scroll.setWidgetResizable(True)
        main_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # ------------------------ 图像分割标签页 ------------------------
        segmentation_tab = QtWidgets.QWidget()
        segmentation_layout = QtWidgets.QVBoxLayout(segmentation_tab)
        segmentation_layout.setContentsMargins(2, 2, 2, 2)
        segmentation_layout.setSpacing(4)

        ai_seg_group = QtWidgets.QGroupBox("AI / 深度学习分割")
        ai_seg_layout = QtWidgets.QVBoxLayout(ai_seg_group)
        ai_auto_btn = QtWidgets.QPushButton("一键自动分割")
        ai_auto_btn.clicked.connect(self.run_unet_segmentation)
        ai_seg_layout.addWidget(ai_auto_btn)
        segmentation_layout.addWidget(ai_seg_group)

        manual_seg_group = QtWidgets.QGroupBox("手动分割")
        manual_seg_layout = QtWidgets.QGridLayout(manual_seg_group)
        manual_seg_layout.setSpacing(4)
        manual_buttons = [
            ("画笔", self.start_brush_annotation),
            ("阈值", self.run_threshold_segmentation),
            ("区域生长", self.run_region_growing),
            ("OTSU", self.run_otsu_segmentation),
        ]
        for idx, (text, callback) in enumerate(manual_buttons):
            btn = QtWidgets.QToolButton()
            btn.setText(text)
            btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
            btn.clicked.connect(callback)
            btn.setMinimumHeight(20)
            btn.setMinimumWidth(44)
            manual_seg_layout.addWidget(btn, idx // 4, idx % 4)
        segmentation_layout.addWidget(manual_seg_group)

        post_seg_group = QtWidgets.QGroupBox("分割后处理")
        post_seg_layout = QtWidgets.QGridLayout(post_seg_group)
        post_seg_layout.setSpacing(4)
        post_buttons = [
            ("平滑", self.postprocess_smooth),
            ("填充", self.postprocess_fill),
            ("裁剪", self.postprocess_crop),
            ("布尔运算", self.postprocess_boolean),
        ]
        for idx, (text, callback) in enumerate(post_buttons):
            btn = QtWidgets.QToolButton()
            btn.setText(text)
            btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
            btn.clicked.connect(callback)
            btn.setMinimumHeight(20)
            btn.setMinimumWidth(44)
            post_seg_layout.addWidget(btn, idx // 4, idx % 4)
        segmentation_layout.addWidget(post_seg_group)

        result_group = QtWidgets.QGroupBox("分割结果管理")
        result_layout = QtWidgets.QVBoxLayout(result_group)
        save_seg_btn = QtWidgets.QPushButton("保存分割")
        save_seg_btn.clicked.connect(self.save_segmentation_result)
        load_seg_btn = QtWidgets.QPushButton("加载分割")
        load_seg_btn.clicked.connect(self.load_segmentation_result)
        export_model_btn = QtWidgets.QPushButton("导出模型")
        export_model_btn.clicked.connect(self.export_segmentation_model)
        result_layout.addWidget(save_seg_btn)
        result_layout.addWidget(load_seg_btn)
        result_layout.addWidget(export_model_btn)
        segmentation_layout.addWidget(result_group)
        segmentation_layout.addStretch()

        left_tabs.addTab(main_scroll, "主控台")
        left_tabs.addTab(segmentation_tab, "图像分割")
        toolbar_layout.addWidget(left_tabs)
        
        # 将左侧工具栏添加到主分割器
        main_splitter.addWidget(self.left_toolbar)
        
        # 保存引用（兼容旧代码）
        self.ww_wl_panel = self.left_toolbar
        
        # 创建中间视图区域
        self.grid_widget = QtWidgets.QWidget()
        self.grid_widget.setStyleSheet("background-color: #000000;")
        self.grid_layout = QtWidgets.QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(2)
        self.grid_layout.setContentsMargins(2, 2, 2, 2)
        
        # 将中间视图区域添加到主分割器
        main_splitter.addWidget(self.grid_widget)
        
        # 创建右侧面板（垂直分割成上下两部分）
        self.right_panel = QtWidgets.QWidget()
        self.right_panel.setMaximumWidth(300)
        self.right_panel.setMinimumWidth(260)
        self.right_panel.setStyleSheet("background-color: #303030; border-left: 1px solid #1f1f1f;")
        right_panel_layout = QtWidgets.QVBoxLayout(self.right_panel)
        right_panel_layout.setContentsMargins(8, 8, 8, 8)
        right_panel_layout.setSpacing(8)
        
        # 数据列表面板（上半部分） - 浅色风格
        data_list_panel = QtWidgets.QWidget()
        data_list_panel.setStyleSheet("""
            QWidget {
                background-color: #2f2f2f;
                border: 1px solid #4a4a4a;
                border-radius: 2px;
            }
        """)
        data_list_layout = QtWidgets.QVBoxLayout(data_list_panel)
        data_list_layout.setContentsMargins(4, 4, 4, 4)
        data_list_layout.setSpacing(4)
        
        # 标题栏
        data_list_label = QtWidgets.QLabel("图层管理")
        data_list_label.setStyleSheet("""
            QLabel {
                color: #d9d9d9; 
                font-size: 9pt; 
                font-weight: bold;
                background-color: transparent;
                border: none;
                padding: 2px;
            }
        """)
        data_list_label.setAlignment(QtCore.Qt.AlignCenter)
        data_list_layout.addWidget(data_list_label)
        
        # 创建列表控件
        self.data_list_widget = QtWidgets.QListWidget()
        self.data_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #262626;
                border: 1px solid #4a4a4a;
                border-radius: 2px;
                padding: 2px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #3b3b3b;
                color: #e8e8e8;
            }
            QListWidget::item:hover {
                background-color: #4c4c4c;
            }
            QListWidget::item:selected {
                background-color: #5d5d5d;
            }
        """)
        data_list_layout.addWidget(self.data_list_widget)

        # 图层可见性与混合设置
        layer_ctrl_group = QtWidgets.QGroupBox("图层控制")
        layer_ctrl_layout = QtWidgets.QFormLayout(layer_ctrl_group)
        self.chk_layer_visible = QtWidgets.QCheckBox("可见")
        self.chk_layer_visible.setChecked(True)
        self.layer_opacity_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.layer_opacity_slider.setRange(0, 100)
        self.layer_opacity_slider.setValue(100)
        self.layer_blend_combo = QtWidgets.QComboBox()
        self.layer_blend_combo.addItems(["Normal", "Add", "Multiply", "Screen"])
        self.layer_mode_combo = QtWidgets.QComboBox()
        self.layer_mode_combo.addItems(["2D", "3D", "2D/3D"])
        self.chk_layer_locked = QtWidgets.QCheckBox("锁定图层")
        layer_ctrl_layout.addRow(self.chk_layer_visible)
        layer_ctrl_layout.addRow("透明度", self.layer_opacity_slider)
        layer_ctrl_layout.addRow("混合模式", self.layer_blend_combo)
        layer_ctrl_layout.addRow("2D/3D", self.layer_mode_combo)
        layer_ctrl_layout.addRow(self.chk_layer_locked)
        data_list_layout.addWidget(layer_ctrl_group)
        
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
                background-color: #4d3535;
                color: #ffb3b3;
                border: 1px solid #7d4b4b;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #614141;
            }
            QPushButton:pressed {
                background-color: #7d4b4b;
            }
        """)
        self.remove_data_btn.clicked.connect(self.remove_selected_data)
        button_layout.addWidget(self.remove_data_btn)
        
        # 清空所有数据按钮
        self.clear_all_data_btn = QtWidgets.QPushButton("清空")
        self.clear_all_data_btn.setStyleSheet("""
            QPushButton {
                background-color: #4d4435;
                color: #ffd8a8;
                border: 1px solid #7b6a4e;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #63573f;
            }
            QPushButton:pressed {
                background-color: #7b6a4e;
            }
        """)
        self.clear_all_data_btn.clicked.connect(self.clear_all_data)
        button_layout.addWidget(self.clear_all_data_btn)
        
        data_list_layout.addLayout(button_layout)

        shortcut_layout = QtWidgets.QHBoxLayout()
        new_layer_btn = QtWidgets.QPushButton("新建")
        new_layer_btn.clicked.connect(self.create_new_layer)
        copy_layer_btn = QtWidgets.QPushButton("复制")
        copy_layer_btn.clicked.connect(self.copy_current_layer)
        import_layer_btn = QtWidgets.QPushButton("导入")
        import_layer_btn.clicked.connect(self.import_file)
        export_layer_btn = QtWidgets.QPushButton("导出")
        export_layer_btn.clicked.connect(self.export_current_layer)
        shortcut_layout.addWidget(new_layer_btn)
        shortcut_layout.addWidget(copy_layer_btn)
        shortcut_layout.addWidget(import_layer_btn)
        shortcut_layout.addWidget(export_layer_btn)
        data_list_layout.addLayout(shortcut_layout)
        
        # 灰度直方图面板（下半部分） - 浅色背景风格
        histogram_panel = QtWidgets.QWidget()
        histogram_panel.setStyleSheet("""
            QWidget {
                background-color: #2f2f2f;
                border: 1px solid #4a4a4a;
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
                color: #d9d9d9; 
                font-size: 9pt; 
                background-color: transparent;
                border: none;
                padding: 2px;
            }
        """)
        histogram_label.setAlignment(QtCore.Qt.AlignCenter)
        histogram_layout.addWidget(histogram_label)
        
        # 创建matplotlib图形用于显示直方图 - 浅色背景
        self.histogram_figure = Figure(facecolor='#2f2f2f')
        self.histogram_canvas = FigureCanvas(self.histogram_figure)
        self.histogram_canvas.setStyleSheet("background-color: #2f2f2f;")
        self.histogram_ax = self.histogram_figure.add_subplot(111)
        
        # 初始化空直方图 - 浅色背景
        self.histogram_ax.set_facecolor('#1f1f1f')
        self.histogram_ax.text(0.5, 0.5, '等待数据导入', 
                              transform=self.histogram_ax.transAxes,
                              ha='center', va='center',
                      fontsize=10, color='#9b9b9b')
        
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

        # 属性设置面板（界面复刻）
        property_panel = QtWidgets.QWidget()
        property_panel.setStyleSheet("""
            QWidget {
                background-color: #2f2f2f;
                border: 1px solid #4a4a4a;
                border-radius: 2px;
            }
        """)
        property_layout = QtWidgets.QVBoxLayout(property_panel)
        property_layout.setContentsMargins(6, 6, 6, 6)
        property_layout.setSpacing(6)

        property_title = QtWidgets.QLabel("数据属性和设定")
        property_title.setAlignment(QtCore.Qt.AlignLeft)
        property_title.setStyleSheet("QLabel { font-weight: bold; font-size: 9pt; color: #dedede; border: none; padding: 1px 2px; }")
        property_layout.addWidget(property_title)

        info_form = QtWidgets.QFormLayout()
        self.prop_size_label = QtWidgets.QLabel("- x - x -")
        self.prop_spacing_label = QtWidgets.QLabel("- x - x -")
        self.prop_type_label = QtWidgets.QLabel("-")
        self.prop_window_label = QtWidgets.QLabel("W: -, L: -")
        info_form.addRow("尺寸:", self.prop_size_label)
        info_form.addRow("间距:", self.prop_spacing_label)
        info_form.addRow("类型:", self.prop_type_label)
        info_form.addRow("窗宽/窗位:", self.prop_window_label)
        property_layout.addLayout(info_form)

        basic_meta_group = QtWidgets.QGroupBox("基本属性")
        basic_meta_layout = QtWidgets.QFormLayout(basic_meta_group)
        self.prop_width_label = QtWidgets.QLabel("-")
        self.prop_height_label = QtWidgets.QLabel("-")
        self.prop_slice_count_label = QtWidgets.QLabel("-")
        self.prop_spacing_xyz_label = QtWidgets.QLabel("-")
        self.prop_format_label = QtWidgets.QLabel("-")
        basic_meta_layout.addRow("宽度", self.prop_width_label)
        basic_meta_layout.addRow("高度", self.prop_height_label)
        basic_meta_layout.addRow("切片数", self.prop_slice_count_label)
        basic_meta_layout.addRow("体素大小", self.prop_spacing_xyz_label)
        basic_meta_layout.addRow("文件格式", self.prop_format_label)
        self.preview_thumb_label = QtWidgets.QLabel("预览")
        self.preview_thumb_label.setMinimumHeight(90)
        self.preview_thumb_label.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_thumb_label.setStyleSheet("QLabel { background-color: #1f1f1f; border: 1px solid #4a4a4a; color: #888; }")
        basic_meta_layout.addRow("预览", self.preview_thumb_label)
        property_layout.addWidget(basic_meta_group)

        setting_group = QtWidgets.QGroupBox("2D 设置")
        setting_layout = QtWidgets.QVBoxLayout(setting_group)
        alpha_row = QtWidgets.QHBoxLayout()
        alpha_row.addWidget(QtWidgets.QLabel("透明度"))
        self.alpha_slider_2d = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.alpha_slider_2d.setRange(0, 100)
        self.alpha_slider_2d.setValue(100)
        alpha_row.addWidget(self.alpha_slider_2d)
        setting_layout.addLayout(alpha_row)

        lut_row = QtWidgets.QHBoxLayout()
        lut_row.addWidget(QtWidgets.QLabel("2D LUT"))
        self.lut_2d_combo = QtWidgets.QComboBox()
        self.lut_2d_combo.addItems(["grayscale", "hot", "bone", "jet"])
        lut_row.addWidget(self.lut_2d_combo)
        setting_layout.addLayout(lut_row)

        self.chk_use_alpha_lut = QtWidgets.QCheckBox("使用 alpha LUT")
        setting_layout.addWidget(self.chk_use_alpha_lut)

        interp_row = QtWidgets.QHBoxLayout()
        interp_row.addWidget(QtWidgets.QLabel("插值"))
        self.interp_2d_combo = QtWidgets.QComboBox()
        self.interp_2d_combo.addItems(["线性", "最近邻"])
        interp_row.addWidget(self.interp_2d_combo)
        setting_layout.addLayout(interp_row)

        self.chk_sync_views = QtWidgets.QCheckBox("同步切片")
        self.chk_sync_views.setChecked(True)
        self.chk_show_overlay = QtWidgets.QCheckBox("显示叠加层")
        self.chk_show_overlay.setChecked(True)
        self.chk_enable_interpolation = QtWidgets.QCheckBox("启用插值")
        setting_layout.addWidget(self.chk_sync_views)
        setting_layout.addWidget(self.chk_show_overlay)
        setting_layout.addWidget(self.chk_enable_interpolation)
        property_layout.addWidget(setting_group)

        preset_group = QtWidgets.QGroupBox("3D 预设")
        preset_layout = QtWidgets.QGridLayout(preset_group)
        preset_layout.setSpacing(4)
        preset_defs = ["骨骼", "血管", "CTA", "软组织", "高对比", "低噪声"]
        for idx, name in enumerate(preset_defs):
            btn = QtWidgets.QToolButton()
            btn.setText(name)
            btn.clicked.connect(lambda _, n=name: self.apply_3d_preset(n))
            preset_layout.addWidget(btn, idx // 3, idx % 3)
        property_layout.addWidget(preset_group)

        setting3d_group = QtWidgets.QGroupBox("3D 设置")
        setting3d_layout = QtWidgets.QVBoxLayout(setting3d_group)
        opacity3d_row = QtWidgets.QHBoxLayout()
        opacity3d_row.addWidget(QtWidgets.QLabel("透明度"))
        self.opacity_3d_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.opacity_3d_slider.setRange(0, 100)
        self.opacity_3d_slider.setValue(80)
        opacity3d_row.addWidget(self.opacity_3d_slider)
        setting3d_layout.addLayout(opacity3d_row)

        self.chk_absolute_lut = QtWidgets.QCheckBox("绝对 LUT")
        self.chk_flip_roi_lut = QtWidgets.QCheckBox("Flip ROI LUT")
        self.chk_gamma_enhance = QtWidgets.QCheckBox("伽马增强")
        self.chk_stereo_interp = QtWidgets.QCheckBox("立体插值")
        setting3d_layout.addWidget(self.chk_absolute_lut)
        setting3d_layout.addWidget(self.chk_flip_roi_lut)
        setting3d_layout.addWidget(self.chk_gamma_enhance)
        setting3d_layout.addWidget(self.chk_stereo_interp)

        self.chk_3d_shading = QtWidgets.QCheckBox("高质量渲染")
        self.chk_3d_shading.setChecked(True)
        self.chk_3d_edge_enhance = QtWidgets.QCheckBox("边缘增强")
        self.chk_3d_hard_gradient = QtWidgets.QCheckBox("Hard gradient")
        self.chk_3d_gradient = QtWidgets.QCheckBox("梯度增强")
        self.chk_3d_gradient.setChecked(True)
        setting3d_layout.addWidget(self.chk_3d_shading)
        setting3d_layout.addWidget(self.chk_3d_edge_enhance)
        setting3d_layout.addWidget(self.chk_3d_hard_gradient)
        setting3d_layout.addWidget(self.chk_3d_gradient)

        lut3d_row = QtWidgets.QHBoxLayout()
        lut3d_row.addWidget(QtWidgets.QLabel("3D LUT"))
        self.lut_3d_combo = QtWidgets.QComboBox()
        self.lut_3d_combo.addItems(["grayscale", "bone", "coolwarm"])
        lut3d_row.addWidget(self.lut_3d_combo)
        setting3d_layout.addLayout(lut3d_row)
        property_layout.addWidget(setting3d_group)

        extension_group = QtWidgets.QGroupBox("扩展")
        extension_layout = QtWidgets.QFormLayout(extension_group)
        self.chk_axis_equalize = QtWidgets.QCheckBox("均摊(X/Y/Z)")
        distance_btn = QtWidgets.QPushButton("距离")
        distance_btn.clicked.connect(self.measure_distance)
        crop_grid_row = QtWidgets.QHBoxLayout()
        self.crop_x = QtWidgets.QSpinBox(); self.crop_x.setRange(1, 9999); self.crop_x.setValue(1)
        self.crop_y = QtWidgets.QSpinBox(); self.crop_y.setRange(1, 9999); self.crop_y.setValue(1)
        self.crop_z = QtWidgets.QSpinBox(); self.crop_z.setRange(1, 9999); self.crop_z.setValue(1)
        crop_grid_row.addWidget(self.crop_x)
        crop_grid_row.addWidget(self.crop_y)
        crop_grid_row.addWidget(self.crop_z)
        crop_preview_btn = QtWidgets.QPushButton("展示效果")
        crop_preview_btn.clicked.connect(self.preview_crop_effect)
        extension_layout.addRow(self.chk_axis_equalize)
        extension_layout.addRow(distance_btn)
        extension_layout.addRow("网格尺寸", crop_grid_row)
        extension_layout.addRow(crop_preview_btn)
        property_layout.addWidget(extension_group)
        
        # 右侧折叠面板布局（更接近专业软件）
        right_toolbox = QtWidgets.QToolBox()
        right_toolbox.addItem(data_list_panel, "数据属性和设定")
        right_toolbox.addItem(property_panel, "属性设置")
        right_toolbox.addItem(histogram_panel, "灰度直方图")
        right_toolbox.setCurrentIndex(0)
        right_panel_layout.addWidget(right_toolbox, 1)
        
        # 将右侧面板添加到主分割器
        main_splitter.addWidget(self.right_panel)
        
        # 设置分割器的初始尺寸比例（左侧固定，中间自适应，右侧固定）
        main_splitter.setStretchFactor(0, 0)  # 左侧工具栏 - 不拉伸
        main_splitter.setStretchFactor(1, 5)  # 中间视图区域 - 主要区域
        main_splitter.setStretchFactor(2, 0)  # 右侧面板 - 不拉伸
        
        # 设置初始分割比例
        total_width = 1600  # 假设的总宽度
        main_splitter.setSizes([200, 1120, 280])  # 左侧:中间:右侧 的比例
        
        # 使用QMainWindow的setCentralWidget方法设置中心部件
        self.setCentralWidget(main_splitter)
        
        # 创建状态栏
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #333333;
                border-top: 1px solid #1f1f1f;
                padding: 4px;
            }
            QStatusBar::item {
                border: none;
            }
        """)
        
        # 创建状态栏标签
        self.status_label = QtWidgets.QLabel("Current state: 跟踪 (Left mouse)")
        self.status_label.setStyleSheet("color: #d8d8d8; padding: 0 10px;")
        self.status_bar.addWidget(self.status_label, 1)  # stretch factor = 1

        self.new_session_btn = QtWidgets.QPushButton("新建Session...")
        self.new_session_btn.setMinimumHeight(22)
        self.new_session_btn.clicked.connect(self.start_new_session)
        self.status_bar.addPermanentWidget(self.new_session_btn)

        self.pref_btn = QtWidgets.QPushButton("首选项")
        self.pref_btn.setMinimumHeight(22)
        self.pref_btn.clicked.connect(self.open_preferences)
        self.status_bar.addPermanentWidget(self.pref_btn)
        
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
                background-color: #151515;
                border: 1px dashed #4f4f4f;
                border-radius: 8px;
                color: #9a9a9a;
                font-size: 14pt;
                font-weight: 500;
            }
        """

        # 左上：3D View
        view3d_placeholder = QtWidgets.QLabel("3D View\n三维体渲染")
        view3d_placeholder.setAlignment(QtCore.Qt.AlignCenter)
        view3d_placeholder.setStyleSheet(
            "QLabel { background-color: #4a0000; border: 1px solid #5f2b2b; color: #d2d2d2; border-radius: 8px; font-size: 14pt; }"
        )
        self.grid_layout.addWidget(view3d_placeholder, 0, 0)

        # 右上：Coronal
        coronal_placeholder = QtWidgets.QLabel("Coronal\n冠状面")
        coronal_placeholder.setAlignment(QtCore.Qt.AlignCenter)
        coronal_placeholder.setStyleSheet(placeholder_style)
        self.grid_layout.addWidget(coronal_placeholder, 0, 1)

        # 左下：Axial
        axial_placeholder = QtWidgets.QLabel("Axial\n轴位面")
        axial_placeholder.setAlignment(QtCore.Qt.AlignCenter)
        axial_placeholder.setStyleSheet(placeholder_style)
        self.grid_layout.addWidget(axial_placeholder, 1, 0)

        # 右下：Sagittal
        sagittal_placeholder = QtWidgets.QLabel("Sagittal\n矢状面")
        sagittal_placeholder.setAlignment(QtCore.Qt.AlignCenter)
        sagittal_placeholder.setStyleSheet(placeholder_style)
        self.grid_layout.addWidget(sagittal_placeholder, 1, 1)
    
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
                self.histogram_ax.set_facecolor('#1f1f1f')
                self.histogram_figure.patch.set_facecolor('#2f2f2f')
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
            self.histogram_ax.set_facecolor('#1f1f1f')
            self.histogram_figure.patch.set_facecolor('#2f2f2f')
            
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

            # 更新属性面板
            if hasattr(self, 'prop_size_label'):
                self.prop_size_label.setText(f"{self.depth_x} x {self.depth_y} x {self.depth_z}")
            if hasattr(self, 'prop_spacing_label'):
                sx, sy, sz = self.spacing if self.spacing is not None else (1.0, 1.0, 1.0)
                self.prop_spacing_label.setText(f"{sx:.4f} x {sy:.4f} x {sz:.4f}")
                if hasattr(self, 'prop_spacing_xyz_label'):
                    self.prop_spacing_xyz_label.setText(f"{sx:.4f} x {sy:.4f} x {sz:.4f}")
            if hasattr(self, 'prop_type_label'):
                self.prop_type_label.setText(str(self.array.dtype))
            if hasattr(self, 'prop_width_label'):
                self.prop_width_label.setText(str(self.depth_x))
            if hasattr(self, 'prop_height_label'):
                self.prop_height_label.setText(str(self.depth_y))
            if hasattr(self, 'prop_slice_count_label'):
                self.prop_slice_count_label.setText(str(self.depth_z))
            if hasattr(self, 'prop_format_label'):
                self.prop_format_label.setText("Volume")
            
            # 重新创建视图
            data_max = float(self.array.max())
            
            # 创建三个方向的切片视图
            if hasattr(self, 'rgb_array') and self.rgb_array is not None:
                # RGB图像的切片获取
                self.axial_viewer = SliceViewer("Axial (彩色)",
                                          lambda z: self.rgb_array[z, :, :, :],
                                                                                    self.depth_z,
                                                                                    parent_viewer=self)
                self.sag_viewer = SliceViewer("Sagittal (彩色)",
                                        lambda x: self.rgb_array[:, :, x, :],
                                                                                self.depth_x,
                                                                                parent_viewer=self)
                self.cor_viewer = SliceViewer("Coronal (彩色)",
                                        lambda y: self.rgb_array[:, y, :, :],
                                                                                self.depth_y,
                                                                                parent_viewer=self)
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
                if hasattr(self.volume_viewer, 'set_background_color'):
                    self.volume_viewer.set_background_color((0.45, 0.08, 0.08))
                
                # 四宫格布局
                self.grid_layout.addWidget(self.volume_viewer, 0, 0)
                self.grid_layout.addWidget(self.cor_viewer, 0, 1)
                self.grid_layout.addWidget(self.axial_viewer, 1, 0)
                self.grid_layout.addWidget(self.sag_viewer, 1, 1)
            else:
                # 数据全为0，只显示2D视图
                self.grid_layout.addWidget(self.cor_viewer, 0, 1)
                self.grid_layout.addWidget(self.axial_viewer, 1, 0)
                self.grid_layout.addWidget(self.sag_viewer, 1, 1)
                
                # 在左上角显示提示信息
                info_label = QtWidgets.QLabel("3D视图不可用\n(数据全为0)")
                info_label.setAlignment(QtCore.Qt.AlignCenter)
                info_label.setStyleSheet("QLabel { background-color: #4a0000; color: #d0d0d0; font-size: 14pt; }")
                self.grid_layout.addWidget(info_label, 0, 0)

            self.active_view = 'axial'
            
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

            if hasattr(self, 'prop_window_label'):
                self.prop_window_label.setText(f"W: {int(self.window_width)}, L: {int(self.window_level)}")
            
            # 更新灰度直方图
            if hasattr(self, 'update_histogram'):
                self.update_histogram(self.array)

            if hasattr(self, '_refresh_preview_thumbnail'):
                self._refresh_preview_thumbnail()
            
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

        if hasattr(self, 'preview_thumb_label'):
            self.preview_thumb_label.setPixmap(QtGui.QPixmap())
            self.preview_thumb_label.setText("预览")
        if hasattr(self, 'prop_size_label'):
            self.prop_size_label.setText("- x - x -")
        if hasattr(self, 'prop_spacing_label'):
            self.prop_spacing_label.setText("- x - x -")
        if hasattr(self, 'prop_type_label'):
            self.prop_type_label.setText("-")
        if hasattr(self, 'prop_window_label'):
            self.prop_window_label.setText("W: -, L: -")

        print("所有数据已移除，状态已重置")

    # ---------------------- 主界面动作方法（新增） ----------------------
    def start_new_session(self):
        self.clear_all_data()
        self.statusBar().showMessage("已创建新会话", 3000)

    def open_preferences(self):
        QtWidgets.QMessageBox.information(self, "首选项", "首选项面板将用于配置快捷键、主题与默认路径。")

    def save_current_session(self):
        QtWidgets.QMessageBox.information(self, "保存会话", "当前版本已保留界面入口，后续可扩展会话序列化。")

    def import_dicom_series(self):
        self.import_file()

    def export_dicom_series(self):
        QtWidgets.QMessageBox.information(self, "导出DICOM", "当前版本未实现DICOM导出算法，已预留接口。")

    def open_python_console(self):
        QtWidgets.QMessageBox.information(self, "Python脚本", "已预留Python脚本控制台入口。")

    def toggle_macro_recording(self):
        self._macro_recording = not getattr(self, '_macro_recording', False)
        state = "开始" if self._macro_recording else "停止"
        self.statusBar().showMessage(f"宏录制已{state}", 3000)

    def open_debug_interface(self):
        QtWidgets.QMessageBox.information(self, "调试接口", "调试接口入口已启用。")

    def open_help_docs(self):
        QtWidgets.QMessageBox.information(self, "文档", "文档入口已启用。")

    def show_version_info(self):
        QtWidgets.QMessageBox.information(self, "版本信息", "CT Viewer Pro\nVersion 2.0")

    def contact_support(self):
        QtWidgets.QMessageBox.information(self, "技术支持", "请联系 support@ctviewer.local")

    def set_pan_mode(self):
        self._sync_manipulate_action('pan')
        self._stop_cine_if_running()
        self.statusBar().showMessage("当前模式：平移", 2000)

    def set_zoom_mode(self):
        self._sync_manipulate_action('zoom')
        self._stop_cine_if_running()
        self.statusBar().showMessage("当前模式：缩放", 2000)

    def set_rotate_mode(self):
        self._stop_cine_if_running()
        self.statusBar().showMessage("当前模式：旋转", 2000)

    def set_track_mode(self):
        self._sync_manipulate_action('track')
        self._stop_cine_if_running()
        if hasattr(self, 'chk_show_crosshair'):
            self.chk_show_crosshair.setChecked(True)
        self.enable_crosshair_mode()

    def set_cine_mode(self, enabled):
        if enabled:
            self._sync_manipulate_action('cine')
            self.cine_timer.start()
            self.statusBar().showMessage("当前模式：Cine 自动滚片", 2000)
            return
        if hasattr(self, 'cine_timer') and self.cine_timer.isActive():
            self.cine_timer.stop()
            self.statusBar().showMessage("Cine 已停止", 1500)

    def _stop_cine_if_running(self):
        if hasattr(self, 'cine_action') and self.cine_action.isChecked():
            self.cine_action.setChecked(False)

    def stop_cine_via_shortcut(self):
        if hasattr(self, 'cine_timer') and self.cine_timer.isActive():
            if hasattr(self, 'cine_action') and self.cine_action.isChecked():
                self.cine_action.setChecked(False)
            else:
                self.cine_timer.stop()
            self.statusBar().showMessage("已通过 Esc 停止自动滚片", 2000)

    def _sync_manipulate_action(self, mode):
        if not hasattr(self, 'manipulate_action_group'):
            return
        action_map = {
            'track': getattr(self, 'track_action', None),
            'pan': getattr(self, 'pan_action', None),
            'cine': getattr(self, 'cine_action', None),
            'zoom': getattr(self, 'zoom_action', None),
        }
        target = action_map.get(mode)
        if target and not target.isChecked():
            target.setChecked(True)

    def _cine_tick(self):
        step = self._get_slice_step()
        for viewer_name in ["axial_viewer", "cor_viewer", "sag_viewer"]:
            viewer = getattr(self, viewer_name, None)
            if viewer is None:
                continue
            cur = viewer.slider.value()
            max_idx = max(0, viewer.max_index - 1)
            nxt = cur + step
            if nxt > max_idx:
                nxt = 0
            viewer.slider.setValue(nxt)

    def fit_all_views(self):
        for viewer_name in ["axial_viewer", "cor_viewer", "sag_viewer"]:
            viewer = getattr(self, viewer_name, None)
            if viewer:
                viewer.update_slice(viewer.slider.value())
        self.statusBar().showMessage("已适配到窗口", 2000)

    def _get_slice_step(self):
        if hasattr(self, 'slice_step_spin'):
            return max(1, int(self.slice_step_spin.value()))
        return 1

    def _get_active_slice_viewer(self):
        active_view = getattr(self, 'active_view', None)
        mapping = {
            'axial': getattr(self, 'axial_viewer', None),
            'coronal': getattr(self, 'cor_viewer', None),
            'sagittal': getattr(self, 'sag_viewer', None),
        }
        viewer = mapping.get(active_view)
        if viewer is not None:
            return viewer
        for name in ["axial_viewer", "cor_viewer", "sag_viewer"]:
            candidate = getattr(self, name, None)
            if candidate is not None:
                return candidate
        return None

    def _active_view_name(self, viewer):
        if viewer is None:
            return "视图"
        return getattr(viewer, 'title', '视图')

    def flip_current_view_horizontal(self):
        viewer = self._get_active_slice_viewer()
        if viewer and hasattr(viewer, 'toggle_flip_horizontal'):
            viewer.toggle_flip_horizontal()
            self.statusBar().showMessage(f"{self._active_view_name(viewer)}：已水平翻转", 2000)

    def flip_current_view_vertical(self):
        viewer = self._get_active_slice_viewer()
        if viewer and hasattr(viewer, 'toggle_flip_vertical'):
            viewer.toggle_flip_vertical()
            self.statusBar().showMessage(f"{self._active_view_name(viewer)}：已垂直翻转", 2000)

    def rotate_current_view_cw_90(self):
        viewer = self._get_active_slice_viewer()
        if viewer and hasattr(viewer, 'rotate_clockwise_90'):
            viewer.rotate_clockwise_90()
            self.statusBar().showMessage(f"{self._active_view_name(viewer)}：已顺时针旋转90°", 2000)

    def rotate_current_view_ccw_90(self):
        viewer = self._get_active_slice_viewer()
        if viewer and hasattr(viewer, 'rotate_counter_clockwise_90'):
            viewer.rotate_counter_clockwise_90()
            self.statusBar().showMessage(f"{self._active_view_name(viewer)}：已逆时针旋转90°", 2000)

    def rotate_current_view_by_step(self, clockwise=True):
        viewer = self._get_active_slice_viewer()
        if viewer is None or not hasattr(viewer, 'rotate_by_angle'):
            return
        step = int(self.rotate_step_spin.value()) if hasattr(self, 'rotate_step_spin') else 10
        delta = step if clockwise else -step
        viewer.rotate_by_angle(delta)
        direction = "顺时针" if clockwise else "逆时针"
        self.statusBar().showMessage(f"{self._active_view_name(viewer)}：{direction}旋转{step}°", 2000)

    def flip_current_view(self):
        self.flip_current_view_horizontal()

    def reset_view_transform(self):
        for viewer_name in ["axial_viewer", "cor_viewer", "sag_viewer"]:
            viewer = getattr(self, viewer_name, None)
            if viewer and hasattr(viewer, 'reset_image_transform'):
                viewer.reset_image_transform()
        self.update_all_views()
        self.statusBar().showMessage("视图变换已重置", 2000)

    def enable_crosshair_mode(self):
        self.statusBar().showMessage("十字线定位模式已启用", 2000)

    def goto_prev_slice(self):
        step = self._get_slice_step()
        for viewer_name in ["axial_viewer", "cor_viewer", "sag_viewer"]:
            viewer = getattr(self, viewer_name, None)
            if viewer:
                viewer.slider.setValue(max(0, viewer.slider.value() - step))

    def goto_next_slice(self):
        step = self._get_slice_step()
        for viewer_name in ["axial_viewer", "cor_viewer", "sag_viewer"]:
            viewer = getattr(self, viewer_name, None)
            if viewer:
                viewer.slider.setValue(min(viewer.max_index - 1, viewer.slider.value() + step))

    def start_brush_annotation(self):
        self.statusBar().showMessage("画笔标注模式入口已启用", 2000)

    def start_eraser_annotation(self):
        self.statusBar().showMessage("橡皮擦标注模式入口已启用", 2000)

    def measure_area_placeholder(self):
        QtWidgets.QMessageBox.information(self, "面积测量", "面积测量入口已预留。")

    def measure_volume_placeholder(self):
        QtWidgets.QMessageBox.information(self, "体积测量", "体积测量入口已预留。")

    def add_text_annotation(self):
        QtWidgets.QMessageBox.information(self, "文本注释", "文本注释入口已预留。")

    def on_render_mode_changed(self, mode):
        if mode == "MIP":
            self.create_mip_projection(axis=0, use_roi=True)
        elif mode == "MinIP":
            self.create_minip_projection(axis=0, use_roi=True)

    def change_background_color(self):
        color = QtWidgets.QColorDialog.getColor(parent=self)
        if not color.isValid():
            return
        if self.volume_viewer and hasattr(self.volume_viewer, 'set_background_color'):
            self.volume_viewer.set_background_color((color.redF(), color.greenF(), color.blueF()))

    def export_screenshot(self):
        pix = self.grab()
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(self, "导出截屏", "", "PNG Files (*.png)")
        if filepath:
            pix.save(filepath)

    def switch_2d_view(self, view_name):
        self.statusBar().showMessage(f"2D视图切换：{view_name}", 2000)

    def configure_visible_plane(self):
        self.statusBar().showMessage("可视平面设置入口已启用", 2000)

    def postprocess_smooth(self):
        self.statusBar().showMessage("分割后处理：平滑", 2000)

    def postprocess_fill(self):
        self.statusBar().showMessage("分割后处理：填充", 2000)

    def postprocess_crop(self):
        self.statusBar().showMessage("分割后处理：裁剪", 2000)

    def postprocess_boolean(self):
        self.statusBar().showMessage("分割后处理：布尔运算", 2000)

    def save_segmentation_result(self):
        QtWidgets.QMessageBox.information(self, "保存分割", "分割结果保存入口已启用。")

    def load_segmentation_result(self):
        QtWidgets.QMessageBox.information(self, "加载分割", "分割结果加载入口已启用。")

    def export_segmentation_model(self):
        QtWidgets.QMessageBox.information(self, "导出模型", "模型导出入口已启用。")

    def create_new_layer(self):
        QtWidgets.QMessageBox.information(self, "新建图层", "新建图层入口已启用。")

    def copy_current_layer(self):
        QtWidgets.QMessageBox.information(self, "复制图层", "复制当前图层入口已启用。")

    def export_current_layer(self):
        QtWidgets.QMessageBox.information(self, "导出图层", "导出当前图层入口已启用。")

    def apply_3d_preset(self, preset_name):
        self.statusBar().showMessage(f"应用3D预设：{preset_name}", 2000)

    def preview_crop_effect(self):
        self.statusBar().showMessage("裁剪预览入口已启用", 2000)

    def _refresh_preview_thumbnail(self):
        if not hasattr(self, 'preview_thumb_label'):
            return
        if self.axial_viewer is None:
            self.preview_thumb_label.setText("预览")
            self.preview_thumb_label.setPixmap(QtGui.QPixmap())
            return

        pixmap = self.axial_viewer.pixmap_item.pixmap()
        if pixmap is None or pixmap.isNull():
            self.preview_thumb_label.setText("预览")
            return

        thumb = pixmap.scaled(
            self.preview_thumb_label.width() - 6,
            self.preview_thumb_label.height() - 6,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        )
        self.preview_thumb_label.setPixmap(thumb)
        self.preview_thumb_label.setText("")

    # ---------------------- 四视图十字线联动 ----------------------
    def sync_crosshair_from_view(self, source_view, x, y, slice_idx):
        if self.array is None:
            return

        z_dim, y_dim, x_dim = self.array.shape

        if source_view == "axial":
            x_idx = int(np.clip(x, 0, x_dim - 1))
            y_idx = int(np.clip(y, 0, y_dim - 1))
            z_idx = int(np.clip(slice_idx, 0, z_dim - 1))
        elif source_view == "coronal":
            x_idx = int(np.clip(x, 0, x_dim - 1))
            y_idx = int(np.clip(slice_idx, 0, y_dim - 1))
            z_idx = int(np.clip(y, 0, z_dim - 1))
        elif source_view == "sagittal":
            x_idx = int(np.clip(slice_idx, 0, x_dim - 1))
            y_idx = int(np.clip(x, 0, y_dim - 1))
            z_idx = int(np.clip(y, 0, z_dim - 1))
        else:
            return

        if self.axial_viewer:
            self.axial_viewer.slider.setValue(z_idx)
            self.axial_viewer.set_crosshair(x_idx, y_idx)
        if self.cor_viewer:
            self.cor_viewer.slider.setValue(y_idx)
            self.cor_viewer.set_crosshair(x_idx, z_idx)
        if self.sag_viewer:
            self.sag_viewer.slider.setValue(x_idx)
            self.sag_viewer.set_crosshair(y_idx, z_idx)

