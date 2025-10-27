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
        
        # 放大按钮
        zoom_btn = QtWidgets.QPushButton("🔍")
        zoom_btn.setMaximumWidth(40)
        zoom_btn.setToolTip("在新窗口中打开，可缩放和平移")
        zoom_btn.clicked.connect(self.open_zoom_window)
        title_layout.addWidget(zoom_btn)
        
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
        
        # 安装事件过滤器以处理鼠标事件
        self.view.viewport().installEventFilter(self)
    
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
            测量模式，例如 'distance'
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
        
        # 确保对应线段列表是空的
        self.corresponding_lines = []
    
    def disable_measurement_mode(self):
        """禁用测量模式"""
        self.measurement_mode = None
        
        # 恢复默认鼠标指针
        self.view.viewport().setCursor(QtCore.Qt.ArrowCursor)
        
        # 清除当前测量状态
        self.is_measuring = False
        self.start_point = None
        self.end_point = None
    
    def eventFilter(self, obj, event):
        """事件过滤器，处理鼠标事件"""
        if obj == self.view.viewport():
            if self.measurement_mode == 'distance':
                if event.type() == QtCore.QEvent.MouseButtonPress:
                    if event.button() == QtCore.Qt.LeftButton:
                        return self.handle_mouse_press(event)
                    elif event.button() == QtCore.Qt.RightButton:
                        return self.handle_right_click(event)
                        
                elif event.type() == QtCore.QEvent.MouseMove:
                    return self.handle_mouse_move(event)
                    
                elif event.type() == QtCore.QEvent.MouseButtonRelease:
                    if event.button() == QtCore.Qt.LeftButton:
                        return self.handle_mouse_release(event)
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
            
        return False
        
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
    
    def handle_mouse_press(self, event):
        """处理鼠标按下事件"""
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
    
    def handle_mouse_move(self, event):
        """处理鼠标移动事件"""
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
    
    def handle_mouse_release(self, event):
        """处理鼠标释放事件"""
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
    
    def calculate_distance(self, p1, p2):
        """计算两点之间的欧几里得距离"""
        return math.sqrt((p2.x() - p1.x())**2 + (p2.y() - p1.y())**2)
    
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
    
    def redraw_measurement_lines(self):
        """重绘所有测量线段"""
        # 清除所有已有的线段和文本
        for item in self.scene.items():
            if isinstance(item, (QtWidgets.QGraphicsLineItem, QtWidgets.QGraphicsTextItem, 
                                QtWidgets.QGraphicsRectItem, QtWidgets.QGraphicsEllipseItem)):
                self.scene.removeItem(item)
        
        # 设置线段样式 - 使用亮红色，但线段更细
        pen = QtGui.QPen(QtGui.QColor(255, 0, 0))
        pen.setWidth(1)  # 减小线段宽度
        
        # 绘制已完成的测量线段
        for i, line in enumerate(self.measurement_lines):
            # 绘制线段
            line_item = self.scene.addLine(
                line['start'].x(), line['start'].y(),
                line['end'].x(), line['end'].y(),
                pen
            )
            
            # 在线段起点和终点绘制更小的方块标记
            start_rect = QtWidgets.QGraphicsRectItem(
                line['start'].x() - 2, line['start'].y() - 2, 4, 4
            )
            start_rect.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0)))
            start_rect.setPen(pen)
            self.scene.addItem(start_rect)
            
            end_rect = QtWidgets.QGraphicsRectItem(
                line['end'].x() - 2, line['end'].y() - 2, 4, 4
            )
            end_rect.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0)))
            end_rect.setPen(pen)
            self.scene.addItem(end_rect)
            
            # 添加距离文本 - 直接显示在线段旁边
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
        
        # 绘制正在测量的线段
        if self.is_measuring and self.start_point and self.end_point:
            # 绘制线段
            line_item = self.scene.addLine(
                self.start_point.x(), self.start_point.y(),
                self.end_point.x(), self.end_point.y(),
                pen
            )
            
            # 在线段起点和终点绘制更小的方块标记
            start_rect = QtWidgets.QGraphicsRectItem(
                self.start_point.x() - 2, self.start_point.y() - 2, 4, 4
            )
            start_rect.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0)))
            start_rect.setPen(pen)
            self.scene.addItem(start_rect)
            
            end_rect = QtWidgets.QGraphicsRectItem(
                self.end_point.x() - 2, self.end_point.y() - 2, 4, 4
            )
            end_rect.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0)))
            end_rect.setPen(pen)
            self.scene.addItem(end_rect)
            
            # 计算并显示当前距离
            distance = self.calculate_distance(self.start_point, self.end_point)
            
            # 计算线段中点
            mid_x = (self.start_point.x() + self.end_point.x()) / 2
            mid_y = (self.start_point.y() + self.end_point.y()) / 2
            
            # 计算文本位置 - 根据线段方向调整
            dx = self.end_point.x() - self.start_point.x()
            dy = self.end_point.y() - self.start_point.y()
            
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