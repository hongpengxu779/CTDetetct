"""
双边滤波（偏差滤波）对话框
用于预览和配置双边滤波参数
"""

from PyQt5 import QtWidgets, QtCore, QtGui
import numpy as np
import itk
from File.DataTransform import to_float255_fixed, to_uint16_fixed


class BilateralFilterDialog(QtWidgets.QDialog):
    """双边滤波对话框，用于预览和配置双边滤波参数"""
    
    def __init__(self, image_array, spacing=None, parent=None):
        """
        初始化双边滤波对话框
        
        参数
        ----
        image_array : numpy.ndarray
            输入的三维图像数据
        spacing : tuple, optional
            像素间距 (sx, sy, sz)
        parent : QWidget, optional
            父窗口
        """
        super().__init__(parent)
        self.setWindowTitle("双边滤波参数")
        self.setMinimumSize(600, 500)
        
        # 保存输入数据
        self.image_array = image_array
        self.spacing = spacing
        self.filtered_array = None  # 存储过滤后的结果
        
        # 当前显示的切片索引
        self.current_slice_idx = image_array.shape[0] // 2  # 默认显示中间切片
        
        # 双边滤波参数
        self.domain_sigma = 2.0
        self.range_sigma = 50.0
        # 注意：ITK的BilateralImageFilter没有迭代次数参数
        
        # 预览图像参数
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.is_dragging = False
        self.last_mouse_pos = None
        
        # 创建界面
        self.init_ui()
        
        # 初始预览
        self.update_preview()
    
    def init_ui(self):
        """初始化界面"""
        # 主布局
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # 预览区域
        preview_group = QtWidgets.QGroupBox("预览")
        preview_layout = QtWidgets.QVBoxLayout(preview_group)
        
        # 预览图像标签
        self.preview_label = QtWidgets.QLabel()
        self.preview_label.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_label.setMinimumSize(400, 300)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
            }
        """)
        self.preview_label.setMouseTracking(True)
        self.preview_label.installEventFilter(self)
        
        # 使用滚动区域包装预览标签，允许图像超出可见区域
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(self.preview_label)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        preview_layout.addWidget(scroll_area)
        
        # 切片选择滑动条
        slice_layout = QtWidgets.QHBoxLayout()
        slice_layout.addWidget(QtWidgets.QLabel("切片:"))
        
        self.slice_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slice_slider.setRange(0, self.image_array.shape[0] - 1)
        self.slice_slider.setValue(self.current_slice_idx)
        self.slice_slider.valueChanged.connect(self.on_slice_changed)
        slice_layout.addWidget(self.slice_slider)
        
        self.slice_label = QtWidgets.QLabel(f"{self.current_slice_idx + 1}/{self.image_array.shape[0]}")
        slice_layout.addWidget(self.slice_label)
        
        preview_layout.addLayout(slice_layout)
        
        main_layout.addWidget(preview_group)
        
        # 参数设置区域
        param_group = QtWidgets.QGroupBox("双边滤波参数")
        param_layout = QtWidgets.QGridLayout(param_group)
        
        # 空间域标准差
        param_layout.addWidget(QtWidgets.QLabel("空间域标准差:"), 0, 0)
        self.domain_sigma_spinbox = QtWidgets.QDoubleSpinBox()
        self.domain_sigma_spinbox.setRange(0.1, 10.0)
        self.domain_sigma_spinbox.setSingleStep(0.1)
        self.domain_sigma_spinbox.setDecimals(1)
        self.domain_sigma_spinbox.setValue(self.domain_sigma)
        self.domain_sigma_spinbox.valueChanged.connect(self.on_param_changed)
        param_layout.addWidget(self.domain_sigma_spinbox, 0, 1)
        
        # 值域标准差
        param_layout.addWidget(QtWidgets.QLabel("值域标准差:"), 1, 0)
        self.range_sigma_spinbox = QtWidgets.QDoubleSpinBox()
        self.range_sigma_spinbox.setRange(1.0, 300.0)
        self.range_sigma_spinbox.setSingleStep(5.0)
        self.range_sigma_spinbox.setDecimals(1)
        self.range_sigma_spinbox.setValue(self.range_sigma)
        self.range_sigma_spinbox.valueChanged.connect(self.on_param_changed)
        param_layout.addWidget(self.range_sigma_spinbox, 1, 1)
        
        # 注意：移除了迭代次数控件，因为ITK的BilateralImageFilter没有此参数
        
        main_layout.addWidget(param_group)
        
        # 按钮区域
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        
        self.apply_btn = QtWidgets.QPushButton("确定")
        self.apply_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.apply_btn)
        
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(button_layout)
    
    def eventFilter(self, obj, event):
        """事件过滤器，处理鼠标事件"""
        if obj == self.preview_label:
            if event.type() == QtCore.QEvent.MouseButtonPress:
                if event.button() == QtCore.Qt.LeftButton:
                    self.is_dragging = True
                    self.last_mouse_pos = event.pos()
                    self.preview_label.setCursor(QtCore.Qt.ClosedHandCursor)
                    return True
            
            elif event.type() == QtCore.QEvent.MouseButtonRelease:
                if event.button() == QtCore.Qt.LeftButton:
                    self.is_dragging = False
                    self.last_mouse_pos = None
                    self.preview_label.setCursor(QtCore.Qt.ArrowCursor)
                    return True
            
            elif event.type() == QtCore.QEvent.MouseMove:
                if self.is_dragging and self.last_mouse_pos:
                    delta = event.pos() - self.last_mouse_pos
                    self.offset_x += delta.x()
                    self.offset_y += delta.y()
                    self.last_mouse_pos = event.pos()
                    self.update_preview()
                    return True
            
            elif event.type() == QtCore.QEvent.Wheel:
                # 鼠标滚轮缩放
                delta = event.angleDelta().y()
                if delta > 0:
                    self.scale_factor *= 1.1
                else:
                    self.scale_factor *= 0.9
                self.scale_factor = max(0.1, min(10.0, self.scale_factor))
                self.update_preview()
                return True
        
        return super().eventFilter(obj, event)
    
    def on_slice_changed(self, value):
        """切片滑动条值改变时的处理"""
        self.current_slice_idx = value
        self.slice_label.setText(f"{value + 1}/{self.image_array.shape[0]}")
        self.update_preview()
    
    def on_param_changed(self):
        """参数改变时的处理"""
        self.domain_sigma = self.domain_sigma_spinbox.value()
        self.range_sigma = self.range_sigma_spinbox.value()
        
        # 应用滤波并更新预览
        self.apply_filter()
        self.update_preview()
    
    def apply_filter(self):
        """应用双边滤波"""
        try:
            # 转换为浮点数据
            image_array = to_float255_fixed(self.image_array)

            # 转换 numpy -> ITK
            Dimension = 3
            InputImageType = itk.Image[itk.F, Dimension]
            itk_image = itk.GetImageFromArray(image_array)  # 自动变成 3D ITK Image
            
            # 如果提供了spacing，设置到ITK图像
            if self.spacing:
                itk_image.SetSpacing(self.spacing)

            # 应用双边滤波器
            FilterType = itk.BilateralImageFilter[InputImageType, InputImageType]
            bilateral_filter = FilterType.New(
                Input=itk_image
            )
            
            # 设置双边滤波器参数
            bilateral_filter.SetDomainSigma(self.domain_sigma)
            bilateral_filter.SetRangeSigma(self.range_sigma)
            # ITK的BilateralImageFilter没有SetNumberOfIterations方法
            # 使用默认的迭代次数
            
            bilateral_filter.Update()
            
            # 转换回 numpy
            output_itk = bilateral_filter.GetOutput()
            output_np = itk.GetArrayFromImage(output_itk)
            self.filtered_array = to_uint16_fixed(output_np)
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"应用双边滤波时出错：{str(e)}")
            self.filtered_array = None
    
    def update_preview(self):
        """更新预览图像"""
        if self.filtered_array is None:
            # 首次调用或滤波失败时，应用滤波
            self.apply_filter()
            if self.filtered_array is None:
                return
        
        # 获取当前切片
        current_slice = self.filtered_array[self.current_slice_idx]
        
        # 转换为8位用于显示
        display_image = (current_slice / 65535.0 * 255).astype(np.uint8)
        
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
        self.preview_label.setPixmap(pixmap)
        self.preview_label.resize(pixmap.size())
    
    def get_result(self):
        """获取滤波结果"""
        return self.filtered_array
