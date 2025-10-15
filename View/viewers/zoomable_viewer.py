"""
可缩放的图像查看器组件
包含支持缩放、平移和窗宽窗位控制的查看器
"""

from PyQt5 import QtWidgets, QtCore, QtGui
import numpy as np


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

