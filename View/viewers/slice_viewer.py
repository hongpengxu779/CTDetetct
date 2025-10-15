"""
切片查看器组件
用于显示医学影像的某个方向切片（支持窗宽窗位）
"""

from PyQt5 import QtWidgets, QtCore
from File.DataTransform import array_to_qpixmap
from .zoomable_viewer import SimpleZoomViewer


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

