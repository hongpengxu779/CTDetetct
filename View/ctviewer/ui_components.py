"""
CT查看器UI组件
包含样式表、菜单、工具栏等UI相关功能
"""

from PyQt5 import QtWidgets, QtCore, QtGui
import numpy as np
import SimpleITK as sitk
import os
import tempfile
from datetime import datetime
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

        # 操作工具组（跟踪 / 平移 / 滚片 / 缩放 + 适配 / 重置）
        manipulate_toolbar = QtWidgets.QToolBar("操作", self)
        manipulate_toolbar.setMovable(False)
        manipulate_toolbar.setIconSize(QtCore.QSize(16, 16))
        manipulate_toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.addToolBar(QtCore.Qt.TopToolBarArea, manipulate_toolbar)

        self.manipulate_action_group = QtWidgets.QActionGroup(self)
        self.manipulate_action_group.setExclusive(True)

        self.track_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_DialogYesButton), "跟踪", self)
        self.track_action.setToolTip("跟踪（十字线联动）")
        self.track_action.setCheckable(True)
        self.track_action.triggered.connect(self.set_track_mode)
        self.manipulate_action_group.addAction(self.track_action)
        manipulate_toolbar.addAction(self.track_action)

        self.pan_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_ArrowLeft), "平移", self)
        self.pan_action.setToolTip("平移")
        self.pan_action.setCheckable(True)
        self.pan_action.triggered.connect(self.set_pan_mode)
        self.manipulate_action_group.addAction(self.pan_action)
        manipulate_toolbar.addAction(self.pan_action)

        self.cine_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_MediaPlay), "滚片", self)
        self.cine_action.setToolTip("滚片（自动浏览切片）")
        self.cine_action.setCheckable(True)
        self.cine_action.toggled.connect(self.set_cine_mode)
        self.manipulate_action_group.addAction(self.cine_action)
        manipulate_toolbar.addAction(self.cine_action)

        self.zoom_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_ArrowUp), "缩放", self)
        self.zoom_action.setToolTip("缩放")
        self.zoom_action.setCheckable(True)
        self.zoom_action.triggered.connect(self.set_zoom_mode)
        self.manipulate_action_group.addAction(self.zoom_action)
        manipulate_toolbar.addAction(self.zoom_action)

        manipulate_toolbar.addSeparator()

        self.fit_view_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_TitleBarMaxButton), "适配", self)
        self.fit_view_action.setToolTip("适配视图")
        self.fit_view_action.triggered.connect(self.fit_all_views)
        manipulate_toolbar.addAction(self.fit_view_action)

        self.reset_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_BrowserReload), "重置", self)
        self.reset_action.setToolTip("重置")
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

        roi_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_DirIcon), "感兴趣区", self)
        roi_action.setToolTip("感兴趣区")
        roi_action.triggered.connect(self.roi_selection_start)
        primary_toolbar.addAction(roi_action)

        roi_clear_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_TrashIcon), "清除感兴趣区", self)
        roi_clear_action.setToolTip("清除感兴趣区")
        roi_clear_action.triggered.connect(self.roi_selection_clear)
        primary_toolbar.addAction(roi_clear_action)

        primary_toolbar.addSeparator()

        segment_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_ArrowForward), "U-Net分割", self)
        segment_action.setToolTip("U-Net分割")
        segment_action.triggered.connect(self.run_unet_segmentation)
        primary_toolbar.addAction(segment_action)

        sam_preseg_action = QtWidgets.QAction(style.standardIcon(QtWidgets.QStyle.SP_ArrowForward), "SAM预分割", self)
        sam_preseg_action.setToolTip("SAM预分割")
        sam_preseg_action.triggered.connect(self.run_sam2_presegmentation)
        primary_toolbar.addAction(sam_preseg_action)

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
        save_session_action.setShortcut("Ctrl+S")
        save_session_action.triggered.connect(self.save_current_session)
        file_menu.addAction(save_session_action)

        load_session_action = QtWidgets.QAction("加载会话...", self)
        load_session_action.setShortcut("Ctrl+O")
        load_session_action.triggered.connect(self.load_session)
        file_menu.addAction(load_session_action)

        file_menu.addSeparator()

        # 导出子菜单
        export_menu = file_menu.addMenu("导出")

        export_nifti_action = QtWidgets.QAction("导出 NIfTI...", self)
        export_nifti_action.triggered.connect(self.export_current_layer)
        export_menu.addAction(export_nifti_action)

        export_dicom_action = QtWidgets.QAction("导出 DICOM 序列...", self)
        export_dicom_action.triggered.connect(self.export_dicom_series)
        export_menu.addAction(export_dicom_action)

        export_raw_mhd_action = QtWidgets.QAction("导出 RAW/MHD...", self)
        export_raw_mhd_action.triggered.connect(self.export_raw_mhd)
        export_menu.addAction(export_raw_mhd_action)

        export_menu.addSeparator()

        export_slices_tiff_action = QtWidgets.QAction("导出切片为TIFF...", self)
        export_slices_tiff_action.triggered.connect(lambda: getattr(self, 'export_slices_dialog', lambda: None)())
        export_menu.addAction(export_slices_tiff_action)

        export_slices_images_action = QtWidgets.QAction("导出切片为图片...", self)
        export_slices_images_action.triggered.connect(self.export_slices_as_images)
        export_menu.addAction(export_slices_images_action)

        file_menu.addSeparator()

        import_dicom_action = QtWidgets.QAction("导入 DICOM...", self)
        import_dicom_action.triggered.connect(self.import_dicom_series)
        file_menu.addAction(import_dicom_action)

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

        musica_action = QtWidgets.QAction("mUSICA增强", self)
        musica_action.triggered.connect(self.apply_musica_enhancement)
        enhance_menu.addAction(musica_action)
        
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

        # 通用图像滤波菜单
        common_filter_menu = tools_menu.addMenu("通用图像滤波")

        cc_menu = common_filter_menu.addMenu("连通域")
        cc_action = QtWidgets.QAction("连通域标记", self)
        cc_action.triggered.connect(self.run_connected_component)
        cc_menu.addAction(cc_action)
        scc_action = QtWidgets.QAction("灰度连通域", self)
        scc_action.triggered.connect(self.run_scalar_connected_component)
        cc_menu.addAction(scc_action)
        relabel_action = QtWidgets.QAction("按大小重排标签", self)
        relabel_action.triggered.connect(self.run_relabel_components)
        cc_menu.addAction(relabel_action)

        conv_menu = common_filter_menu.addMenu("卷积与相关")
        conv_action = QtWidgets.QAction("空间域卷积", self)
        conv_action.triggered.connect(self.run_convolution)
        conv_menu.addAction(conv_action)
        fft_conv_action = QtWidgets.QAction("频域卷积(FFT)", self)
        fft_conv_action.triggered.connect(self.run_fft_convolution)
        conv_menu.addAction(fft_conv_action)
        corr_action = QtWidgets.QAction("归一化相关(NCC)", self)
        corr_action.triggered.connect(self.run_correlation_ncc)
        conv_menu.addAction(corr_action)
        fft_corr_action = QtWidgets.QAction("频域归一化相关(FFT NCC)", self)
        fft_corr_action.triggered.connect(self.run_fft_correlation_ncc)
        conv_menu.addAction(fft_corr_action)
        streaming_fft_corr_action = QtWidgets.QAction("流式频域归一化相关", self)
        streaming_fft_corr_action.triggered.connect(self.run_streaming_fft_correlation_ncc)
        conv_menu.addAction(streaming_fft_corr_action)

        dist_menu = common_filter_menu.addMenu("距离图")
        maurer_action = QtWidgets.QAction("有符号 Maurer 距离图", self)
        maurer_action.triggered.connect(self.run_signed_maurer_distance_map)
        dist_menu.addAction(maurer_action)
        danielsson_action = QtWidgets.QAction("Danielsson 距离图", self)
        danielsson_action.triggered.connect(self.run_danielsson_distance_map)
        dist_menu.addAction(danielsson_action)

        edge_menu = common_filter_menu.addMenu("边缘检测")
        canny_action = QtWidgets.QAction("Canny 边缘检测", self)
        canny_action.triggered.connect(self.run_canny_edge)
        edge_menu.addAction(canny_action)
        sobel_action = QtWidgets.QAction("Sobel 梯度边缘", self)
        sobel_action.triggered.connect(self.run_sobel_edge)
        edge_menu.addAction(sobel_action)

        grad_menu = common_filter_menu.addMenu("梯度与导数")
        gm_action = QtWidgets.QAction("梯度幅值", self)
        gm_action.triggered.connect(self.run_gradient_magnitude)
        grad_menu.addAction(gm_action)
        gmr_action = QtWidgets.QAction("递归高斯梯度幅值", self)
        gmr_action.triggered.connect(self.run_gradient_magnitude_recursive_gaussian)
        grad_menu.addAction(gmr_action)
        deriv_action = QtWidgets.QAction("导数", self)
        deriv_action.triggered.connect(self.run_derivative)
        grad_menu.addAction(deriv_action)
        if hasattr(sitk, "HigherOrderAccurateDerivativeImageFilter"):
            hderiv_action = QtWidgets.QAction("高阶精确导数", self)
            hderiv_action.triggered.connect(self.run_higher_order_accurate_derivative)
            grad_menu.addAction(hderiv_action)

        morph_menu = common_filter_menu.addMenu("形态学")
        dilation_action = QtWidgets.QAction("灰度膨胀", self)
        dilation_action.triggered.connect(self.run_morphology_dilation)
        morph_menu.addAction(dilation_action)

        erosion_action = QtWidgets.QAction("灰度腐蚀", self)
        erosion_action.triggered.connect(self.run_morphology_erosion)
        morph_menu.addAction(erosion_action)

        opening_action = QtWidgets.QAction("开运算", self)
        opening_action.triggered.connect(self.run_morphology_opening)
        morph_menu.addAction(opening_action)

        closing_action = QtWidgets.QAction("闭运算", self)
        closing_action.triggered.connect(self.run_morphology_closing)
        morph_menu.addAction(closing_action)

        obr_action = QtWidgets.QAction("重建开运算", self)
        obr_action.triggered.connect(self.run_morphology_opening_by_reconstruction)
        morph_menu.addAction(obr_action)

        cbr_action = QtWidgets.QAction("重建闭运算", self)
        cbr_action.triggered.connect(self.run_morphology_closing_by_reconstruction)
        morph_menu.addAction(cbr_action)

        thinning_action = QtWidgets.QAction("二值细化/骨架化", self)
        thinning_action.triggered.connect(self.run_binary_thinning)
        morph_menu.addAction(thinning_action)

        fill_bin_action = QtWidgets.QAction("二值孔洞填充", self)
        fill_bin_action.triggered.connect(self.run_fill_hole_binary)
        morph_menu.addAction(fill_bin_action)

        fill_gray_action = QtWidgets.QAction("灰度孔洞填充", self)
        fill_gray_action.triggered.connect(self.run_fill_hole_grayscale)
        morph_menu.addAction(fill_gray_action)

        vessel_action = QtWidgets.QAction("血管增强(Vesselness)", self)
        vessel_action.triggered.connect(self.run_vessel_enhancement)
        common_filter_menu.addAction(vessel_action)

        hessian_action = QtWidgets.QAction("Hessian 特征值分析", self)
        hessian_action.triggered.connect(self.run_hessian_eigen_analysis)
        common_filter_menu.addAction(hessian_action)

        log_action = QtWidgets.QAction("高斯拉普拉斯(LoG)", self)
        log_action.triggered.connect(self.run_laplacian_of_gaussian)
        common_filter_menu.addAction(log_action)
        
        # 人工智能分割菜单
        ai_menu = tools_menu.addMenu("人工智能分割")
        unet_action = QtWidgets.QAction("基线方法", self)
        unet_action.triggered.connect(self.run_unet_segmentation)
        ai_menu.addAction(unet_action)
        sam_preseg_action = QtWidgets.QAction("SAM预分割", self)
        sam_preseg_action.triggered.connect(self.run_sam2_presegmentation)
        ai_menu.addAction(sam_preseg_action)
        ml_seg_action = QtWidgets.QAction("机器学习分割（KNN/集成）", self)
        ml_seg_action.triggered.connect(self.run_ml_segmentation)
        ai_menu.addAction(ml_seg_action)
        label_create_action = QtWidgets.QAction("交互创建标签文件", self)
        label_create_action.triggered.connect(self.run_label_file_creator)
        ai_menu.addAction(label_create_action)
        
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
        self.left_toolbar.setMaximumWidth(520)
        self.left_toolbar.setMinimumWidth(210)
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
        main_console_layout.setContentsMargins(4, 4, 4, 4)
        main_console_layout.setSpacing(6)

        def _make_console_button(text, callback):
            btn = QtWidgets.QToolButton()
            btn.setText(text)
            btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
            btn.clicked.connect(callback)
            btn.setMinimumHeight(24)
            btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            return btn

        # 操作区
        ops_group = QtWidgets.QGroupBox("操作区")
        ops_layout = QtWidgets.QGridLayout(ops_group)
        ops_layout.setHorizontalSpacing(6)
        ops_layout.setVerticalSpacing(6)
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
            btn = _make_console_button(text, callback)
            ops_layout.addWidget(btn, idx // 2, idx % 2)
        ops_layout.setColumnStretch(0, 1)
        ops_layout.setColumnStretch(1, 1)
        main_console_layout.addWidget(ops_group)

        # 翻转/旋转面板
        flip_rotate_group = QtWidgets.QGroupBox("翻转/旋转")
        flip_rotate_layout = QtWidgets.QGridLayout(flip_rotate_group)
        flip_rotate_layout.setHorizontalSpacing(6)
        flip_rotate_layout.setVerticalSpacing(6)

        flip_h_btn = _make_console_button("水平翻转", self.flip_current_view_horizontal)
        flip_rotate_layout.addWidget(flip_h_btn, 0, 0)

        flip_v_btn = _make_console_button("垂直翻转", self.flip_current_view_vertical)
        flip_rotate_layout.addWidget(flip_v_btn, 0, 1)

        rot_cw_90_btn = _make_console_button("旋转+90°", self.rotate_current_view_cw_90)
        flip_rotate_layout.addWidget(rot_cw_90_btn, 1, 0)

        rot_ccw_90_btn = _make_console_button("旋转-90°", self.rotate_current_view_ccw_90)
        flip_rotate_layout.addWidget(rot_ccw_90_btn, 1, 1)

        angle_label = QtWidgets.QLabel("角度")
        flip_rotate_layout.addWidget(angle_label, 2, 0)
        self.rotate_step_spin = QtWidgets.QSpinBox()
        self.rotate_step_spin.setRange(1, 180)
        self.rotate_step_spin.setValue(10)
        self.rotate_step_spin.setSuffix("°")
        self.rotate_step_spin.setMinimumHeight(24)
        flip_rotate_layout.addWidget(self.rotate_step_spin, 2, 1)

        rot_cw_btn = _make_console_button("顺时针", lambda: self.rotate_current_view_by_step(True))
        flip_rotate_layout.addWidget(rot_cw_btn, 3, 0)

        rot_ccw_btn = _make_console_button("逆时针", lambda: self.rotate_current_view_by_step(False))
        flip_rotate_layout.addWidget(rot_ccw_btn, 3, 1)
        flip_rotate_layout.setColumnStretch(0, 1)
        flip_rotate_layout.setColumnStretch(1, 1)

        main_console_layout.addWidget(flip_rotate_group)

        sep1 = QtWidgets.QFrame()
        sep1.setFrameShape(QtWidgets.QFrame.HLine)
        sep1.setStyleSheet("color:#4a4a4a;")
        main_console_layout.addWidget(sep1)
        
        # 窗宽窗位控制已迁移到右侧灰度直方图面板

        # 标注区
        annotation_group = QtWidgets.QGroupBox("标注区")
        annotation_layout = QtWidgets.QGridLayout(annotation_group)
        annotation_layout.setHorizontalSpacing(6)
        annotation_layout.setVerticalSpacing(6)
        annotation_buttons = [
            ("画笔", self.start_brush_annotation),
            ("橡皮擦", self.start_eraser_annotation),
            ("ROI绘制", self.roi_selection_start),
            ("SAM点", self.start_sam_point_prompt),
            ("SAM框", self.start_sam_box_prompt),
            ("长度", self.measure_distance),
            ("角度", self.measure_angle),
            ("面积", self.measure_area_placeholder),
            ("体积", self.measure_volume_placeholder),
            ("文本", self.add_text_annotation),
        ]
        for idx, (text, callback) in enumerate(annotation_buttons):
            btn = _make_console_button(text, callback)
            annotation_layout.addWidget(btn, idx // 2, idx % 2)
        annotation_layout.setColumnStretch(0, 1)
        annotation_layout.setColumnStretch(1, 1)

        annotation_form = QtWidgets.QFormLayout()
        annotation_form.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        annotation_form.setFormAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        annotation_form.setHorizontalSpacing(8)
        annotation_form.setVerticalSpacing(6)

        param_row_1 = QtWidgets.QHBoxLayout()
        self.annotation_label_spin = QtWidgets.QSpinBox()
        self.annotation_label_spin.setRange(0, 255)
        self.annotation_label_spin.setValue(0)
        self.annotation_label_spin.setMaximumWidth(72)
        self.annotation_label_spin.setMinimumHeight(24)
        self.annotation_label_spin.valueChanged.connect(self._on_annotation_label_changed)
        param_row_1.addWidget(self.annotation_label_spin)
        param_row_1.addSpacing(8)
        param_row_1.addWidget(QtWidgets.QLabel("半径"))
        self.annotation_brush_radius_spin = QtWidgets.QSpinBox()
        self.annotation_brush_radius_spin.setRange(1, 30)
        self.annotation_brush_radius_spin.setValue(3)
        self.annotation_brush_radius_spin.setMaximumWidth(72)
        self.annotation_brush_radius_spin.setMinimumHeight(24)
        param_row_1.addWidget(self.annotation_brush_radius_spin)
        param_row_1.addStretch()
        annotation_form.addRow("标签值", param_row_1)

        self.annotation_name_edit = QtWidgets.QLineEdit()
        self.annotation_name_edit.setPlaceholderText("例如：缺陷A")
        self.annotation_name_edit.setMinimumHeight(24)
        annotation_form.addRow("标签名", self.annotation_name_edit)

        action_row = QtWidgets.QHBoxLayout()
        clear_annotation_btn = QtWidgets.QPushButton("清空标注")
        clear_annotation_btn.clicked.connect(self.clear_annotation_volume)
        clear_annotation_btn.setMinimumHeight(24)
        action_row.addWidget(clear_annotation_btn)

        save_annotation_btn = QtWidgets.QPushButton("保存标签")
        save_annotation_btn.clicked.connect(self.save_annotation_as_label_file)
        save_annotation_btn.setMinimumHeight(24)
        action_row.addWidget(save_annotation_btn)
        annotation_form.addRow("操作", action_row)

        annotation_layout.addLayout(annotation_form, 4, 0, 1, 2)
        main_console_layout.addWidget(annotation_group)

        sep2 = QtWidgets.QFrame()
        sep2.setFrameShape(QtWidgets.QFrame.HLine)
        sep2.setStyleSheet("color:#4a4a4a;")
        main_console_layout.addWidget(sep2)

        # 移动区
        move_group = QtWidgets.QGroupBox("移动区")
        move_layout = QtWidgets.QVBoxLayout(move_group)
        move_btn_row = QtWidgets.QHBoxLayout()
        self.move_tool_btn = QtWidgets.QToolButton()
        self.move_tool_btn.setText("移动")
        self.move_tool_btn.setCheckable(True)
        self.move_tool_btn.setToolTip("左键平移，右键旋转")
        self.move_tool_btn.toggled.connect(self.toggle_move_tool)
        move_btn_row.addWidget(self.move_tool_btn)

        self.move_undo_btn = QtWidgets.QToolButton()
        self.move_undo_btn.setText("撤销")
        self.move_undo_btn.setToolTip("撤销上一步平移/旋转")
        self.move_undo_btn.clicked.connect(self.undo_move_tool)
        move_btn_row.addWidget(self.move_undo_btn)
        move_btn_row.addStretch()
        move_layout.addLayout(move_btn_row)

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
        self.view_mode_combo.addItems(["二维", "三维", "二维+三维"])
        self.view_mode_combo.setCurrentIndex(2)
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

        # 场景/光照控制事件绑定
        self.view_mode_combo.currentTextChanged.connect(lambda _: self.apply_scene_view_options())
        for _cb in [
            self.chk_show_scale,
            self.chk_show_legend,
            self.chk_show_annotations,
            self.chk_show_crosshair,
            self.chk_orthogonal_projection,
            self.chk_reduce_quality_during_op,
            self.chk_best_quality,
            self.chk_show_orientation,
        ]:
            _cb.toggled.connect(lambda _: self.apply_scene_view_options())

        for _slider in [
            self.light_pos_slider,
            self.light_intensity_slider,
            self.shadow_strength_slider,
            self.shadow_alpha_slider,
            self.brightness_slider,
            self.spot_slider,
            self.specular_slider,
            self.scatter_slider,
        ]:
            _slider.valueChanged.connect(lambda _: self.apply_3d_lighting_settings())

        self.chk_auto_focus.toggled.connect(lambda _: self.apply_3d_focus_settings())
        self.focus_distance_slider.valueChanged.connect(lambda _: self.apply_3d_focus_settings())
        self.depth_of_field_slider.valueChanged.connect(lambda _: self.apply_3d_focus_settings())

        # 2D视图
        view2d_group = QtWidgets.QGroupBox("二维视图")
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
        roi_group = QtWidgets.QGroupBox("三维感兴趣区域")
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
        depth_min_text = QtWidgets.QLabel("最小:")
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
        depth_max_text = QtWidgets.QLabel("最大:")
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
        roi_3d_btn = QtWidgets.QPushButton("三维预览")
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

        ai_seg_group = QtWidgets.QGroupBox("智能分割")
        ai_seg_layout = QtWidgets.QVBoxLayout(ai_seg_group)
        ai_auto_btn = QtWidgets.QPushButton("一键自动分割")
        ai_auto_btn.clicked.connect(self.run_unet_segmentation)
        ai_seg_layout.addWidget(ai_auto_btn)
        sam_preseg_btn = QtWidgets.QPushButton("SAM预分割")
        sam_preseg_btn.clicked.connect(self.run_sam2_presegmentation)
        ai_seg_layout.addWidget(sam_preseg_btn)
        ml_seg_btn = QtWidgets.QPushButton("机器学习分割")
        ml_seg_btn.clicked.connect(self.run_ml_segmentation)
        ai_seg_layout.addWidget(ml_seg_btn)
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
        self.right_panel.setMaximumWidth(360)
        self.right_panel.setMinimumWidth(300)
        self.right_panel.setStyleSheet("background-color: #2f2f2f; border-left: 1px solid #1f1f1f;")
        right_panel_layout = QtWidgets.QVBoxLayout(self.right_panel)
        right_panel_layout.setContentsMargins(6, 6, 6, 6)
        right_panel_layout.setSpacing(6)

        right_panel_title = QtWidgets.QLabel("图像属性和设置")
        right_panel_title.setStyleSheet("QLabel { font-weight: bold; font-size: 10pt; color: #e3e3e3; border: none; padding: 2px 4px; }")
        right_panel_layout.addWidget(right_panel_title)
        
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
        data_list_label = QtWidgets.QLabel("数据列表")
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

        dataset_toolbar = QtWidgets.QHBoxLayout()
        dataset_toolbar.setSpacing(4)

        self.dataset_filter_btn = QtWidgets.QToolButton()
        self.dataset_filter_btn.setText("F")
        self.dataset_filter_btn.setToolTip("过滤数据项")
        self.dataset_filter_btn.clicked.connect(self._filter_dataset_items)
        dataset_toolbar.addWidget(self.dataset_filter_btn)

        self.dataset_eye_btn = QtWidgets.QToolButton()
        self.dataset_eye_btn.setText("👁")
        self.dataset_eye_btn.setToolTip("显示/隐藏当前数据")
        self.dataset_eye_btn.clicked.connect(self._toggle_current_dataset_visibility)
        dataset_toolbar.addWidget(self.dataset_eye_btn)
        dataset_toolbar.addStretch()
        data_list_layout.addLayout(dataset_toolbar)
        
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
        self.data_list_widget.currentItemChanged.connect(self.on_data_selection_changed)
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
        self.layer_blend_combo.addItems(["普通", "相加", "相乘", "滤色"])
        self.layer_mode_combo = QtWidgets.QComboBox()
        self.layer_mode_combo.addItems(["二维", "三维", "二维/三维"])
        self.chk_layer_locked = QtWidgets.QCheckBox("锁定图层")
        layer_ctrl_layout.addRow(self.chk_layer_visible)
        layer_ctrl_layout.addRow("透明度", self.layer_opacity_slider)
        layer_ctrl_layout.addRow("混合模式", self.layer_blend_combo)
        layer_ctrl_layout.addRow("二维/三维", self.layer_mode_combo)
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
        self.histogram_log_y = True
        self.histogram_bin_width = 4
        self.histogram_mode = 'window'
        self.histogram_pan_last_x = None
        self.histogram_zoom_anchor_x = None
        self.histogram_current_data = None
        self.histogram_plot_range = None
        
        # 连接鼠标事件
        self.histogram_canvas.mpl_connect('button_press_event', self.on_histogram_mouse_press)
        self.histogram_canvas.mpl_connect('button_release_event', self.on_histogram_mouse_release)
        self.histogram_canvas.mpl_connect('motion_notify_event', self.on_histogram_mouse_move)
        self.histogram_canvas.mpl_connect('scroll_event', self.on_histogram_scroll)
        
        self.histogram_canvas.draw()
        
        histogram_layout.addWidget(self.histogram_canvas, 1)  # 添加stretch factor让画布填充

        # 高级直方图控制区（按 Dragonfly 风格）
        histogram_ctrl_panel = QtWidgets.QWidget()
        histogram_ctrl_layout = QtWidgets.QVBoxLayout(histogram_ctrl_panel)
        histogram_ctrl_layout.setContentsMargins(2, 2, 2, 2)
        histogram_ctrl_layout.setSpacing(4)

        # 第一行：Log Y + 窗口阈值
        top_row = QtWidgets.QHBoxLayout()
        self.histogram_logy_checkbox = QtWidgets.QCheckBox("Y轴对数")
        self.histogram_logy_checkbox.setChecked(True)
        self.histogram_logy_checkbox.toggled.connect(self.on_histogram_log_toggled)
        top_row.addWidget(self.histogram_logy_checkbox)
        top_row.addStretch()
        top_row.addWidget(QtWidgets.QLabel("最小:"))
        self.histogram_window_min_edit = QtWidgets.QLineEdit("0")
        self.histogram_window_min_edit.setFixedWidth(62)
        self.histogram_window_min_edit.editingFinished.connect(self.on_histogram_window_edit_finished)
        top_row.addWidget(self.histogram_window_min_edit)
        top_row.addWidget(QtWidgets.QLabel("最大:"))
        self.histogram_window_max_edit = QtWidgets.QLineEdit("0")
        self.histogram_window_max_edit.setFixedWidth(62)
        self.histogram_window_max_edit.editingFinished.connect(self.on_histogram_window_edit_finished)
        top_row.addWidget(self.histogram_window_max_edit)
        histogram_ctrl_layout.addLayout(top_row)

        # 第二行：窗宽/窗位滑条（从左侧迁移）
        ww_row = QtWidgets.QHBoxLayout()
        ww_row.addWidget(QtWidgets.QLabel("窗宽:"))
        self.ww_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.ww_slider.setMinimum(1)
        self.ww_slider.setMaximum(65535)
        self.ww_slider.setValue(65535)
        self.ww_slider.valueChanged.connect(self.on_window_level_changed)
        ww_row.addWidget(self.ww_slider, 1)
        self.ww_value = QtWidgets.QLabel("65535")
        self.ww_value.setMinimumWidth(58)
        self.ww_value.setAlignment(QtCore.Qt.AlignCenter)
        ww_row.addWidget(self.ww_value)
        histogram_ctrl_layout.addLayout(ww_row)

        wl_row = QtWidgets.QHBoxLayout()
        wl_row.addWidget(QtWidgets.QLabel("窗位:"))
        self.wl_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.wl_slider.setMinimum(0)
        self.wl_slider.setMaximum(65535)
        self.wl_slider.setValue(32767)
        self.wl_slider.valueChanged.connect(self.on_window_level_changed)
        wl_row.addWidget(self.wl_slider, 1)
        self.wl_value = QtWidgets.QLabel("32767")
        self.wl_value.setMinimumWidth(58)
        self.wl_value.setAlignment(QtCore.Qt.AlignCenter)
        wl_row.addWidget(self.wl_value)
        histogram_ctrl_layout.addLayout(wl_row)

        # 第三行：高级绘图范围控制
        adv_group = QtWidgets.QGroupBox("高级绘图控制")
        adv_layout = QtWidgets.QVBoxLayout(adv_group)
        adv_layout.setContentsMargins(6, 8, 6, 6)
        adv_layout.setSpacing(4)

        adv_range_row = QtWidgets.QHBoxLayout()
        adv_range_row.addWidget(QtWidgets.QLabel("最小:"))
        self.histogram_plot_min_edit = QtWidgets.QLineEdit("0")
        self.histogram_plot_min_edit.setFixedWidth(62)
        adv_range_row.addWidget(self.histogram_plot_min_edit)
        adv_range_row.addSpacing(8)
        adv_range_row.addWidget(QtWidgets.QLabel("最大:"))
        self.histogram_plot_max_edit = QtWidgets.QLineEdit("0")
        self.histogram_plot_max_edit.setFixedWidth(62)
        adv_range_row.addWidget(self.histogram_plot_max_edit)
        adv_layout.addLayout(adv_range_row)

        adv_btn_row = QtWidgets.QHBoxLayout()
        self.hist_mode_window_btn = QtWidgets.QToolButton()
        self.hist_mode_window_btn.setText("窗")
        self.hist_mode_window_btn.setCheckable(True)
        self.hist_mode_window_btn.setChecked(True)
        self.hist_mode_window_btn.clicked.connect(lambda: self.set_histogram_interaction_mode('window'))
        adv_btn_row.addWidget(self.hist_mode_window_btn)

        self.hist_mode_pan_btn = QtWidgets.QToolButton()
        self.hist_mode_pan_btn.setText("拖")
        self.hist_mode_pan_btn.setCheckable(True)
        self.hist_mode_pan_btn.clicked.connect(lambda: self.set_histogram_interaction_mode('pan'))
        adv_btn_row.addWidget(self.hist_mode_pan_btn)

        self.hist_mode_zoom_btn = QtWidgets.QToolButton()
        self.hist_mode_zoom_btn.setText("缩")
        self.hist_mode_zoom_btn.setCheckable(True)
        self.hist_mode_zoom_btn.clicked.connect(lambda: self.set_histogram_interaction_mode('zoom'))
        adv_btn_row.addWidget(self.hist_mode_zoom_btn)
        adv_btn_row.addStretch()

        self.histogram_reset_btn = QtWidgets.QPushButton("重置")
        self.histogram_reset_btn.setFixedHeight(22)
        self.histogram_reset_btn.clicked.connect(self.on_histogram_reset_clicked)
        adv_btn_row.addWidget(self.histogram_reset_btn)

        self.histogram_apply_btn = QtWidgets.QPushButton("应用")
        self.histogram_apply_btn.setFixedHeight(22)
        self.histogram_apply_btn.clicked.connect(self.on_histogram_apply_clicked)
        adv_btn_row.addWidget(self.histogram_apply_btn)
        adv_layout.addLayout(adv_btn_row)
        histogram_ctrl_layout.addWidget(adv_group)

        # 第四行：bin width + home
        bottom_row = QtWidgets.QHBoxLayout()
        bottom_row.addWidget(QtWidgets.QLabel("分箱宽度:"))
        self.histogram_bin_width_spin = QtWidgets.QSpinBox()
        self.histogram_bin_width_spin.setRange(1, 256)
        self.histogram_bin_width_spin.setValue(4)
        self.histogram_bin_width_spin.valueChanged.connect(self.on_histogram_bin_width_changed)
        bottom_row.addWidget(self.histogram_bin_width_spin)
        bottom_row.addStretch()
        self.histogram_home_btn = QtWidgets.QToolButton()
        self.histogram_home_btn.setText("↺")
        self.histogram_home_btn.clicked.connect(self.on_histogram_home_clicked)
        bottom_row.addWidget(self.histogram_home_btn)
        histogram_ctrl_layout.addLayout(bottom_row)

        # 第五行：窗口级别交互、区域自动窗调平、重置
        wl_action_row = QtWidgets.QHBoxLayout()
        self.window_level_interact_btn = QtWidgets.QToolButton()
        self.window_level_interact_btn.setText("◐")
        self.window_level_interact_btn.setCheckable(True)
        self.window_level_interact_btn.setToolTip("窗口级别交互：在任意2D视图左键拖拽（上/下改窗位，左/右改窗宽）")
        self.window_level_interact_btn.toggled.connect(self.on_window_level_interact_toggled)
        wl_action_row.addWidget(self.window_level_interact_btn)

        self.window_level_roi_btn = QtWidgets.QToolButton()
        self.window_level_roi_btn.setText("▦")
        self.window_level_roi_btn.setCheckable(True)
        self.window_level_roi_btn.setToolTip("区域自动窗调平：在2D视图框选ROI后自动应用")
        self.window_level_roi_btn.toggled.connect(self.on_window_level_roi_toggled)
        wl_action_row.addWidget(self.window_level_roi_btn)

        self.window_level_reset_btn = QtWidgets.QToolButton()
        self.window_level_reset_btn.setText("↻")
        self.window_level_reset_btn.setToolTip("重置窗宽窗位")
        self.window_level_reset_btn.clicked.connect(self.reset_window_level)
        wl_action_row.addWidget(self.window_level_reset_btn)
        wl_action_row.addStretch()
        histogram_ctrl_layout.addLayout(wl_action_row)

        mode_group = QtWidgets.QButtonGroup(self)
        mode_group.setExclusive(True)
        mode_group.addButton(self.hist_mode_window_btn)
        mode_group.addButton(self.hist_mode_pan_btn)
        mode_group.addButton(self.hist_mode_zoom_btn)
        self.histogram_mode_group = mode_group

        histogram_layout.addWidget(histogram_ctrl_panel)

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

        property_title = QtWidgets.QLabel("图像属性和设置")
        property_title.setAlignment(QtCore.Qt.AlignLeft)
        property_title.setStyleSheet("QLabel { font-weight: bold; font-size: 9pt; color: #dedede; border: none; padding: 1px 2px; }")
        property_layout.addWidget(property_title)

        info_form = QtWidgets.QFormLayout()
        self.prop_size_label = QtWidgets.QLabel("- × - × -")
        self.prop_spacing_label = QtWidgets.QLabel("- × - × -")
        self.prop_type_label = QtWidgets.QLabel("-")
        self.prop_window_label = QtWidgets.QLabel("窗宽: -, 窗位: -")
        info_form.addRow("尺寸:", self.prop_size_label)
        info_form.addRow("间距:", self.prop_spacing_label)
        info_form.addRow("类型:", self.prop_type_label)
        info_form.addRow("窗宽/窗位:", self.prop_window_label)
        property_layout.addLayout(info_form)

        basic_meta_group = QtWidgets.QGroupBox("基本属性")
        basic_meta_layout = QtWidgets.QVBoxLayout(basic_meta_group)

        self.basic_properties_table = QtWidgets.QTableWidget(8, 3)
        self.basic_properties_table.setHorizontalHeaderLabels(["属性", "数值", "说明"])
        self.basic_properties_table.verticalHeader().setVisible(False)
        self.basic_properties_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.basic_properties_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.basic_properties_table.setFocusPolicy(QtCore.Qt.NoFocus)
        self.basic_properties_table.setWordWrap(True)
        self.basic_properties_table.horizontalHeader().setStretchLastSection(True)
        self.basic_properties_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.basic_properties_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.basic_properties_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.basic_properties_table.setAlternatingRowColors(True)
        self.basic_properties_table.setMinimumHeight(220)
        self.basic_properties_table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a2a;
                border: 1px solid #4b4b4b;
                gridline-color: #4b4b4b;
            }
            QHeaderView::section {
                background-color: #3e3e3e;
                color: #e8e8e8;
                border: 1px solid #4b4b4b;
                padding: 3px;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 4px;
            }
        """)
        basic_meta_layout.addWidget(self.basic_properties_table)

        self.prop_width_label = QtWidgets.QLabel("-")
        self.prop_height_label = QtWidgets.QLabel("-")
        self.prop_slice_count_label = QtWidgets.QLabel("-")
        self.prop_spacing_xyz_label = QtWidgets.QLabel("-")
        self.prop_format_label = QtWidgets.QLabel("-")

        self.preview_thumb_label = QtWidgets.QLabel("预览")
        self.preview_thumb_label.setMinimumHeight(90)
        self.preview_thumb_label.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_thumb_label.setStyleSheet("QLabel { background-color: #1f1f1f; border: 1px solid #4a4a4a; color: #888; }")
        basic_meta_layout.addWidget(self.preview_thumb_label)

        self.basic_properties_note = QtWidgets.QLabel(
            "已选数据的更多信息可在图像属性面板中查看与调整。"
        )
        self.basic_properties_note.setWordWrap(True)
        self.basic_properties_note.setStyleSheet(
            "QLabel { background-color: #3b3f44; border: 1px solid #5a5a5a; border-radius: 4px; padding: 6px; color: #d7d7d7; }"
        )
        basic_meta_layout.addWidget(self.basic_properties_note)

        self._update_basic_properties_table()
        property_layout.addWidget(basic_meta_group)

        tools_group = QtWidgets.QGroupBox("工具")
        tools_layout = QtWidgets.QVBoxLayout(tools_group)
        tools_row_1 = QtWidgets.QHBoxLayout()
        tool_distance_btn = QtWidgets.QPushButton("距离")
        tool_distance_btn.clicked.connect(self.measure_distance)
        tool_angle_btn = QtWidgets.QPushButton("角度")
        tool_angle_btn.clicked.connect(self.measure_angle)
        tools_row_1.addWidget(tool_distance_btn)
        tools_row_1.addWidget(tool_angle_btn)
        tools_layout.addLayout(tools_row_1)

        tools_row_2 = QtWidgets.QHBoxLayout()
        tool_export_btn = QtWidgets.QPushButton("导出")
        tool_export_btn.clicked.connect(self.export_current_layer)
        tool_remove_btn = QtWidgets.QPushButton("删除")
        tool_remove_btn.clicked.connect(self.remove_selected_data)
        tools_row_2.addWidget(tool_export_btn)
        tools_row_2.addWidget(tool_remove_btn)
        tools_layout.addLayout(tools_row_2)
        property_layout.addWidget(tools_group)

        setting_group = QtWidgets.QGroupBox("二维设置")
        setting_layout = QtWidgets.QVBoxLayout(setting_group)
        alpha_row = QtWidgets.QHBoxLayout()
        alpha_row.addWidget(QtWidgets.QLabel("透明度"))
        self.alpha_slider_2d = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.alpha_slider_2d.setRange(0, 100)
        self.alpha_slider_2d.setValue(100)
        alpha_row.addWidget(self.alpha_slider_2d)
        setting_layout.addLayout(alpha_row)

        lut_row = QtWidgets.QHBoxLayout()
        lut_row.addWidget(QtWidgets.QLabel("二维 LUT"))
        self.lut_2d_combo = QtWidgets.QComboBox()
        self.lut_2d_combo.addItems(["grayscale", "hot", "bone", "jet"])
        lut_row.addWidget(self.lut_2d_combo)
        setting_layout.addLayout(lut_row)

        self.chk_use_alpha_lut = QtWidgets.QCheckBox("使用透明度 LUT")
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

        self.alpha_slider_2d.valueChanged.connect(self._on_2d_setting_changed)
        self.lut_2d_combo.currentTextChanged.connect(self._on_2d_setting_changed)
        self.chk_use_alpha_lut.toggled.connect(self._on_2d_setting_changed)
        self.interp_2d_combo.currentTextChanged.connect(self._on_2d_setting_changed)
        self.chk_sync_views.toggled.connect(self._on_sync_slices_toggled)
        self.chk_show_overlay.toggled.connect(self._on_2d_setting_changed)
        self.chk_enable_interpolation.toggled.connect(self._on_2d_setting_changed)

        preset_group = QtWidgets.QGroupBox("三维预设")
        preset_layout = QtWidgets.QGridLayout(preset_group)
        preset_layout.setSpacing(4)
        preset_defs = ["骨骼", "血管", "CTA", "软组织", "高对比", "低噪声"]
        for idx, name in enumerate(preset_defs):
            btn = QtWidgets.QToolButton()
            btn.setText(name)
            btn.clicked.connect(lambda _, n=name: self.apply_3d_preset(n))
            preset_layout.addWidget(btn, idx // 3, idx % 3)
        property_layout.addWidget(preset_group)

        setting3d_group = QtWidgets.QGroupBox("三维设置")
        setting3d_layout = QtWidgets.QVBoxLayout(setting3d_group)

        opacity3d_row = QtWidgets.QHBoxLayout()
        opacity3d_row.addWidget(QtWidgets.QLabel("实心度"))
        self.opacity_3d_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.opacity_3d_slider.setRange(0, 100)
        self.opacity_3d_slider.setValue(80)
        opacity3d_row.addWidget(self.opacity_3d_slider)
        setting3d_layout.addLayout(opacity3d_row)

        diffuse_row = QtWidgets.QHBoxLayout()
        diffuse_row.addWidget(QtWidgets.QLabel("漫反射"))
        self.diffuse_3d_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.diffuse_3d_slider.setRange(0, 100)
        self.diffuse_3d_slider.setValue(75)
        diffuse_row.addWidget(self.diffuse_3d_slider)
        setting3d_layout.addLayout(diffuse_row)

        specular_row = QtWidgets.QHBoxLayout()
        specular_row.addWidget(QtWidgets.QLabel("高光"))
        self.specular_3d_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.specular_3d_slider.setRange(0, 100)
        self.specular_3d_slider.setValue(20)
        specular_row.addWidget(self.specular_3d_slider)
        setting3d_layout.addLayout(specular_row)

        shininess_row = QtWidgets.QHBoxLayout()
        shininess_row.addWidget(QtWidgets.QLabel("光泽度"))
        self.shininess_3d_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.shininess_3d_slider.setRange(1, 100)
        self.shininess_3d_slider.setValue(35)
        shininess_row.addWidget(self.shininess_3d_slider)
        setting3d_layout.addLayout(shininess_row)

        self.chk_tone_mapping = QtWidgets.QCheckBox("色调映射")
        self.chk_unsharp = QtWidgets.QCheckBox("反锐化")
        self.chk_specular_boost = QtWidgets.QCheckBox("高光增强")
        self.chk_noise_reduction = QtWidgets.QCheckBox("降噪")
        self.chk_3d_edge_enhance = QtWidgets.QCheckBox("边缘对比")
        self.chk_filtered_gradient = QtWidgets.QCheckBox("平滑梯度")
        self.chk_3d_shading = QtWidgets.QCheckBox("高质量")
        self.chk_3d_shading.setChecked(True)
        self.chk_median_3d = QtWidgets.QCheckBox("中值平滑")
        self.chk_3d_hard_gradient = self.chk_unsharp
        self.chk_3d_gradient = self.chk_filtered_gradient
        self.chk_3d_gradient.setChecked(False)

        setting3d_layout.addWidget(self.chk_tone_mapping)
        setting3d_layout.addWidget(self.chk_unsharp)
        setting3d_layout.addWidget(self.chk_specular_boost)
        setting3d_layout.addWidget(self.chk_noise_reduction)
        setting3d_layout.addWidget(self.chk_3d_edge_enhance)
        setting3d_layout.addWidget(self.chk_filtered_gradient)
        setting3d_layout.addWidget(self.chk_3d_shading)
        setting3d_layout.addWidget(self.chk_median_3d)

        render3d_row = QtWidgets.QHBoxLayout()
        render3d_row.addWidget(QtWidgets.QLabel("渲染模式"))
        self.render_mode_3d_combo = QtWidgets.QComboBox()
        self.render_mode_3d_combo.addItems(["默认", "MIP", "MinIP", "ISO", "体渲染"])
        render3d_row.addWidget(self.render_mode_3d_combo)
        setting3d_layout.addLayout(render3d_row)

        interpolation3d_row = QtWidgets.QHBoxLayout()
        interpolation3d_row.addWidget(QtWidgets.QLabel("插值方式"))
        self.interp_3d_combo = QtWidgets.QComboBox()
        self.interp_3d_combo.addItems(["最近邻", "线性", "三次"])
        interpolation3d_row.addWidget(self.interp_3d_combo)
        setting3d_layout.addLayout(interpolation3d_row)

        lut3d_row = QtWidgets.QHBoxLayout()
        lut3d_row.addWidget(QtWidgets.QLabel("三维 LUT"))
        self.lut_3d_combo = QtWidgets.QComboBox()
        self.lut_3d_combo.addItems(["grayscale", "bone", "coolwarm"])
        lut3d_row.addWidget(self.lut_3d_combo)
        setting3d_layout.addLayout(lut3d_row)

        self.chk_absolute_lut = QtWidgets.QCheckBox("绝对值 LUT")
        self.chk_flip_roi_lut = QtWidgets.QCheckBox("反转 LUT 映射")
        self.chk_gamma_enhance = QtWidgets.QCheckBox("伽马增强")
        setting3d_layout.addWidget(self.chk_absolute_lut)
        setting3d_layout.addWidget(self.chk_flip_roi_lut)
        setting3d_layout.addWidget(self.chk_gamma_enhance)
        property_layout.addWidget(setting3d_group)

        self.opacity_3d_slider.valueChanged.connect(self.apply_advanced_3d_settings)
        self.diffuse_3d_slider.valueChanged.connect(self.apply_advanced_3d_settings)
        self.specular_3d_slider.valueChanged.connect(self.apply_advanced_3d_settings)
        self.shininess_3d_slider.valueChanged.connect(self.apply_advanced_3d_settings)
        self.chk_tone_mapping.toggled.connect(self.apply_advanced_3d_settings)
        self.chk_unsharp.toggled.connect(self.apply_advanced_3d_settings)
        self.chk_specular_boost.toggled.connect(self.apply_advanced_3d_settings)
        self.chk_noise_reduction.toggled.connect(self.apply_advanced_3d_settings)
        self.chk_3d_edge_enhance.toggled.connect(self.apply_advanced_3d_settings)
        self.chk_filtered_gradient.toggled.connect(self.apply_advanced_3d_settings)
        self.chk_3d_shading.toggled.connect(self.apply_advanced_3d_settings)
        self.chk_median_3d.toggled.connect(self.apply_advanced_3d_settings)
        self.interp_3d_combo.currentTextChanged.connect(self.apply_advanced_3d_settings)
        self.lut_3d_combo.currentTextChanged.connect(self.apply_advanced_3d_settings)
        self.chk_absolute_lut.toggled.connect(self.apply_advanced_3d_settings)
        self.chk_flip_roi_lut.toggled.connect(self.apply_advanced_3d_settings)
        self.chk_gamma_enhance.toggled.connect(self.apply_advanced_3d_settings)
        self.render_mode_3d_combo.currentTextChanged.connect(self.on_render_mode_changed)

        extension_group = QtWidgets.QGroupBox("裁剪")
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
        
        # 右侧单页滚动布局（更接近参考界面）
        right_scroll = QtWidgets.QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        right_scroll_content = QtWidgets.QWidget()
        right_scroll_layout = QtWidgets.QVBoxLayout(right_scroll_content)
        right_scroll_layout.setContentsMargins(2, 2, 2, 2)
        right_scroll_layout.setSpacing(6)
        right_scroll_layout.addWidget(data_list_panel)
        right_scroll_layout.addWidget(property_panel)
        right_scroll_layout.addWidget(histogram_panel)
        right_scroll_layout.addStretch()

        right_scroll.setWidget(right_scroll_content)
        right_panel_layout.addWidget(right_scroll, 1)
        
        # 将右侧面板添加到主分割器
        main_splitter.addWidget(self.right_panel)
        
        # 设置分割器的初始尺寸比例（左侧可扩展，中间自适应，右侧固定）
        main_splitter.setStretchFactor(0, 1)  # 左侧工具栏 - 可拉伸
        main_splitter.setStretchFactor(1, 5)  # 中间视图区域 - 主要区域
        main_splitter.setStretchFactor(2, 0)  # 右侧面板 - 不拉伸
        
        # 设置初始分割比例
        total_width = 1600  # 假设的总宽度
        main_splitter.setSizes([280, 1000, 320])  # 左侧:中间:右侧 的比例
        
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
        self.status_label = QtWidgets.QLabel("当前状态：跟踪（左键）")
        self.status_label.setStyleSheet("color: #d8d8d8; padding: 0 10px;")
        self.status_bar.addWidget(self.status_label, 1)  # stretch factor = 1

        self.new_session_btn = QtWidgets.QPushButton("新建会话...")
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
        self.window_level_drag_mode = False
        self.window_level_roi_mode = False
        self.move_tool_enabled = False
        self.sam_prompt_mode = None
        self.sam_prompt_state = {'point': None, 'box': None}

        # 兜底：确保默认场景模式为2D+3D
        if hasattr(self, 'view_mode_combo'):
            self.view_mode_combo.setCurrentIndex(2)
            if hasattr(self, 'apply_scene_view_options'):
                self.apply_scene_view_options()
    
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

        # 左上：三维视图
        view3d_placeholder = QtWidgets.QLabel("三维视图\n三维体渲染")
        view3d_placeholder.setAlignment(QtCore.Qt.AlignCenter)
        view3d_placeholder.setStyleSheet(
            "QLabel { background-color: #151515; border: 1px solid #3f3f3f; color: #d2d2d2; border-radius: 8px; font-size: 14pt; }"
        )
        self.grid_layout.addWidget(view3d_placeholder, 0, 0)

        # 右上：Coronal
        coronal_placeholder = QtWidgets.QLabel("冠状面")
        coronal_placeholder.setAlignment(QtCore.Qt.AlignCenter)
        coronal_placeholder.setStyleSheet(placeholder_style)
        self.grid_layout.addWidget(coronal_placeholder, 0, 1)

        # 左下：Axial
        axial_placeholder = QtWidgets.QLabel("轴位面")
        axial_placeholder.setAlignment(QtCore.Qt.AlignCenter)
        axial_placeholder.setStyleSheet(placeholder_style)
        self.grid_layout.addWidget(axial_placeholder, 1, 0)

        # 右下：Sagittal
        sagittal_placeholder = QtWidgets.QLabel("矢状面")
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
            if data_array is None:
                self.histogram_current_data = None
                self.histogram_ax.clear()
                self.histogram_ax.set_facecolor('#1f1f1f')
                self.histogram_figure.patch.set_facecolor('#2f2f2f')
                self.histogram_canvas.draw_idle()
                return

            self.histogram_current_data = data_array
            from matplotlib.colors import LinearSegmentedColormap

            current_xlim = None
            # 仅复用用户已显式设置的绘图范围，避免首次绘制误用matplotlib默认(0,1)
            if self.histogram_plot_range is not None:
                current_xlim = self.histogram_plot_range

            self.histogram_ax.clear()
            self.histogram_temp_label = None

            if data_array.size > 1e7:
                sample_size = int(data_array.size * 0.1)
                flat_data = data_array.flatten()
                sample_indices = np.random.choice(flat_data.size, sample_size, replace=False)
                sampled_data = flat_data[sample_indices]
            else:
                sampled_data = data_array.flatten()

            data_min = float(sampled_data.min())
            data_max = float(sampled_data.max())
            if data_max <= data_min:
                data_max = data_min + 1.0

            self.histogram_data_range = (data_min, data_max)

            bin_width = float(getattr(self, 'histogram_bin_width', 4))
            if hasattr(self, 'histogram_bin_width_spin'):
                bin_width = float(self.histogram_bin_width_spin.value())
            self.histogram_bin_width = max(1.0, bin_width)

            n_bins = int(np.clip(np.ceil((data_max - data_min) / self.histogram_bin_width), 32, 2048))
            hist_values, bin_edges = np.histogram(sampled_data, bins=n_bins, range=(data_min, data_max))
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

            colors = [(0.15, 0.15, 0.15), (0.5, 0.5, 0.5), (0.85, 0.85, 0.85)]
            cmap = LinearSegmentedColormap.from_list('grayscale', colors, N=len(bin_centers))
            bar_colors = [cmap(i / max(1, len(bin_centers))) for i in range(len(bin_centers))]

            bar_width = bin_edges[1] - bin_edges[0]
            if self.histogram_log_y:
                draw_values = np.maximum(hist_values, 1)
                self.histogram_ax.set_yscale('log')
                y_max = max(2.0, float(draw_values.max()) * 1.25)
                self.histogram_ax.set_ylim(0.8, y_max)
            else:
                draw_values = hist_values
                self.histogram_ax.set_yscale('linear')
                y_max = max(1.0, float(hist_values.max()) * 1.1)
                self.histogram_ax.set_ylim(0, y_max)

            self.histogram_ax.bar(
                bin_centers,
                draw_values,
                width=bar_width * 0.95,
                color=bar_colors,
                edgecolor='none'
            )

            self.histogram_ax.set_facecolor('#1f1f1f')
            self.histogram_figure.patch.set_facecolor('#2f2f2f')
            self.histogram_ax.set_xticks([])
            self.histogram_ax.set_yticks([])
            self.histogram_ax.spines['bottom'].set_visible(False)
            self.histogram_ax.spines['left'].set_visible(False)
            self.histogram_ax.spines['top'].set_visible(False)
            self.histogram_ax.spines['right'].set_visible(False)

            plot_min, plot_max = data_min, data_max
            if current_xlim is not None:
                try:
                    pmin = float(current_xlim[0])
                    pmax = float(current_xlim[1])
                    if pmax > pmin:
                        plot_min = max(data_min, pmin)
                        plot_max = min(data_max, pmax)
                except (TypeError, ValueError):
                    pass
            if plot_max <= plot_min:
                plot_min, plot_max = data_min, data_max
            self.histogram_ax.set_xlim(plot_min, plot_max)
            self.histogram_plot_range = (plot_min, plot_max)

            self.histogram_bin_centers = bin_centers
            self.histogram_values = hist_values

            line_left_pos = float(getattr(self, 'window_level', (data_min + data_max) * 0.5) - getattr(self, 'window_width', (data_max - data_min)) / 2.0)
            line_right_pos = float(getattr(self, 'window_level', (data_min + data_max) * 0.5) + getattr(self, 'window_width', (data_max - data_min)) / 2.0)
            line_left_pos = max(data_min, min(data_max, line_left_pos))
            line_right_pos = max(data_min, min(data_max, line_right_pos))
            if line_right_pos <= line_left_pos:
                mid = 0.5 * (line_left_pos + line_right_pos)
                half = max((data_max - data_min) * 0.005, 0.5)
                line_left_pos = max(data_min, mid - half)
                line_right_pos = min(data_max, mid + half)

            self.histogram_left_line = self.histogram_ax.axvline(
                line_left_pos, color='blue', linewidth=2, linestyle='-', alpha=0.85
            )
            self.histogram_right_line = self.histogram_ax.axvline(
                line_right_pos, color='red', linewidth=2, linestyle='-', alpha=0.85
            )

            data_mean = float(sampled_data.mean())
            data_std = float(sampled_data.std())
            self._update_status_bar(data_min, data_max, data_mean, data_std)
            self._update_histogram_control_values()

            self.histogram_figure.tight_layout(pad=0.5)
            self.histogram_canvas.draw_idle()
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

        mode = getattr(self, 'histogram_mode', 'window')
        if mode == 'pan':
            self.histogram_dragging_line = 'pan'
            self.histogram_pan_last_x = float(event.xdata)
            return
        if mode == 'zoom':
            self.histogram_dragging_line = 'zoom'
            self.histogram_zoom_anchor_x = float(event.xdata)
            self.histogram_pan_last_x = float(event.xdata)
            return

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
        if self.histogram_dragging_line in ('left', 'right'):
            self._apply_window_from_histogram_lines(update_views=True)

        if self.histogram_dragging_line:
            self.histogram_dragging_line = None
            self.histogram_pan_last_x = None
            self.histogram_zoom_anchor_x = None
            # 重绘以清除临时标签
            self._redraw_histogram_lines()
    
    def on_histogram_mouse_move(self, event):
        """处理直方图的鼠标移动事件"""
        if event.inaxes != self.histogram_ax or event.xdata is None:
            return

        if self.histogram_dragging_line in ('pan', 'zoom'):
            if self.histogram_pan_last_x is None:
                self.histogram_pan_last_x = float(event.xdata)
                return

            last_x = float(self.histogram_pan_last_x)
            curr_x = float(event.xdata)
            self.histogram_pan_last_x = curr_x

            x0, x1 = self.histogram_ax.get_xlim()
            data_min, data_max = self.histogram_data_range

            if self.histogram_dragging_line == 'pan':
                delta = curr_x - last_x
                new_min = x0 - delta
                new_max = x1 - delta
                view_width = x1 - x0
                if new_min < data_min:
                    new_min = data_min
                    new_max = data_min + view_width
                if new_max > data_max:
                    new_max = data_max
                    new_min = data_max - view_width
                if new_max > new_min:
                    self.histogram_ax.set_xlim(new_min, new_max)
                    self.histogram_plot_range = (new_min, new_max)
                    self._update_histogram_control_values()
                    self.histogram_canvas.draw_idle()
                return

            if self.histogram_dragging_line == 'zoom':
                anchor = self.histogram_zoom_anchor_x if self.histogram_zoom_anchor_x is not None else (x0 + x1) * 0.5
                delta = curr_x - last_x
                zoom_factor = 1.0 - (delta * 0.01)
                zoom_factor = max(0.85, min(1.15, zoom_factor))

                left_span = (anchor - x0) * zoom_factor
                right_span = (x1 - anchor) * zoom_factor
                new_min = anchor - left_span
                new_max = anchor + right_span

                min_width = max((data_max - data_min) * 0.005, 1.0)
                if new_max - new_min < min_width:
                    center = 0.5 * (new_min + new_max)
                    new_min = center - min_width * 0.5
                    new_max = center + min_width * 0.5

                if new_min < data_min:
                    shift = data_min - new_min
                    new_min += shift
                    new_max += shift
                if new_max > data_max:
                    shift = new_max - data_max
                    new_min -= shift
                    new_max -= shift

                new_min = max(data_min, new_min)
                new_max = min(data_max, new_max)
                if new_max > new_min:
                    self.histogram_ax.set_xlim(new_min, new_max)
                    self.histogram_plot_range = (new_min, new_max)
                    self._update_histogram_control_values()
                    self.histogram_canvas.draw_idle()
                return

        # 如果正在拖动窗阈值线段
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
            self._apply_window_from_histogram_lines(update_views=True)
            self._update_histogram_control_values()
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

    def set_histogram_interaction_mode(self, mode):
        """设置直方图交互模式：window / pan / zoom"""
        self.histogram_mode = mode
        if hasattr(self, 'hist_mode_window_btn'):
            self.hist_mode_window_btn.setChecked(mode == 'window')
        if hasattr(self, 'hist_mode_pan_btn'):
            self.hist_mode_pan_btn.setChecked(mode == 'pan')
        if hasattr(self, 'hist_mode_zoom_btn'):
            self.hist_mode_zoom_btn.setChecked(mode == 'zoom')

    def on_histogram_log_toggled(self, checked):
        """切换Log Y显示"""
        self.histogram_log_y = bool(checked)
        if self.histogram_current_data is not None:
            self.update_histogram(self.histogram_current_data)

    def on_histogram_bin_width_changed(self, value):
        """修改直方图bin宽"""
        self.histogram_bin_width = max(1, int(value))
        if self.histogram_current_data is not None:
            self.update_histogram(self.histogram_current_data)

    def on_histogram_window_edit_finished(self):
        """从输入框应用窗阈值线位置"""
        if not self.histogram_left_line or not self.histogram_right_line:
            return
        try:
            left_val = float(self.histogram_window_min_edit.text())
            right_val = float(self.histogram_window_max_edit.text())
        except (TypeError, ValueError):
            self._update_histogram_control_values()
            return

        data_min, data_max = self.histogram_data_range
        left_val = max(data_min, min(data_max, left_val))
        right_val = max(data_min, min(data_max, right_val))
        if right_val <= left_val:
            right_val = min(data_max, left_val + max((data_max - data_min) * 0.002, 1.0))

        self.histogram_left_line.set_xdata([left_val, left_val])
        self.histogram_right_line.set_xdata([right_val, right_val])
        self._apply_window_from_histogram_lines(update_views=True)
        self._update_histogram_control_values()
        self.histogram_canvas.draw_idle()

    def on_histogram_apply_clicked(self):
        """应用高级绘图范围输入"""
        if not hasattr(self, 'histogram_plot_min_edit'):
            return
        try:
            plot_min = float(self.histogram_plot_min_edit.text())
            plot_max = float(self.histogram_plot_max_edit.text())
        except (TypeError, ValueError):
            self._update_histogram_control_values()
            return

        self._set_histogram_plot_range(plot_min, plot_max)
        self.histogram_canvas.draw_idle()

    def on_histogram_reset_clicked(self):
        """重置高级绘图范围并回到窗口模式"""
        data_min, data_max = self.histogram_data_range
        self._set_histogram_plot_range(data_min, data_max)
        self.set_histogram_interaction_mode('window')
        self._sync_histogram_lines_to_window_level()
        self.histogram_canvas.draw_idle()

    def on_histogram_home_clicked(self):
        """直方图Home按钮：复位显示范围"""
        data_min, data_max = self.histogram_data_range
        self._set_histogram_plot_range(data_min, data_max)
        self.histogram_canvas.draw_idle()

    def on_histogram_scroll(self, event):
        """滚轮缩放直方图X轴范围"""
        if event.inaxes != self.histogram_ax or event.xdata is None:
            return

        x0, x1 = self.histogram_ax.get_xlim()
        data_min, data_max = self.histogram_data_range
        center = float(event.xdata)
        factor = 0.9 if event.step > 0 else 1.1

        left_span = (center - x0) * factor
        right_span = (x1 - center) * factor
        new_min = center - left_span
        new_max = center + right_span

        min_width = max((data_max - data_min) * 0.005, 1.0)
        if new_max - new_min < min_width:
            half = min_width * 0.5
            new_min = center - half
            new_max = center + half

        if new_min < data_min:
            shift = data_min - new_min
            new_min += shift
            new_max += shift
        if new_max > data_max:
            shift = new_max - data_max
            new_min -= shift
            new_max -= shift

        new_min = max(data_min, new_min)
        new_max = min(data_max, new_max)
        if new_max > new_min:
            self._set_histogram_plot_range(new_min, new_max)
            self.histogram_canvas.draw_idle()

    def _set_histogram_plot_range(self, plot_min, plot_max):
        """设置直方图X轴显示范围"""
        data_min, data_max = self.histogram_data_range
        plot_min = max(data_min, float(plot_min))
        plot_max = min(data_max, float(plot_max))
        if plot_max <= plot_min:
            return
        self.histogram_ax.set_xlim(plot_min, plot_max)
        self.histogram_plot_range = (plot_min, plot_max)
        self._update_histogram_control_values()

    def _apply_window_from_histogram_lines(self, update_views=True):
        """根据直方图左右线反算窗宽窗位并同步到滑条"""
        if not self.histogram_left_line or not self.histogram_right_line:
            return
        if not hasattr(self, 'ww_slider') or not hasattr(self, 'wl_slider'):
            return

        left_val = float(self.histogram_left_line.get_xdata()[0])
        right_val = float(self.histogram_right_line.get_xdata()[0])
        if right_val <= left_val:
            return

        width_val = right_val - left_val
        level_val = (right_val + left_val) * 0.5

        ww_min, ww_max = self.ww_slider.minimum(), self.ww_slider.maximum()
        wl_min, wl_max = self.wl_slider.minimum(), self.wl_slider.maximum()
        width_int = int(round(max(ww_min, min(ww_max, width_val))))
        level_int = int(round(max(wl_min, min(wl_max, level_val))))

        self._syncing_histogram_window = True
        try:
            self.ww_slider.blockSignals(True)
            self.wl_slider.blockSignals(True)
            self.ww_slider.setValue(width_int)
            self.wl_slider.setValue(level_int)
        finally:
            self.ww_slider.blockSignals(False)
            self.wl_slider.blockSignals(False)
            self._syncing_histogram_window = False

        self.window_width = width_int
        self.window_level = level_int
        if hasattr(self, 'ww_value'):
            self.ww_value.setText(str(int(self.window_width)))
        if hasattr(self, 'wl_value'):
            self.wl_value.setText(str(int(self.window_level)))
        if hasattr(self, 'prop_window_label'):
            self.prop_window_label.setText(f"窗宽: {int(self.window_width)}, 窗位: {int(self.window_level)}")
        if update_views and hasattr(self, 'update_all_views'):
            self.update_all_views()

    def _sync_histogram_lines_to_window_level(self):
        """根据当前窗宽窗位更新直方图左右线位置"""
        if not self.histogram_left_line or not self.histogram_right_line:
            return

        data_min, data_max = self.histogram_data_range
        left_val = float(self.window_level - self.window_width / 2.0)
        right_val = float(self.window_level + self.window_width / 2.0)
        left_val = max(data_min, min(data_max, left_val))
        right_val = max(data_min, min(data_max, right_val))
        if right_val <= left_val:
            right_val = min(data_max, left_val + max((data_max - data_min) * 0.002, 1.0))

        self.histogram_left_line.set_xdata([left_val, left_val])
        self.histogram_right_line.set_xdata([right_val, right_val])
        self._update_histogram_control_values()

    def _update_histogram_control_values(self):
        """刷新直方图控制区输入框"""
        if self.histogram_left_line and hasattr(self, 'histogram_window_min_edit'):
            left_val = float(self.histogram_left_line.get_xdata()[0])
            self.histogram_window_min_edit.setText(f"{left_val:.2f}")
        if self.histogram_right_line and hasattr(self, 'histogram_window_max_edit'):
            right_val = float(self.histogram_right_line.get_xdata()[0])
            self.histogram_window_max_edit.setText(f"{right_val:.2f}")

        if hasattr(self, 'histogram_plot_min_edit') and hasattr(self.histogram_ax, 'get_xlim'):
            x0, x1 = self.histogram_ax.get_xlim()
            self.histogram_plot_min_edit.setText(f"{x0:.2f}")
            self.histogram_plot_max_edit.setText(f"{x1:.2f}")

    def on_window_level_interact_toggled(self, checked):
        """窗口级别拖拽模式开关"""
        self.window_level_drag_mode = bool(checked)
        if checked and hasattr(self, 'roi_mode') and self.roi_mode == 'selection' and hasattr(self, 'exit_roi_mode'):
            self.exit_roi_mode()
        if checked and hasattr(self, 'window_level_roi_btn') and self.window_level_roi_btn.isChecked():
            self.window_level_roi_btn.blockSignals(True)
            self.window_level_roi_btn.setChecked(False)
            self.window_level_roi_btn.blockSignals(False)
            self.window_level_roi_mode = False

        if hasattr(self, 'statusBar'):
            if self.window_level_drag_mode:
                self.statusBar().showMessage("窗口级别模式：在任意2D视图左键拖拽，上下调整窗位，左右调整窗宽")
            else:
                self.statusBar().showMessage("窗口级别模式已关闭", 2000)

    def on_window_level_roi_toggled(self, checked):
        """区域自动窗调平模式开关"""
        self.window_level_roi_mode = bool(checked)
        if checked and hasattr(self, 'roi_mode') and self.roi_mode == 'selection' and hasattr(self, 'exit_roi_mode'):
            self.exit_roi_mode()
        if checked and hasattr(self, 'window_level_interact_btn') and self.window_level_interact_btn.isChecked():
            self.window_level_interact_btn.blockSignals(True)
            self.window_level_interact_btn.setChecked(False)
            self.window_level_interact_btn.blockSignals(False)
            self.window_level_drag_mode = False

        if not checked:
            for viewer_name in ('axial_viewer', 'sag_viewer', 'cor_viewer'):
                viewer = getattr(self, viewer_name, None)
                if viewer is not None and hasattr(viewer, '_clear_window_level_roi_rect'):
                    viewer._clear_window_level_roi_rect()
                    viewer._wl_roi_selecting = False
                    viewer._wl_roi_start = None

        if hasattr(self, 'statusBar'):
            if self.window_level_roi_mode:
                self.statusBar().showMessage("区域自动窗调平：在任意2D视图左键拖动框选ROI，松开后自动应用")
            else:
                self.statusBar().showMessage("区域自动窗调平已关闭", 2000)

    def toggle_move_tool(self, checked):
        """切换移动工具（2D视图左键平移、右键旋转）"""
        self.move_tool_enabled = bool(checked)
        if checked:
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage("移动工具已启用：左键平移，右键旋转")
        else:
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage("移动工具已关闭", 2000)

    def undo_move_tool(self):
        """撤销当前活动视图的移动变换"""
        viewer_map = {
            'axial': getattr(self, 'axial_viewer', None),
            'sagittal': getattr(self, 'sag_viewer', None),
            'coronal': getattr(self, 'cor_viewer', None)
        }
        active = getattr(self, 'active_view', 'axial')
        viewer = viewer_map.get(active)
        if viewer is not None and hasattr(viewer, 'undo_move_transform'):
            viewer.undo_move_transform()
            if hasattr(self, 'statusBar'):
                active_label = {
                    'axial': '轴位',
                    'sagittal': '矢状位',
                    'coronal': '冠状位'
                }.get(active, active)
                self.statusBar().showMessage(f"已撤销 {active_label} 视图上一步移动操作", 2000)
    
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
        每条数据对应一个带小眼睛按钮的行
        
        参数
        ----
        data_name : str
            数据的显示名称
        data_item : dict
            数据项，包含image, array, spacing等信息
        """
        previous_item = self.data_list_widget.currentItem() if hasattr(self, 'data_list_widget') else None

        # 创建新列表项
        display_name = data_name
        data_type = data_item.get('data_type', 'image') if isinstance(data_item, dict) else 'image'
        if data_type == 'label' and isinstance(data_item, dict):
            if 'label_color' not in data_item:
                palette = [
                    (255, 90, 90),
                    (90, 220, 120),
                    (80, 170, 255),
                    (255, 210, 70),
                    (220, 120, 255),
                    (100, 230, 230),
                ]
                idx = getattr(self, '_label_color_index', 0)
                data_item['label_color'] = palette[idx % len(palette)]
                self._label_color_index = idx + 1
        if data_type == 'label' and '[标签]' not in display_name:
            display_name = f"{display_name} [标签]"

        list_item = QtWidgets.QListWidgetItem(display_name)
        list_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        
        # 将数据信息存储到item中
        list_item.setData(QtCore.Qt.UserRole, data_item)
        list_item.setData(QtCore.Qt.UserRole + 1, True)  # visible
        
        # 添加到列表
        self.data_list_widget.addItem(list_item)
        item_widget = self._build_dataset_list_item_widget(list_item, display_name)
        list_item.setSizeHint(item_widget.sizeHint())
        self.data_list_widget.setItemWidget(list_item, item_widget)

        if data_type == 'label':
            if previous_item is not None:
                self.data_list_widget.setCurrentItem(previous_item)
            else:
                self.data_list_widget.setCurrentItem(list_item)
        else:
            self.data_list_widget.setCurrentItem(list_item)
            self.switch_to_data(data_item, display_name)
        
        print(f"数据已添加到列表: {display_name} (已自动显示)")
    
    def _build_dataset_list_item_widget(self, item, data_name):
        row_widget = QtWidgets.QWidget()
        row_layout = QtWidgets.QHBoxLayout(row_widget)
        row_layout.setContentsMargins(4, 2, 4, 2)
        row_layout.setSpacing(6)

        eye_btn = QtWidgets.QToolButton(row_widget)
        eye_btn.setFixedWidth(24)
        eye_btn.clicked.connect(lambda _, list_item=item: self._toggle_dataset_item_visibility(list_item))
        row_layout.addWidget(eye_btn)

        name_label = QtWidgets.QLabel(data_name, row_widget)
        name_label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)

        data_item = item.data(QtCore.Qt.UserRole)
        if isinstance(data_item, dict) and data_item.get('data_type') == 'label':
            label_color = data_item.get('label_color', (255, 128, 64))
            name_label.setStyleSheet(
                f"color: rgb({int(label_color[0])}, {int(label_color[1])}, {int(label_color[2])}); font-weight: bold;"
            )
        row_layout.addWidget(name_label, 1)

        item.setData(QtCore.Qt.UserRole + 2, eye_btn)
        item.setData(QtCore.Qt.UserRole + 3, name_label)
        self._refresh_dataset_item_eye(item)
        return row_widget

    def _refresh_dataset_item_eye(self, item):
        eye_btn = item.data(QtCore.Qt.UserRole + 2)
        if eye_btn is None:
            return
        visible = bool(item.data(QtCore.Qt.UserRole + 1))
        eye_btn.setText("👁" if visible else "○")
        eye_btn.setToolTip("隐藏数据" if visible else "显示数据")

    def on_data_selection_changed(self, current, previous):
        """
        当数据项选中行变化时切换显示
        
        参数
        ----
        current : QListWidgetItem
            当前选中的列表项
        previous : QListWidgetItem
            之前选中的列表项
        """
        if current is None:
            return
        if not bool(current.data(QtCore.Qt.UserRole + 1)):
            return
        data_item = current.data(QtCore.Qt.UserRole)
        if data_item is None:
            return
        self.switch_to_data(data_item, current.text())
        print(f"切换到数据: {current.text()}")

    def _on_2d_setting_changed(self, *_):
        self.apply_2d_settings_to_viewers(refresh_slices=True)

    def _on_sync_slices_toggled(self, checked):
        if checked:
            self._slice_positions_before_sync = {
                'axial': getattr(getattr(self, 'axial_viewer', None), 'slider', None).value() if getattr(self, 'axial_viewer', None) else None,
                'sagittal': getattr(getattr(self, 'sag_viewer', None), 'slider', None).value() if getattr(self, 'sag_viewer', None) else None,
                'coronal': getattr(getattr(self, 'cor_viewer', None), 'slider', None).value() if getattr(self, 'cor_viewer', None) else None,
            }
        self._setup_slice_sync_connections()
        if checked:
            self._sync_other_slices_from('axial', getattr(getattr(self, 'axial_viewer', None), 'slider', None).value() if getattr(self, 'axial_viewer', None) else 0)
        else:
            old_pos = getattr(self, '_slice_positions_before_sync', None)
            if isinstance(old_pos, dict):
                self._syncing_slice_sliders = True
                try:
                    mapping = {
                        'axial': getattr(self, 'axial_viewer', None),
                        'sagittal': getattr(self, 'sag_viewer', None),
                        'coronal': getattr(self, 'cor_viewer', None),
                    }
                    for key, viewer in mapping.items():
                        if viewer is None or not hasattr(viewer, 'slider'):
                            continue
                        value = old_pos.get(key, None)
                        if value is None:
                            continue
                        viewer.slider.setValue(max(0, min(viewer.max_index - 1, int(value))))
                finally:
                    self._syncing_slice_sliders = False

    def _setup_slice_sync_connections(self):
        viewers = {
            'axial': getattr(self, 'axial_viewer', None),
            'sagittal': getattr(self, 'sag_viewer', None),
            'coronal': getattr(self, 'cor_viewer', None),
        }
        for name, viewer in viewers.items():
            if viewer is None or not hasattr(viewer, 'slider'):
                continue
            try:
                while True:
                    if name == 'axial':
                        viewer.slider.valueChanged.disconnect(self._on_axial_slice_changed)
                    elif name == 'sagittal':
                        viewer.slider.valueChanged.disconnect(self._on_sagittal_slice_changed)
                    else:
                        viewer.slider.valueChanged.disconnect(self._on_coronal_slice_changed)
            except Exception:
                pass

            if hasattr(self, 'chk_sync_views') and self.chk_sync_views.isChecked():
                if name == 'axial':
                    viewer.slider.valueChanged.connect(self._on_axial_slice_changed)
                elif name == 'sagittal':
                    viewer.slider.valueChanged.connect(self._on_sagittal_slice_changed)
                else:
                    viewer.slider.valueChanged.connect(self._on_coronal_slice_changed)

    def _on_axial_slice_changed(self, value):
        self._sync_other_slices_from('axial', value)

    def _on_sagittal_slice_changed(self, value):
        self._sync_other_slices_from('sagittal', value)

    def _on_coronal_slice_changed(self, value):
        self._sync_other_slices_from('coronal', value)

    def _sync_other_slices_from(self, source_name, source_value):
        if not hasattr(self, 'chk_sync_views') or not self.chk_sync_views.isChecked():
            return
        if getattr(self, '_syncing_slice_sliders', False):
            return

        viewer_map = {
            'axial': getattr(self, 'axial_viewer', None),
            'sagittal': getattr(self, 'sag_viewer', None),
            'coronal': getattr(self, 'cor_viewer', None),
        }
        source_viewer = viewer_map.get(source_name)
        if source_viewer is None or source_viewer.max_index <= 1:
            return

        ratio = float(source_value) / float(max(1, source_viewer.max_index - 1))

        self._syncing_slice_sliders = True
        try:
            for name, viewer in viewer_map.items():
                if name == source_name or viewer is None or not hasattr(viewer, 'slider'):
                    continue
                target = int(round(ratio * max(1, viewer.max_index - 1)))
                target = max(0, min(viewer.max_index - 1, target))
                if viewer.slider.value() != target:
                    viewer.slider.setValue(target)
        finally:
            self._syncing_slice_sliders = False

    def apply_2d_settings_to_viewers(self, refresh_slices=True):
        viewers = [
            getattr(self, 'axial_viewer', None),
            getattr(self, 'sag_viewer', None),
            getattr(self, 'cor_viewer', None),
        ]
        alpha_value = self.alpha_slider_2d.value() if hasattr(self, 'alpha_slider_2d') else 100
        overlay_visible = self.chk_show_overlay.isChecked() if hasattr(self, 'chk_show_overlay') else True
        interpolation_enabled = self.chk_enable_interpolation.isChecked() if hasattr(self, 'chk_enable_interpolation') else True
        interpolation_mode = self.interp_2d_combo.currentText() if hasattr(self, 'interp_2d_combo') else "线性"

        for viewer in viewers:
            if viewer is None:
                continue
            if hasattr(viewer, 'set_slice_opacity'):
                viewer.set_slice_opacity(alpha_value)
            if hasattr(viewer, 'set_overlay_visible'):
                viewer.set_overlay_visible(overlay_visible)
            if hasattr(viewer, 'set_interpolation_settings'):
                viewer.set_interpolation_settings(interpolation_enabled, interpolation_mode)

            if refresh_slices and hasattr(viewer, 'slider'):
                viewer.update_slice(viewer.slider.value())

    def _on_2d_viewers_created(self):
        self._setup_slice_sync_connections()
        self.apply_2d_settings_to_viewers(refresh_slices=True)
    
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

            if data_item.get('data_type') == 'label':
                self.annotation_volume = self.array.astype(np.uint16).copy()
                if 'annotation_drawn_mask' in data_item and data_item.get('annotation_drawn_mask') is not None:
                    self.annotation_drawn_mask = data_item['annotation_drawn_mask'].copy()
                else:
                    self.annotation_drawn_mask = self.array > 0
                if 'label_color' in data_item:
                    self.annotation_overlay_color = tuple(data_item['label_color'])
                if 'label_color_map' in data_item and isinstance(data_item['label_color_map'], dict):
                    self.annotation_label_colors = {
                        int(k): tuple(v) for k, v in data_item['label_color_map'].items()
                    }

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
                self.prop_format_label.setText("体数据")
            if hasattr(self, '_update_basic_properties_table'):
                self._update_basic_properties_table()

            if data_item.get('data_type') == 'label' and hasattr(self, 'status_label'):
                info = data_item.get('label_info', '')
                if info:
                    self.status_label.setText(f"标签数据: {info}")
            
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
                    self.volume_viewer.set_background_color((0.08, 0.08, 0.10))
                if hasattr(self, 'apply_current_3d_controls'):
                    self.apply_current_3d_controls()
                
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
                info_label = QtWidgets.QLabel("三维视图不可用\n(数据全为0)")
                info_label.setAlignment(QtCore.Qt.AlignCenter)
                info_label.setStyleSheet("QLabel { background-color: #151515; border: 1px solid #3f3f3f; color: #d0d0d0; font-size: 14pt; }")
                self.grid_layout.addWidget(info_label, 0, 0)

            if hasattr(self, '_on_2d_viewers_created'):
                self._on_2d_viewers_created()

            self.active_view = 'axial'
            
            # 更新窗口标题
            self.setWindowTitle(f"工业CT智能软件 - {data_name}")
            
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
                self.prop_window_label.setText(f"窗宽: {int(self.window_width)}, 窗位: {int(self.window_level)}")
            
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
        deleting_current = (self.data_list_widget.currentItem() is current_item)

        reply = QtWidgets.QMessageBox.question(
            self, '确认删除',
            f'确定要删除数据 "{data_name}" 吗？',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        row = self.data_list_widget.row(current_item)

        # 删除项
        self.data_list_widget.takeItem(row)
        print(f"已删除数据: {data_name}")

        remaining = self.data_list_widget.count()

        if remaining > 0 and deleting_current:
            # 删除的是当前显示的数据 → 自动切换到第一个
            first_item = self.data_list_widget.item(0)
            self.data_list_widget.setCurrentItem(first_item)
            data_item = first_item.data(QtCore.Qt.UserRole)
            self.switch_to_data(data_item, first_item.text())
        else:
            # 列表已空 → 清理全部状态
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

        self.data_list_widget.clear()
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
            self.prop_window_label.setText("窗宽: -, 窗位: -")
        if hasattr(self, '_update_basic_properties_table'):
            self._update_basic_properties_table()

        print("所有数据已移除，状态已重置")

    # ---------------------- 主界面动作方法（新增） ----------------------
    def start_new_session(self):
        self.clear_all_data()
        self.statusBar().showMessage("已创建新会话", 3000)

    def open_preferences(self):
        QtWidgets.QMessageBox.information(self, "首选项", "首选项面板将用于配置快捷键、主题与默认路径。")

    def save_current_session(self):
        """保存当前会话到文件"""
        from .save_export import SessionManager
        
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "保存会话",
            "session.ctsession",
            "CT会话文件 (*.ctsession);;所有文件 (*)"
        )
        if not filepath:
            return
        
        if not filepath.endswith('.ctsession'):
            filepath += '.ctsession'
        
        # 询问是否包含数据
        include_data = QtWidgets.QMessageBox.question(
            self,
            "保存选项",
            "是否保存原始数据？\n\n选择'是'将保存完整数据（文件较大）。\n选择'否'仅保存视图状态。",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.Yes
        ) == QtWidgets.QMessageBox.Yes
        
        progress = QtWidgets.QProgressDialog("正在保存会话...", None, 0, 0, self)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.show()
        QtWidgets.QApplication.processEvents()
        
        success = SessionManager.save_session(self, filepath, include_data=include_data)
        
        progress.close()
        
        if success:
            self.statusBar().showMessage(f"会话已保存: {filepath}", 3000)
        else:
            QtWidgets.QMessageBox.critical(self, "保存失败", "保存会话时发生错误")
    
    def load_session(self):
        """加载会话文件"""
        from .save_export import SessionManager
        
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "加载会话",
            "",
            "CT会话文件 (*.ctsession);;所有文件 (*)"
        )
        if not filepath:
            return
        
        progress = QtWidgets.QProgressDialog("正在加载会话...", None, 0, 0, self)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.show()
        QtWidgets.QApplication.processEvents()
        
        success, msg = SessionManager.load_session(self, filepath)
        
        progress.close()
        
        if success:
            self.statusBar().showMessage(msg, 3000)
        else:
            QtWidgets.QMessageBox.critical(self, "加载失败", msg)

    def import_dicom_series(self):
        self.import_file()

    def export_dicom_series(self):
        """导出当前数据为DICOM序列"""
        from .save_export import ExportDialogs
        
        # 获取当前数据
        arr = None
        if hasattr(self, 'data_list_widget') and self.data_list_widget is not None:
            current_item = self.data_list_widget.currentItem()
            if current_item is not None:
                data_item = current_item.data(QtCore.Qt.UserRole)
                if isinstance(data_item, dict) and 'array' in data_item:
                    arr = data_item['array']
        
        if arr is None and hasattr(self, 'raw_array') and self.raw_array is not None:
            arr = self.raw_array
        
        if arr is None:
            QtWidgets.QMessageBox.warning(self, "导出失败", "没有可用的数据来导出")
            return
        
        spacing = getattr(self, 'spacing', None)
        ExportDialogs.show_dicom_export_dialog(self, arr, spacing)
    
    def export_raw_mhd(self):
        """导出当前数据为RAW/MHD格式"""
        from .save_export import ExportDialogs
        
        # 获取当前数据
        arr = None
        if hasattr(self, 'data_list_widget') and self.data_list_widget is not None:
            current_item = self.data_list_widget.currentItem()
            if current_item is not None:
                data_item = current_item.data(QtCore.Qt.UserRole)
                if isinstance(data_item, dict) and 'array' in data_item:
                    arr = data_item['array']
        
        if arr is None and hasattr(self, 'raw_array') and self.raw_array is not None:
            arr = self.raw_array
        
        if arr is None:
            QtWidgets.QMessageBox.warning(self, "导出失败", "没有可用的数据来导出")
            return
        
        spacing = getattr(self, 'spacing', None)
        ExportDialogs.show_raw_mhd_export_dialog(self, arr, spacing)
    
    def export_slices_as_images(self):
        """导出切片为图片序列（PNG/JPEG/TIFF/BMP）"""
        from .save_export import ExportDialogs
        
        # 获取当前数据
        arr = None
        if hasattr(self, 'data_list_widget') and self.data_list_widget is not None:
            current_item = self.data_list_widget.currentItem()
            if current_item is not None:
                data_item = current_item.data(QtCore.Qt.UserRole)
                if isinstance(data_item, dict) and 'array' in data_item:
                    arr = data_item['array']
        
        if arr is None and hasattr(self, 'raw_array') and self.raw_array is not None:
            arr = self.raw_array
        
        if arr is None:
            QtWidgets.QMessageBox.warning(self, "导出失败", "没有可用的数据来导出")
            return
        
        ww = getattr(self, 'window_width', None)
        wc = getattr(self, 'window_center', None)
        ExportDialogs.show_image_export_dialog(self, arr, ww, wc)

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

    def _ensure_sam_prompt_state(self):
        if not hasattr(self, 'sam_prompt_state') or not isinstance(self.sam_prompt_state, dict):
            self.sam_prompt_state = {'point': None, 'box': None}
        else:
            if 'point' not in self.sam_prompt_state:
                self.sam_prompt_state['point'] = None
            if 'box' not in self.sam_prompt_state:
                self.sam_prompt_state['box'] = None
        if not hasattr(self, 'sam_prompt_mode'):
            self.sam_prompt_mode = None

    def start_sam_point_prompt(self):
        if not self._prepare_annotation_environment():
            return
        self._ensure_sam_prompt_state()
        self.sam_prompt_mode = 'point'
        self.annotation_enabled = False
        if getattr(self, 'roi_mode', None) == 'selection' and hasattr(self, 'exit_roi_mode'):
            self.exit_roi_mode()
        self.statusBar().showMessage("SAM点提示采集已启用：在任意切片视图 Ctrl+左键单击 即可触发单切片分割", 3500)

    def start_sam_box_prompt(self):
        if not self._prepare_annotation_environment():
            return
        self._ensure_sam_prompt_state()
        self.sam_prompt_mode = 'box'
        self.annotation_enabled = False
        if hasattr(self, 'roi_mode') and self.roi_mode == 'selection':
            self.statusBar().showMessage("SAM框提示采集中：请在轴位视图拖拽ROI框，完成后自动分割", 3500)
            return
        if hasattr(self, 'roi_selection_start'):
            self.roi_selection_start()
        self.statusBar().showMessage("SAM框提示采集已启用：请在轴位视图拖拽ROI框，完成后自动分割", 3500)

    def clear_sam_prompt(self):
        self._ensure_sam_prompt_state()
        self.sam_prompt_state['point'] = None
        self.sam_prompt_state['box'] = None
        self.sam_prompt_mode = None
        for viewer_name in ["axial_viewer", "cor_viewer", "sag_viewer"]:
            viewer = getattr(self, viewer_name, None)
            if viewer is not None and hasattr(viewer, 'clear_sam_prompt_marks'):
                viewer.clear_sam_prompt_marks('all')
        self.statusBar().showMessage("SAM提示已清除", 2000)

    def set_sam_point_prompt(self, view_type, z, y, x, point_label=1):
        self._ensure_sam_prompt_state()
        view_type_str = str(view_type)

        # 根据视图类型确定正确的切片轴索引
        # axial  : slice沿Z轴, 2D图像=(Y,X), scene(px,py)→point_xy=(x,y)
        # coronal: slice沿Y轴, 2D图像=(Z,X), scene(px,py)→point_xy=(x,z)
        # sagittal:slice沿X轴, 2D图像=(Z,Y), scene(px,py)→point_xy=(y,z)
        # _scene_to_voxel: axial→(z=slice,y=py,x=px)
        #                  coronal→(z=py,y=slice,x=px)
        #                  sagittal→(z=py,y=px,x=slice)
        if view_type_str == 'coronal':
            proper_slice_index = int(y)       # Y 轴切片索引
            point_xy_2d = (int(x), int(z))    # (px, py) in coronal image (Z×X)
        elif view_type_str == 'sagittal':
            proper_slice_index = int(x)       # X 轴切片索引
            point_xy_2d = (int(y), int(z))    # (px, py) in sagittal image (Z×Y)
        else:  # axial (default)
            proper_slice_index = int(z)
            point_xy_2d = (int(x), int(y))

        self.sam_prompt_state['point'] = {
            'view_type': view_type_str,
            'slice_index': proper_slice_index,
            'x': int(x),
            'y': int(y),
            'z': int(z),
            'point_label': int(point_label),
        }

        self.statusBar().showMessage(
            f"SAM点提示已设置：{view_type_str}切片={proper_slice_index}, 点={point_xy_2d}，正在快速分割...",
            3000,
        )

        if hasattr(self, 'run_sam_prompt_quick'):
            self.run_sam_prompt_quick(
                prompt_type='point',
                view_type=view_type_str,
                slice_index=proper_slice_index,
                point_xy=point_xy_2d,
                point_label=int(point_label),
                box_xyxy=None,
            )

    def on_sam_box_prompt_from_roi(self, view_type, rect, slice_index):
        self._ensure_sam_prompt_state()
        if self.sam_prompt_mode != 'box':
            return

        if str(view_type) != 'axial':
            self.statusBar().showMessage("SAM框提示当前仅支持轴位视图ROI，请在Axial视图拖拽。", 3500)
            return

        x1 = int(round(rect.left()))
        y1 = int(round(rect.top()))
        x2 = int(round(rect.right()))
        y2 = int(round(rect.bottom()))

        if x2 <= x1 or y2 <= y1:
            self.statusBar().showMessage("SAM框提示无效：请重新拖拽有效矩形框。", 2500)
            return

        self.sam_prompt_state['box'] = {
            'view_type': 'axial',
            'slice_index': int(slice_index),
            'x1': x1,
            'y1': y1,
            'x2': x2,
            'y2': y2,
        }

        axial_viewer = getattr(self, 'axial_viewer', None)
        if axial_viewer is not None and hasattr(axial_viewer, 'mark_sam_box_prompt'):
            axial_viewer.mark_sam_box_prompt(rect, int(slice_index))

        self.sam_prompt_mode = None
        self.statusBar().showMessage(
            f"SAM框提示已设置：Z={int(slice_index)}, 框=({x1},{y1},{x2},{y2})，正在快速分割...",
            3500,
        )
        if hasattr(self, 'exit_roi_mode'):
            self.exit_roi_mode()

        if hasattr(self, 'run_sam_prompt_quick'):
            self.run_sam_prompt_quick(
                prompt_type='box',
                slice_index=int(slice_index),
                point_xy=None,
                point_label=1,
                box_xyxy=(x1, y1, x2, y2),
            )

    def get_sam_prompt_state(self):
        self._ensure_sam_prompt_state()
        point = self.sam_prompt_state.get('point')
        box = self.sam_prompt_state.get('box')
        return {
            'point': dict(point) if isinstance(point, dict) else None,
            'box': dict(box) if isinstance(box, dict) else None,
        }

    def start_brush_annotation(self):
        if not self._prepare_annotation_environment():
            return
        self.annotation_enabled = True
        self.annotation_mode = 'brush'
        current_label = self.get_current_annotation_label()
        self.annotation_overlay_color = self.get_annotation_label_color(current_label)
        self.statusBar().showMessage(
            f"画笔标注已启用（标签={current_label}，半径={self.get_current_annotation_radius()}）",
            2500,
        )

    def start_eraser_annotation(self):
        if not self._prepare_annotation_environment():
            return
        self.annotation_enabled = True
        self.annotation_mode = 'eraser'
        self.statusBar().showMessage("橡皮擦已启用（按住左键擦除）", 2500)

    def _prepare_annotation_environment(self):
        if not hasattr(self, 'array') or self.array is None:
            QtWidgets.QMessageBox.warning(self, "数据不可用", "请先加载CT数据后再进行标注。")
            return False

        if len(self.array.shape) != 3:
            QtWidgets.QMessageBox.warning(self, "数据不可用", "当前数据不是3D灰度体数据，暂不支持手工标注。")
            return False

        if not hasattr(self, 'annotation_volume') or self.annotation_volume is None or self.annotation_volume.shape != self.array.shape:
            self.annotation_volume = np.zeros(self.array.shape, dtype=np.uint16)
        if not hasattr(self, 'annotation_drawn_mask') or self.annotation_drawn_mask is None or self.annotation_drawn_mask.shape != self.array.shape:
            self.annotation_drawn_mask = np.zeros(self.array.shape, dtype=bool)

        if not hasattr(self, 'annotation_overlay_color'):
            self.annotation_overlay_color = (255, 60, 60)
        if not hasattr(self, 'annotation_overlay_alpha'):
            self.annotation_overlay_alpha = 110
        if not hasattr(self, 'annotation_mode'):
            self.annotation_mode = 'brush'
        if not hasattr(self, 'annotation_label_colors'):
            self.annotation_label_colors = {}
        if not hasattr(self, '_annotation_color_palette'):
            self._annotation_color_palette = [
                (255, 90, 90),
                (80, 200, 120),
                (90, 160, 255),
                (255, 210, 70),
                (220, 120, 255),
                (100, 230, 230),
                (255, 150, 70),
                (180, 255, 120),
            ]

        return True

    def get_annotation_label_color(self, label_value):
        if not self._prepare_annotation_environment():
            return (255, 60, 60)
        label_value = int(label_value)
        if label_value <= 0:
            return (0, 0, 0)
        if label_value not in self.annotation_label_colors:
            palette = self._annotation_color_palette
            self.annotation_label_colors[label_value] = palette[(label_value - 1) % len(palette)]
        return tuple(self.annotation_label_colors[label_value])

    def get_current_annotation_label(self):
        if hasattr(self, 'annotation_label_spin'):
            return int(self.annotation_label_spin.value())
        return 0

    def get_current_annotation_radius(self):
        if hasattr(self, 'annotation_brush_radius_spin'):
            return int(self.annotation_brush_radius_spin.value())
        return 3

    def _on_annotation_label_changed(self, value):
        if not self._prepare_annotation_environment():
            return
        self.annotation_overlay_color = self.get_annotation_label_color(int(value))
        if getattr(self, 'annotation_enabled', False) and getattr(self, 'annotation_mode', 'brush') == 'brush':
            self.statusBar().showMessage(
                f"当前画笔标签={int(value)}，颜色={self.annotation_overlay_color}",
                1500,
            )

    def apply_annotation_stroke(self, view_type, z, y, x, is_erase=False):
        if not self._prepare_annotation_environment():
            return

        z = int(z)
        y = int(y)
        x = int(x)
        if not (0 <= z < self.annotation_volume.shape[0] and 0 <= y < self.annotation_volume.shape[1] and 0 <= x < self.annotation_volume.shape[2]):
            return

        radius = self.get_current_annotation_radius()
        label_value = self.get_current_annotation_label()
        if not is_erase:
            self.annotation_overlay_color = self.get_annotation_label_color(label_value)

        if view_type == 'axial':
            y_min = max(0, y - radius)
            y_max = min(self.annotation_volume.shape[1] - 1, y + radius)
            x_min = max(0, x - radius)
            x_max = min(self.annotation_volume.shape[2] - 1, x + radius)
            yy, xx = np.ogrid[y_min:y_max + 1, x_min:x_max + 1]
            mask = (yy - y) ** 2 + (xx - x) ** 2 <= radius ** 2
            region = self.annotation_volume[z, y_min:y_max + 1, x_min:x_max + 1]
            if is_erase:
                region[mask] = 0
                drawn_region = self.annotation_drawn_mask[z, y_min:y_max + 1, x_min:x_max + 1]
                drawn_region[mask] = False
                self.annotation_drawn_mask[z, y_min:y_max + 1, x_min:x_max + 1] = drawn_region
            else:
                region[mask] = label_value
                drawn_region = self.annotation_drawn_mask[z, y_min:y_max + 1, x_min:x_max + 1]
                drawn_region[mask] = True
                self.annotation_drawn_mask[z, y_min:y_max + 1, x_min:x_max + 1] = drawn_region
            self.annotation_volume[z, y_min:y_max + 1, x_min:x_max + 1] = region
        elif view_type == 'sagittal':
            z_min = max(0, z - radius)
            z_max = min(self.annotation_volume.shape[0] - 1, z + radius)
            y_min = max(0, y - radius)
            y_max = min(self.annotation_volume.shape[1] - 1, y + radius)
            zz, yy = np.ogrid[z_min:z_max + 1, y_min:y_max + 1]
            mask = (zz - z) ** 2 + (yy - y) ** 2 <= radius ** 2
            region = self.annotation_volume[z_min:z_max + 1, y_min:y_max + 1, x]
            if is_erase:
                region[mask] = 0
                drawn_region = self.annotation_drawn_mask[z_min:z_max + 1, y_min:y_max + 1, x]
                drawn_region[mask] = False
                self.annotation_drawn_mask[z_min:z_max + 1, y_min:y_max + 1, x] = drawn_region
            else:
                region[mask] = label_value
                drawn_region = self.annotation_drawn_mask[z_min:z_max + 1, y_min:y_max + 1, x]
                drawn_region[mask] = True
                self.annotation_drawn_mask[z_min:z_max + 1, y_min:y_max + 1, x] = drawn_region
            self.annotation_volume[z_min:z_max + 1, y_min:y_max + 1, x] = region
        elif view_type == 'coronal':
            z_min = max(0, z - radius)
            z_max = min(self.annotation_volume.shape[0] - 1, z + radius)
            x_min = max(0, x - radius)
            x_max = min(self.annotation_volume.shape[2] - 1, x + radius)
            zz, xx = np.ogrid[z_min:z_max + 1, x_min:x_max + 1]
            mask = (zz - z) ** 2 + (xx - x) ** 2 <= radius ** 2
            region = self.annotation_volume[z_min:z_max + 1, y, x_min:x_max + 1]
            if is_erase:
                region[mask] = 0
                drawn_region = self.annotation_drawn_mask[z_min:z_max + 1, y, x_min:x_max + 1]
                drawn_region[mask] = False
                self.annotation_drawn_mask[z_min:z_max + 1, y, x_min:x_max + 1] = drawn_region
            else:
                region[mask] = label_value
                drawn_region = self.annotation_drawn_mask[z_min:z_max + 1, y, x_min:x_max + 1]
                drawn_region[mask] = True
                self.annotation_drawn_mask[z_min:z_max + 1, y, x_min:x_max + 1] = drawn_region
            self.annotation_volume[z_min:z_max + 1, y, x_min:x_max + 1] = region
        else:
            return

        self.refresh_annotation_overlays()

    def refresh_annotation_overlays(self):
        for viewer_name in ["axial_viewer", "cor_viewer", "sag_viewer"]:
            viewer = getattr(self, viewer_name, None)
            if viewer and hasattr(viewer, '_update_annotation_overlay'):
                viewer._update_annotation_overlay(viewer.slider.value())

    def clear_annotation_volume(self):
        if not hasattr(self, 'annotation_volume') or self.annotation_volume is None:
            self.annotation_volume = None
            self.statusBar().showMessage("当前无标注可清空", 1500)
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "清空标注",
            "确认清空当前所有手工标注吗？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        self.annotation_volume.fill(0)
        if hasattr(self, 'annotation_drawn_mask') and self.annotation_drawn_mask is not None:
            self.annotation_drawn_mask.fill(False)
        self._remove_annotation_label_datasets()
        self.refresh_annotation_overlays()
        self.statusBar().showMessage("手工标注已清空", 2000)

    def _remove_annotation_label_datasets(self):
        """移除数据列表中由手工标注生成的标签数据项。"""
        if not hasattr(self, 'data_list_widget'):
            return

        rows_to_remove = []
        for idx in range(self.data_list_widget.count()):
            item = self.data_list_widget.item(idx)
            if item is None:
                continue
            data_item = item.data(QtCore.Qt.UserRole)
            if not isinstance(data_item, dict):
                continue
            if data_item.get('data_type') != 'label':
                continue
            if data_item.get('label_source') == 'annotation':
                rows_to_remove.append(idx)

        if not rows_to_remove:
            return

        for row in reversed(rows_to_remove):
            self.data_list_widget.takeItem(row)

        if self.data_list_widget.count() > 0:
            first_item = self.data_list_widget.item(0)
            self.data_list_widget.setCurrentItem(first_item)
            data_item = first_item.data(QtCore.Qt.UserRole)
            if data_item is not None:
                self.switch_to_data(data_item, first_item.text())
        else:
            self.clear_viewers()
            self.create_placeholder_views()

    def save_annotation_as_label_file(self):
        return self.create_label_file_from_annotation(suggested_output_path="annotation_labels.nii.gz", ask_save=True)

    def create_label_file_from_annotation(self, suggested_output_path=None, ask_save=True):
        if not self._prepare_annotation_environment():
            return None

        has_annotation = bool(np.any(self.annotation_drawn_mask)) if hasattr(self, 'annotation_drawn_mask') else bool(np.count_nonzero(self.annotation_volume) > 0)
        if not has_annotation:
            QtWidgets.QMessageBox.information(
                self,
                "标注为空",
                "当前还没有手工标注。\n请先点击“标注区-画笔/橡皮擦”进行标注，然后再创建标签文件。",
            )
            return None

        save_to_file = True
        filepath = None
        if ask_save:
            reply = QtWidgets.QMessageBox.question(
                self,
                "保存标签文件",
                "是否将当前标注保存为标签文件？\n"
                "- 是：选择路径保存\n"
                "- 否：仅加入数据列表（自动生成临时标签文件供算法使用）",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel,
            )
            if reply == QtWidgets.QMessageBox.Cancel:
                return None
            save_to_file = (reply == QtWidgets.QMessageBox.Yes)

        if save_to_file:
            default_name = suggested_output_path if suggested_output_path else "annotation_labels.nii.gz"
            filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "保存标签文件",
                default_name,
                "NIfTI文件 (*.nii.gz *.nii);;所有文件 (*)",
            )
            if not filepath:
                return None
            if not (filepath.endswith('.nii.gz') or filepath.endswith('.nii')):
                filepath += '.nii.gz'
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(tempfile.gettempdir(), f"annotation_labels_temp_{timestamp}.nii.gz")

        try:
            label_image = sitk.GetImageFromArray(self.annotation_volume.astype(np.uint16))
            if hasattr(self, 'image') and self.image is not None:
                label_image.CopyInformation(self.image)
            sitk.WriteImage(label_image, filepath)

            label_info, unique_vals = self._summarize_label_array(self.annotation_volume, self.annotation_drawn_mask if hasattr(self, 'annotation_drawn_mask') else None)
            dataset_name = self._build_annotation_dataset_name(unique_vals, fallback=os.path.basename(filepath) if save_to_file else "手工标签")
            data_item = {
                'image': label_image,
                'array': self.annotation_volume.astype(np.uint16).copy(),
                'shape': self.annotation_volume.shape,
                'spacing': self.spacing if hasattr(self, 'spacing') else (1.0, 1.0, 1.0),
                'rgb_array': None,
                'is_segmentation': True,
                'data_type': 'label',
                'label_source': 'annotation',
                'annotation_view_type': getattr(self, 'active_view', 'axial'),
                'label_info': label_info,
                'label_values': unique_vals,
                'label_color_map': {int(v): self.get_annotation_label_color(int(v)) for v in unique_vals},
                'label_path': filepath if save_to_file else None,
                'annotation_drawn_mask': self.annotation_drawn_mask.copy() if hasattr(self, 'annotation_drawn_mask') else None,
            }
            if hasattr(self, 'add_data_to_list'):
                self.add_data_to_list(dataset_name, data_item)

            msg = f"标签值统计：\n{label_info}"
            if save_to_file:
                msg = f"标签文件已保存：\n{filepath}\n\n{msg}"
            else:
                msg = "标签未落盘（仅加入数据列表，可后续导出）。\n\n" + msg

            QtWidgets.QMessageBox.information(self, "标签创建完成", msg)
            return filepath
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "创建失败", f"创建标签文件失败：{str(e)}")
            return None

    def _build_annotation_dataset_name(self, unique_vals, fallback="手工标签"):
        name = ""
        if hasattr(self, 'annotation_name_edit'):
            name = self.annotation_name_edit.text().strip()
        if not name:
            if unique_vals:
                vals = "-".join(str(v) for v in unique_vals)
                return f"{fallback}(标签{vals})"
            return fallback
        if unique_vals:
            vals = "-".join(str(v) for v in unique_vals)
            return f"{name}(标签{vals})"
        return name

    def get_available_label_datasets(self):
        """返回数据列表中可用于机器学习分割的标签数据集信息。"""
        datasets = []
        if not hasattr(self, 'data_list_widget'):
            return datasets

        for index in range(self.data_list_widget.count()):
            item = self.data_list_widget.item(index)
            if item is None:
                continue
            data_item = item.data(QtCore.Qt.UserRole)
            if not isinstance(data_item, dict):
                continue
            if data_item.get('data_type') != 'label':
                continue

            label_path = data_item.get('label_path', None)
            if not label_path or not os.path.exists(label_path):
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    tmp_path = os.path.join(tempfile.gettempdir(), f"label_dataset_{timestamp}.nii.gz")
                    export_image = sitk.GetImageFromArray(data_item['array'])
                    src_img = data_item.get('image', None)
                    if src_img is not None:
                        export_image.CopyInformation(src_img)
                    elif hasattr(self, 'image') and self.image is not None:
                        export_image.CopyInformation(self.image)
                    sitk.WriteImage(export_image, tmp_path)
                    label_path = tmp_path
                    data_item['label_path'] = tmp_path
                except Exception:
                    label_path = None

            if not label_path:
                continue

            datasets.append({
                'name': item.text(),
                'path': label_path,
                'label_info': data_item.get('label_info', ''),
                'label_values': data_item.get('label_values', []),
                'annotation_drawn_mask': data_item.get('annotation_drawn_mask', None),
                'annotation_view_type': data_item.get('annotation_view_type', None),
            })

        return datasets

    def _summarize_label_array(self, label_array, drawn_mask=None):
        if drawn_mask is not None:
            selected = label_array[drawn_mask]
        else:
            selected = label_array[label_array > 0]

        if selected.size == 0:
            return "无前景标签", []

        values, counts = np.unique(selected, return_counts=True)
        lines = []
        kept_values = []
        for value, count in zip(values, counts):
            kept_values.append(int(value))
            lines.append(f"标签 {int(value)}: {int(count)} 体素")
        return "；".join(lines), kept_values

    def measure_area_placeholder(self):
        QtWidgets.QMessageBox.information(self, "面积测量", "面积测量入口已预留。")

    def measure_volume_placeholder(self):
        QtWidgets.QMessageBox.information(self, "体积测量", "体积测量入口已预留。")

    def add_text_annotation(self):
        QtWidgets.QMessageBox.information(self, "文本注释", "文本注释入口已预留。")

    def on_render_mode_changed(self, mode):
        if hasattr(self, 'render_mode_3d_combo') and self.render_mode_3d_combo.currentText() != mode:
            self.render_mode_3d_combo.blockSignals(True)
            self.render_mode_3d_combo.setCurrentText(mode)
            self.render_mode_3d_combo.blockSignals(False)
        if hasattr(self, 'render_mode_combo') and self.render_mode_combo.currentText() != mode:
            self.render_mode_combo.blockSignals(True)
            self.render_mode_combo.setCurrentText(mode)
            self.render_mode_combo.blockSignals(False)

        if self.volume_viewer and hasattr(self.volume_viewer, 'set_render_mode'):
            self.volume_viewer.set_render_mode(mode)
            self.apply_advanced_3d_settings()
            self.statusBar().showMessage(f"3D渲染模式：{mode}", 1500)

    def apply_advanced_3d_settings(self, *_):
        """应用3D settings面板中的高级参数。"""
        if self.volume_viewer is None or not hasattr(self.volume_viewer, 'configure_advanced_3d'):
            return

        self.volume_viewer.configure_advanced_3d(
            solidity=self.opacity_3d_slider.value() if hasattr(self, 'opacity_3d_slider') else 80,
            diffuse=self.diffuse_3d_slider.value() if hasattr(self, 'diffuse_3d_slider') else 75,
            specular=self.specular_3d_slider.value() if hasattr(self, 'specular_3d_slider') else 20,
            shininess=self.shininess_3d_slider.value() if hasattr(self, 'shininess_3d_slider') else 35,
            tone_mapping=self.chk_tone_mapping.isChecked() if hasattr(self, 'chk_tone_mapping') else False,
            unsharp=self.chk_unsharp.isChecked() if hasattr(self, 'chk_unsharp') else False,
            specular_boost=self.chk_specular_boost.isChecked() if hasattr(self, 'chk_specular_boost') else False,
            noise_reduction=self.chk_noise_reduction.isChecked() if hasattr(self, 'chk_noise_reduction') else False,
            edge_contrast=self.chk_3d_edge_enhance.isChecked() if hasattr(self, 'chk_3d_edge_enhance') else False,
            filtered_gradient=self.chk_filtered_gradient.isChecked() if hasattr(self, 'chk_filtered_gradient') else False,
            high_quality=self.chk_3d_shading.isChecked() if hasattr(self, 'chk_3d_shading') else True,
            median=self.chk_median_3d.isChecked() if hasattr(self, 'chk_median_3d') else False,
            interpolation_3d=(
                'Nearest' if (hasattr(self, 'interp_3d_combo') and self.interp_3d_combo.currentText() == '最近邻')
                else 'Cubic' if (hasattr(self, 'interp_3d_combo') and self.interp_3d_combo.currentText() == '三次')
                else 'Linear'
            ),
            lut_3d=self.lut_3d_combo.currentText() if hasattr(self, 'lut_3d_combo') else 'grayscale',
            absolute_lut=self.chk_absolute_lut.isChecked() if hasattr(self, 'chk_absolute_lut') else False,
            flip_roi_lut=self.chk_flip_roi_lut.isChecked() if hasattr(self, 'chk_flip_roi_lut') else False,
            gamma_enhance=self.chk_gamma_enhance.isChecked() if hasattr(self, 'chk_gamma_enhance') else False,
        )

    def change_background_color(self):
        color = QtWidgets.QColorDialog.getColor(parent=self)
        if not color.isValid():
            return
        if self.volume_viewer and hasattr(self.volume_viewer, 'set_background_color'):
            self.volume_viewer.set_background_color((color.redF(), color.greenF(), color.blueF()))

    def export_screenshot(self):
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "导出截屏",
            "",
            "PNG Files (*.png);;JPEG Files (*.jpg *.jpeg)"
        )
        if not filepath:
            return

        if self.volume_viewer and hasattr(self.volume_viewer, 'save_screenshot') and filepath.lower().endswith('.png'):
            ok = self.volume_viewer.save_screenshot(filepath)
            if ok:
                self.statusBar().showMessage(f"已导出3D截屏：{filepath}", 2500)
                return

        pix = self.grab()
        if pix.save(filepath):
            self.statusBar().showMessage(f"已导出截屏：{filepath}", 2500)
        else:
            QtWidgets.QMessageBox.warning(self, "导出失败", "截屏保存失败，请检查路径或格式。")

    def switch_2d_view(self, view_name):
        mapping = {
            "side": ("sagittal", getattr(self, 'sag_viewer', None)),
            "front": ("coronal", getattr(self, 'cor_viewer', None)),
            "back": ("axial", getattr(self, 'axial_viewer', None)),
        }
        active_name, viewer = mapping.get(view_name, ("axial", getattr(self, 'axial_viewer', None)))
        self.active_view = active_name
        if viewer is not None:
            viewer.setFocus()
        self.statusBar().showMessage(f"2D视图切换：{view_name}", 2000)

    def configure_visible_plane(self):
        options = ["全部显示", "仅轴位", "仅冠状", "仅矢状"]
        choice, ok = QtWidgets.QInputDialog.getItem(self, "可视平面", "选择显示平面", options, 0, False)
        if not ok:
            return

        show_axial = choice in ("全部显示", "仅轴位")
        show_cor = choice in ("全部显示", "仅冠状")
        show_sag = choice in ("全部显示", "仅矢状")

        if getattr(self, 'axial_viewer', None):
            self.axial_viewer.setVisible(show_axial)
        if getattr(self, 'cor_viewer', None):
            self.cor_viewer.setVisible(show_cor)
        if getattr(self, 'sag_viewer', None):
            self.sag_viewer.setVisible(show_sag)

        self.statusBar().showMessage(f"可视平面：{choice}", 2000)

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

    def _filter_dataset_items(self):
        """按关键字过滤数据列表（简单版）。"""
        if not hasattr(self, 'data_list_widget'):
            return
        keyword, ok = QtWidgets.QInputDialog.getText(self, "过滤数据项", "输入名称关键字（留空显示全部）:")
        if not ok:
            return
        text = (keyword or "").strip().lower()
        for index in range(self.data_list_widget.count()):
            item = self.data_list_widget.item(index)
            visible = (text == "") or (text in item.text().lower())
            item.setHidden(not visible)

    def _toggle_current_dataset_visibility(self):
        """切换当前数据项显示状态（行内小眼睛）。"""
        if not hasattr(self, 'data_list_widget'):
            return
        current_item = self.data_list_widget.currentItem()
        if current_item is None:
            QtWidgets.QMessageBox.information(self, "提示", "请先在数据列表中选中一项。")
            return
        self._toggle_dataset_item_visibility(current_item)

    def _toggle_dataset_item_visibility(self, item):
        if item is None:
            return
        current_visible = bool(item.data(QtCore.Qt.UserRole + 1))
        new_visible = not current_visible
        item.setData(QtCore.Qt.UserRole + 1, new_visible)
        self._refresh_dataset_item_eye(item)

        if self.data_list_widget.currentItem() is item:
            if new_visible:
                data_item = item.data(QtCore.Qt.UserRole)
                if data_item is not None:
                    self.switch_to_data(data_item, item.text())
            else:
                self.clear_viewers()
                self.create_placeholder_views()

        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(
                f"数据 {item.text()} 已{'显示' if new_visible else '隐藏'}",
                2000
            )

    def create_new_layer(self):
        QtWidgets.QMessageBox.information(self, "新建图层", "新建图层入口已启用。")

    def copy_current_layer(self):
        QtWidgets.QMessageBox.information(self, "复制图层", "复制当前图层入口已启用。")

    def export_current_layer(self):
        if not hasattr(self, 'data_list_widget'):
            return
        current_item = self.data_list_widget.currentItem()
        if current_item is None:
            QtWidgets.QMessageBox.information(self, "提示", "请先在数据列表选择要导出的图层。")
            return

        data_item = current_item.data(QtCore.Qt.UserRole)
        if data_item is None or 'array' not in data_item:
            QtWidgets.QMessageBox.warning(self, "导出失败", "当前图层数据不可用。")
            return

        default_name = current_item.text().replace('[标签]', '').strip().replace(' ', '_') + ".nii.gz"
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "导出当前图层",
            default_name,
            "NIfTI文件 (*.nii.gz *.nii);;所有文件 (*)",
        )
        if not filepath:
            return
        if not (filepath.endswith('.nii.gz') or filepath.endswith('.nii')):
            filepath += '.nii.gz'

        try:
            arr = data_item['array']
            export_image = sitk.GetImageFromArray(arr)
            src_img = data_item.get('image', None)
            if src_img is not None:
                export_image.CopyInformation(src_img)
            elif hasattr(self, 'image') and self.image is not None:
                export_image.CopyInformation(self.image)
            sitk.WriteImage(export_image, filepath)
            self.statusBar().showMessage(f"图层已导出: {filepath}", 3000)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "导出失败", f"导出当前图层失败：{str(e)}")

    def apply_3d_preset(self, preset_name):
        presets = {
            "骨骼": dict(mode="表面渲染", opacity=92, specular=55, brightness=70, scatter=35),
            "血管": dict(mode="MIP", opacity=80, specular=45, brightness=65, scatter=30),
            "CTA": dict(mode="体渲染", opacity=85, specular=50, brightness=68, scatter=42),
            "软组织": dict(mode="默认", opacity=72, specular=25, brightness=52, scatter=60),
            "高对比": dict(mode="ISO", opacity=95, specular=60, brightness=75, scatter=25),
            "低噪声": dict(mode="体渲染", opacity=70, specular=18, brightness=50, scatter=72),
        }
        cfg = presets.get(preset_name)
        if not cfg:
            return

        if hasattr(self, 'opacity_3d_slider'):
            self.opacity_3d_slider.setValue(int(cfg["opacity"]))
        if hasattr(self, 'specular_3d_slider'):
            self.specular_3d_slider.setValue(int(cfg["specular"]))
        self.specular_slider.setValue(int(cfg["specular"]))
        self.brightness_slider.setValue(int(cfg["brightness"]))
        self.scatter_slider.setValue(int(cfg["scatter"]))
        self.render_mode_combo.setCurrentText(cfg["mode"])

        self.apply_scene_view_options()
        self.apply_3d_lighting_settings()
        self.apply_advanced_3d_settings()
        self.statusBar().showMessage(f"应用3D预设：{preset_name}", 2000)

    def apply_scene_view_options(self):
        """应用场景视图相关选项到2D/3D视图。"""
        mode = self.view_mode_combo.currentText() if hasattr(self, 'view_mode_combo') else "二维+三维"

        volume_visible = (mode in ("三维", "二维+三维", "3D", "2D+3D"))
        slice_visible = (mode in ("二维", "二维+三维", "2D", "2D+3D"))

        if getattr(self, 'volume_viewer', None):
            self.volume_viewer.setVisible(volume_visible)

        for viewer_name in ('axial_viewer', 'sag_viewer', 'cor_viewer'):
            viewer = getattr(self, viewer_name, None)
            if viewer is None:
                continue
            viewer.setVisible(slice_visible)
            if hasattr(viewer, 'title_label'):
                viewer.title_label.setVisible(self.chk_show_annotations.isChecked())
            if hasattr(viewer, '_redraw_crosshair'):
                viewer._redraw_crosshair()

        if self.volume_viewer is not None:
            if hasattr(self.volume_viewer, 'set_projection_mode'):
                self.volume_viewer.set_projection_mode(self.chk_orthogonal_projection.isChecked())
            if hasattr(self.volume_viewer, 'set_interaction_quality'):
                self.volume_viewer.set_interaction_quality(
                    reduce_quality=self.chk_reduce_quality_during_op.isChecked(),
                    best_quality=self.chk_best_quality.isChecked(),
                )

    def apply_3d_lighting_settings(self):
        """应用光照参数到3D体渲染。"""
        if self.volume_viewer is None or not hasattr(self.volume_viewer, 'set_light_settings'):
            return

        self.volume_viewer.set_light_settings(
            light_position=self.light_pos_slider.value(),
            light_intensity=self.light_intensity_slider.value(),
            shadow_strength=self.shadow_strength_slider.value(),
            shadow_alpha=self.shadow_alpha_slider.value(),
            brightness=self.brightness_slider.value(),
            spot=self.spot_slider.value(),
            specular=self.specular_slider.value(),
            scatter=self.scatter_slider.value(),
        )

    def apply_3d_focus_settings(self):
        """应用焦距/景深相关参数到3D相机。"""
        if self.volume_viewer is None or not hasattr(self.volume_viewer, 'set_focus_settings'):
            return
        self.volume_viewer.set_focus_settings(
            auto_focus=self.chk_auto_focus.isChecked(),
            focus_distance=self.focus_distance_slider.value(),
            depth_of_field=self.depth_of_field_slider.value(),
        )

    def apply_current_3d_controls(self):
        """在重建或切换数据后，重新应用当前3D控制面板状态。"""
        if self.volume_viewer is None:
            return
        self.apply_scene_view_options()
        if hasattr(self, 'render_mode_combo') and self.render_mode_combo.currentText() != "默认":
            self.on_render_mode_changed(self.render_mode_combo.currentText())

    def preview_crop_effect(self):
        self.statusBar().showMessage("裁剪预览入口已启用", 2000)

    def _update_basic_properties_table(self):
        if not hasattr(self, 'basic_properties_table'):
            return

        has_data = getattr(self, 'array', None) is not None
        if has_data:
            depth, height, width = self.array.shape[:3]
            sx, sy, sz = getattr(self, 'spacing', (1.0, 1.0, 1.0)) or (1.0, 1.0, 1.0)
            time_steps = 1
            voxels = int(width * height * depth * time_steps)
            size_mb = float(getattr(self.array, 'nbytes', 0)) / (1024.0 * 1024.0)
            data_type = str(self.array.dtype)
            volume = voxels * float(sx) * float(sy) * float(sz)
            rows = [
                ("宽度", str(width), "X 方向像素总数及其物理尺寸。"),
                ("高度", str(height), "Y 方向像素总数及其物理尺寸。"),
                ("深度", str(depth), "Z 方向像素总数及其物理尺寸。"),
                ("时间步", str(time_steps), "时间维度（T）的大小。"),
                ("体素数", str(voxels), "数据集中体素总数。"),
                ("数据大小", f"{size_mb:.2f} MB", "图像数据占用的文件大小。"),
                ("数据类型", data_type, "数据集使用的基础数据类型。"),
                ("体积", f"{volume:.2f}", "数据集占用的总体积。"),
            ]
        else:
            rows = [
                ("宽度", "-", "X 方向像素总数及其物理尺寸。"),
                ("高度", "-", "Y 方向像素总数及其物理尺寸。"),
                ("深度", "-", "Z 方向像素总数及其物理尺寸。"),
                ("时间步", "-", "时间维度（T）的大小。"),
                ("体素数", "-", "数据集中体素总数。"),
                ("数据大小", "-", "图像数据占用的文件大小。"),
                ("数据类型", "-", "数据集使用的基础数据类型。"),
                ("体积", "-", "数据集占用的总体积。"),
            ]

        self.basic_properties_table.setRowCount(len(rows))
        for row_index, (property_text, value_text, description_text) in enumerate(rows):
            property_item = QtWidgets.QTableWidgetItem(property_text)
            value_item = QtWidgets.QTableWidgetItem(value_text)
            description_item = QtWidgets.QTableWidgetItem(description_text)
            property_item.setForeground(QtGui.QBrush(QtGui.QColor('#e7e7e7')))
            value_item.setForeground(QtGui.QBrush(QtGui.QColor('#e7e7e7')))
            description_item.setForeground(QtGui.QBrush(QtGui.QColor('#d0d0d0')))
            self.basic_properties_table.setItem(row_index, 0, property_item)
            self.basic_properties_table.setItem(row_index, 1, value_item)
            self.basic_properties_table.setItem(row_index, 2, description_item)

        self.basic_properties_table.resizeRowsToContents()

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

        self._syncing_slice_sliders = True
        try:
            if self.axial_viewer:
                self.axial_viewer.slider.setValue(z_idx)
                self.axial_viewer.set_crosshair(x_idx, y_idx)
            if self.cor_viewer:
                self.cor_viewer.slider.setValue(y_idx)
                self.cor_viewer.set_crosshair(x_idx, z_idx)
            if self.sag_viewer:
                self.sag_viewer.slider.setValue(x_idx)
                self.sag_viewer.set_crosshair(y_idx, z_idx)
        finally:
            self._syncing_slice_sliders = False

