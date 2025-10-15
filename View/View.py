from PyQt5 import QtWidgets, QtCore, QtGui
import os
import sys
import math
import numpy as np
import matplotlib
matplotlib.use("TKAGG")  # 使用与ball_phantom_calibration.py相同的后端
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg as FigureCanvas
from matplotlib.figure import Figure

# SimpleITK 相关
import SimpleITK as sitk

# VTK 相关
import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from File.DataTransform import *
from File.readData import *
from Traditional.EdgeDetection.edgeDetection import *
from Traditional.Filter.filter_op import Filter_op

# LEAP库导入（用于多球标定）
try:
    from leap_preprocessing_algorithms import *
    from leapctype import *
    # 显式导入ball_phantom_calibration类
    from leap_preprocessing_algorithms import ball_phantom_calibration
except ImportError:
    print("警告：未找到LEAP库，多球标定功能将不可用")

# 导入CT对话框
from CT.ball_phantom_dialog import BallPhantomCalibrationDialog
from CT.helical_ct_dialog import HelicalCTReconstructionDialog
from CT.circle_ct_dialog import CircleCTReconstructionDialog

# 导入AI分割相关模块
from AISegmeant.unet_segmentation_dialog import UnetSegmentationDialog
from AISegmeant.segmentation_inference import UnetSegmentationInference
from AISegmeant.image_overlay import create_overlay_from_files


class ZoomableLabelViewer(QtWidgets.QWidget):
    """支持缩放和平移的图像查看器"""
    
    def __init__(self, title, image_array, window_width=None, window_level=None):
        super().__init__()
        self.setWindowTitle(title)
        self.image_array = image_array  # 原始图像数据
        self.window_width = window_width if window_width is not None else 65535
        self.window_level = window_level if window_level is not None else 32767
        
        # 缩放和平移参数
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # 用于拖拽平移
        self.last_mouse_pos = None
        self.is_dragging = False
        
        # 创建界面
        self.init_ui()
        
        # 初始显示
        self.update_display()
    
    def init_ui(self):
        """初始化界面"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # 图像显示标签
        self.image_label = QtWidgets.QLabel()
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setMouseTracking(True)
        self.image_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        
        # 为标签安装事件过滤器
        self.image_label.installEventFilter(self)
        
        # 滚动区域
        scroll = QtWidgets.QScrollArea()
        scroll.setWidget(self.image_label)
        scroll.setWidgetResizable(False)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        layout.addWidget(scroll)
        
        # 控制面板
        control_panel = QtWidgets.QWidget()
        control_layout = QtWidgets.QHBoxLayout(control_panel)
        
        # 缩放控制
        zoom_label = QtWidgets.QLabel("缩放:")
        control_layout.addWidget(zoom_label)
        
        zoom_out_btn = QtWidgets.QPushButton("-")
        zoom_out_btn.setMaximumWidth(40)
        zoom_out_btn.clicked.connect(lambda: self.zoom(0.8))
        control_layout.addWidget(zoom_out_btn)
        
        self.zoom_display = QtWidgets.QLabel(f"{int(self.scale_factor*100)}%")
        self.zoom_display.setMinimumWidth(50)
        self.zoom_display.setAlignment(QtCore.Qt.AlignCenter)
        control_layout.addWidget(self.zoom_display)
        
        zoom_in_btn = QtWidgets.QPushButton("+")
        zoom_in_btn.setMaximumWidth(40)
        zoom_in_btn.clicked.connect(lambda: self.zoom(1.25))
        control_layout.addWidget(zoom_in_btn)
        
        reset_btn = QtWidgets.QPushButton("重置")
        reset_btn.clicked.connect(self.reset_view)
        control_layout.addWidget(reset_btn)
        
        control_layout.addStretch()
        
        # 窗宽窗位控制
        ww_label = QtWidgets.QLabel("窗宽:")
        control_layout.addWidget(ww_label)
        
        self.ww_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.ww_slider.setMinimum(1)
        self.ww_slider.setMaximum(65535)
        self.ww_slider.setValue(int(self.window_width))
        self.ww_slider.setMinimumWidth(150)
        self.ww_slider.valueChanged.connect(self.on_window_changed)
        control_layout.addWidget(self.ww_slider)
        
        self.ww_value = QtWidgets.QLabel(str(int(self.window_width)))
        self.ww_value.setMinimumWidth(50)
        control_layout.addWidget(self.ww_value)
        
        wl_label = QtWidgets.QLabel("窗位:")
        control_layout.addWidget(wl_label)
        
        self.wl_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.wl_slider.setMinimum(0)
        self.wl_slider.setMaximum(65535)
        self.wl_slider.setValue(int(self.window_level))
        self.wl_slider.setMinimumWidth(150)
        self.wl_slider.valueChanged.connect(self.on_window_changed)
        control_layout.addWidget(self.wl_slider)
        
        self.wl_value = QtWidgets.QLabel(str(int(self.window_level)))
        self.wl_value.setMinimumWidth(50)
        control_layout.addWidget(self.wl_value)
        
        layout.addWidget(control_panel)
        
        # 设置窗口大小
        self.resize(800, 600)
    
    def eventFilter(self, obj, event):
        """事件过滤器，处理鼠标事件"""
        if obj == self.image_label:
            if event.type() == QtCore.QEvent.MouseButtonPress:
                if event.button() == QtCore.Qt.LeftButton:
                    self.is_dragging = True
                    self.last_mouse_pos = event.pos()
                    self.image_label.setCursor(QtCore.Qt.ClosedHandCursor)
                    return True
            
            elif event.type() == QtCore.QEvent.MouseButtonRelease:
                if event.button() == QtCore.Qt.LeftButton:
                    self.is_dragging = False
                    self.last_mouse_pos = None
                    self.image_label.setCursor(QtCore.Qt.ArrowCursor)
                    return True
            
            elif event.type() == QtCore.QEvent.MouseMove:
                if self.is_dragging and self.last_mouse_pos:
                    delta = event.pos() - self.last_mouse_pos
                    self.offset_x += delta.x()
                    self.offset_y += delta.y()
                    self.last_mouse_pos = event.pos()
                    self.update_display()
                    return True
            
            elif event.type() == QtCore.QEvent.Wheel:
                # 鼠标滚轮缩放
                delta = event.angleDelta().y()
                if delta > 0:
                    self.zoom(1.1)
                else:
                    self.zoom(0.9)
                return True
        
        return super().eventFilter(obj, event)
    
    def zoom(self, factor):
        """缩放图像"""
        self.scale_factor *= factor
        self.scale_factor = max(0.1, min(10.0, self.scale_factor))  # 限制缩放范围
        self.zoom_display.setText(f"{int(self.scale_factor*100)}%")
        self.update_display()
    
    def reset_view(self):
        """重置视图"""
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.zoom_display.setText("100%")
        self.update_display()
    
    def on_window_changed(self):
        """窗宽窗位改变时的处理"""
        self.window_width = self.ww_slider.value()
        self.window_level = self.wl_slider.value()
        self.ww_value.setText(str(int(self.window_width)))
        self.wl_value.setText(str(int(self.window_level)))
        self.update_display()
    
    def apply_window_level(self, image):
        """应用窗宽窗位"""
        # 计算窗口的最小值和最大值
        ww_min = self.window_level - self.window_width / 2.0
        ww_max = self.window_level + self.window_width / 2.0
        
        # 检查窗宽是否为0，避免除零错误
        if ww_max - ww_min <= 0:
            # 返回全灰度图像
            return np.full(image.shape, 128, dtype=np.uint8)
        
        # 应用窗宽窗位
        image = image.astype(np.float32)
        image = (image - ww_min) / (ww_max - ww_min) * 255.0
        image = np.clip(image, 0, 255)
        
        return image.astype(np.uint8)
    
    def update_display(self):
        """更新显示"""
        # 应用窗宽窗位
        display_image = self.apply_window_level(self.image_array)
        
        # 获取图像尺寸
        h, w = display_image.shape
        
        # 计算缩放后的尺寸
        new_w = int(w * self.scale_factor)
        new_h = int(h * self.scale_factor)
        
        # 转换为QImage
        qimg = QtGui.QImage(display_image.data, w, h, w, QtGui.QImage.Format_Grayscale8)
        
        # 缩放
        if self.scale_factor != 1.0:
            qimg = qimg.scaled(new_w, new_h, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        
        # 转换为QPixmap
        pixmap = QtGui.QPixmap.fromImage(qimg)
        
        # 显示
        self.image_label.setPixmap(pixmap)
        self.image_label.resize(pixmap.size())


class SimpleZoomViewer(QtWidgets.QWidget):
    """简化的缩放查看器（无窗宽窗位控制，图像已经应用过窗宽窗位）"""
    
    def __init__(self, title, image_array):
        super().__init__()
        self.setWindowTitle(title)
        self.image_array = image_array  # 原始图像数据（已应用窗宽窗位）
        
        # 缩放和平移参数
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # 用于拖拽平移
        self.last_mouse_pos = None
        self.is_dragging = False
        
        # 创建界面
        self.init_ui()
        
        # 初始显示（自适应窗口大小）
        self.fit_to_window()
    
    def init_ui(self):
        """初始化界面"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # 图像显示标签
        self.image_label = QtWidgets.QLabel()
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setMouseTracking(True)
        self.image_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        
        # 为标签安装事件过滤器
        self.image_label.installEventFilter(self)
        
        # 滚动区域
        scroll = QtWidgets.QScrollArea()
        scroll.setWidget(self.image_label)
        scroll.setWidgetResizable(False)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        layout.addWidget(scroll)
        
        # 控制面板
        control_panel = QtWidgets.QWidget()
        control_layout = QtWidgets.QHBoxLayout(control_panel)
        
        # 缩放控制
        zoom_label = QtWidgets.QLabel("缩放:")
        control_layout.addWidget(zoom_label)
        
        zoom_out_btn = QtWidgets.QPushButton("-")
        zoom_out_btn.setMaximumWidth(40)
        zoom_out_btn.clicked.connect(lambda: self.zoom(0.8))
        control_layout.addWidget(zoom_out_btn)
        
        self.zoom_display = QtWidgets.QLabel(f"{int(self.scale_factor*100)}%")
        self.zoom_display.setMinimumWidth(50)
        self.zoom_display.setAlignment(QtCore.Qt.AlignCenter)
        control_layout.addWidget(self.zoom_display)
        
        zoom_in_btn = QtWidgets.QPushButton("+")
        zoom_in_btn.setMaximumWidth(40)
        zoom_in_btn.clicked.connect(lambda: self.zoom(1.25))
        control_layout.addWidget(zoom_in_btn)
        
        fit_btn = QtWidgets.QPushButton("适应窗口")
        fit_btn.clicked.connect(self.fit_to_window)
        control_layout.addWidget(fit_btn)
        
        reset_btn = QtWidgets.QPushButton("1:1")
        reset_btn.clicked.connect(self.reset_view)
        control_layout.addWidget(reset_btn)
        
        control_layout.addStretch()
        
        layout.addWidget(control_panel)
        
        # 设置窗口大小
        self.resize(800, 600)
    
    def eventFilter(self, obj, event):
        """事件过滤器，处理鼠标事件"""
        if obj == self.image_label:
            if event.type() == QtCore.QEvent.MouseButtonPress:
                if event.button() == QtCore.Qt.LeftButton:
                    self.is_dragging = True
                    self.last_mouse_pos = event.pos()
                    self.image_label.setCursor(QtCore.Qt.ClosedHandCursor)
                    return True
            
            elif event.type() == QtCore.QEvent.MouseButtonRelease:
                if event.button() == QtCore.Qt.LeftButton:
                    self.is_dragging = False
                    self.last_mouse_pos = None
                    self.image_label.setCursor(QtCore.Qt.ArrowCursor)
                    return True
            
            elif event.type() == QtCore.QEvent.MouseMove:
                if self.is_dragging and self.last_mouse_pos:
                    delta = event.pos() - self.last_mouse_pos
                    self.offset_x += delta.x()
                    self.offset_y += delta.y()
                    self.last_mouse_pos = event.pos()
                    self.update_display()
                    return True
            
            elif event.type() == QtCore.QEvent.Wheel:
                # 鼠标滚轮缩放
                delta = event.angleDelta().y()
                if delta > 0:
                    self.zoom(1.1)
                else:
                    self.zoom(0.9)
                return True
        
        return super().eventFilter(obj, event)
    
    def zoom(self, factor):
        """缩放图像"""
        self.scale_factor *= factor
        self.scale_factor = max(0.1, min(10.0, self.scale_factor))  # 限制缩放范围
        self.zoom_display.setText(f"{int(self.scale_factor*100)}%")
        self.update_display()
    
    def reset_view(self):
        """重置为1:1显示"""
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.zoom_display.setText("100%")
        self.update_display()
    
    def fit_to_window(self):
        """自适应窗口大小"""
        # 获取图像尺寸
        h, w = self.image_array.shape
        
        # 获取可用的显示区域（留一些边距）
        available_width = self.width() - 100
        available_height = self.height() - 150
        
        # 计算缩放比例
        scale_w = available_width / w
        scale_h = available_height / h
        self.scale_factor = min(scale_w, scale_h)
        
        # 重置偏移
        self.offset_x = 0
        self.offset_y = 0
        
        self.zoom_display.setText(f"{int(self.scale_factor*100)}%")
        self.update_display()
    
    def update_image(self, new_image):
        """更新显示的图像"""
        self.image_array = new_image
        self.update_display()
    
    def update_display(self):
        """更新显示"""
        # 转换为uint8用于显示
        display_image = (self.image_array / 65535.0 * 255).astype(np.uint8)
        
        # 获取图像尺寸
        h, w = display_image.shape
        
        # 计算缩放后的尺寸
        new_w = int(w * self.scale_factor)
        new_h = int(h * self.scale_factor)
        
        # 转换为QImage
        qimg = QtGui.QImage(display_image.data, w, h, w, QtGui.QImage.Format_Grayscale8)
        
        # 缩放
        if self.scale_factor != 1.0:
            qimg = qimg.scaled(new_w, new_h, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        
        # 转换为QPixmap
        pixmap = QtGui.QPixmap.fromImage(qimg)
        
        # 显示
        self.image_label.setPixmap(pixmap)
        self.image_label.resize(pixmap.size())


class SliceViewer(QtWidgets.QWidget):
    """单视图 + 滑动条 + 放大按钮，用于显示医学影像的某个方向切片（支持窗宽窗位）"""

    def __init__(self, title, get_slice, max_index, parent_viewer=None):
        """
        初始化切片浏览器。

        参数
        ----
        title : str
            QLabel 的初始标题（比如 "Axial"、"Sagittal"、"Coronal"）。
        get_slice : callable
            一个函数，形式为 get_slice(idx) -> np.ndarray，
            用于根据索引 idx 返回对应的二维切片数组。
        max_index : int
            切片总数，用于设置滑动条的范围 (0 ~ max_index-1)。
        parent_viewer : CTViewer4, optional
            父窗口引用，用于访问窗宽窗位设置
        """
        super().__init__()
        self.title = title  # 保存标题
        self.get_slice = get_slice  # 保存获取切片的函数
        self.max_index = max_index  # 保存最大索引
        self.zoom_window = None  # 缩放窗口引用
        self.parent_viewer = parent_viewer  # 父窗口引用

        # 主布局
        main_layout = QtWidgets.QVBoxLayout()
        
        # 顶部标题栏布局
        title_layout = QtWidgets.QHBoxLayout()
        
        # 标题标签
        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet("font-weight: bold;")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        # 放大按钮
        zoom_btn = QtWidgets.QPushButton("🔍")
        zoom_btn.setMaximumWidth(40)
        zoom_btn.setToolTip("在新窗口中打开，可缩放和平移")
        zoom_btn.clicked.connect(self.open_zoom_window)
        title_layout.addWidget(zoom_btn)
        
        main_layout.addLayout(title_layout)

        # QLabel 用于显示图像
        self.label = QtWidgets.QLabel()
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(self.label)

        # QSlider 用于选择切片索引
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(0, max_index - 1)  # 设置滑动条范围
        self.slider.valueChanged.connect(self.update_slice)  # 当值改变时触发 update_slice
        main_layout.addWidget(self.slider)
        
        self.setLayout(main_layout)

        # 默认显示中间切片
        self.slider.setValue(max_index // 2)
    
    def open_zoom_window(self):
        """打开缩放窗口（简化版，无窗宽窗位控制）"""
        try:
            # 获取当前切片
            current_idx = self.slider.value()
            current_slice = self.get_slice(current_idx)
            
            # 创建简化的缩放窗口
            window_title = f"{self.title} - 切片 {current_idx+1}/{self.max_index}"
            self.zoom_window = SimpleZoomViewer(window_title, current_slice)
            self.zoom_window.show()
            
        except Exception as e:
            print(f"打开缩放窗口时出错: {str(e)}")
            QtWidgets.QMessageBox.warning(self, "错误", f"无法打开缩放窗口：{str(e)}")

    def update_slice(self, idx):
        """
        槽函数：当滑动条的值变化时，更新 QLabel 显示新的切片。

        参数
        ----
        idx : int
            当前滑动条的值，即切片索引。
        """
        # 通过外部传入的函数获取切片数据
        arr = self.get_slice(idx)

        # 将 numpy 数组转换为 QPixmap（灰度图）
        pix = array_to_qpixmap(arr)

        # 缩放 QPixmap 以适应 QLabel 大小，并保持长宽比
        self.label.setPixmap(pix.scaled(
            self.label.size(),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        ))
        
        # 如果缩放窗口打开着，更新它的图像
        if self.zoom_window and self.zoom_window.isVisible():
            self.zoom_window.update_image(arr)
            self.zoom_window.setWindowTitle(f"{self.title} - 切片 {idx+1}/{self.max_index}")



# 由于使用TKAGG后端，不再需要QtWidgets中的MatplotlibCanvas类
# 我们将在运行时直接使用plt.figure()创建图形


class VolumeViewer(QtWidgets.QFrame):
    """基于 VTK 的三维体渲染视图，可以嵌入到 PyQt 界面中（内存优化版）"""

    def __init__(self, volume_array, spacing=(1.0, 1.0, 1.0), simplified=False, downsample_factor=None):
        """
        参数
        ----
        volume_array : np.ndarray
            三维体数据 (z, y, x)，例如 CT 扫描数据，通常是 uint16。
        spacing : tuple of float
            像素间距 (sx, sy, sz)，默认为 (1.0, 1.0, 1.0)。
        simplified : bool
            是否使用简化渲染模式，默认为 False。
            如果为 True，则仅显示3D图像，不应用高级渲染效果。
        downsample_factor : int, optional
            降采样因子。如果为None，则自动计算。对于大数据会自动降采样以节省内存。
        """
        super().__init__()

        # ========= 0. 内存优化：对大数据进行降采样 =========
        original_shape = volume_array.shape
        z, y, x = original_shape
        
        # 自动计算降采样因子
        if downsample_factor is None:
            # 如果任一维度超过512，进行降采样
            max_dim = max(z, y, x)
            if max_dim > 512:
                downsample_factor = int(math.ceil(max_dim / 512))
            else:
                downsample_factor = 1
        
        # 执行降采样
        if downsample_factor > 1:
            print(f"3D视图降采样因子: {downsample_factor}, 原始大小: {original_shape}")
            volume_array = volume_array[::downsample_factor, ::downsample_factor, ::downsample_factor].copy()
            spacing = (spacing[0]*downsample_factor, spacing[1]*downsample_factor, spacing[2]*downsample_factor)
            print(f"降采样后大小: {volume_array.shape}, 新间距: {spacing}")

        # ========= 1. 在 Qt 中嵌入 VTK 窗口 =========
        self.vtkWidget = QVTKRenderWindowInteractor(self)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.vtkWidget)
        self.setLayout(layout)

        # ========= 2. 将 NumPy 数据导入 VTK =========
        importer = vtk.vtkImageImport()
        data_string = volume_array.tobytes()  # 转为字节流
        importer.CopyImportVoidPointer(data_string, len(data_string))  # 传入 VTK
        importer.SetDataScalarTypeToUnsignedShort()  # 数据类型：uint16
        importer.SetNumberOfScalarComponents(1)      # 单通道（灰度）

        # 设置数据维度信息
        z, y, x = volume_array.shape
        importer.SetWholeExtent(0, x - 1, 0, y - 1, 0, z - 1)  # 数据范围
        importer.SetDataExtentToWholeExtent()
        importer.SetDataSpacing(spacing)  # 设置体素间距

        if not simplified:
            # 标准渲染模式 - 使用全功能体渲染
            # ========= 3. 映射器 (Mapper) =========
            volume_mapper = vtk.vtkGPUVolumeRayCastMapper()
            volume_mapper.SetInputConnection(importer.GetOutputPort())  # 输入数据

            # ========= 4. 颜色映射 (灰度 → RGB) =========
            color_func = vtk.vtkColorTransferFunction()
            color_func.AddRGBPoint(0,     0.0, 0.0, 0.0)   # 黑色
            color_func.AddRGBPoint(65535, 1.0, 1.0, 1.0)   # 白色

            # ========= 5. 透明度映射 =========
            opacity_func = vtk.vtkPiecewiseFunction()
            opacity_func.AddPoint(0,     0.0)  # HU=0 完全透明
            opacity_func.AddPoint(65535, 1.0)  # HU=65535 完全不透明

            # ========= 6. 渲染属性 =========
            volume_property = vtk.vtkVolumeProperty()
            volume_property.SetColor(color_func)              # 设置颜色映射
            volume_property.SetScalarOpacity(opacity_func)    # 设置透明度映射
            volume_property.ShadeOn()                         # 开启光照
            volume_property.SetInterpolationTypeToLinear()    # 线性插值

            # ========= 7. 创建体数据对象 (Volume) =========
            volume = vtk.vtkVolume()
            volume.SetMapper(volume_mapper)
            volume.SetProperty(volume_property)

            # ========= 8. 渲染器 Renderer =========
            renderer = vtk.vtkRenderer()
            renderer.AddVolume(volume)              # 添加体数据
            renderer.SetBackground(0.1, 0.1, 0.1)   # 背景颜色
        else:
            # 简化渲染模式 - 使用标准体渲染但简化传输函数
            # 这样可以保留3D结构同时提高清晰度
            
            # 使用GPU光线投射映射器，优化CT数据的体绘制
            volume_mapper = vtk.vtkGPUVolumeRayCastMapper()
            volume_mapper.SetInputConnection(importer.GetOutputPort())  # 输入数据
            volume_mapper.SetBlendModeToComposite()  # 使用复合模式进行体渲染
            volume_mapper.SetSampleDistance(0.5)     # 设置较小的采样距离，提高质量
            volume_mapper.SetAutoAdjustSampleDistances(True)  # 自动调整采样距离
            # 对CT数据设置更合适的MIP模式
            # volume_mapper.SetBlendModeToMaximumIntensity()  # MIP渲染模式，适合显示高对比度结构
            
            # 动态确定数据范围，避免硬编码阈值
            scalar_range = [0, 65535]  # 默认范围
            
            # 尝试从数据中确定实际范围并计算合适的阈值
            try:
                if hasattr(volume_array, 'min') and hasattr(volume_array, 'max'):
                    min_val = float(volume_array.min())
                    max_val = float(volume_array.max())
                    
                    # 如果有足够的数据范围，则使用直方图分析确定更合适的阈值
                    if max_val > min_val and volume_array.size > 1000:
                        # 计算数据直方图
                        try:
                            import numpy as np
                            flat_data = volume_array.flatten()
                            hist, bins = np.histogram(flat_data, bins=100)
                            
                            # 使用累积分布确定合适的低阈值和高阈值
                            # 去除最低的10%值（通常是噪声或背景）
                            cumsum = np.cumsum(hist)
                            total_pixels = cumsum[-1]
                            
                            # 找到10%和90%的像素值
                            low_idx = np.where(cumsum >= total_pixels * 0.10)[0][0]
                            high_idx = np.where(cumsum >= total_pixels * 0.90)[0][0]
                            
                            lower_threshold = bins[low_idx]
                            upper_threshold = bins[high_idx]
                            
                            scalar_range = [lower_threshold, upper_threshold]
                        except:
                            # 如果直方图分析失败，则使用简单的百分比阈值
                            lower_threshold = min_val + (max_val - min_val) * 0.10  # 低于10%的值视为背景
                            upper_threshold = min_val + (max_val - min_val) * 0.90  # 保留90%的有效范围
                            scalar_range = [lower_threshold, upper_threshold]
                    else:
                        # 简单的范围缩放
                        scalar_range = [min_val, max_val]
            except Exception as e:
                print(f"计算3D阈值时出错: {str(e)}")
                # 如果失败则使用默认范围
                scalar_range = [0, 65535]
            
            print(f"3D视图数据范围: {scalar_range}")
            
            # 分析数据直方图以获取更准确的阈值
            try:
                import numpy as np
                flat_data = volume_array.flatten()
                
                # 使用直方图分析确定更合理的阈值
                hist, bins = np.histogram(flat_data, bins=200)
                cumsum = np.cumsum(hist)
                total_pixels = cumsum[-1]
                
                # 找到对应百分比的阈值点
                # 使用更高的起始阈值，确保背景被剔除
                low_idx = np.where(cumsum >= total_pixels * 0.50)[0][0]  # 忽略低于50%的值
                threshold = bins[low_idx]
                
                print(f"CT数据直方图分析: 有效阈值 = {threshold}")
            except Exception as e:
                print(f"直方图分析失败: {e}")
                # 如果直方图分析失败，使用简单的阈值
                threshold = scalar_range[0] + (scalar_range[1] - scalar_range[0]) * 0.5
            
            # 创建专为CT数据优化的灰度颜色映射
            color_func = vtk.vtkColorTransferFunction()
            # 使用灰度模式 - 但增加中间色调以提高结构可见性
            color_func.AddRGBPoint(scalar_range[0], 0.0, 0.0, 0.0)  # 背景为黑色
            color_func.AddRGBPoint(threshold * 0.9, 0.2, 0.2, 0.2)  # 阈值附近的低值为深灰色
            color_func.AddRGBPoint(threshold, 0.7, 0.7, 0.7)        # 阈值处为中灰色
            color_func.AddRGBPoint(scalar_range[1], 1.0, 1.0, 1.0)  # 最高值为纯白
            
            # 创建更适合CT数据的不透明度映射
            opacity_func = vtk.vtkPiecewiseFunction()
            # 使用陡峭的不透明度曲线，阈值处明显变化
            opacity_func.AddPoint(scalar_range[0], 0.00)        # 低值完全透明(背景)
            opacity_func.AddPoint(threshold * 0.95, 0.00)       # 阈值之下略微透明
            opacity_func.AddPoint(threshold, 0.7)               # 阈值处突然变不透明
            opacity_func.AddPoint(scalar_range[1], 1.0)         # 最高值完全不透明
            
            # 设置体渲染属性，优化CT数据显示
            volume_property = vtk.vtkVolumeProperty()
            volume_property.SetColor(color_func)              # 设置颜色映射
            volume_property.SetScalarOpacity(opacity_func)    # 设置透明度映射
            
            # 优化光照设置以增强CT数据的细节
            volume_property.ShadeOn()                 # 开启光照
            volume_property.SetAmbient(0.2)          # 环境光较少
            volume_property.SetDiffuse(0.9)          # 增强漫反射，提高结构细节
            volume_property.SetSpecular(0.3)         # 适当高光，增加立体感
            volume_property.SetSpecularPower(15)     # 高光强度和集中度
            
            # 线性插值提高质量
            volume_property.SetInterpolationTypeToLinear()
            
            # 启用梯度不透明度，让结构边缘更清晰
            gradient_opacity = vtk.vtkPiecewiseFunction()
            gradient_opacity.AddPoint(0,   0.0)    # 平坦区域（低梯度）更透明
            gradient_opacity.AddPoint(10,  0.5)    # 中等梯度部分透明
            gradient_opacity.AddPoint(20,  1.0)    # 边缘（高梯度）不透明
            volume_property.SetGradientOpacity(gradient_opacity)
            
            # 创建体数据对象
            volume = vtk.vtkVolume()
            volume.SetMapper(volume_mapper)
            volume.SetProperty(volume_property)
            
            # 创建渲染器
            renderer = vtk.vtkRenderer()
            renderer.AddVolume(volume)              # 添加体数据
            renderer.SetBackground(0.1, 0.1, 0.2)   # 背景颜色偏蓝，增强对比度
            
            # 设置为CT数据优化的相机视角
            renderer.ResetCamera()  # 首先重置相机以适应数据
            
            camera = renderer.GetActiveCamera()
            camera.Elevation(30)      # 较高的仰角，便于观察内部结构
            camera.Azimuth(45)        # 45度方位角，提供立体感
            camera.Zoom(1.3)          # 稍微放大
            camera.Roll(0)            # 确保没有倾斜
            
            # 设置高质量渲染
            renWin = self.vtkWidget.GetRenderWindow()
            renWin.SetMultiSamples(4)  # 抗锯齿
            
            # 启用高级渲染选项
            renderer.SetUseFXAA(True)        # 抗锯齿
            renderer.SetTwoSidedLighting(True)  # 双面光照
            
            # 设置CT数据专用的相机裁剪范围
            camera_range = camera.GetClippingRange()
            camera.SetClippingRange(camera_range[0] * 0.1, camera_range[1] * 2.0)  # 扩展裁剪范围

        # ========= 9. 渲染窗口 =========
        renWin = self.vtkWidget.GetRenderWindow()
        renWin.AddRenderer(renderer)

        # ========= 10. 交互器 =========
        iren = renWin.GetInteractor()
        iren.Initialize()
        
        # 保存关键对象供后续访问
        self.renderer = renderer
        self.mapper = volume_mapper if 'volume_mapper' in locals() else None
        self.property = volume_property if 'volume_property' in locals() else None
        
    def adjust_contrast(self, opacity_scale=1.0, contrast_scale=1.0):
        """
        调整3D视图的对比度和不透明度
        
        参数
        ----
        opacity_scale : float
            不透明度缩放因子，>1增加不透明度，<1降低不透明度
        contrast_scale : float
            对比度缩放因子，>1增加对比度，<1降低对比度
        """
        if not hasattr(self, 'property') or self.property is None:
            return
            
        # 获取当前的不透明度函数
        opacity_func = self.property.GetScalarOpacity()
        
        # 调整每个控制点的不透明度
        if opacity_func:
            # 这个循环和调整不透明度的方法似乎无法正常工作
            # 使用更简单的方法 - 直接重新定义不透明度函数
            # 获取数据范围
            if hasattr(self, 'mapper') and self.mapper:
                input_data = self.mapper.GetInput()
                if input_data:
                    scalar_range = input_data.GetScalarRange()
                    
                    # 创建新的不透明度函数
                    new_opacity_func = vtk.vtkPiecewiseFunction()
                    # 使用简单灰度显示，不使用复杂的颜色渲染
                    new_opacity_func.AddPoint(scalar_range[0], 0.0)  # 低值完全透明
                    new_opacity_func.AddPoint(scalar_range[0] + (scalar_range[1]-scalar_range[0])*0.2, 0.0)  # 较低值也透明
                    new_opacity_func.AddPoint(scalar_range[0] + (scalar_range[1]-scalar_range[0])*0.5, 0.5 * opacity_scale)  # 中间值半透明
                    new_opacity_func.AddPoint(scalar_range[1], 0.8 * opacity_scale)  # 高值不透明
                    
                    # 设置新的不透明度函数
                    self.property.SetScalarOpacity(new_opacity_func)
                
        # 强制更新渲染
        if hasattr(self, 'renderer') and self.renderer:
            self.renderer.GetRenderWindow().Render()



class CTViewer4(QtWidgets.QMainWindow):
    """
    四宫格 CT 浏览器：
    - 左上：Axial（横断面）切片 + 滑动条
    - 右上：Sagittal（矢状面）切片 + 滑动条
    - 左下：Coronal（冠状面）切片 + 滑动条
    - 右下：VTK 三维体渲染窗口
    
    功能菜单：
    - 文件操作：导入文件
    - 滤波：各向异性平滑
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
        
        # 如果提供了文件名，则加载数据
        if filename:
            self.load_data(filename, shape, spacing, dtype)
    
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
    
    def on_window_level_changed(self):
        """窗宽窗位改变时的处理"""
        if self.raw_array is None:
            return
        
        self.window_width = self.ww_slider.value()
        self.window_level = self.wl_slider.value()
        self.ww_value.setText(str(int(self.window_width)))
        self.wl_value.setText(str(int(self.window_level)))
        
        # 不再预先处理整个数据集，只在显示时处理单个切片
        # self.apply_window_level_to_data()  # 注释掉，避免内存问题
        
        # 更新所有视图
        self.update_all_views()
    
    def reset_window_level(self):
        """重置窗宽窗位"""
        if self.raw_array is None:
            return
        
        # 计算数据范围
        data_min = float(self.raw_array.min())
        data_max = float(self.raw_array.max())
        
        # 重置为全范围
        self.window_width = int(data_max - data_min)
        self.window_level = int((data_max + data_min) / 2)
        
        self.ww_slider.setValue(self.window_width)
        self.wl_slider.setValue(self.window_level)
    
    def apply_window_level_to_slice(self, slice_array):
        """将窗宽窗位应用到单个切片（内存高效）"""
        if slice_array is None:
            return slice_array
        
        # 计算窗口的最小值和最大值
        ww_min = self.window_level - self.window_width / 2.0
        ww_max = self.window_level + self.window_width / 2.0
        
        # 检查窗宽是否为0，避免除零错误
        if ww_max - ww_min <= 0:
            return slice_array
        
        # 应用窗宽窗位到切片（内存高效）
        temp_slice = slice_array.astype(np.float32)
        temp_slice = (temp_slice - ww_min) / (ww_max - ww_min) * 65535.0
        np.clip(temp_slice, 0, 65535, out=temp_slice)
        
        return temp_slice.astype(np.uint16)
    
    def apply_window_level_to_data(self):
        """将窗宽窗位应用到整个数据集（已弃用，保留以兼容旧代码）"""
        # 此方法已弃用，不再使用，以避免大数据集的内存问题
        # 窗宽窗位现在在显示切片时实时应用
        pass
    
    def update_all_views(self):
        """更新所有2D视图"""
        if self.axial_viewer:
            self.axial_viewer.update_slice(self.axial_viewer.slider.value())
        if self.sag_viewer:
            self.sag_viewer.update_slice(self.sag_viewer.slider.value())
        if self.cor_viewer:
            self.cor_viewer.update_slice(self.cor_viewer.slider.value())
    
    def import_file(self):
        """导入文件对话框"""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 
            "选择医学影像文件", 
            "", 
            "医学影像文件 (*.nii *.nii.gz *.mhd *.dcm *.raw);;所有文件 (*)"
        )
        
        if filename:
            # 如果选择了.raw文件，则需要询问维度
            if filename.endswith('.raw'):
                dialog = QtWidgets.QDialog(self)
                dialog.setWindowTitle("输入RAW文件维度")
                
                form_layout = QtWidgets.QFormLayout(dialog)
                
                z_input = QtWidgets.QSpinBox()
                z_input.setRange(1, 2000)
                z_input.setValue(512)
                form_layout.addRow("Z 维度:", z_input)
                
                y_input = QtWidgets.QSpinBox()
                y_input.setRange(1, 2000)
                y_input.setValue(512)
                form_layout.addRow("Y 维度:", y_input)
                
                x_input = QtWidgets.QSpinBox()
                x_input.setRange(1, 2000)
                x_input.setValue(512)
                form_layout.addRow("X 维度:", x_input)
                
                button_box = QtWidgets.QDialogButtonBox(
                    QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
                )
                button_box.accepted.connect(dialog.accept)
                button_box.rejected.connect(dialog.reject)
                form_layout.addRow(button_box)
                
                if dialog.exec_() == QtWidgets.QDialog.Accepted:
                    shape = (z_input.value(), y_input.value(), x_input.value())
                    self.load_data(filename, shape)
            else:
                # 对于其他格式，直接加载
                self.load_data(filename)
    
    def load_data(self, filename, shape=None, spacing=None, dtype=np.uint16):
        """加载CT数据并更新视图"""
        try:
            # 清除旧的视图组件
            self.clear_viewers()
            
            # 读取CT数据
            CTdata = CTImageData(filename, shape, spacing)
            self.image = CTdata.image
            self.array = CTdata.array
            
            # 检查数据类型并获取尺寸
            original_dtype = self.array.dtype
            print(f"原始数据类型: {original_dtype}, 形状: {self.array.shape}")
            
            # 检查是否为RGB图像
            # NIfTI的RGB图像可能是 (3, Z, Y, X) 或 (Z, Y, X, 3) 格式
            is_rgb = False
            
            if len(self.array.shape) == 4:
                # 检查是否为 (Z, Y, X, 3/4) 格式
                if self.array.shape[3] in [3, 4]:
                    is_rgb = True
                    print(f"检测到RGB图像（通道在最后）: {self.array.shape}")
                    self.rgb_array = self.array.copy()
                    self.depth_z, self.depth_y, self.depth_x = self.array.shape[:3]
                # 检查是否为 (3/4, Z, Y, X) 格式（NIfTI常见格式）
                elif self.array.shape[0] in [3, 4]:
                    is_rgb = True
                    print(f"检测到RGB图像（通道在最前）: {self.array.shape}")
                    # 需要转置维度: (C, Z, Y, X) -> (Z, Y, X, C)
                    self.rgb_array = np.transpose(self.array, (1, 2, 3, 0))
                    print(f"转置后形状: {self.rgb_array.shape}")
                    self.depth_z, self.depth_y, self.depth_x = self.rgb_array.shape[:3]
                else:
                    # 其他4D格式，按普通3D处理
                    is_rgb = False
                    self.depth_z, self.depth_y, self.depth_x = self.array.shape[:3]
            else:
                # 3D或其他维度
                is_rgb = False
                if len(self.array.shape) == 3:
                    self.depth_z, self.depth_y, self.depth_x = self.array.shape
            
            # 获取spacing，确保只有3个值（x, y, z）
            spacing_raw = self.image.GetSpacing()
            if len(spacing_raw) > 3:
                # RGB图像可能有4个spacing值，只取前3个（忽略颜色通道）
                self.spacing = spacing_raw[:3]
                print(f"Spacing从{len(spacing_raw)}维调整为3维: {self.spacing}")
            else:
                self.spacing = spacing_raw
            
            if is_rgb:
                print(f"RGB数组形状: {self.rgb_array.shape}")
                print(f"数据尺寸: Z={self.depth_z}, Y={self.depth_y}, X={self.depth_x}")
                print(f"Spacing: {self.spacing}")
                
                # 为了3D显示，将RGB转换为灰度
                # 使用标准RGB转灰度公式: Y = 0.299*R + 0.587*G + 0.114*B
                # 使用转置后的rgb_array (Z, Y, X, 3)
                if self.rgb_array.shape[3] >= 3:
                    gray = (0.299 * self.rgb_array[:,:,:,0] + 
                           0.587 * self.rgb_array[:,:,:,1] + 
                           0.114 * self.rgb_array[:,:,:,2])
                    # 转换为uint16以供VolumeViewer使用
                    if self.rgb_array.dtype == np.uint8:
                        self.array = (gray.astype(np.float32) * 257).astype(np.uint16)
                    else:
                        self.array = gray.astype(np.uint16)
                    print(f"RGB已转换为灰度用于3D显示，范围: [{self.array.min()}, {self.array.max()}]")
            else:
                # 非RGB图像，保持原有逻辑
                self.rgb_array = None
                
                if self.array.dtype == np.uint8:
                    # 将uint8转换为uint16，扩展到完整范围
                    print("检测到uint8数据，转换为uint16以便3D显示")
                    # 方案：uint8的0-255映射到uint16的0-65535
                    self.array = (self.array.astype(np.float32) * 257).astype(np.uint16)
                elif self.array.dtype != np.uint16:
                    # 其他类型也转换为uint16
                    print(f"转换数据类型 {self.array.dtype} -> uint16")
                    data_min = self.array.min()
                    data_max = self.array.max()
                    if data_max > data_min:
                        self.array = ((self.array - data_min) / (data_max - data_min) * 65535).astype(np.uint16)
                    else:
                        self.array = self.array.astype(np.uint16)
            
            # 检查数据范围，判断是否为分割结果
            data_min = float(self.array.min())
            data_max = float(self.array.max())
            print(f"转换后数据范围: [{data_min}, {data_max}]")
            
            # 如果数据范围很小或全为0，可能是分割结果且没有检测到目标
            if data_max == 0 or (data_max - data_min) < 1:
                QtWidgets.QMessageBox.warning(
                    self,
                    "数据警告",
                    f"加载的数据范围异常: [{data_min}, {data_max}]\n\n"
                    "这可能是分割结果但未检测到任何目标区域。\n"
                    "建议检查：\n"
                    "1. 输入数据是否正确\n"
                    "2. 模型权重是否匹配\n"
                    "3. 分割阈值是否需要调整"
                )
            
            # 创建三个方向的切片视图
            # 如果有RGB数据，使用RGB数组；否则使用灰度数组
            if hasattr(self, 'rgb_array') and self.rgb_array is not None:
                # RGB图像的切片获取
                # 横断面 (Axial)，沿 z 轴浏览
                self.axial_viewer = SliceViewer("Axial (彩色)",
                                          lambda z: self.rgb_array[z, :, :, :],
                                          self.depth_z)
                # 矢状面 (Sagittal)，沿 x 轴浏览
                self.sag_viewer = SliceViewer("Sagittal (彩色)",
                                        lambda x: self.rgb_array[:, :, x, :],
                                        self.depth_x)
                # 冠状面 (Coronal)，沿 y 轴浏览
                self.cor_viewer = SliceViewer("Coronal (彩色)",
                                        lambda y: self.rgb_array[:, y, :, :],
                                        self.depth_y)
            else:
                # 灰度图像的切片获取
                # 横断面 (Axial)，沿 z 轴浏览
                self.axial_viewer = SliceViewer("Axial",
                                          lambda z: self.array[z, :, :],
                                          self.depth_z)
                # 矢状面 (Sagittal)，沿 x 轴浏览
                self.sag_viewer = SliceViewer("Sagittal",
                                        lambda x: self.array[:, :, x],
                                        self.depth_x)
                # 冠状面 (Coronal)，沿 y 轴浏览
                self.cor_viewer = SliceViewer("Coronal",
                                        lambda y: self.array[:, y, :],
                                        self.depth_y)
            
            # 只有在数据不全为0时才创建3D视图（使用灰度版本）
            if data_max > 0:
                # 创建三维体渲染视图（禁用降采样）
                self.volume_viewer = VolumeViewer(self.array, self.spacing, simplified=True, downsample_factor=1)
                
                # 四宫格布局
                self.grid_layout.addWidget(self.axial_viewer, 0, 0)  # 左上
                self.grid_layout.addWidget(self.sag_viewer, 0, 1)    # 右上
                self.grid_layout.addWidget(self.cor_viewer, 1, 0)    # 左下
                self.grid_layout.addWidget(self.volume_viewer, 1, 1) # 右下
            else:
                # 数据全为0，只显示2D视图
                print("数据全为0，跳过3D视图创建")
                self.grid_layout.addWidget(self.axial_viewer, 0, 0)  # 左上
                self.grid_layout.addWidget(self.sag_viewer, 0, 1)    # 右上
                self.grid_layout.addWidget(self.cor_viewer, 1, 0)    # 左下
                
                # 在右下角显示提示信息
                info_label = QtWidgets.QLabel("3D视图不可用\n(数据全为0)")
                info_label.setAlignment(QtCore.Qt.AlignCenter)
                info_label.setStyleSheet("QLabel { background-color: #f0f0f0; color: #666; font-size: 14pt; }")
                self.grid_layout.addWidget(info_label, 1, 1)
            
            # 更新显示
            self.setWindowTitle(f"CT Viewer - {os.path.basename(filename)}")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "错误", f"加载文件时出错：{str(e)}")
    
    def clear_viewers(self):
        """清除现有的视图组件"""
        # 清除grid_layout中的所有widget
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 重置视图引用
        self.axial_viewer = None
        self.sag_viewer = None
        self.cor_viewer = None
        self.volume_viewer = None
    
    def apply_anisotropic_filter(self):
        """应用各向异性平滑滤波"""
        if not hasattr(self, 'array') or self.array is None:
            QtWidgets.QMessageBox.warning(self, "警告", "请先加载数据")
            return
            
        try:
            # 创建滤波器对象
            filter_op = Filter_op()
            
            # 创建进度对话框
            progress = QtWidgets.QProgressDialog("应用各向异性平滑滤波...", "取消", 0, 0, self)
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.show()
            QtWidgets.QApplication.processEvents()
              # 调用滤波函数，不在滤波函数内部显示进度对话框
            filtered_array = filter_op.apply_anisotropic_filter(
                self.array, 
                spacing=self.spacing
            )
            
            # 关闭进度对话框
            progress.close()
            
            if filtered_array is not None:
                # 更新当前数组
                self.array = filtered_array
                
                # 显示成功消息
                QtWidgets.QMessageBox.information(self, "成功", "滤波处理完成，正在更新视图...")
                QtWidgets.QApplication.processEvents()
                
                # 更新视图
                self.update_viewers()
                
                # 通知用户完成
                QtWidgets.QMessageBox.information(self, "成功", "视图已更新")
            else:
                QtWidgets.QMessageBox.warning(self, "警告", "滤波处理未返回结果")
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"应用滤波时出错：{str(e)}")
    
    def apply_curvature_flow_filter(self):
        """应用曲率流去噪滤波"""
        if not hasattr(self, 'array') or self.array is None:
            QtWidgets.QMessageBox.warning(self, "警告", "请先加载数据")
            return
            
        try:
            # 弹出参数设置对话框
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("曲率流去噪参数")
            
            form_layout = QtWidgets.QFormLayout(dialog)
            
            iterations_input = QtWidgets.QSpinBox()
            iterations_input.setRange(1, 100)
            iterations_input.setValue(10)
            form_layout.addRow("迭代次数:", iterations_input)
            
            time_step_input = QtWidgets.QDoubleSpinBox()
            time_step_input.setRange(0.001, 0.1)
            time_step_input.setSingleStep(0.005)
            time_step_input.setDecimals(4)
            time_step_input.setValue(0.0625)
            form_layout.addRow("时间步长:", time_step_input)
            
            button_box = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
            )
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            form_layout.addRow(button_box)
            
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                # 创建滤波器对象
                filter_op = Filter_op()
                
                # 获取参数
                num_iterations = iterations_input.value()
                time_step = time_step_input.value()
                
                # 创建进度对话框
                progress = QtWidgets.QProgressDialog(f"应用曲率流去噪...\n迭代次数: {num_iterations}, 时间步长: {time_step}", "取消", 0, 0, self)
                progress.setWindowModality(QtCore.Qt.WindowModal)
                progress.show()
                QtWidgets.QApplication.processEvents()
                
                # 调用滤波函数
                filtered_array = filter_op.apply_curvature_flow_filter(
                    self.array, 
                    num_iterations=num_iterations,
                    time_step=time_step,
                    spacing=self.spacing
                )
                
                # 关闭进度对话框
                progress.close()
                
                if filtered_array is not None:
                    # 更新当前数组
                    self.array = filtered_array
                    
                    # 显示成功消息
                    QtWidgets.QMessageBox.information(self, "成功", "曲率流去噪完成，正在更新视图...")
                    QtWidgets.QApplication.processEvents()
                    
                    # 更新视图
                    self.update_viewers()
                    
                    # 通知用户完成
                    QtWidgets.QMessageBox.information(self, "成功", "视图已更新")
                else:
                    QtWidgets.QMessageBox.warning(self, "警告", "滤波处理未返回结果")
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"应用曲率流去噪时出错：{str(e)}")
    
    def update_viewers(self):
        """更新所有视图"""
        # 清除现有的视图组件
        self.clear_viewers()
        
        # 重新创建视图组件
        # 横断面 (Axial)，沿 z 轴浏览
        self.axial_viewer = SliceViewer("Axial",
                                  lambda z: self.array[z, :, :],
                                  self.depth_z)
        # 矢状面 (Sagittal)，沿 x 轴浏览
        self.sag_viewer = SliceViewer("Sagittal",
                                lambda x: self.array[:, :, x],
                                self.depth_x)
        # 冠状面 (Coronal)，沿 y 轴浏览
        self.cor_viewer = SliceViewer("Coronal",
                                lambda y: self.array[:, y, :],
                                self.depth_y)
        
        # 创建简化版3D体渲染视图（右下角，禁用降采样）
        self.volume_viewer = VolumeViewer(self.array, self.spacing, simplified=True, downsample_factor=1)
        
        # 应用与load_reconstructed_data相同的3D视图参数调整
        self.volume_viewer.adjust_contrast(opacity_scale=1.5)
        
        # 四视图布局
        self.grid_layout.addWidget(self.axial_viewer, 0, 0)  # 左上
        self.grid_layout.addWidget(self.sag_viewer, 0, 1)    # 右上
        self.grid_layout.addWidget(self.cor_viewer, 1, 0)    # 左下
        self.grid_layout.addWidget(self.volume_viewer, 1, 1) # 右下
        
    def load_reconstructed_data(self, image, array, title="重建数据"):
        """
        加载CT重建的数据并在四视图中显示
        
        参数
        ----
        image : sitk.Image
            SimpleITK图像对象
        array : np.ndarray
            原始三维数组，形状为(z, y, x)
        title : str
            窗口标题
        """
        try:
            # 清除现有的视图组件
            self.clear_viewers()
            
            # 打印调试信息
            print(f"加载重建数据: 形状={array.shape}, 类型={array.dtype}")
            print(f"数据范围: 最小值={array.min()}, 最大值={array.max()}")
            
            # 保存图像数据
            self.image = image
            
            # 处理数组数据用于显示
            # 首先确保数据范围在0-65535之间（uint16的范围）
            processed_array = array.copy()
            
            # 负值处理
            if processed_array.min() < 0:
                processed_array = processed_array - processed_array.min()
            
            # 归一化并缩放到uint16范围
            if processed_array.max() > 0:
                scale_factor = 65535.0 / processed_array.max()
                processed_array = (processed_array * scale_factor).astype(np.uint16)
            else:
                processed_array = processed_array.astype(np.uint16)
            
            # 保存处理后的数组
            self.array = processed_array
            
            # 获取尺寸信息
            self.depth_z, self.depth_y, self.depth_x = self.array.shape
            self.spacing = self.image.GetSpacing()
            
            print(f"处理后数据: 形状={self.array.shape}, 类型={self.array.dtype}")
            print(f"处理后范围: 最小值={self.array.min()}, 最大值={self.array.max()}")
            
            # 创建进度对话框
            progress = QtWidgets.QProgressDialog("正在创建视图...", "取消", 0, 4, self)
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.setValue(0)
            progress.show()
            QtWidgets.QApplication.processEvents()
            
            # 重新创建视图组件
            # 横断面 (Axial)，沿 z 轴浏览
            self.axial_viewer = SliceViewer("Axial",
                                      lambda z: self.array[z, :, :],
                                      self.depth_z)
            progress.setValue(1)
            QtWidgets.QApplication.processEvents()
            
            # 矢状面 (Sagittal)，沿 x 轴浏览
            self.sag_viewer = SliceViewer("Sagittal",
                                    lambda x: self.array[:, :, x],
                                    self.depth_x)
            progress.setValue(2)
            QtWidgets.QApplication.processEvents()
            
            # 冠状面 (Coronal)，沿 y 轴浏览
            self.cor_viewer = SliceViewer("Coronal",
                                    lambda y: self.array[:, y, :],
                                    self.depth_y)
            progress.setValue(3)
            QtWidgets.QApplication.processEvents()
            
            # 创建简化版3D体渲染视图（右下角，禁用降采样）
            self.volume_viewer = VolumeViewer(self.array, self.spacing, simplified=True, downsample_factor=1)
            
            # 针对重建数据特点自动调整3D视图参数
            # CT数据的不透明度可能需要增强以显示内部结构
            self.volume_viewer.adjust_contrast(opacity_scale=1.5)
            
            progress.setValue(4)
            QtWidgets.QApplication.processEvents()
            
            # 四视图布局
            self.grid_layout.addWidget(self.axial_viewer, 0, 0)  # 左上
            self.grid_layout.addWidget(self.sag_viewer, 0, 1)    # 右上
            self.grid_layout.addWidget(self.cor_viewer, 1, 0)    # 左下
            self.grid_layout.addWidget(self.volume_viewer, 1, 1)  # 右下
            
            # 关闭进度对话框
            progress.close()
            
            # 更新窗口标题
            self.setWindowTitle(f"CT Viewer - {title}")
            
            # 显示成功消息
            QtWidgets.QMessageBox.information(self, "成功", f"已加载{title}")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "错误", f"加载重建数据时出错：{str(e)}")
    
    def load_reconstructed_data_no_copy(self, data_array, spacing, title="重建数据"):
        """
        加载CT重建的数据并在四视图中显示（内存优化版本，不创建数据副本）
        
        参数
        ----
        data_array : np.ndarray
            LEAP重建的原始数组（直接引用，不会复制）
        spacing : tuple
            体素间距，形式为(sx, sy, sz)
        title : str
            窗口标题
        """
        try:
            # 清除现有的视图组件
            self.clear_viewers()
            
            # 打印调试信息
            print(f"加载重建数据（无副本模式）: 形状={data_array.shape}, 类型={data_array.dtype}")
            print(f"原始数据范围: 最小值={np.min(data_array)}, 最大值={np.max(data_array)}")
            
            # 创建进度对话框
            progress = QtWidgets.QProgressDialog("正在处理重建数据...", "取消", 0, 100, self)
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.setValue(0)
            progress.show()
            QtWidgets.QApplication.processEvents()
            
            # 获取数据统计信息（不创建副本）
            data_min = float(np.min(data_array))
            data_max = float(np.max(data_array))
            
            progress.setValue(10)
            progress.setLabelText("计算归一化参数...")
            QtWidgets.QApplication.processEvents()
            
            # 计算归一化参数
            if data_min < 0:
                offset = -data_min
            else:
                offset = 0.0
            
            if data_max + offset > 0:
                scale = 65535.0 / (data_max + offset)
            else:
                scale = 1.0
            
            print(f"归一化参数: offset={offset}, scale={scale}")
            
            progress.setValue(20)
            progress.setLabelText("创建SimpleITK图像...")
            QtWidgets.QApplication.processEvents()
            
            # 创建SimpleITK图像（这里会创建一个副本，但这是必需的）
            # 我们使用原地操作来最小化内存使用
            sitk_array = np.ascontiguousarray(data_array, dtype=np.float32)
            sitk_image = sitk.GetImageFromArray(sitk_array)
            sitk_image.SetSpacing(spacing)
            self.image = sitk_image
            
            # 设置spacing和尺寸
            self.spacing = spacing
            self.depth_z, self.depth_y, self.depth_x = data_array.shape
            
            progress.setValue(30)
            progress.setLabelText("准备显示数据...")
            QtWidgets.QApplication.processEvents()
            
            # 对于显示，我们需要uint16格式的数据
            # 使用分块处理来减少峰值内存使用
            print("开始转换为uint16格式...")
            
            # 分配uint16数组
            display_array = np.empty(data_array.shape, dtype=np.uint16)
            
            # 分块处理，减少内存峰值
            chunk_size = 100  # 每次处理100个切片
            num_slices = data_array.shape[0]
            
            for start_z in range(0, num_slices, chunk_size):
                end_z = min(start_z + chunk_size, num_slices)
                
                # 处理当前块
                chunk = data_array[start_z:end_z, :, :]
                
                # 原地处理：偏移和缩放
                if offset != 0:
                    chunk = chunk + offset
                if scale != 1.0:
                    chunk = chunk * scale
                
                # 裁剪到uint16范围并转换
                np.clip(chunk, 0, 65535, out=chunk)
                display_array[start_z:end_z, :, :] = chunk.astype(np.uint16)
                
                # 更新进度
                progress_val = 30 + int(50 * (end_z / num_slices))
                progress.setValue(progress_val)
                QtWidgets.QApplication.processEvents()
                
                print(f"已处理 {end_z}/{num_slices} 切片")
            
            # 保存原始数据（不再预先创建display_array副本，节省内存）
            self.raw_array = display_array  # 保存为原始数据（uint16格式）
            self.array = self.raw_array  # 兼容旧代码
            
            print(f"转换完成: 形状={self.raw_array.shape}, 类型={self.raw_array.dtype}")
            print(f"显示数据范围: 最小值={self.raw_array.min()}, 最大值={self.raw_array.max()}")
            
            # 初始化窗宽窗位控制
            data_min = int(self.raw_array.min())
            data_max = int(self.raw_array.max())
            self.window_width = data_max - data_min
            self.window_level = (data_max + data_min) // 2
            
            # 更新滑动条范围和值
            self.ww_slider.setMaximum(data_max)
            self.ww_slider.setValue(self.window_width)
            self.wl_slider.setMaximum(data_max)
            self.wl_slider.setValue(self.window_level)
            self.ww_value.setText(str(self.window_width))
            self.wl_value.setText(str(self.window_level))
            
            # 显示窗宽窗位控制面板
            self.ww_wl_panel.show()
            
            progress.setValue(85)
            progress.setLabelText("创建2D视图...")
            QtWidgets.QApplication.processEvents()
            
            # 重新创建视图组件（从raw_array获取并实时应用窗宽窗位）
            # 横断面 (Axial)，沿 z 轴浏览
            self.axial_viewer = SliceViewer("Axial",
                                      lambda z: self.apply_window_level_to_slice(self.raw_array[z, :, :]),
                                      self.depth_z,
                                      parent_viewer=self)
            
            # 矢状面 (Sagittal)，沿 x 轴浏览
            self.sag_viewer = SliceViewer("Sagittal",
                                    lambda x: self.apply_window_level_to_slice(self.raw_array[:, :, x]),
                                    self.depth_x,
                                    parent_viewer=self)
            
            # 冠状面 (Coronal)，沿 y 轴浏览
            self.cor_viewer = SliceViewer("Coronal",
                                    lambda y: self.apply_window_level_to_slice(self.raw_array[:, y, :]),
                                    self.depth_y,
                                    parent_viewer=self)
            
            progress.setValue(90)
            progress.setLabelText("创建3D视图（这可能需要较长时间）...")
            QtWidgets.QApplication.processEvents()
            
            # 创建简化版3D体渲染视图（右下角，禁用降采样）
            self.volume_viewer = VolumeViewer(self.raw_array, self.spacing, simplified=True, downsample_factor=1)
            
            # 针对重建数据特点自动调整3D视图参数
            self.volume_viewer.adjust_contrast(opacity_scale=1.5)
            
            progress.setValue(95)
            progress.setLabelText("布局视图...")
            QtWidgets.QApplication.processEvents()
            
            # 四视图布局
            self.grid_layout.addWidget(self.axial_viewer, 0, 0)  # 左上
            self.grid_layout.addWidget(self.sag_viewer, 0, 1)    # 右上
            self.grid_layout.addWidget(self.cor_viewer, 1, 0)    # 左下
            self.grid_layout.addWidget(self.volume_viewer, 1, 1)  # 右下
            
            progress.setValue(100)
            progress.close()
            
            # 更新窗口标题
            self.setWindowTitle(f"CT Viewer - {title}")
            
            print(f"成功加载 {title}")
            print(f"窗宽窗位控制已启用: WW={self.window_width}, WL={self.window_level}")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            if 'progress' in locals():
                progress.close()
            QtWidgets.QMessageBox.critical(self, "错误", f"加载重建数据时出错：{str(e)}")
        
    def run_ball_phantom_calibration(self):
        """运行多球标定程序"""
        try:
            # 创建球体标定对话框（无需先加载CT数据，因为支持模拟数据）
            dialog = BallPhantomCalibrationDialog(self)
            dialog.exec_()
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"运行多球标定程序时出错：{str(e)}")
    
    def run_helical_ct_reconstruction(self):
        """运行螺旋CT重建程序"""
        try:
            # 创建螺旋CT重建对话框
            dialog = HelicalCTReconstructionDialog(self)
            dialog.exec_()
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"运行螺旋CT重建程序时出错：{str(e)}")
    
    def run_circle_ct_reconstruction(self):
        """运行圆轨迹CT重建程序"""
        try:
            # 创建圆轨迹CT重建对话框
            dialog = CircleCTReconstructionDialog(self)
            dialog.exec_()
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"运行圆轨迹CT重建程序时出错：{str(e)}")
    
    def run_unet_segmentation(self):
        """运行UNet分割程序"""
        try:
            # 准备当前数据
            current_data = None
            if hasattr(self, 'image') and self.image is not None and hasattr(self, 'array') and self.array is not None:
                # 包含图像和数组数据
                current_data = {
                    'image': self.image,
                    'array': self.array,
                    'spacing': self.spacing if hasattr(self, 'spacing') else (1.0, 1.0, 1.0)
                }
            
            # 创建UNet分割对话框，传递当前数据
            dialog = UnetSegmentationDialog(self, current_data=current_data)
            
            # 如果用户点击了确定
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                # 获取用户输入的参数
                params = dialog.get_parameters()
                
                # 显示进度对话框
                progress = QtWidgets.QProgressDialog(
                    "正在进行分割，请稍候...", 
                    "取消", 
                    0, 
                    0, 
                    self
                )
                progress.setWindowTitle("AI分割进度")
                progress.setWindowModality(QtCore.Qt.WindowModal)
                progress.setCancelButton(None)  # 禁用取消按钮
                progress.show()
                QtWidgets.QApplication.processEvents()
                
                try:
                    # 初始化推理器（使用滑窗推理）
                    inferencer = UnetSegmentationInference(
                        checkpoint_path=params['checkpoint_path'],
                        output_dir=params['output_dir'],
                        roi_size=params['roi_size'],
                        sw_batch_size=params['sw_batch_size']
                    )
                    
                    # 执行分割 - 根据是否使用当前数据选择不同的方法
                    if params['use_current_data']:
                        # 使用当前数据进行分割
                        data = params['current_data']
                        output_filename = "current_data_segmented.nii.gz"
                        
                        # 获取affine矩阵
                        import SimpleITK as sitk
                        affine_matrix = None
                        if data['image'] is not None:
                            # 从SimpleITK图像获取affine
                            # SimpleITK使用方向矩阵和原点，需要转换为affine
                            direction = data['image'].GetDirection()
                            spacing = data['image'].GetSpacing()
                            origin = data['image'].GetOrigin()
                            
                            # 构建affine矩阵
                            import numpy as np
                            affine_matrix = np.eye(4)
                            # 设置旋转和缩放部分
                            for i in range(3):
                                for j in range(3):
                                    affine_matrix[i, j] = direction[i*3 + j] * spacing[j]
                            # 设置平移部分
                            affine_matrix[:3, 3] = origin
                        
                        result_path = inferencer.run_from_array(
                            data['array'], 
                            affine=affine_matrix,
                            output_filename=output_filename
                        )
                    else:
                        # 从文件加载进行分割
                        output_filename = os.path.basename(params['input_file']).replace('.nii', '_segmented.nii')
                        result_path = inferencer.run(params['input_file'], output_filename)
                    
                    progress.close()
                    
                    # 如果选择了融合显示，创建融合图像
                    if params['overlay_with_original']:
                        try:
                            # 创建融合图像
                            if params['use_current_data']:
                                overlay_filename = "current_data_overlay.nii.gz"
                            else:
                                overlay_filename = os.path.basename(params['input_file']).replace('.nii', '_overlay.nii')
                            overlay_path = os.path.join(params['output_dir'], overlay_filename)
                            
                            # 显示融合进度
                            overlay_progress = QtWidgets.QProgressDialog(
                                "正在创建融合图像...", 
                                None, 
                                0, 
                                0, 
                                self
                            )
                            overlay_progress.setWindowTitle("图像融合")
                            overlay_progress.setWindowModality(QtCore.Qt.WindowModal)
                            overlay_progress.show()
                            QtWidgets.QApplication.processEvents()
                            
                            # 根据是否使用当前数据选择不同的方法
                            if params['use_current_data']:
                                # 使用当前数据创建融合图像
                                # 先将当前数据保存为临时文件，然后调用融合函数
                                import tempfile
                                import SimpleITK as sitk
                                
                                temp_input = tempfile.NamedTemporaryFile(suffix='.nii.gz', delete=False)
                                temp_input.close()
                                
                                # 保存当前数据为NIfTI文件
                                sitk.WriteImage(params['current_data']['image'], temp_input.name)
                                
                                # 创建融合图像
                                create_overlay_from_files(
                                    temp_input.name,
                                    result_path,
                                    overlay_path,
                                    color=params['overlay_color'],
                                    alpha=params['overlay_alpha']
                                )
                                
                                # 删除临时文件
                                os.unlink(temp_input.name)
                            else:
                                # 从文件创建融合图像
                                create_overlay_from_files(
                                    params['input_file'],
                                    result_path,
                                    overlay_path,
                                    color=params['overlay_color'],
                                    alpha=params['overlay_alpha']
                                )
                            
                            overlay_progress.close()
                            
                            # 询问用户加载哪个结果
                            reply = QtWidgets.QMessageBox.question(
                                self,
                                "分割完成",
                                f"分割完成！\n\n"
                                f"• 分割结果: {result_path}\n"
                                f"• 融合图像: {overlay_path}\n\n"
                                f"选择要加载的图像：\n"
                                f"- 是(Y)：加载融合图像（推荐）\n"
                                f"- 否(N)：加载纯分割结果",
                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel
                            )
                            
                            if reply == QtWidgets.QMessageBox.Yes:
                                # 加载融合图像
                                self.load_data(overlay_path)
                            elif reply == QtWidgets.QMessageBox.No:
                                # 加载纯分割结果
                                self.load_data(result_path)
                            # Cancel则不加载任何图像
                            
                        except Exception as e:
                            QtWidgets.QMessageBox.warning(
                                self,
                                "融合警告",
                                f"创建融合图像时出错：{str(e)}\n\n将显示纯分割结果"
                            )
                            # 如果融合失败，仍然可以显示分割结果
                            reply = QtWidgets.QMessageBox.question(
                                self,
                                "分割完成",
                                f"分割完成！结果已保存到：\n{result_path}\n\n是否加载分割结果？",
                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                            )
                            if reply == QtWidgets.QMessageBox.Yes:
                                self.load_data(result_path)
                    else:
                        # 不使用融合，直接询问是否加载分割结果
                        reply = QtWidgets.QMessageBox.question(
                            self,
                            "分割完成",
                            f"分割完成！结果已保存到：\n{result_path}\n\n是否加载分割结果？",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                        )
                        
                        if reply == QtWidgets.QMessageBox.Yes:
                            # 加载并显示分割结果
                            self.load_data(result_path)
                        
                except Exception as e:
                    progress.close()
                    QtWidgets.QMessageBox.critical(
                        self, 
                        "分割错误", 
                        f"执行分割时出错：{str(e)}\n\n请检查：\n1. 模型权重文件是否正确\n2. 输入文件格式是否正确\n3. 是否安装了所需的依赖包(torch, monai等)"
                    )
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"运行UNet分割程序时出错：{str(e)}")



