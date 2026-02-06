"""
CTViewer4主类
整合所有功能模块的主窗口类
"""

import numpy as np
from PyQt5 import QtWidgets

from .ui_components import UIComponents
from .window_level import WindowLevelControl
from .data_loader import DataLoader
from .filter_operations import FilterOperations
from .ct_operations import CTOperations
from .ai_operations import AIOperations
from .measurement_operations import MeasurementOperations
from .roi_operations import ROIOperations
from .projection_operations import ProjectionOperations
from Traditional.Segmentation.traditional_segmentation_operations import TraditionalSegmentationOperations


class CTViewer4(QtWidgets.QMainWindow, UIComponents, WindowLevelControl, 
                DataLoader, FilterOperations, CTOperations, AIOperations, 
                MeasurementOperations, ROIOperations, ProjectionOperations, TraditionalSegmentationOperations):
    """
    四宫格 CT 浏览器：
    - 左上：Axial（横断面）切片 + 滑动条
    - 右上：Sagittal（矢状面）切片 + 滑动条
    - 左下：Coronal（冠状面）切片 + 滑动条
    - 右下：VTK 三维体渲染窗口

    功能菜单：
    - 文件操作：导入文件
    - 滤波：曲率流去噪
    - CT重建：CT螺旋重建、CT圆轨迹
    - 传统分割检测：区域生长、OTSU阈值分割
    - 人工智能分割：基线方法
    - 配准（占位）
    """

    def __init__(self, filename=None, shape=None, spacing=None, dtype=np.uint16):
        """
        参数
        ----
        filename : str, optional
            输入影像文件路径，可以是 .nii/.mhd/.dcm 等医学影像文件，
            也可以是原始 .raw 文件（需配合 shape 使用）。
            如果为None，则通过菜单导入文件。
        shape : tuple, optional
            如果输入文件是 .raw，则必须提供 (z, y, x) 维度信息。
        spacing : tuple, optional
            像素间距 (sx, sy, sz)，通常从头文件获取。
        dtype : numpy.dtype, default=np.uint16
            原始数据类型，默认 16 位无符号整型。
        """
        super().__init__()
        self.setWindowTitle("工业CT智能软件")
        
        # 应用样式表
        self.apply_stylesheet()
        
        # 创建菜单栏
        self.create_menu()
        
        # 初始化界面布局
        self.init_ui()
        
        # 初始化测量功能
        self.setup_measurement()

        # 初始化 ROI 功能
        self.setup_roi()
        
        # 初始化传统分割功能
        TraditionalSegmentationOperations.__init__(self)
        
        # 初始化分割结果标志
        self.is_segmentation = False
        
        # 如果提供了文件名，则加载数据
        if filename:
            self.load_data(filename, shape, spacing, dtype)

