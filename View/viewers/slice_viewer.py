"""
切片查看器组件
用于显示医学影像的某个方向切片（支持窗宽窗位）
"""

from PyQt5 import QtWidgets, QtCore, QtGui
import numpy as np
import math
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
        
        # 测量相关变量
        self.measurement_mode = None  # 当前测量模式
        self.is_measuring = False  # 是否正在测量
        self.start_point = None  # 测量起点
        self.end_point = None  # 测量终点
        self.measurement_lines = []  # 已完成的测量线段
        self.corresponding_lines = []  # 对应的线段（其他视图中的线段）
        self.active_line_index = -1  # 当前活动的线段索引
        self.dragging_point = None  # 正在拖动的点 ('start' 或 'end')
        
        # 角度测量相关变量
        self.angle_points = []  # 角度测量的三个点 [p1, p2, p3]
        self.angle_measuring = False  # 是否正在测量角度
        self.angle_measurements = []  # 已完成的角度测量
        self.corresponding_angles = []  # 对应的角度（其他视图中的角度）
        self.active_angle_index = -1  # 当前活动的角度索引
        self.dragging_angle_point = None  # 正在拖动的角度点索引 (0, 1, 2)
        
        # ROI相关变量
        self.roi_mode = None
        self.roi_rects = []
        self.current_roi = None
        self.roi_start = None
        self.roi_end = None
        self.parent_controller = None
        self.is_roi_dragging = False
        self.active_roi = -1
        
        # 确定视图类型
        if "Axial" in title:
            self.view_type = "axial"
        elif "Sagittal" in title:
            self.view_type = "sagittal"
        elif "Coronal" in title:
            self.view_type = "coronal"
        else:
            self.view_type = "unknown"
            
        # 打印视图类型，用于调试
        print(f"创建视图: {title} -> {self.view_type}")

        # 主布局
        main_layout = QtWidgets.QVBoxLayout()
        
        # 顶部标题栏布局
        title_layout = QtWidgets.QHBoxLayout()
        
        # 标题标签
        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet("font-weight: bold;")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        main_layout.addLayout(title_layout)

        # 创建一个QGraphicsView用于显示图像和测量线
        self.scene = QtWidgets.QGraphicsScene()
        self.view = QtWidgets.QGraphicsView(self.scene)
        self.view.setRenderHint(QtGui.QPainter.Antialiasing)
        self.view.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        self.view.setAlignment(QtCore.Qt.AlignCenter)
        self.view.setMinimumHeight(300)  # 设置最小高度
        self.view.setStyleSheet("border: 1px solid #cccccc; background-color: #f0f0f0;")
        
        # 图像项
        self.pixmap_item = QtWidgets.QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        
        # 创建放大按钮作为视图的叠加层
        self.zoom_btn = QtWidgets.QPushButton("🔍", self.view)
        self.zoom_btn.setFixedSize(32, 32)
        self.zoom_btn.setToolTip("在新窗口中打开，可缩放和平移")
        self.zoom_btn.clicked.connect(self.open_zoom_window)
        self.zoom_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 200);
                border: 1px solid #aaaaaa;
                border-radius: 4px;
                font-size: 16px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(230, 230, 230, 220);
                border: 1px solid #888888;
            }
            QPushButton:pressed {
                background-color: rgba(200, 200, 200, 220);
            }
        """)
        self.zoom_btn.setCursor(QtCore.Qt.PointingHandCursor)
        # 初始位置会在resizeEvent中设置
        self.zoom_btn.raise_()  # 确保按钮在最上层
        
        # 添加视图到布局
        main_layout.addWidget(self.view)

        # QSlider 用于选择切片索引
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(0, max_index - 1)  # 设置滑动条范围
        self.slider.valueChanged.connect(self.update_slice)  # 当值改变时触发 update_slice
        main_layout.addWidget(self.slider)
        
        self.setLayout(main_layout)

        # 默认显示中间切片
        self.slider.setValue(max_index // 2)
        
        # 初始化放大按钮位置
        QtCore.QTimer.singleShot(0, self._update_zoom_button_position)
        
        # 安装事件过滤器以处理鼠标事件
        self.view.viewport().installEventFilter(self)
    
    def _update_zoom_button_position(self):
        """更新放大按钮位置到视图右上角"""
        if hasattr(self, 'zoom_btn') and hasattr(self, 'view'):
            view_width = self.view.width()
            self.zoom_btn.move(view_width - self.zoom_btn.width() - 8, 8)
    
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
        
        # 更新图像项
        self.pixmap_item.setPixmap(pix)
        
        # 调整场景大小以适应图像
        self.scene.setSceneRect(self.pixmap_item.boundingRect())
        
        # 清除对应线段，因为切片已经改变
        self.corresponding_lines = []
        
        # 重绘测量线
        self.redraw_measurement_lines()
        
        # 如果在测量模式下，通知父控制器更新其他视图中的对应线段
        if self.measurement_mode and hasattr(self, 'parent_controller') and self.parent_controller:
            # 获取当前视图中的所有测量线段
            if hasattr(self.parent_controller, 'sync_measurement_lines'):
                self.parent_controller.sync_measurement_lines(self.view_type)
        
        # 更新视图以适应场景
        self.view.fitInView(self.scene.sceneRect(), QtCore.Qt.KeepAspectRatio)
        
        # 如果缩放窗口打开着，更新它的图像
        if hasattr(self, 'zoom_window') and self.zoom_window and self.zoom_window.isVisible():
            self.zoom_window.update_image(arr)
            self.zoom_window.setWindowTitle(f"{self.title} - 切片 {idx+1}/{self.max_index}")
    
    def resizeEvent(self, event):
        """处理窗口大小变化事件"""
        super().resizeEvent(event)
        
        # 更新放大按钮的位置到视图内部右上角
        self._update_zoom_button_position()
        
        # 获取当前场景矩形
        scene_rect = self.scene.sceneRect()
        
        # 确保场景矩形有效
        if not scene_rect.isEmpty():
            # 调整视图以适应场景
            self.view.fitInView(scene_rect, QtCore.Qt.KeepAspectRatio)
            
            # 在Qt事件循环的下一个周期重新绘制测量线
            # 这样可以确保视图已经完成调整后再绘制线段
            QtCore.QTimer.singleShot(0, self.redraw_measurement_lines)
    
    def enable_measurement_mode(self, mode, parent_controller):
        """
        启用测量模式
        
        参数
        ----
        mode : str
            测量模式，例如 'distance' 或 'angle'
        parent_controller : object
            父控制器对象，用于回调
        """
        self.measurement_mode = mode
        self.parent_controller = parent_controller
        
        # 打印调试信息
        print(f"启用测量模式: 视图={self.view_type}, 模式={mode}")
        
        # 设置鼠标指针为十字形
        self.view.viewport().setCursor(QtCore.Qt.CrossCursor)
        
        # 清除当前测量状态
        self.is_measuring = False
        self.start_point = None
        self.end_point = None
        self.active_line_index = -1
        self.dragging_point = None
        
        # 清除角度测量状态
        self.angle_measuring = False
        self.angle_points = []
        self.active_angle_index = -1
        self.dragging_angle_point = None
        
        # 清除ROI相关状态
        self.roi_mode = None
        self.roi_rects = []
        self.current_roi = None
        self.roi_start = None
        self.roi_end = None
        self.parent_controller = None
        self.is_roi_dragging = False
        self.active_roi = -1
    
    def disable_measurement_mode(self):
        """禁用测量模式"""
        self.measurement_mode = None
        
        # 恢复默认鼠标指针
        self.view.viewport().setCursor(QtCore.Qt.ArrowCursor)
        
        # 清除当前测量状态
        self.is_measuring = False
        self.start_point = None
        self.end_point = None
        
        # 清除角度测量状态
        self.angle_measuring = False
        self.angle_points = []
        self.active_angle_index = -1
        self.dragging_angle_point = None
    
    def eventFilter(self, obj, event):
        """事件过滤器，处理鼠标事件"""
        if obj == self.view.viewport():
            if self.roi_mode == 'selection':
                # ... existing code ...
                if event.type() == QtCore.QEvent.MouseButtonPress:
                    if event.button() == QtCore.Qt.LeftButton:
                        return self.handle_roi_mouse_press(event)
                elif event.type() == QtCore.QEvent.MouseMove:
                    buttons = event.buttons()
                    if buttons & QtCore.Qt.LeftButton:
                        return self.handle_roi_mouse_move(event)
                    else:
                        self.view.viewport().setCursor(QtCore.Qt.CrossCursor)
                        return True
                elif event.type() == QtCore.QEvent.MouseButtonRelease:
                    if event.button() == QtCore.Qt.LeftButton:
                        return self.handle_roi_mouse_release(event)
            elif self.measurement_mode == 'distance':
                if event.type() == QtCore.QEvent.MouseButtonPress:
                    if event.button() == QtCore.Qt.LeftButton:
                        return self.handle_mouse_press(event)
                    elif event.button() == QtCore.Qt.RightButton:
                        return self.handle_right_click(event)
                        
                elif event.type() == QtCore.QEvent.MouseMove:
                    # 只有在左键按下时才处理移动事件，避免鼠标没有按下时也跟随移动
                    buttons = event.buttons()
                    if buttons & QtCore.Qt.LeftButton:
                        return self.handle_mouse_move(event)
                    else:
                        # 当鼠标没有按下时，只改变光标形状
                        scene_pos = self.view.mapToScene(event.pos())
                        # 检查鼠标是否靠近任何线段的端点
                        line_index, point_type = self.check_line_endpoints(scene_pos)
                        if line_index >= 0:
                            self.view.viewport().setCursor(QtCore.Qt.SizeAllCursor)
                        else:
                            self.view.viewport().setCursor(QtCore.Qt.CrossCursor)
                        return True
                    
                elif event.type() == QtCore.QEvent.MouseButtonRelease:
                    if event.button() == QtCore.Qt.LeftButton:
                        return self.handle_mouse_release(event)
            elif self.measurement_mode == 'angle':
                if event.type() == QtCore.QEvent.MouseButtonPress:
                    if event.button() == QtCore.Qt.LeftButton:
                        return self.handle_angle_mouse_press(event)
                    elif event.button() == QtCore.Qt.RightButton:
                        return self.handle_right_click(event)
                        
                elif event.type() == QtCore.QEvent.MouseMove:
                    # 只有在左键按下时才处理移动事件，避免鼠标没有按下时也跟随移动
                    buttons = event.buttons()
                    if buttons & QtCore.Qt.LeftButton:
                        return self.handle_angle_mouse_move(event)
                    else:
                        # 当鼠标没有按下时，只改变光标形状
                        scene_pos = self.view.mapToScene(event.pos())
                        # 检查鼠标是否靠近任何角度测量的点
                        angle_index, point_idx = self.check_angle_points(scene_pos)
                        if angle_index >= 0 and point_idx is not None:
                            self.view.viewport().setCursor(QtCore.Qt.SizeAllCursor)
                        else:
                            # 检查鼠标是否靠近任何角度测量的线段
                            angle_index = self.find_angle_near_point(scene_pos)
                            if angle_index >= 0:
                                self.view.viewport().setCursor(QtCore.Qt.PointingHandCursor)
                            else:
                                self.view.viewport().setCursor(QtCore.Qt.CrossCursor)
                        return True
                    
                elif event.type() == QtCore.QEvent.MouseButtonRelease:
                    if event.button() == QtCore.Qt.LeftButton:
                        return self.handle_angle_mouse_release(event)
            else:
                # 即使不在测量模式，也处理右键点击
                if event.type() == QtCore.QEvent.MouseButtonPress:
                    if event.button() == QtCore.Qt.RightButton:
                        return self.handle_right_click(event)
        
        return super().eventFilter(obj, event)
        
    def handle_right_click(self, event):
        """处理右键点击事件，显示上下文菜单"""
        scene_pos = self.view.mapToScene(event.pos())
        
        # 检查是否点击了测量线
        line_index = self.find_line_near_point(scene_pos)
        
        if line_index >= 0:
            # 创建上下文菜单
            context_menu = QtWidgets.QMenu(self)
            
            # 添加删除线段的动作
            delete_action = context_menu.addAction("删除测量线")
            delete_action.triggered.connect(lambda: self.delete_measurement_line(line_index))
            
            # 在鼠标位置显示菜单
            context_menu.exec_(event.globalPos())
            return True
        
        # 检查是否点击了角度测量
        angle_index = self.find_angle_near_point(scene_pos)
        
        if angle_index >= 0:
            # 创建上下文菜单
            context_menu = QtWidgets.QMenu(self)
            
            # 添加删除角度测量的动作
            delete_action = context_menu.addAction("删除角度测量")
            delete_action.triggered.connect(lambda: self.delete_angle_measurement(angle_index))
            
            # 在鼠标位置显示菜单
            context_menu.exec_(event.globalPos())
            return True
        
        # 如果没有点击测量线或角度测量，显示通用菜单
        context_menu = QtWidgets.QMenu(self)
        
        # 添加选择种子点的选项
        add_seed_action = context_menu.addAction("添加区域生长种子点")
        add_seed_action.triggered.connect(lambda: self.add_seed_point(scene_pos))
        
        # 添加清除所有种子点的选项
        if self.parent_viewer and hasattr(self.parent_viewer, 'region_growing_seed_points') and self.parent_viewer.region_growing_seed_points:
            clear_seeds_action = context_menu.addAction("清除所有种子点")
            clear_seeds_action.triggered.connect(self.clear_all_seed_points)
        
        # 在鼠标位置显示菜单
        context_menu.exec_(event.globalPos())
        return True
    
    def add_seed_point(self, scene_pos):
        """添加区域生长的种子点"""
        if not self.parent_viewer:
            return
        
        # 将场景坐标转换为图像坐标
        x = int(scene_pos.x())
        y = int(scene_pos.y())
        
        # 获取当前切片索引
        current_slice = self.slider.value()
        
        # 根据视图类型确定3D坐标
        # 需要知道这是哪个视图（Axial, Sagittal, Coronal）
        if "Axial" in self.title:
            # Axial视图: z = current_slice, y = y, x = x
            seed_point = (current_slice, y, x)
        elif "Sagittal" in self.title:
            # Sagittal视图: z = y, y = x, x = current_slice
            seed_point = (y, x, current_slice)
        elif "Coronal" in self.title:
            # Coronal视图: z = y, y = current_slice, x = x
            seed_point = (y, current_slice, x)
        else:
            seed_point = (current_slice, y, x)
        
        # 添加到父窗口的种子点列表
        if hasattr(self.parent_viewer, 'add_region_growing_seed_point'):
            self.parent_viewer.add_region_growing_seed_point(seed_point)
            
            # 在图像上标记种子点
            self.mark_seed_point(scene_pos)
            
            # 在状态栏显示简洁提示（如果父窗口有状态栏）
            if hasattr(self.parent_viewer, 'status_label'):
                total_seeds = len(self.parent_viewer.region_growing_seed_points) if hasattr(self.parent_viewer, 'region_growing_seed_points') else 1
                self.parent_viewer.status_label.setText(
                    f"✓ 种子点已添加: {seed_point} (共 {total_seeds} 个) | "
                    f"继续右键添加更多，或在菜单选择\"传统分割检测\" -> \"区域生长\"开始分割"
                )
            
            print(f"种子点已添加: {seed_point} (在 {self.title} 视图，切片 {current_slice})")
    
    def mark_seed_point(self, pos):
        """在图像上标记种子点"""
        # 创建一个十字标记
        pen = QtGui.QPen(QtCore.Qt.red, 2)
        
        # 绘制十字
        size = 5
        h_line = self.scene.addLine(pos.x() - size, pos.y(), pos.x() + size, pos.y(), pen)
        v_line = self.scene.addLine(pos.x(), pos.y() - size, pos.x(), pos.y() + size, pen)
        
        # 绘制小圆圈
        circle = self.scene.addEllipse(pos.x() - 3, pos.y() - 3, 6, 6, pen)
        
        # 保存标记引用（用于后续清除）
        if not hasattr(self, 'seed_point_marks'):
            self.seed_point_marks = []
        self.seed_point_marks.append((h_line, v_line, circle))
    
    def clear_all_seed_points(self):
        """清除所有种子点"""
        if self.parent_viewer and hasattr(self.parent_viewer, 'clear_region_growing_seed_points'):
            self.parent_viewer.clear_region_growing_seed_points()
            
            # 清除所有视图中的标记
            self._clear_seed_marks_in_all_views()
            
            # 在状态栏显示简洁提示
            if hasattr(self.parent_viewer, 'status_label'):
                self.parent_viewer.status_label.setText("✓ 所有种子点已清除")
            
            print("所有种子点已清除")
    
    def _clear_seed_marks_in_all_views(self):
        """清除所有视图中的种子点标记"""
        if not self.parent_viewer:
            return
        
        # 清除所有视图中的标记
        for viewer in [self.parent_viewer.axial_viewer, 
                      self.parent_viewer.sag_viewer, 
                      self.parent_viewer.cor_viewer]:
            if viewer and hasattr(viewer, 'seed_point_marks'):
                for h_line, v_line, circle in viewer.seed_point_marks:
                    try:
                        viewer.scene.removeItem(h_line)
                        viewer.scene.removeItem(v_line)
                        viewer.scene.removeItem(circle)
                    except:
                        pass
                viewer.seed_point_marks = []
        
    def find_line_near_point(self, pos, threshold=5):
        """
        查找靠近指定点的线段
        
        参数
        ----
        pos : QPointF
            要检查的位置
        threshold : float
            距离阈值
            
        返回
        ----
        line_index : int
            如果找到线段，返回线段索引；否则返回-1
        """
        for i, line in enumerate(self.measurement_lines):
            # 计算点到线段的距离
            dist = self.point_to_line_distance(pos, line['start'], line['end'])
            if dist < threshold:
                return i
        
        return -1
        
    def find_angle_near_point(self, pos, threshold=10):
        """
        查找靠近指定点的角度测量
        
        参数
        ----
        pos : QPointF
            要检查的位置
        threshold : float
            距离阈值
            
        返回
        ----
        angle_index : int
            如果找到角度，返回角度索引；否则返回-1
        """
        for i, angle in enumerate(self.angle_measurements):
            # 检查是否靠近任何一个点
            if (self.calculate_distance(pos, angle['p1']) < threshold or
                self.calculate_distance(pos, angle['p2']) < threshold or
                self.calculate_distance(pos, angle['p3']) < threshold):
                return i
                
            # 检查是否靠近任何一条线段
            if (self.point_to_line_distance(pos, angle['p1'], angle['p2']) < threshold or
                self.point_to_line_distance(pos, angle['p2'], angle['p3']) < threshold):
                return i
        
        return -1
        
    def point_to_line_distance(self, point, line_start, line_end):
        """
        计算点到线段的距离
        
        参数
        ----
        point : QPointF
            点
        line_start : QPointF
            线段起点
        line_end : QPointF
            线段终点
            
        返回
        ----
        distance : float
            点到线段的距离
        """
        # 线段长度的平方
        line_length_sq = (line_end.x() - line_start.x())**2 + (line_end.y() - line_start.y())**2
        
        # 如果线段长度为0，则返回点到起点的距离
        if line_length_sq == 0:
            return self.calculate_distance(point, line_start)
        
        # 计算投影比例 t
        t = ((point.x() - line_start.x()) * (line_end.x() - line_start.x()) + 
             (point.y() - line_start.y()) * (line_end.y() - line_start.y())) / line_length_sq
        
        # 将 t 限制在 [0, 1] 范围内
        t = max(0, min(1, t))
        
        # 计算投影点
        proj_x = line_start.x() + t * (line_end.x() - line_start.x())
        proj_y = line_start.y() + t * (line_end.y() - line_start.y())
        
        # 计算点到投影点的距离
        return math.sqrt((point.x() - proj_x)**2 + (point.y() - proj_y)**2)
        
    def delete_measurement_line(self, line_index):
        """
        删除指定的测量线
        
        参数
        ----
        line_index : int
            要删除的线段索引
        """
        if 0 <= line_index < len(self.measurement_lines):
            # 删除线段
            del self.measurement_lines[line_index]
            
            # 重绘测量线
            self.redraw_measurement_lines()
            
            # 通知父控制器线段已删除，并同步删除其他视图中的对应线段
            if hasattr(self, 'parent_controller') and self.parent_controller:
                # 更新当前视图的线段列表
                self.parent_controller.measurement_lines[self.view_type] = self.measurement_lines.copy()
                
                # 调用父控制器的同步方法，确保所有视图的线段同步
                self.parent_controller.sync_measurement_lines(self.view_type)
                
    def delete_angle_measurement(self, angle_index):
        """
        删除指定的角度测量
        
        参数
        ----
        angle_index : int
            要删除的角度索引
        """
        if 0 <= angle_index < len(self.angle_measurements):
            # 删除角度测量
            del self.angle_measurements[angle_index]
            
            # 重绘测量线和角度
            self.redraw_measurement_lines()
            
            # 通知父控制器角度已删除，并同步删除其他视图中的对应角度
            if hasattr(self, 'parent_controller') and self.parent_controller:
                # 更新当前视图的角度列表
                if hasattr(self.parent_controller, 'angle_measurements'):
                    self.parent_controller.angle_measurements[self.view_type] = self.angle_measurements.copy()
                
                # 调用父控制器的同步方法，确保所有视图的角度同步
                if hasattr(self.parent_controller, 'sync_angle_measurements'):
                    self.parent_controller.sync_angle_measurements(self.view_type)
    
    def handle_mouse_press(self, event):
        """处理鼠标按下事件（距离测量模式）"""
        # 获取场景坐标
        scene_pos = self.view.mapToScene(event.pos())
        
        # 检查是否点击了已有线段的端点
        line_index, point_type = self.check_line_endpoints(scene_pos)
        
        if line_index >= 0:
            # 点击了已有线段的端点，开始拖动
            self.active_line_index = line_index
            self.dragging_point = point_type
            self.is_measuring = False
            return True
        
        # 开始新的测量前，清除所有现有线段
        if hasattr(self, 'parent_controller') and self.parent_controller:
            # 清空所有视图的线段
            self.parent_controller.clear_all_measurement_lines()
        else:
            # 如果没有父控制器，只清空当前视图的线段
            self.measurement_lines = []
            self.corresponding_lines = []
        
        # 开始新的测量
        self.is_measuring = True
        self.start_point = scene_pos
        self.end_point = scene_pos  # 初始时终点与起点相同
        
        # 重置活动线段索引
        self.active_line_index = -1
        self.dragging_point = None
        
        # 重绘测量线
        self.redraw_measurement_lines()
        return True
        
    def handle_angle_mouse_press(self, event):
        """处理鼠标按下事件（角度测量模式）"""
        # 获取场景坐标
        scene_pos = self.view.mapToScene(event.pos())
        
        # 检查是否点击了已有角度测量的点
        angle_index, point_idx = self.check_angle_points(scene_pos)
        
        if angle_index >= 0 and point_idx is not None:
            # 点击了已有角度测量的点，开始拖动
            self.active_angle_index = angle_index
            self.dragging_angle_point = point_idx
            self.angle_measuring = False
            self.end_point = None  # 清除临时点
            return True
            
        # 如果没有正在进行的测量，则开始新的测量
        if not self.angle_measuring:
            # 清除已有的角度测量
            self.angle_measurements = []
            
            # 开始新的测量
            self.angle_measuring = True
            self.angle_points = [scene_pos]
            self.end_point = None  # 确保清除之前的临时点
            self.redraw_measurement_lines()
            return True
        
        # 如果正在测量角度，添加新的点
        if self.angle_measuring:
            # 添加点到列表
            if len(self.angle_points) < 3:
                # 如果是第二个点，则设置为顶点
                if len(self.angle_points) == 1:
                    self.angle_points.append(scene_pos)  # 添加顶点
                    self.end_point = None  # 清除临时的第二个点
                # 如果是第三个点，则添加并完成测量
                elif len(self.angle_points) == 2:
                    self.angle_points.append(scene_pos)  # 添加第三个点
                    # 完成当前测量并添加到列表
                    self.complete_angle_measurement()
                    
                    # 重置测量状态，不立即开始新测量
                    self.angle_measuring = False
                    self.angle_points = []
                    self.end_point = None
            
            # 重绘测量线和角度
            self.redraw_measurement_lines()
            return True
        
        # 如果没有正在进行的测量，则开始新的测量
        if not self.angle_measuring:
            # 清除已有的角度测量
            if hasattr(self, 'parent_controller') and self.parent_controller and hasattr(self.parent_controller, 'clear_all_angle_measurements'):
                self.parent_controller.clear_all_angle_measurements()
            else:
                self.angle_measurements = []
                self.corresponding_angles = []
            
            # 开始新的测量
            self.angle_measuring = True
            self.angle_points = [scene_pos]
            
            # 重置活动角度索引
            self.active_angle_index = -1
            self.dragging_angle_point = None
            
            # 重绘测量线和角度
            self.redraw_measurement_lines()
            return True
        
        # 如果正在测量角度，添加新的点
        if self.angle_measuring:
            # 添加点到列表
            self.angle_points.append(scene_pos)
            
            # 如果已有三个点，则完成测量
            if len(self.angle_points) == 3:
                # 重绘测量线和角度，显示角度值
                self.redraw_measurement_lines()
            else:
                # 重绘测量线和角度
                self.redraw_measurement_lines()
                
            return True
        
        return False
    
    def handle_mouse_move(self, event):
        """处理鼠标移动事件（距离测量模式）"""
        scene_pos = self.view.mapToScene(event.pos())
        
        if self.is_measuring:
            # 更新终点位置
            self.end_point = scene_pos
            # 重绘测量线
            self.redraw_measurement_lines()
            
            # 更新状态栏显示当前距离
            if hasattr(self, 'parent_controller') and self.parent_controller and hasattr(self.parent_controller, 'statusBar'):
                distance = self.calculate_distance(self.start_point, self.end_point)
                self.parent_controller.statusBar().showMessage(f"测量距离: {int(distance)} 像素")
                
            # 实时更新其他视图中的临时线段
            if hasattr(self, 'parent_controller') and self.parent_controller:
                # 调用父控制器的方法来实时更新其他视图
                self.parent_controller.update_temp_line(self.view_type, self.start_point, self.end_point)
            
            return True
        
        elif self.active_line_index >= 0 and self.dragging_point:
            # 更新正在拖动的端点
            if self.dragging_point == 'start':
                self.measurement_lines[self.active_line_index]['start'] = scene_pos
            else:  # 'end'
                self.measurement_lines[self.active_line_index]['end'] = scene_pos
                
            # 重新计算距离
            start = self.measurement_lines[self.active_line_index]['start']
            end = self.measurement_lines[self.active_line_index]['end']
            distance = self.calculate_distance(start, end)
            self.measurement_lines[self.active_line_index]['distance'] = distance
            
            # 重绘测量线
            self.redraw_measurement_lines()
            
            # 更新状态栏显示当前距离
            if hasattr(self, 'parent_controller') and self.parent_controller and hasattr(self.parent_controller, 'statusBar'):
                self.parent_controller.statusBar().showMessage(f"测量距离: {int(distance)} 像素")
            
            # 实时更新其他视图中的对应线段
            if hasattr(self, 'parent_controller') and self.parent_controller:
                # 更新当前视图的线段列表
                self.parent_controller.measurement_lines[self.view_type] = self.measurement_lines.copy()
                
                # 调用父控制器的同步方法，确保所有视图的线段同步
                self.parent_controller.sync_measurement_lines(self.view_type)
                
            return True
        
        # 检查鼠标是否靠近任何线段的端点，如果是则改变鼠标形状
        line_index, point_type = self.check_line_endpoints(scene_pos)
        if line_index >= 0:
            self.view.viewport().setCursor(QtCore.Qt.SizeAllCursor)
        else:
            # 检查鼠标是否靠近任何线段，如果是则改变鼠标形状
            line_index = self.find_line_near_point(scene_pos)
            if line_index >= 0:
                self.view.viewport().setCursor(QtCore.Qt.PointingHandCursor)
            else:
                self.view.viewport().setCursor(QtCore.Qt.CrossCursor)
            
        return False
        
    def handle_angle_mouse_move(self, event):
        """处理鼠标移动事件（角度测量模式）"""
        scene_pos = self.view.mapToScene(event.pos())
        
        if self.angle_measuring and len(self.angle_points) > 0:
            # 如果正在测量第二个点，更新它
            if len(self.angle_points) == 1:
                # 显示临时的第二个点
                self.end_point = scene_pos  # 使用end_point来显示临时的第二个点
                # 重绘测量线和角度
                self.redraw_measurement_lines()
            # 如果正在测量第三个点，更新它
            elif len(self.angle_points) == 2:
                # 显示临时的第三个点
                self.end_point = scene_pos  # 使用end_point来显示临时的第三个点
                # 重绘测量线和角度
                self.redraw_measurement_lines()
                
                # 计算并显示角度
                if len(self.angle_points) == 3:
                    angle_value = self.calculate_angle(
                        self.angle_points[0], 
                        self.angle_points[1], 
                        self.angle_points[2]
                    )
                    
                    # 更新状态栏显示当前角度
                    if hasattr(self, 'parent_controller') and self.parent_controller and hasattr(self.parent_controller, 'statusBar'):
                        self.parent_controller.statusBar().showMessage(f"角度测量: {angle_value:.1f}°")
                    
                    # 实时更新其他视图中的临时角度
                    if hasattr(self, 'parent_controller') and self.parent_controller and hasattr(self.parent_controller, 'update_temp_angle'):
                        self.parent_controller.update_temp_angle(
                            self.view_type, 
                            self.angle_points[0], 
                            self.angle_points[1], 
                            self.angle_points[2]
                        )
            
            return True
        
        elif self.active_angle_index >= 0 and self.dragging_angle_point is not None:
            # 更新正在拖动的点
            point_keys = ['p1', 'p2', 'p3']
            self.angle_measurements[self.active_angle_index][point_keys[self.dragging_angle_point]] = scene_pos
            
            # 重新计算角度
            p1 = self.angle_measurements[self.active_angle_index]['p1']
            p2 = self.angle_measurements[self.active_angle_index]['p2']
            p3 = self.angle_measurements[self.active_angle_index]['p3']
            angle_value = self.calculate_angle(p1, p2, p3)
            self.angle_measurements[self.active_angle_index]['angle'] = angle_value
            
            # 重绘测量线和角度
            self.redraw_measurement_lines()
            
            # 更新状态栏显示当前角度
            if hasattr(self, 'parent_controller') and self.parent_controller and hasattr(self.parent_controller, 'statusBar'):
                self.parent_controller.statusBar().showMessage(f"角度测量: {angle_value:.1f}°")
            
            # 实时更新其他视图中的对应角度
            if hasattr(self, 'parent_controller') and self.parent_controller and hasattr(self.parent_controller, 'angle_measurements') and hasattr(self.parent_controller, 'sync_angle_measurements'):
                # 更新当前视图的角度列表
                self.parent_controller.angle_measurements[self.view_type] = self.angle_measurements.copy()
                
                # 调用父控制器的同步方法，确保所有视图的角度同步
                self.parent_controller.sync_angle_measurements(self.view_type)
                
            # 清除临时点，避免拖动完成后仍然显示临时线段
            self.end_point = None
                
            return True
        
        # 检查鼠标是否靠近任何角度测量的点，如果是则改变鼠标形状
        angle_index, point_idx = self.check_angle_points(scene_pos)
        if angle_index >= 0 and point_idx is not None:
            self.view.viewport().setCursor(QtCore.Qt.SizeAllCursor)
        else:
            # 检查鼠标是否靠近任何角度测量的线段，如果是则改变鼠标形状
            angle_index = self.find_angle_near_point(scene_pos)
            if angle_index >= 0:
                self.view.viewport().setCursor(QtCore.Qt.PointingHandCursor)
            else:
                self.view.viewport().setCursor(QtCore.Qt.CrossCursor)
            
        return False
    
    def handle_mouse_release(self, event):
        """处理鼠标释放事件（距离测量模式）"""
        if self.is_measuring and self.start_point and self.end_point:
            # 计算距离
            distance = self.calculate_distance(self.start_point, self.end_point)
            
            # 如果距离太小，则忽略这次测量
            if distance < 5:
                self.is_measuring = False
                self.start_point = None
                self.end_point = None
                self.redraw_measurement_lines()
                return True
                
            # 检查起点和终点是否相同（避免创建重复线段）
            if abs(self.start_point.x() - self.end_point.x()) < 1 and abs(self.start_point.y() - self.end_point.y()) < 1:
                self.is_measuring = False
                self.start_point = None
                self.end_point = None
                self.redraw_measurement_lines()
                return True
            
            # 添加新的测量线段
            self.measurement_lines.append({
                'start': self.start_point,
                'end': self.end_point,
                'distance': distance
            })
            
            # 通知父控制器测量完成
            if hasattr(self, 'parent_controller') and self.parent_controller:
                # 调整其他视图的切片位置
                if hasattr(self.parent_controller, 'adjust_slices_for_measurement'):
                    self.parent_controller.adjust_slices_for_measurement(
                        self.view_type,
                        self.start_point,
                        self.end_point
                    )
                
                self.parent_controller.on_measurement_completed(
                    self.view_type,
                    self.start_point,
                    self.end_point,
                    distance
                )
                
                # 更新状态栏显示测量完成
                if hasattr(self.parent_controller, 'statusBar'):
                    self.parent_controller.statusBar().showMessage(f"测量完成: {int(distance)} 像素", 3000)
            
            # 重置测量状态
            self.is_measuring = False
            self.start_point = None
            self.end_point = None
            
            # 重绘测量线
            self.redraw_measurement_lines()
            return True
            
        elif self.active_line_index >= 0 and self.dragging_point:
            # 通知父控制器线段已更新
            if hasattr(self, 'parent_controller') and self.parent_controller:
                start = self.measurement_lines[self.active_line_index]['start']
                end = self.measurement_lines[self.active_line_index]['end']
                distance = self.measurement_lines[self.active_line_index]['distance']
                
                self.parent_controller.on_measurement_completed(
                    self.view_type,
                    start,
                    end,
                    distance
                )
                
                # 更新状态栏显示测量更新
                if hasattr(self.parent_controller, 'statusBar'):
                    self.parent_controller.statusBar().showMessage(f"测量更新: {int(distance)} 像素", 3000)
            
            # 重置拖动状态
            self.active_line_index = -1
            self.dragging_point = None
            return True
        
        return False
        
    def handle_angle_mouse_release(self, event):
        """处理鼠标释放事件（角度测量模式）"""
        if self.angle_measuring and len(self.angle_points) == 3:
            # 计算角度
            angle_value = self.calculate_angle(
                self.angle_points[0], 
                self.angle_points[1], 
                self.angle_points[2]
            )
            
            # 完成测量，添加到列表
            self.complete_angle_measurement()
            
            # 重置测量状态，完全退出测量模式
            self.angle_measuring = False
            self.angle_points = []
            self.end_point = None
            
            # 重绘测量线和角度
            self.redraw_measurement_lines()
            return True
            
        elif self.active_angle_index >= 0 and self.dragging_angle_point is not None:
            # 通知父控制器角度已更新
            if hasattr(self, 'parent_controller') and self.parent_controller and hasattr(self.parent_controller, 'on_angle_measurement_completed'):
                p1 = self.angle_measurements[self.active_angle_index]['p1']
                p2 = self.angle_measurements[self.active_angle_index]['p2']
                p3 = self.angle_measurements[self.active_angle_index]['p3']
                angle = self.angle_measurements[self.active_angle_index]['angle']
                
                self.parent_controller.on_angle_measurement_completed(
                    self.view_type,
                    p1,
                    p2,
                    p3,
                    angle
                )
                
                # 更新状态栏显示测量更新
                if hasattr(self.parent_controller, 'statusBar'):
                    self.parent_controller.statusBar().showMessage(f"角度测量更新: {angle:.1f}°", 3000)
            
            # 重置拖动状态
            self.active_angle_index = -1
            self.dragging_angle_point = None
            self.end_point = None  # 确保清除临时点
            return True
        
        # 在所有情况下都清除临时点
        self.end_point = None
        
        return False
        
    def complete_angle_measurement(self):
        """完成角度测量并添加到列表"""
        if len(self.angle_points) == 3:
            # 计算角度
            angle_value = self.calculate_angle(
                self.angle_points[0], 
                self.angle_points[1], 
                self.angle_points[2]
            )
            
            # 清除已有的角度测量，只保留一个角度测量
            self.angle_measurements = []
            
            # 添加新的角度测量
            self.angle_measurements.append({
                'p1': self.angle_points[0],
                'p2': self.angle_points[1],  # 顶点
                'p3': self.angle_points[2],
                'angle': angle_value
            })
            
            # 通知父控制器测量完成
            if hasattr(self, 'parent_controller') and self.parent_controller and hasattr(self.parent_controller, 'on_angle_measurement_completed'):
                # 调整其他视图的切片位置
                if hasattr(self.parent_controller, 'adjust_slices_for_angle_measurement'):
                    self.parent_controller.adjust_slices_for_angle_measurement(
                        self.view_type,
                        self.angle_points[0],
                        self.angle_points[1],
                        self.angle_points[2]
                    )
                
                self.parent_controller.on_angle_measurement_completed(
                    self.view_type,
                    self.angle_points[0],
                    self.angle_points[1],
                    self.angle_points[2],
                    angle_value
                )
                
                # 更新状态栏显示测量完成
                if hasattr(self.parent_controller, 'statusBar'):
                    self.parent_controller.statusBar().showMessage(f"角度测量完成: {angle_value:.1f}°", 3000)
    
    def calculate_distance(self, p1, p2):
        """计算两点之间的欧几里得距离"""
        return math.sqrt((p2.x() - p1.x())**2 + (p2.y() - p1.y())**2)
        
    def calculate_angle(self, p1, p2, p3):
        """
        计算由三个点形成的角度，p2是角的顶点
        
        参数
        ----
        p1, p2, p3 : QPointF
            构成角度的三个点，p2是角的顶点
            
        返回
        ----
        angle : float
            角度值，以度为单位 (0-180)
        """
        # 计算向量
        v1 = QtCore.QPointF(p1.x() - p2.x(), p1.y() - p2.y())
        v2 = QtCore.QPointF(p3.x() - p2.x(), p3.y() - p2.y())
        
        # 计算向量长度
        len_v1 = math.sqrt(v1.x() ** 2 + v1.y() ** 2)
        len_v2 = math.sqrt(v2.x() ** 2 + v2.y() ** 2)
        
        # 防止除以0
        if len_v1 < 0.0001 or len_v2 < 0.0001:
            return 0
        
        # 计算点积
        dot_product = v1.x() * v2.x() + v1.y() * v2.y()
        
        # 计算夹角的余弦值
        cos_angle = dot_product / (len_v1 * len_v2)
        
        # 防止浮点误差导致的值超过范围
        cos_angle = max(-1, min(1, cos_angle))
        
        # 计算角度并转换为度
        angle_rad = math.acos(cos_angle)
        angle_deg = math.degrees(angle_rad)
        
        return angle_deg
    
    def check_line_endpoints(self, pos, threshold=10):
        """
        检查位置是否靠近任何线段的端点
        
        参数
        ----
        pos : QPointF
            要检查的位置
        threshold : float
            距离阈值
            
        返回
        ----
        (line_index, point_type) : (int, str)
            如果靠近端点，返回线段索引和端点类型（'start'或'end'）
            如果不靠近任何端点，返回 (-1, None)
        """
        closest_dist = float('inf')
        closest_line = -1
        closest_point = None
        
        for i, line in enumerate(self.measurement_lines):
            # 检查起点
            start_dist = self.calculate_distance(pos, line['start'])
            if start_dist < threshold and start_dist < closest_dist:
                closest_dist = start_dist
                closest_line = i
                closest_point = 'start'
            
            # 检查终点
            end_dist = self.calculate_distance(pos, line['end'])
            if end_dist < threshold and end_dist < closest_dist:
                closest_dist = end_dist
                closest_line = i
                closest_point = 'end'
        
        return closest_line, closest_point
        
    def check_angle_points(self, pos, threshold=10):
        """
        检查位置是否靠近任何角度测量的点
        
        参数
        ----
        pos : QPointF
            要检查的位置
        threshold : float
            距离阈值
            
        返回
        ----
        (angle_index, point_idx) : (int, int)
            如果靠近点，返回角度索引和点索引（0, 1, 2）
            如果不靠近任何点，返回 (-1, None)
        """
        closest_dist = float('inf')
        closest_angle = -1
        closest_point_idx = None
        
        for i, angle in enumerate(self.angle_measurements):
            # 检查三个点
            points = [angle['p1'], angle['p2'], angle['p3']]
            for j, point in enumerate(points):
                dist = self.calculate_distance(pos, point)
                if dist < threshold and dist < closest_dist:
                    closest_dist = dist
                    closest_angle = i
                    closest_point_idx = j
        
        return closest_angle, closest_point_idx
    
    def get_image_rect(self):
        """获取当前图像的矩形边界"""
        if self.pixmap_item and not self.pixmap_item.pixmap().isNull():
            return self.pixmap_item.boundingRect()
        return QtCore.QRectF()
    
    def constrain_point_to_image(self, point):
        """将点限制在图像边界内"""
        image_rect = self.get_image_rect()
        if image_rect.isEmpty():
            return point
        
        # 限制点在图像边界内
        x = max(image_rect.left(), min(point.x(), image_rect.right()))
        y = max(image_rect.top(), min(point.y(), image_rect.bottom()))
        
        return QtCore.QPointF(x, y)
    
    def redraw_measurement_lines(self):
        """重绘所有测量线段和角度"""
        # 清除所有已有的线段和文本
        for item in self.scene.items():
            if isinstance(item, (QtWidgets.QGraphicsLineItem, QtWidgets.QGraphicsTextItem, 
                                QtWidgets.QGraphicsRectItem, QtWidgets.QGraphicsEllipseItem,
                                QtWidgets.QGraphicsPathItem)):
                self.scene.removeItem(item)
        
        # 设置线段样式 - 使用亮红色，但线段更细
        pen = QtGui.QPen(QtGui.QColor(255, 0, 0))
        pen.setWidth(1)  # 减小线段宽度
        
        # 绘制已完成的测量线段
        for i, line in enumerate(self.measurement_lines):
            # 限制点在图像边界内
            constrained_start = self.constrain_point_to_image(line['start'])
            constrained_end = self.constrain_point_to_image(line['end'])
            
            # 绘制线段
            line_item = self.scene.addLine(
                constrained_start.x(), constrained_start.y(),
                constrained_end.x(), constrained_end.y(),
                pen
            )
            
            # 在线段起点和终点绘制更小的方块标记
            start_rect = QtWidgets.QGraphicsRectItem(
                constrained_start.x() - 2, constrained_start.y() - 2, 4, 4
            )
            start_rect.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0)))
            start_rect.setPen(pen)
            self.scene.addItem(start_rect)
            
            end_rect = QtWidgets.QGraphicsRectItem(
                constrained_end.x() - 2, constrained_end.y() - 2, 4, 4
            )
            end_rect.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0)))
            end_rect.setPen(pen)
            self.scene.addItem(end_rect)
            
            # 添加距离文本 - 直接显示在线段旁边
            # 计算线段中点
            mid_x = (constrained_start.x() + constrained_end.x()) / 2
            mid_y = (constrained_start.y() + constrained_end.y()) / 2
            
            # 计算文本位置 - 根据线段方向调整
            dx = constrained_end.x() - constrained_start.x()
            dy = constrained_end.y() - constrained_start.y()
            
            # 计算线段角度
            angle = math.atan2(dy, dx)
            
            # 根据角度决定文本位置
            if -math.pi/4 <= angle <= math.pi/4:  # 线段接近水平向右
                text_x = mid_x - 25
                text_y = mid_y - 20
            elif math.pi/4 < angle <= 3*math.pi/4:  # 线段接近垂直向下
                text_x = mid_x + 10
                text_y = mid_y - 10
            elif -3*math.pi/4 <= angle < -math.pi/4:  # 线段接近垂直向上
                text_x = mid_x + 10
                text_y = mid_y - 10
            else:  # 线段接近水平向左
                text_x = mid_x + 10
                text_y = mid_y - 20
                
            # 创建文本项 - 只显示整数值
            text = QtWidgets.QGraphicsTextItem(f"{int(line['distance'])}")
            text.setPos(text_x, text_y)
            text.setDefaultTextColor(QtGui.QColor(255, 0, 0))
            
            # 设置文本字体
            font = QtGui.QFont()
            font.setBold(True)
            font.setPointSize(10)
            text.setFont(font)
            
            # 使用白色背景确保文本可见
            text_bg = QtWidgets.QGraphicsRectItem(text.boundingRect())
            text_bg.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))
            text_bg.setPen(QtGui.QPen(QtCore.Qt.NoPen))
            text_bg.setPos(text_x, text_y)
            
            # 先添加背景，再添加文本
            self.scene.addItem(text_bg)
            self.scene.addItem(text)
            
        # 绘制角度测量
        self.draw_angle_measurements()
        
        # 绘制正在测量的线段
        if self.is_measuring and self.start_point and self.end_point:
            # 限制点在图像边界内
            constrained_start = self.constrain_point_to_image(self.start_point)
            constrained_end = self.constrain_point_to_image(self.end_point)
            
            # 绘制线段
            line_item = self.scene.addLine(
                constrained_start.x(), constrained_start.y(),
                constrained_end.x(), constrained_end.y(),
                pen
            )
            
            # 在线段起点和终点绘制更小的方块标记
            start_rect = QtWidgets.QGraphicsRectItem(
                constrained_start.x() - 2, constrained_start.y() - 2, 4, 4
            )
            start_rect.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0)))
            start_rect.setPen(pen)
            self.scene.addItem(start_rect)
            
            end_rect = QtWidgets.QGraphicsRectItem(
                constrained_end.x() - 2, constrained_end.y() - 2, 4, 4
            )
            end_rect.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0)))
            end_rect.setPen(pen)
            self.scene.addItem(end_rect)
            
            # 计算并显示当前距离
            distance = self.calculate_distance(constrained_start, constrained_end)
            
            # 计算线段中点
            mid_x = (constrained_start.x() + constrained_end.x()) / 2
            mid_y = (constrained_start.y() + constrained_end.y()) / 2
            
            # 计算文本位置 - 根据线段方向调整
            dx = constrained_end.x() - constrained_start.x()
            dy = constrained_end.y() - constrained_start.y()
            
            # 计算线段角度
            angle = math.atan2(dy, dx)
            
            # 根据角度决定文本位置
            if -math.pi/4 <= angle <= math.pi/4:  # 线段接近水平向右
                text_x = mid_x - 25
                text_y = mid_y - 20
            elif math.pi/4 < angle <= 3*math.pi/4:  # 线段接近垂直向下
                text_x = mid_x + 10
                text_y = mid_y - 10
            elif -3*math.pi/4 <= angle < -math.pi/4:  # 线段接近垂直向上
                text_x = mid_x + 10
                text_y = mid_y - 10
            else:  # 线段接近水平向左
                text_x = mid_x + 10
                text_y = mid_y - 20
            
            # 创建文本项 - 只显示整数值
            text = QtWidgets.QGraphicsTextItem(f"{int(distance)}")
            text.setPos(text_x, text_y)
            text.setDefaultTextColor(QtGui.QColor(255, 0, 0))
            
            # 设置文本字体
            font = QtGui.QFont()
            font.setBold(True)
            font.setPointSize(10)
            text.setFont(font)
            
            # 使用白色背景确保文本可见
            text_bg = QtWidgets.QGraphicsRectItem(text.boundingRect())
            text_bg.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))
            text_bg.setPen(QtGui.QPen(QtCore.Qt.NoPen))
            text_bg.setPos(text_x, text_y)
            
            self.scene.addItem(text_bg)
            self.scene.addItem(text)
        
        # 绘制对应线段（其他视图中的线段）
        other_pen = QtGui.QPen(QtGui.QColor(0, 0, 255))  # 蓝色
        other_pen.setWidth(1)  # 更细的线段
        other_pen.setStyle(QtCore.Qt.SolidLine)  # 使用实线而不是虚线
        
    def draw_angle_measurements(self):
        """绘制所有角度测量"""
        # 设置线段样式 - 使用绿色
        pen = QtGui.QPen(QtGui.QColor(0, 200, 0))
        pen.setWidth(1)
        
        # 获取图像边界
        image_rect = self.get_image_rect()
        
        # 绘制已完成的角度测量
        for i, angle in enumerate(self.angle_measurements):
            # 限制点在图像边界内
            p1 = self.constrain_point_to_image(angle['p1'])
            p2 = self.constrain_point_to_image(angle['p2'])  # 顶点
            p3 = self.constrain_point_to_image(angle['p3'])
            
            # 绘制两条线段
            line1 = self.scene.addLine(
                p2.x(), p2.y(),
                p1.x(), p1.y(),
                pen
            )
            
            line2 = self.scene.addLine(
                p2.x(), p2.y(),
                p3.x(), p3.y(),
                pen
            )
            
            # 在三个点上绘制小方块标记
            points = [p1, p2, p3]
            for j, point in enumerate(points):
                rect = QtWidgets.QGraphicsRectItem(
                    point.x() - 2, point.y() - 2, 4, 4
                )
                rect.setBrush(QtGui.QBrush(QtGui.QColor(0, 200, 0)))
                rect.setPen(pen)
                self.scene.addItem(rect)
            
            # 绘制角度弧
            # 计算向量
            v1 = QtCore.QPointF(p1.x() - p2.x(), p1.y() - p2.y())
            v2 = QtCore.QPointF(p3.x() - p2.x(), p3.y() - p2.y())
            
            # 计算向量长度
            len_v1 = math.sqrt(v1.x() ** 2 + v1.y() ** 2)
            len_v2 = math.sqrt(v2.x() ** 2 + v2.y() ** 2)
            
            # 计算单位向量
            if len_v1 > 0:
                v1_unit = QtCore.QPointF(v1.x() / len_v1, v1.y() / len_v1)
            else:
                v1_unit = QtCore.QPointF(0, 0)
                
            if len_v2 > 0:
                v2_unit = QtCore.QPointF(v2.x() / len_v2, v2.y() / len_v2)
            else:
                v2_unit = QtCore.QPointF(0, 0)
            
            # 计算弧的半径
            arc_radius = min(15, min(len_v1, len_v2) / 3)
            
            # 计算起始角度和结束角度
            start_angle = math.degrees(math.atan2(-v1.y(), v1.x()))
            end_angle = math.degrees(math.atan2(-v2.y(), v2.x()))
            
            # 确保角度是小于180度的
            angle_diff = (end_angle - start_angle) % 360
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
                temp = start_angle
                start_angle = end_angle
                end_angle = temp
            
            # 创建弧形路径
            path = QtGui.QPainterPath()
            path.moveTo(p2.x() + arc_radius * v1_unit.x(), 
                       p2.y() + arc_radius * v1_unit.y())
            
            # 添加弧形
            rect = QtCore.QRectF(
                p2.x() - arc_radius,
                p2.y() - arc_radius,
                arc_radius * 2,
                arc_radius * 2
            )
            
            # 计算角度范围
            span_angle = angle_diff
            
            # 添加弧形到路径
            path.arcTo(rect, start_angle, span_angle)
            
            # 绘制路径
            path_item = self.scene.addPath(path, pen)
            
            # 添加角度文本
            # 计算文本位置（在角度外侧）
            text_radius = arc_radius * 1.5
            mid_angle = math.radians((start_angle + end_angle) / 2)
            text_x = p2.x() + text_radius * math.cos(mid_angle)
            text_y = p2.y() - text_radius * math.sin(mid_angle)
            
            # 创建文本项 - 显示一位小数
            text = QtWidgets.QGraphicsTextItem(f"{angle['angle']:.1f}°")
            text.setPos(text_x - 15, text_y - 10)  # 调整位置使文本居中
            text.setDefaultTextColor(QtGui.QColor(0, 200, 0))
            
            # 设置文本字体
            font = QtGui.QFont()
            font.setBold(True)
            font.setPointSize(10)
            text.setFont(font)
            
            # 使用白色背景确保文本可见
            text_bg = QtWidgets.QGraphicsRectItem(text.boundingRect())
            text_bg.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))
            text_bg.setPen(QtGui.QPen(QtCore.Qt.NoPen))
            text_bg.setPos(text_x - 15, text_y - 10)
            
            # 先添加背景，再添加文本
            self.scene.addItem(text_bg)
            self.scene.addItem(text)
        
        # 绘制正在测量的角度
        if self.angle_measuring and len(self.angle_points) > 0:
            # 绘制已有的点
            for i, point in enumerate(self.angle_points):
                # 限制点在图像边界内
                constrained_point = self.constrain_point_to_image(point)
                rect = QtWidgets.QGraphicsRectItem(
                    constrained_point.x() - 2, constrained_point.y() - 2, 4, 4
                )
                rect.setBrush(QtGui.QBrush(QtGui.QColor(0, 200, 0)))
                rect.setPen(pen)
                self.scene.addItem(rect)
            
            # 绘制第一条线段（从第一个点到鼠标位置）
            if len(self.angle_points) == 1 and self.end_point:
                # 限制点在图像边界内
                constrained_p1 = self.constrain_point_to_image(self.angle_points[0])
                constrained_end = self.constrain_point_to_image(self.end_point)
                line = self.scene.addLine(
                    constrained_p1.x(), constrained_p1.y(),
                    constrained_end.x(), constrained_end.y(),
                    pen
                )
            
            # 绘制第一条完成的线段（从第一个点到顶点）
            if len(self.angle_points) >= 2:
                # 限制点在图像边界内
                constrained_p1 = self.constrain_point_to_image(self.angle_points[0])
                constrained_p2 = self.constrain_point_to_image(self.angle_points[1])
                line = self.scene.addLine(
                    constrained_p2.x(), constrained_p2.y(),  # 顶点
                    constrained_p1.x(), constrained_p1.y(),  # 第一个点
                    pen
                )
            
            # 绘制第二条线段（从顶点到鼠标位置或第三个点）
            if len(self.angle_points) == 2 and self.end_point:
                # 限制点在图像边界内
                constrained_p2 = self.constrain_point_to_image(self.angle_points[1])
                constrained_end = self.constrain_point_to_image(self.end_point)
                line = self.scene.addLine(
                    constrained_p2.x(), constrained_p2.y(),  # 顶点
                    constrained_end.x(), constrained_end.y(),  # 鼠标位置
                    pen
                )
                
                # 计算并显示角度
                angle_value = self.calculate_angle(
                    self.angle_points[0], 
                    self.angle_points[1], 
                    self.angle_points[2]
                )
                
                # 绘制角度弧和文本（与上面的代码类似）
                # 计算向量
                v1 = QtCore.QPointF(
                    self.angle_points[0].x() - self.angle_points[1].x(), 
                    self.angle_points[0].y() - self.angle_points[1].y()
                )
                v2 = QtCore.QPointF(
                    self.angle_points[2].x() - self.angle_points[1].x(), 
                    self.angle_points[2].y() - self.angle_points[1].y()
                )
                
                # 计算向量长度
                len_v1 = math.sqrt(v1.x() ** 2 + v1.y() ** 2)
                len_v2 = math.sqrt(v2.x() ** 2 + v2.y() ** 2)
                
                # 计算单位向量
                if len_v1 > 0:
                    v1_unit = QtCore.QPointF(v1.x() / len_v1, v1.y() / len_v1)
                else:
                    v1_unit = QtCore.QPointF(0, 0)
                    
                if len_v2 > 0:
                    v2_unit = QtCore.QPointF(v2.x() / len_v2, v2.y() / len_v2)
                else:
                    v2_unit = QtCore.QPointF(0, 0)
                
                # 计算弧的半径
                arc_radius = min(15, min(len_v1, len_v2) / 3)
                
                # 计算起始角度和结束角度
                start_angle = math.degrees(math.atan2(-v1.y(), v1.x()))
                end_angle = math.degrees(math.atan2(-v2.y(), v2.x()))
                
                # 确保角度是小于180度的
                angle_diff = (end_angle - start_angle) % 360
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff
                    temp = start_angle
                    start_angle = end_angle
                    end_angle = temp
                
                # 创建弧形路径
                path = QtGui.QPainterPath()
                path.moveTo(
                    self.angle_points[1].x() + arc_radius * v1_unit.x(), 
                    self.angle_points[1].y() + arc_radius * v1_unit.y()
                )
                
                # 添加弧形
                rect = QtCore.QRectF(
                    self.angle_points[1].x() - arc_radius,
                    self.angle_points[1].y() - arc_radius,
                    arc_radius * 2,
                    arc_radius * 2
                )
                
                # 计算角度范围
                span_angle = angle_diff
                
                # 添加弧形到路径
                path.arcTo(rect, start_angle, span_angle)
                
                # 绘制路径
                path_item = self.scene.addPath(path, pen)
                
                # 添加角度文本
                # 计算文本位置（在角度外侧）
                text_radius = arc_radius * 1.5
                mid_angle = math.radians((start_angle + end_angle) / 2)
                text_x = self.angle_points[1].x() + text_radius * math.cos(mid_angle)
                text_y = self.angle_points[1].y() - text_radius * math.sin(mid_angle)
                
                # 创建文本项 - 显示一位小数
                text = QtWidgets.QGraphicsTextItem(f"{angle_value:.1f}°")
                text.setPos(text_x - 15, text_y - 10)  # 调整位置使文本居中
                text.setDefaultTextColor(QtGui.QColor(0, 200, 0))
                
                # 设置文本字体
                font = QtGui.QFont()
                font.setBold(True)
                font.setPointSize(10)
                text.setFont(font)
                
                # 使用白色背景确保文本可见
                text_bg = QtWidgets.QGraphicsRectItem(text.boundingRect())
                text_bg.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))
                text_bg.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                text_bg.setPos(text_x - 15, text_y - 10)
                
                # 先添加背景，再添加文本
                self.scene.addItem(text_bg)
                self.scene.addItem(text)
                
                # 更新状态栏显示当前角度
                if hasattr(self, 'parent_controller') and self.parent_controller and hasattr(self.parent_controller, 'statusBar'):
                    self.parent_controller.statusBar().showMessage(f"角度测量: {angle_value:.1f}°")
        
        # 绘制对应的角度（其他视图中的角度）
        other_pen = QtGui.QPen(QtGui.QColor(0, 100, 255))  # 蓝绿色
        other_pen.setWidth(1)
        
        for angle in self.corresponding_angles:
            # 绘制两条线段
            line1 = self.scene.addLine(
                angle['p2'].x(), angle['p2'].y(),
                angle['p1'].x(), angle['p1'].y(),
                other_pen
            )
            
            line2 = self.scene.addLine(
                angle['p2'].x(), angle['p2'].y(),
                angle['p3'].x(), angle['p3'].y(),
                other_pen
            )
            
            # 在三个点上绘制小方块标记
            for point in ['p1', 'p2', 'p3']:
                rect = QtWidgets.QGraphicsRectItem(
                    angle[point].x() - 2, angle[point].y() - 2, 4, 4
                )
                rect.setBrush(QtGui.QBrush(QtGui.QColor(0, 100, 255)))
                rect.setPen(other_pen)
                self.scene.addItem(rect)
            
            # 绘制角度弧和文本（与上面的代码类似）
            if 'angle' in angle:
                # 计算向量
                v1 = QtCore.QPointF(angle['p1'].x() - angle['p2'].x(), angle['p1'].y() - angle['p2'].y())
                v2 = QtCore.QPointF(angle['p3'].x() - angle['p2'].x(), angle['p3'].y() - angle['p2'].y())
                
                # 计算向量长度
                len_v1 = math.sqrt(v1.x() ** 2 + v1.y() ** 2)
                len_v2 = math.sqrt(v2.x() ** 2 + v2.y() ** 2)
                
                # 计算单位向量
                if len_v1 > 0:
                    v1_unit = QtCore.QPointF(v1.x() / len_v1, v1.y() / len_v1)
                else:
                    v1_unit = QtCore.QPointF(0, 0)
                    
                if len_v2 > 0:
                    v2_unit = QtCore.QPointF(v2.x() / len_v2, v2.y() / len_v2)
                else:
                    v2_unit = QtCore.QPointF(0, 0)
                
                # 计算弧的半径
                arc_radius = min(15, min(len_v1, len_v2) / 3)
                
                # 计算起始角度和结束角度
                start_angle = math.degrees(math.atan2(-v1.y(), v1.x()))
                end_angle = math.degrees(math.atan2(-v2.y(), v2.x()))
                
                # 确保角度是小于180度的
                angle_diff = (end_angle - start_angle) % 360
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff
                    temp = start_angle
                    start_angle = end_angle
                    end_angle = temp
                
                # 创建弧形路径
                path = QtGui.QPainterPath()
                path.moveTo(angle['p2'].x() + arc_radius * v1_unit.x(), 
                           angle['p2'].y() + arc_radius * v1_unit.y())
                
                # 添加弧形
                rect = QtCore.QRectF(
                    angle['p2'].x() - arc_radius,
                    angle['p2'].y() - arc_radius,
                    arc_radius * 2,
                    arc_radius * 2
                )
                
                # 计算角度范围
                span_angle = angle_diff
                
                # 添加弧形到路径
                path.arcTo(rect, start_angle, span_angle)
                
                # 绘制路径
                path_item = self.scene.addPath(path, other_pen)
                
                # 添加角度文本
                # 计算文本位置（在角度外侧）
                text_radius = arc_radius * 1.5
                mid_angle = math.radians((start_angle + end_angle) / 2)
                text_x = angle['p2'].x() + text_radius * math.cos(mid_angle)
                text_y = angle['p2'].y() - text_radius * math.sin(mid_angle)
                
                # 创建文本项 - 显示一位小数
                text = QtWidgets.QGraphicsTextItem(f"{angle['angle']:.1f}°")
                text.setPos(text_x - 15, text_y - 10)  # 调整位置使文本居中
                text.setDefaultTextColor(QtGui.QColor(0, 100, 255))
                
                # 设置文本字体
                font = QtGui.QFont()
                font.setBold(True)
                font.setPointSize(10)
                text.setFont(font)
                
                # 使用白色背景确保文本可见
                text_bg = QtWidgets.QGraphicsRectItem(text.boundingRect())
                text_bg.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))
                text_bg.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                text_bg.setPos(text_x - 15, text_y - 10)
                
                # 先添加背景，再添加文本
                self.scene.addItem(text_bg)
                self.scene.addItem(text)
        
        for line in self.corresponding_lines:
            # 绘制线段
            line_item = self.scene.addLine(
                line['start'].x(), line['start'].y(),
                line['end'].x(), line['end'].y(),
                other_pen
            )
            
            # 在线段起点和终点绘制更小的方块标记
            start_rect = QtWidgets.QGraphicsRectItem(
                line['start'].x() - 2, line['start'].y() - 2, 4, 4
            )
            start_rect.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 255)))  # 蓝色
            start_rect.setPen(other_pen)
            self.scene.addItem(start_rect)
            
            end_rect = QtWidgets.QGraphicsRectItem(
                line['end'].x() - 2, line['end'].y() - 2, 4, 4
            )
            end_rect.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 255)))  # 蓝色
            end_rect.setPen(other_pen)
            self.scene.addItem(end_rect)
            
            # 添加距离文本
            if 'distance' in line:
                # 计算线段中点
                mid_x = (line['start'].x() + line['end'].x()) / 2
                mid_y = (line['start'].y() + line['end'].y()) / 2
                
                # 计算文本位置 - 根据线段方向调整
                dx = line['end'].x() - line['start'].x()
                dy = line['end'].y() - line['start'].y()
                
                # 计算线段角度
                angle = math.atan2(dy, dx)
                
                # 根据角度决定文本位置
                if -math.pi/4 <= angle <= math.pi/4:  # 线段接近水平向右
                    text_x = mid_x - 25
                    text_y = mid_y - 20
                elif math.pi/4 < angle <= 3*math.pi/4:  # 线段接近垂直向下
                    text_x = mid_x + 10
                    text_y = mid_y - 10
                elif -3*math.pi/4 <= angle < -math.pi/4:  # 线段接近垂直向上
                    text_x = mid_x + 10
                    text_y = mid_y - 10
                else:  # 线段接近水平向左
                    text_x = mid_x + 10
                    text_y = mid_y - 20
                
                # 创建文本项 - 只显示整数值
                text = QtWidgets.QGraphicsTextItem(f"{int(line['distance'])}")
                text.setPos(text_x, text_y)
                text.setDefaultTextColor(QtGui.QColor(0, 0, 255))  # 蓝色
                
                # 设置文本字体
                font = QtGui.QFont()
                font.setBold(True)
                font.setPointSize(10)
                text.setFont(font)
                
                # 使用白色背景确保文本可见
                text_bg = QtWidgets.QGraphicsRectItem(text.boundingRect())
                text_bg.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))
                text_bg.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                text_bg.setPos(text_x, text_y)
                
                # 先添加背景，再添加文本
                self.scene.addItem(text_bg)
                self.scene.addItem(text)
    
    def add_corresponding_line(self, start, end, distance=None):
        """
        添加对应的线段（其他视图中的线段）
        
        参数
        ----
        start : QPoint
            起始点
        end : QPoint
            结束点
        distance : float, optional
            线段的距离，如果为None则自动计算
        """
        # 转换为场景坐标
        scene_start = QtCore.QPointF(start.x(), start.y())
        scene_end = QtCore.QPointF(end.x(), end.y())
        
        # 限制点在图像边界内
        scene_start = self.constrain_point_to_image(scene_start)
        scene_end = self.constrain_point_to_image(scene_end)
        
        # 如果没有提供距离，则计算距离
        if distance is None:
            distance = math.sqrt((scene_end.x() - scene_start.x())**2 + (scene_end.y() - scene_start.y())**2)
        
        # 添加到对应线段列表
        self.corresponding_lines.append({
            'start': scene_start,
            'end': scene_end,
            'distance': distance
        })
        
        # 重绘测量线
        self.redraw_measurement_lines()
        
    def add_corresponding_angle(self, p1, p2, p3, angle=None):
        """
        添加对应的角度（其他视图中的角度）
        
        参数
        ----
        p1, p2, p3 : QPoint
            构成角度的三个点，p2是角的顶点
        angle : float, optional
            角度值，如果为None则自动计算
        """
        # 转换为场景坐标
        scene_p1 = QtCore.QPointF(p1.x(), p1.y())
        scene_p2 = QtCore.QPointF(p2.x(), p2.y())
        scene_p3 = QtCore.QPointF(p3.x(), p3.y())
        
        # 限制点在图像边界内
        scene_p1 = self.constrain_point_to_image(scene_p1)
        scene_p2 = self.constrain_point_to_image(scene_p2)
        scene_p3 = self.constrain_point_to_image(scene_p3)
        
        # 如果没有提供角度，则计算角度
        if angle is None:
            angle = self.calculate_angle(scene_p1, scene_p2, scene_p3)
        
        # 添加到对应角度列表
        self.corresponding_angles.append({
            'p1': scene_p1,
            'p2': scene_p2,
            'p3': scene_p3,
            'angle': angle
        })
        
        # 重绘测量线和角度
        self.redraw_measurement_lines()
    
    def enable_roi_mode(self, mode, parent_controller):
        """启用ROI模式"""
        self.roi_mode = mode
        self.parent_controller = parent_controller
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage(f"ROI模式: {mode}")
    
    def disable_roi_mode(self):
        """禁用ROI模式"""
        self.roi_mode = None
        self.parent_controller = None
    
    def setup_roi_variables(self):
        """初始化ROI相关变量"""
        self.roi_mode = None
        self.roi_rects = []  # 存储该视图中的ROI矩形
        self.current_roi = None  # 当前正在绘制的ROI
        self.roi_start = None  # ROI绘制起点
        self.roi_end = None  # ROI绘制终点
        self.parent_controller = None  # 父控制器引用
        self.is_roi_dragging = False  # 是否在拖动ROI
        self.active_roi = -1  # 当前活动的ROI索引
    
    def handle_roi_mouse_press(self, event):
        """处理ROI模式的鼠标按下事件"""
        if self.roi_mode != 'selection':
            return False
        
        # 检查是否已经在其他视图中选取了ROI
        if self.parent_controller and hasattr(self.parent_controller, 'roi_selection_view'):
            if self.parent_controller.roi_selection_view is not None:
                # 已经在其他视图中选取了ROI，禁止在本视图继续选取
                if self.parent_controller.roi_selection_view != self.view_type:
                    print(f"禁止在{self.view_type}视图选取ROI，因为已经在{self.parent_controller.roi_selection_view}视图中选取")
                    return False
        
        scene_pos = self.view.mapToScene(event.pos())
        
        # 检查是否点击在现有ROI上
        for i, roi in enumerate(self.roi_rects):
            if self.point_in_roi(scene_pos, roi):
                self.active_roi = i
                self.is_roi_dragging = True
                return True
        
        # 在该视图中开始绘制新ROI
        self.roi_start = scene_pos
        self.roi_end = scene_pos
        self.current_roi = {'start': scene_pos, 'end': scene_pos}
        
        # 记录在哪个视图中选取了ROI
        if self.parent_controller and hasattr(self.parent_controller, 'roi_selection_view'):
            self.parent_controller.roi_selection_view = self.view_type
            print(f"在{self.view_type}视图中开始选取ROI")
            
            # 更新深度滑动条的范围和标签
            if hasattr(self.parent_controller, 'update_depth_slider_for_view'):
                self.parent_controller.update_depth_slider_for_view(self.view_type)
        
        self.redraw_roi()
        return True
    
    def handle_roi_mouse_move(self, event):
        """处理ROI模式的鼠标移动事件"""
        if self.roi_mode != 'selection':
            return False
        
        scene_pos = self.view.mapToScene(event.pos())
        
        if self.is_roi_dragging and hasattr(self, 'active_roi'):
            # 拖动现有ROI
            roi = self.roi_rects[self.active_roi]
            dx = scene_pos.x() - self.roi_end.x()
            dy = scene_pos.y() - self.roi_end.y()
            
            roi['rect'].translate(dx, dy)
            self.roi_end = scene_pos
            self.redraw_roi()
            return True
        
        elif self.current_roi is not None:
            # 正在绘制新ROI
            self.roi_end = scene_pos
            self.current_roi['end'] = scene_pos
            self.redraw_roi()
            
            # 更新状态栏显示ROI大小
            width = abs(self.roi_end.x() - self.roi_start.x())
            height = abs(self.roi_end.y() - self.roi_start.y())
            if hasattr(self, 'parent_controller') and self.parent_controller and hasattr(self.parent_controller, 'statusBar'):
                self.parent_controller.statusBar().showMessage(f"ROI大小: {int(width)}x{int(height)}")
            
            return True
        
        return False
    
    def handle_roi_mouse_release(self, event):
        """处理ROI模式的鼠标释放事件"""
        if self.roi_mode != 'selection':
            return False
        
        self.is_roi_dragging = False
        
        if self.current_roi is not None:
            # 完成ROI绘制
            start = self.current_roi['start']
            end = self.current_roi['end']
            
            if abs(end.x() - start.x()) > 5 and abs(end.y() - start.y()) > 5:
                # ROI有效（大小足够大）
                # 创建矩形
                x_min = min(start.x(), end.x())
                x_max = max(start.x(), end.x())
                y_min = min(start.y(), end.y())
                y_max = max(start.y(), end.y())
                
                rect = QtCore.QRectF(x_min, y_min, x_max - x_min, y_max - y_min)
                
                roi_data = {
                    'rect': rect,
                    'slice_index': self.slider.value(),
                    'view_type': self.view_type
                }
                
                self.roi_rects.append(roi_data)
                
                # 通知父控制器
                if hasattr(self, 'parent_controller') and self.parent_controller:
                    self.parent_controller.add_roi_to_view(self.view_type, rect, self.slider.value())
            
            self.current_roi = None
            self.roi_start = None
            self.roi_end = None
            self.redraw_roi()
            return True
        
        return False
    
    def point_in_roi(self, point, roi):
        """检查点是否在ROI内"""
        rect = roi['rect']
        return rect.contains(point)
    
    def redraw_roi(self):
        """重绘所有ROI矩形"""
        if hasattr(self, 'scene'):
            # 只清除ROI相关的图形项（矩形和文本标签）
            # 查找并删除所有ROI矩形和标签
            items_to_remove = []
            for item in self.scene.items():
                # 跳过pixmap_item
                if item == self.pixmap_item:
                    continue
                # 保留测量线段和角度标记（使用特定的颜色检查）
                if isinstance(item, QtWidgets.QGraphicsLineItem):
                    # 保留红色或蓝色的线段（测量线）
                    pen_color = item.pen().color()
                    if pen_color.red() in [255, 0] and pen_color.green() == 0:
                        continue
                if isinstance(item, QtWidgets.QGraphicsRectItem):
                    # 保留不是我们绘制的ROI框（红蓝色的小点）
                    pen_color = item.pen().color()
                    if pen_color.red() in [255, 0] and pen_color.green() == 0:
                        continue
                # 删除绿色和黄色的项（ROI框和标签）
                if isinstance(item, (QtWidgets.QGraphicsRectItem, QtWidgets.QGraphicsTextItem)):
                    if isinstance(item, QtWidgets.QGraphicsTextItem):
                        # 保留数字标签（距离、角度），删除ROI标签
                        if "ROI-" in item.toPlainText():
                            items_to_remove.append(item)
                    else:
                        items_to_remove.append(item)
            
            for item in items_to_remove:
                self.scene.removeItem(item)
            
            # 绘制所有已保存的ROI
            roi_pen = QtGui.QPen(QtGui.QColor(0, 255, 0))  # 绿色
            roi_pen.setWidth(2)
            roi_pen.setStyle(QtCore.Qt.SolidLine)
            
            for roi in self.roi_rects:
                rect = roi['rect']
                self.scene.addRect(rect, roi_pen)
                
                # 添加ROI标签
                text = QtWidgets.QGraphicsTextItem(f"ROI-{roi.get('id', 0)}")
                text.setPos(rect.x(), rect.y() - 15)
                text.setDefaultTextColor(QtGui.QColor(0, 255, 0))
                font = QtGui.QFont()
                font.setBold(True)
                text.setFont(font)
                self.scene.addItem(text)
            
            # 绘制当前正在绘制的ROI
            if self.current_roi is not None:
                start = self.current_roi['start']
                end = self.current_roi['end']
                
                x_min = min(start.x(), end.x())
                x_max = max(start.x(), end.x())
                y_min = min(start.y(), end.y())
                y_max = max(start.y(), end.y())
                
                temp_pen = QtGui.QPen(QtGui.QColor(255, 255, 0))  # 黄色虚线
                temp_pen.setWidth(1)
                temp_pen.setStyle(QtCore.Qt.DashLine)
                
                temp_rect = QtCore.QRectF(x_min, y_min, x_max - x_min, y_max - y_min)
                self.scene.addRect(temp_rect, temp_pen)
    
    def _array_to_pixmap(self, arr):
        """将numpy数组转换为QPixmap"""
        from File.DataTransform import array_to_qpixmap
        
        # array_to_qpixmap会自动进行归一化，无需传递窗宽窗位参数
        pixmap = array_to_qpixmap(arr)
        return pixmap