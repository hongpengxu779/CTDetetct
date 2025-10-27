"""
测量功能模块
提供距离测量等功能
"""

from PyQt5 import QtWidgets, QtCore, QtGui
import numpy as np
import math


class MeasurementOperations:
    """测量功能类，作为Mixin使用"""
    
    def setup_measurement(self):
        """初始化测量相关的变量"""
        # 当前测量模式
        self.measurement_mode = None
        # 存储所有视图中的测量线段
        self.measurement_lines = {
            'axial': [],
            'sagittal': [],
            'coronal': []
        }
        # 存储所有视图中的角度测量
        self.angle_measurements = {
            'axial': [],
            'sagittal': [],
            'coronal': []
        }
        # 当前活动的视图
        self.active_view = None
        # 当前正在绘制的线段
        self.current_line = None
        # 当前正在绘制的角度点
        self.current_angle_points = []
        
    def measure_distance(self):
        """启动距离测量模式"""
        # 如果已经在距离测量模式，则退出测量模式
        if self.measurement_mode == 'distance':
            self.exit_measurement_mode()
            return
        
        # 设置测量模式为距离
        self.measurement_mode = 'distance'
        
        # 通知用户当前模式
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage("距离测量模式：在视图中点击并拖动鼠标来测量距离")
        
        # 为所有切片视图启用测量模式
        if hasattr(self, 'axial_viewer') and self.axial_viewer:
            self.axial_viewer.enable_measurement_mode('distance', self)
        if hasattr(self, 'sag_viewer') and self.sag_viewer:
            self.sag_viewer.enable_measurement_mode('distance', self)
        if hasattr(self, 'cor_viewer') and self.cor_viewer:
            self.cor_viewer.enable_measurement_mode('distance', self)
            
    def measure_angle(self):
        """启动角度测量模式"""
        # 如果已经在角度测量模式，则退出测量模式
        if self.measurement_mode == 'angle':
            self.exit_measurement_mode()
            return
        
        # 设置测量模式为角度
        self.measurement_mode = 'angle'
        
        # 通知用户当前模式
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage("角度测量模式：在视图中点击三个点来测量角度")
        
        # 为所有切片视图启用测量模式
        if hasattr(self, 'axial_viewer') and self.axial_viewer:
            self.axial_viewer.enable_measurement_mode('angle', self)
        if hasattr(self, 'sag_viewer') and self.sag_viewer:
            self.sag_viewer.enable_measurement_mode('angle', self)
        if hasattr(self, 'cor_viewer') and self.cor_viewer:
            self.cor_viewer.enable_measurement_mode('angle', self)
    
    def clear_all_measurement_lines(self):
        """清除所有视图中的测量线段"""
        # 清空所有视图的线段
        self.measurement_lines = {
            'axial': [],
            'sagittal': [],
            'coronal': []
        }
        
        # 清空所有视图中的对应线段
        if hasattr(self, 'axial_viewer') and self.axial_viewer:
            self.axial_viewer.measurement_lines = []
            self.axial_viewer.corresponding_lines = []
            self.axial_viewer.redraw_measurement_lines()
        if hasattr(self, 'sag_viewer') and self.sag_viewer:
            self.sag_viewer.measurement_lines = []
            self.sag_viewer.corresponding_lines = []
            self.sag_viewer.redraw_measurement_lines()
        if hasattr(self, 'cor_viewer') and self.cor_viewer:
            self.cor_viewer.measurement_lines = []
            self.cor_viewer.corresponding_lines = []
            self.cor_viewer.redraw_measurement_lines()
            
        print("已清除所有测量线段")
        
    def clear_all_angle_measurements(self):
        """清除所有视图中的角度测量"""
        # 清空所有视图的角度测量
        self.angle_measurements = {
            'axial': [],
            'sagittal': [],
            'coronal': []
        }
        
        # 清空所有视图中的对应角度
        if hasattr(self, 'axial_viewer') and self.axial_viewer:
            self.axial_viewer.angle_measurements = []
            self.axial_viewer.corresponding_angles = []
            self.axial_viewer.redraw_measurement_lines()
        if hasattr(self, 'sag_viewer') and self.sag_viewer:
            self.sag_viewer.angle_measurements = []
            self.sag_viewer.corresponding_angles = []
            self.sag_viewer.redraw_measurement_lines()
        if hasattr(self, 'cor_viewer') and self.cor_viewer:
            self.cor_viewer.angle_measurements = []
            self.cor_viewer.corresponding_angles = []
            self.cor_viewer.redraw_measurement_lines()
            
        print("已清除所有角度测量")
    
    def exit_measurement_mode(self):
        """退出测量模式"""
        self.measurement_mode = None
        
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage("已退出测量模式", 3000)
        
        # 为所有切片视图禁用测量模式
        if hasattr(self, 'axial_viewer') and self.axial_viewer:
            self.axial_viewer.disable_measurement_mode()
        if hasattr(self, 'sag_viewer') and self.sag_viewer:
            self.sag_viewer.disable_measurement_mode()
        if hasattr(self, 'cor_viewer') and self.cor_viewer:
            self.cor_viewer.disable_measurement_mode()
            
    def adjust_slices_for_measurement(self, source_view, start_point, end_point):
        """
        调整其他视图的切片位置，以便显示距离测量区域
        
        参数
        ----
        source_view : str
            源视图类型，'axial', 'sagittal' 或 'coronal'
        start_point : QPointF
            起始点
        end_point : QPointF
            结束点
        """
        # 获取坐标
        start_x = int(start_point.x())
        start_y = int(start_point.y())
        end_x = int(end_point.x())
        end_y = int(end_point.y())
        
        # 计算中点坐标，用于调整切片位置
        mid_x = (start_x + end_x) // 2
        mid_y = (start_y + end_y) // 2
        
        # 根据源视图类型调整其他视图的切片位置
        if source_view == 'axial':
            # 获取当前轴位面切片索引
            z_index = self.axial_viewer.slider.value()
            
            # 调整矢状面切片位置到测量线的中点x坐标
            if hasattr(self, 'sag_viewer') and self.sag_viewer:
                # 矢状面的切片索引对应轴位面的x坐标
                self.sag_viewer.slider.setValue(mid_x)
                print(f"调整矢状面切片位置: {mid_x}")
            
            # 调整冠状面切片位置到测量线的中点y坐标
            if hasattr(self, 'cor_viewer') and self.cor_viewer:
                # 冠状面的切片索引对应轴位面的y坐标
                self.cor_viewer.slider.setValue(mid_y)
                print(f"调整冠状面切片位置: {mid_y}")
                
        elif source_view == 'sagittal':
            # 获取当前矢状面切片索引
            x_index = self.sag_viewer.slider.value()
            
            # 调整轴位面切片位置到测量线的中点x坐标(z轴)
            if hasattr(self, 'axial_viewer') and self.axial_viewer:
                # 轴位面的切片索引对应矢状面的x坐标(z轴)
                self.axial_viewer.slider.setValue(mid_x)
                print(f"调整轴位面切片位置: {mid_x}")
            
            # 调整冠状面切片位置到测量线的中点y坐标
            if hasattr(self, 'cor_viewer') and self.cor_viewer:
                # 冠状面的切片索引对应矢状面的y坐标
                self.cor_viewer.slider.setValue(mid_y)
                print(f"调整冠状面切片位置: {mid_y}")
                
        elif source_view == 'coronal':
            # 获取当前冠状面切片索引
            y_index = self.cor_viewer.slider.value()
            
            # 调整轴位面切片位置到测量线的中点y坐标(z轴)
            if hasattr(self, 'axial_viewer') and self.axial_viewer:
                # 轴位面的切片索引对应冠状面的y坐标(z轴)
                self.axial_viewer.slider.setValue(mid_y)
                print(f"调整轴位面切片位置: {mid_y}")
            
            # 调整矢状面切片位置到测量线的中点x坐标
            if hasattr(self, 'sag_viewer') and self.sag_viewer:
                # 矢状面的切片索引对应冠状面的x坐标
                self.sag_viewer.slider.setValue(mid_x)
                print(f"调整矢状面切片位置: {mid_x}")
    
    def update_temp_line(self, source_view, start_point, end_point):
        """
        实时更新其他视图中的临时线段
        
        参数
        ----
        source_view : str
            源视图类型，'axial', 'sagittal' 或 'coronal'
        start_point : QPointF
            起始点
        end_point : QPointF
            结束点
        """
        # 清空所有视图中的对应线段
        if hasattr(self, 'axial_viewer') and self.axial_viewer and source_view != 'axial':
            self.axial_viewer.corresponding_lines = []
        if hasattr(self, 'sag_viewer') and self.sag_viewer and source_view != 'sagittal':
            self.sag_viewer.corresponding_lines = []
        if hasattr(self, 'cor_viewer') and self.cor_viewer and source_view != 'coronal':
            self.cor_viewer.corresponding_lines = []
            
        # 计算距离
        distance = None
        
        # 如果起点和终点都有效
        if start_point and end_point:
            # 计算距离
            dx = end_point.x() - start_point.x()
            dy = end_point.y() - start_point.y()
            distance = math.sqrt(dx*dx + dy*dy)
            
            # 更新其他视图中的对应线段
            self.update_corresponding_lines(source_view, start_point, end_point, distance)
            
    def update_temp_angle(self, source_view, p1, p2, p3):
        """
        实时更新其他视图中的临时角度
        
        参数
        ----
        source_view : str
            源视图类型，'axial', 'sagittal' 或 'coronal'
        p1, p2, p3 : QPointF
            构成角度的三个点，p2是角的顶点
        """
        # 清空所有视图中的对应角度
        if hasattr(self, 'axial_viewer') and self.axial_viewer and source_view != 'axial':
            self.axial_viewer.corresponding_angles = []
        if hasattr(self, 'sag_viewer') and self.sag_viewer and source_view != 'sagittal':
            self.sag_viewer.corresponding_angles = []
        if hasattr(self, 'cor_viewer') and self.cor_viewer and source_view != 'coronal':
            self.cor_viewer.corresponding_angles = []
            
        # 计算角度
        angle_value = None
        
        # 如果三个点都有效
        if p1 and p2 and p3:
            # 计算角度
            if hasattr(self, source_view + '_viewer') and getattr(self, source_view + '_viewer'):
                viewer = getattr(self, source_view + '_viewer')
                angle_value = viewer.calculate_angle(p1, p2, p3)
            
            # 更新其他视图中的对应角度
            self.update_corresponding_angles(source_view, p1, p2, p3, angle_value)
            
            # 调整其他视图的切片位置，以便实时显示测量区域
            # 计算中点坐标，用于调整切片位置
            # 使用角度的顶点作为中心点
            self.adjust_slices_for_angle_measurement(source_view, p1, p2, p3)
            
            # 在这里不需要调整切片位置，因为这是角度测量的函数
            pass
                    
    def adjust_slices_for_angle_measurement(self, source_view, p1, p2, p3):
        """
        调整其他视图的切片位置，以便显示角度测量区域
        
        参数
        ----
        source_view : str
            源视图类型，'axial', 'sagittal' 或 'coronal'
        p1, p2, p3 : QPointF
            构成角度的三个点，p2是角的顶点
        """
        # 获取坐标
        p1_x = int(p1.x())
        p1_y = int(p1.y())
        p2_x = int(p2.x())  # 顶点
        p2_y = int(p2.y())  # 顶点
        p3_x = int(p3.x())
        p3_y = int(p3.y())
        
        # 使用角度的顶点作为中心点来调整切片位置
        mid_x = p2_x
        mid_y = p2_y
        
        # 根据源视图类型调整其他视图的切片位置
        if source_view == 'axial':
            # 获取当前轴位面切片索引
            z_index = self.axial_viewer.slider.value()
            
            # 调整矢状面切片位置到角度顶点的x坐标
            if hasattr(self, 'sag_viewer') and self.sag_viewer:
                self.sag_viewer.slider.setValue(mid_x)
            
            # 调整冠状面切片位置到角度顶点的y坐标
            if hasattr(self, 'cor_viewer') and self.cor_viewer:
                self.cor_viewer.slider.setValue(mid_y)
                
        elif source_view == 'sagittal':
            # 调整轴位面切片位置到角度顶点的x坐标(z轴)
            if hasattr(self, 'axial_viewer') and self.axial_viewer:
                self.axial_viewer.slider.setValue(mid_x)
            
            # 调整冠状面切片位置到角度顶点的y坐标
            if hasattr(self, 'cor_viewer') and self.cor_viewer:
                self.cor_viewer.slider.setValue(mid_y)
                
        elif source_view == 'coronal':
            # 调整轴位面切片位置到角度顶点的y坐标(z轴)
            if hasattr(self, 'axial_viewer') and self.axial_viewer:
                self.axial_viewer.slider.setValue(mid_y)
            
            # 调整矢状面切片位置到角度顶点的x坐标
                if hasattr(self, 'sag_viewer') and self.sag_viewer:
                    self.sag_viewer.slider.setValue(mid_x)
        
        # 强制重绘其他视图
        if hasattr(self, 'axial_viewer') and self.axial_viewer and source_view != 'axial':
            self.axial_viewer.redraw_measurement_lines()
        if hasattr(self, 'sag_viewer') and self.sag_viewer and source_view != 'sagittal':
            self.sag_viewer.redraw_measurement_lines()
        if hasattr(self, 'cor_viewer') and self.cor_viewer and source_view != 'coronal':
            self.cor_viewer.redraw_measurement_lines()
    
    def sync_measurement_lines(self, source_view):
        """
        同步所有视图中的测量线段
        
        参数
        ----
        source_view : str
            源视图类型，'axial', 'sagittal' 或 'coronal'
        """
        print(f"同步测量线段: 源视图={source_view}")
        
        # 清空所有视图中的线段，确保同步
        # 首先保存当前视图的线段
        current_lines = self.measurement_lines[source_view].copy()
        
        # 清空所有视图的线段
        self.measurement_lines = {
            'axial': [],
            'sagittal': [],
            'coronal': []
        }
        
        # 恢复当前视图的线段
        self.measurement_lines[source_view] = current_lines
        
        # 清空所有视图中的对应线段
        if hasattr(self, 'axial_viewer') and self.axial_viewer:
            self.axial_viewer.corresponding_lines = []
        if hasattr(self, 'sag_viewer') and self.sag_viewer:
            self.sag_viewer.corresponding_lines = []
        if hasattr(self, 'cor_viewer') and self.cor_viewer:
            self.cor_viewer.corresponding_lines = []
            
        # 对每个测量线段更新其他视图中的对应线段
        for line in self.measurement_lines[source_view]:
            self.update_corresponding_lines(source_view, line['start'], line['end'], line['distance'])
            
        # 强制重绘所有视图以确保显示更新
        if hasattr(self, 'axial_viewer') and self.axial_viewer:
            self.axial_viewer.redraw_measurement_lines()
        if hasattr(self, 'sag_viewer') and self.sag_viewer:
            self.sag_viewer.redraw_measurement_lines()
        if hasattr(self, 'cor_viewer') and self.cor_viewer:
            self.cor_viewer.redraw_measurement_lines()
            
    def sync_angle_measurements(self, source_view):
        """
        同步所有视图中的角度测量
        
        参数
        ----
        source_view : str
            源视图类型，'axial', 'sagittal' 或 'coronal'
        """
        print(f"同步角度测量: 源视图={source_view}")
        
        # 清空所有视图中的角度，确保同步
        # 首先保存当前视图的角度
        current_angles = self.angle_measurements[source_view].copy()
        
        # 清空所有视图的角度
        self.angle_measurements = {
            'axial': [],
            'sagittal': [],
            'coronal': []
        }
        
        # 恢复当前视图的角度
        self.angle_measurements[source_view] = current_angles
        
        # 清空所有视图中的对应角度
        if hasattr(self, 'axial_viewer') and self.axial_viewer:
            self.axial_viewer.corresponding_angles = []
        if hasattr(self, 'sag_viewer') and self.sag_viewer:
            self.sag_viewer.corresponding_angles = []
        if hasattr(self, 'cor_viewer') and self.cor_viewer:
            self.cor_viewer.corresponding_angles = []
            
        # 对每个角度测量更新其他视图中的对应角度
        for angle in self.angle_measurements[source_view]:
            self.update_corresponding_angles(source_view, angle['p1'], angle['p2'], angle['p3'], angle['angle'])
            
        # 强制重绘所有视图以确保显示更新
        if hasattr(self, 'axial_viewer') and self.axial_viewer:
            self.axial_viewer.redraw_measurement_lines()
        if hasattr(self, 'sag_viewer') and self.sag_viewer:
            self.sag_viewer.redraw_measurement_lines()
        if hasattr(self, 'cor_viewer') and self.cor_viewer:
            self.cor_viewer.redraw_measurement_lines()
    
    def on_measurement_completed(self, view_type, start_point, end_point, pixel_distance):
        """
        当距离测量完成时的回调函数
        
        参数
        ----
        view_type : str
            视图类型，'axial', 'sagittal' 或 'coronal'
        start_point : QPointF
            起始点
        end_point : QPointF
            结束点
        pixel_distance : float
            像素距离
        """
        # 检查是否已存在相同的测量线段
        # 由于QPointF的比较可能不精确，我们使用坐标值进行比较
        start_x, start_y = start_point.x(), start_point.y()
        end_x, end_y = end_point.x(), end_point.y()
        
        # 打印调试信息
        print(f"距离测量完成: 视图={view_type}, 起点=({start_x}, {start_y}), 终点=({end_x}, {end_y}), 距离={pixel_distance}")
        
        # 检查是否是编辑现有线段
        is_existing_line = False
        for line in self.measurement_lines[view_type]:
            line_start_x, line_start_y = line['start'].x(), line['start'].y()
            line_end_x, line_end_y = line['end'].x(), line['end'].y()
            
            # 检查两个线段是否相同（考虑方向）
            if ((abs(start_x - line_start_x) < 1 and abs(start_y - line_start_y) < 1 and
                 abs(end_x - line_end_x) < 1 and abs(end_y - line_end_y) < 1) or
                (abs(start_x - line_end_x) < 1 and abs(start_y - line_end_y) < 1 and
                 abs(end_x - line_start_x) < 1 and abs(end_y - line_start_y) < 1)):
                is_existing_line = True
                break
        
        # 如果不是已存在的线段，则添加到列表中
        if not is_existing_line:
            self.measurement_lines[view_type].append({
                'start': start_point,
                'end': end_point,
                'distance': pixel_distance
            })
        
        # 调整其他视图的切片位置，以便显示测量区域
        self.adjust_slices_for_measurement(view_type, start_point, end_point)
        
        # 同步所有视图中的测量线段
        self.sync_measurement_lines(view_type)
        
    def on_angle_measurement_completed(self, view_type, p1, p2, p3, angle_value):
        """
        当角度测量完成时的回调函数
        
        参数
        ----
        view_type : str
            视图类型，'axial', 'sagittal' 或 'coronal'
        p1, p2, p3 : QPointF
            构成角度的三个点，p2是角的顶点
        angle_value : float
            角度值（度）
        """
        # 检查是否已存在相同的角度测量
        p1_x, p1_y = p1.x(), p1.y()
        p2_x, p2_y = p2.x(), p2.y()
        p3_x, p3_y = p3.x(), p3.y()
        
        # 打印调试信息
        print(f"角度测量完成: 视图={view_type}, 点1=({p1_x}, {p1_y}), 点2=({p2_x}, {p2_y}), 点3=({p3_x}, {p3_y}), 角度={angle_value:.1f}°")
        
        # 清除当前视图中的所有角度测量
        self.angle_measurements[view_type] = []
        
        # 添加新的角度测量
        self.angle_measurements[view_type].append({
            'p1': p1,
            'p2': p2,  # 顶点
            'p3': p3,
            'angle': angle_value
        })
        
        # 调整其他视图的切片位置，以便显示测量区域
        self.adjust_slices_for_angle_measurement(view_type, p1, p2, p3)
        
        # 同步所有视图中的角度测量
        self.sync_angle_measurements(view_type)
        
    def update_corresponding_lines(self, source_view, start_point, end_point, original_distance=None):
        """
        在其他视图中更新对应的线段
        
        参数
        ----
        source_view : str
            源视图类型，'axial', 'sagittal' 或 'coronal'
        start_point : QPointF
            起始点
        end_point : QPointF
            结束点
        original_distance : float, optional
            原始线段的距离，如果提供则所有视图使用相同的距离值
        """
        # 将QPointF转换为图像坐标系中的整数坐标
        start_x = int(start_point.x())
        start_y = int(start_point.y())
        end_x = int(end_point.x())
        end_y = int(end_point.y())
        
        # 计算距离（如果没有提供）
        if original_distance is None:
            dx = end_x - start_x
            dy = end_y - start_y
            original_distance = math.sqrt(dx*dx + dy*dy)
        
        # 根据源视图类型计算其他视图中的对应线段
        if source_view == 'axial':
            # 在轴位面(Axial)上，坐标为(x, y)，对应3D空间中的(x, y, z)
            # 其中z是当前切片索引
            z_index = self.axial_viewer.slider.value() if hasattr(self, 'axial_viewer') else 0
            
            # 在矢状面(Sagittal)上显示线段
            # 矢状面显示(z, y)平面，x是当前切片索引
            sag_x = self.sag_viewer.slider.value() if hasattr(self, 'sag_viewer') else 0
            
            # 在矢状面上，x坐标表示z轴，y坐标表示y轴
            # 因此，我们将轴位面上的z坐标和y坐标映射到矢状面上
            sag_start = QtCore.QPoint(z_index, start_y)
            sag_end = QtCore.QPoint(z_index, end_y)
            
            # 计算矢状面上的距离
            sag_distance = math.sqrt((sag_end.x() - sag_start.x())**2 + (sag_end.y() - sag_start.y())**2)
            
            # 在冠状面(Coronal)上显示线段
            # 冠状面显示(x, z)平面，y是当前切片索引
            cor_y = self.cor_viewer.slider.value() if hasattr(self, 'cor_viewer') else 0
            
            # 在冠状面上，x坐标表示x轴，y坐标表示z轴
            # 因此，我们将轴位面上的x坐标和z坐标映射到冠状面上
            cor_start = QtCore.QPoint(start_x, z_index)
            cor_end = QtCore.QPoint(end_x, z_index)
            
            # 计算冠状面上的距离
            cor_distance = math.sqrt((cor_end.x() - cor_start.x())**2 + (cor_end.y() - cor_start.y())**2)
            
            # 更新其他视图
            if hasattr(self, 'sag_viewer') and self.sag_viewer:
                self.sag_viewer.add_corresponding_line(sag_start, sag_end, original_distance)
            if hasattr(self, 'cor_viewer') and self.cor_viewer:
                self.cor_viewer.add_corresponding_line(cor_start, cor_end, original_distance)
                
        elif source_view == 'sagittal':
            # 在矢状面(Sagittal)上，坐标为(z, y)，对应3D空间中的(x, y, z)
            # 其中x是当前切片索引
            x_index = self.sag_viewer.slider.value() if hasattr(self, 'sag_viewer') else 0
            
            # 在轴位面(Axial)上显示线段
            # 轴位面显示(x, y)平面，z是当前切片索引
            axial_z = self.axial_viewer.slider.value() if hasattr(self, 'axial_viewer') else 0
            
            # 在轴位面上，x坐标表示x轴，y坐标表示y轴
            # 因此，将矢状面上的y坐标映射到轴位面的y坐标，x坐标固定为当前矢状面的切片索引
            axial_start = QtCore.QPoint(x_index, start_y)
            axial_end = QtCore.QPoint(x_index, end_y)
            
            # 计算轴位面上的距离
            axial_distance = math.sqrt((axial_end.x() - axial_start.x())**2 + (axial_end.y() - axial_start.y())**2)
            
            # 在冠状面(Coronal)上显示线段
            # 冠状面显示(x, z)平面，y是当前切片索引
            cor_y = self.cor_viewer.slider.value() if hasattr(self, 'cor_viewer') else 0
            
            # 在冠状面上，x坐标表示x轴，y坐标表示z轴
            # 因此，将矢状面上的x坐标(z轴)映射到冠状面的y坐标(z轴)，x坐标固定为当前矢状面的切片索引
            cor_start = QtCore.QPoint(x_index, start_x)
            cor_end = QtCore.QPoint(x_index, end_x)
            
            # 计算冠状面上的距离
            cor_distance = math.sqrt((cor_end.x() - cor_start.x())**2 + (cor_end.y() - cor_start.y())**2)
            
            # 更新其他视图
            if hasattr(self, 'axial_viewer') and self.axial_viewer:
                self.axial_viewer.add_corresponding_line(axial_start, axial_end, original_distance)
            if hasattr(self, 'cor_viewer') and self.cor_viewer:
                self.cor_viewer.add_corresponding_line(cor_start, cor_end, original_distance)
                
        elif source_view == 'coronal':
            # 在冠状面(Coronal)上，坐标为(x, z)，对应3D空间中的(x, y, z)
            # 其中y是当前切片索引
            y_index = self.cor_viewer.slider.value() if hasattr(self, 'cor_viewer') else 0
            
            # 在轴位面(Axial)上显示线段
            # 轴位面显示(x, y)平面，z是当前切片索引
            axial_z = self.axial_viewer.slider.value() if hasattr(self, 'axial_viewer') else 0
            
            # 在轴位面上，x坐标表示x轴，y坐标表示y轴
            # 因此，将冠状面上的x坐标映射到轴位面的x坐标，y坐标固定为当前冠状面的切片索引
            axial_start = QtCore.QPoint(start_x, y_index)
            axial_end = QtCore.QPoint(end_x, y_index)
            
            # 计算轴位面上的距离
            axial_distance = math.sqrt((axial_end.x() - axial_start.x())**2 + (axial_end.y() - axial_start.y())**2)
            
            # 在矢状面(Sagittal)上显示线段
            # 矢状面显示(z, y)平面，x是当前切片索引
            sag_x = self.sag_viewer.slider.value() if hasattr(self, 'sag_viewer') else 0
            
            # 在矢状面上，x坐标表示z轴，y坐标表示y轴
            # 因此，将冠状面上的y坐标(z轴)映射到矢状面的x坐标(z轴)，y坐标固定为当前冠状面的切片索引
            sag_start = QtCore.QPoint(start_y, y_index)
            sag_end = QtCore.QPoint(end_y, y_index)
            
            # 计算矢状面上的距离
            sag_distance = math.sqrt((sag_end.x() - sag_start.x())**2 + (sag_end.y() - sag_start.y())**2)
            
            # 更新其他视图
            if hasattr(self, 'axial_viewer') and self.axial_viewer:
                self.axial_viewer.add_corresponding_line(axial_start, axial_end, original_distance)
            if hasattr(self, 'sag_viewer') and self.sag_viewer:
                self.sag_viewer.add_corresponding_line(sag_start, sag_end, original_distance)
        
        # 强制重绘其他视图
        if hasattr(self, 'axial_viewer') and self.axial_viewer and source_view != 'axial':
            self.axial_viewer.redraw_measurement_lines()
        if hasattr(self, 'sag_viewer') and self.sag_viewer and source_view != 'sagittal':
            self.sag_viewer.redraw_measurement_lines()
        if hasattr(self, 'cor_viewer') and self.cor_viewer and source_view != 'coronal':
            self.cor_viewer.redraw_measurement_lines()
        
    def update_corresponding_angles(self, source_view, p1, p2, p3, original_angle=None):
        """
        在其他视图中更新对应的角度
        
        参数
        ----
        source_view : str
            源视图类型，'axial', 'sagittal' 或 'coronal'
        p1, p2, p3 : QPointF
            构成角度的三个点，p2是角的顶点
        original_angle : float, optional
            原始角度值，如果提供则所有视图使用相同的角度值
        """
        # 将QPointF转换为图像坐标系中的整数坐标
        p1_x = int(p1.x())
        p1_y = int(p1.y())
        p2_x = int(p2.x())  # 顶点
        p2_y = int(p2.y())  # 顶点
        p3_x = int(p3.x())
        p3_y = int(p3.y())
        
        # 根据源视图类型计算其他视图中的对应点
        if source_view == 'axial':
            # 在轴位面(Axial)上，坐标为(x, y)，对应3D空间中的(x, y, z)
            # 其中z是当前切片索引
            z_index = self.axial_viewer.slider.value() if hasattr(self, 'axial_viewer') else 0
            
            # 在矢状面(Sagittal)上显示角度
            # 矢状面显示(z, y)平面，x是当前切片索引
            sag_x = self.sag_viewer.slider.value() if hasattr(self, 'sag_viewer') else 0
            
            # 在矢状面上，x坐标表示z轴，y坐标表示y轴
            sag_p1 = QtCore.QPoint(z_index, p1_y)
            sag_p2 = QtCore.QPoint(z_index, p2_y)  # 顶点
            sag_p3 = QtCore.QPoint(z_index, p3_y)
            
            # 在冠状面(Coronal)上显示角度
            # 冠状面显示(x, z)平面，y是当前切片索引
            cor_y = self.cor_viewer.slider.value() if hasattr(self, 'cor_viewer') else 0
            
            # 在冠状面上，x坐标表示x轴，y坐标表示z轴
            cor_p1 = QtCore.QPoint(p1_x, z_index)
            cor_p2 = QtCore.QPoint(p2_x, z_index)  # 顶点
            cor_p3 = QtCore.QPoint(p3_x, z_index)
            
            # 使用原始角度或计算角度
            if original_angle is not None:
                sag_angle = original_angle
                cor_angle = original_angle
            else:
                # 计算矢状面和冠状面上的角度
                if hasattr(self, 'sag_viewer') and self.sag_viewer:
                    sag_angle = self.sag_viewer.calculate_angle(sag_p1, sag_p2, sag_p3)
                else:
                    sag_angle = 0
                    
                if hasattr(self, 'cor_viewer') and self.cor_viewer:
                    cor_angle = self.cor_viewer.calculate_angle(cor_p1, cor_p2, cor_p3)
                else:
                    cor_angle = 0
            
            # 更新其他视图
            if hasattr(self, 'sag_viewer') and self.sag_viewer:
                self.sag_viewer.add_corresponding_angle(sag_p1, sag_p2, sag_p3, sag_angle)
            if hasattr(self, 'cor_viewer') and self.cor_viewer:
                self.cor_viewer.add_corresponding_angle(cor_p1, cor_p2, cor_p3, cor_angle)
                
        elif source_view == 'sagittal':
            # 在矢状面(Sagittal)上，坐标为(z, y)，对应3D空间中的(x, y, z)
            # 其中x是当前切片索引
            x_index = self.sag_viewer.slider.value() if hasattr(self, 'sag_viewer') else 0
            
            # 在轴位面(Axial)上显示角度
            # 轴位面显示(x, y)平面，z是当前切片索引
            axial_z = self.axial_viewer.slider.value() if hasattr(self, 'axial_viewer') else 0
            
            # 在轴位面上，x坐标表示x轴，y坐标表示y轴
            axial_p1 = QtCore.QPoint(x_index, p1_y)
            axial_p2 = QtCore.QPoint(x_index, p2_y)  # 顶点
            axial_p3 = QtCore.QPoint(x_index, p3_y)
            
            # 在冠状面(Coronal)上显示角度
            # 冠状面显示(x, z)平面，y是当前切片索引
            cor_y = self.cor_viewer.slider.value() if hasattr(self, 'cor_viewer') else 0
            
            # 在冠状面上，x坐标表示x轴，y坐标表示z轴
            cor_p1 = QtCore.QPoint(x_index, p1_x)  # p1_x在矢状面上表示z轴
            cor_p2 = QtCore.QPoint(x_index, p2_x)  # 顶点
            cor_p3 = QtCore.QPoint(x_index, p3_x)
            
            # 使用原始角度或计算角度
            if original_angle is not None:
                axial_angle = original_angle
                cor_angle = original_angle
            else:
                # 计算轴位面和冠状面上的角度
                if hasattr(self, 'axial_viewer') and self.axial_viewer:
                    axial_angle = self.axial_viewer.calculate_angle(axial_p1, axial_p2, axial_p3)
                else:
                    axial_angle = 0
                    
                if hasattr(self, 'cor_viewer') and self.cor_viewer:
                    cor_angle = self.cor_viewer.calculate_angle(cor_p1, cor_p2, cor_p3)
                else:
                    cor_angle = 0
            
            # 更新其他视图
            if hasattr(self, 'axial_viewer') and self.axial_viewer:
                self.axial_viewer.add_corresponding_angle(axial_p1, axial_p2, axial_p3, axial_angle)
            if hasattr(self, 'cor_viewer') and self.cor_viewer:
                self.cor_viewer.add_corresponding_angle(cor_p1, cor_p2, cor_p3, cor_angle)
                
        elif source_view == 'coronal':
            # 在冠状面(Coronal)上，坐标为(x, z)，对应3D空间中的(x, y, z)
            # 其中y是当前切片索引
            y_index = self.cor_viewer.slider.value() if hasattr(self, 'cor_viewer') else 0
            
            # 在轴位面(Axial)上显示角度
            # 轴位面显示(x, y)平面，z是当前切片索引
            axial_z = self.axial_viewer.slider.value() if hasattr(self, 'axial_viewer') else 0
            
            # 在轴位面上，x坐标表示x轴，y坐标表示y轴
            axial_p1 = QtCore.QPoint(p1_x, y_index)
            axial_p2 = QtCore.QPoint(p2_x, y_index)  # 顶点
            axial_p3 = QtCore.QPoint(p3_x, y_index)
            
            # 在矢状面(Sagittal)上显示角度
            # 矢状面显示(z, y)平面，x是当前切片索引
            sag_x = self.sag_viewer.slider.value() if hasattr(self, 'sag_viewer') else 0
            
            # 在矢状面上，x坐标表示z轴，y坐标表示y轴
            sag_p1 = QtCore.QPoint(p1_y, y_index)  # p1_y在冠状面上表示z轴
            sag_p2 = QtCore.QPoint(p2_y, y_index)  # 顶点
            sag_p3 = QtCore.QPoint(p3_y, y_index)
            
            # 使用原始角度或计算角度
            if original_angle is not None:
                axial_angle = original_angle
                sag_angle = original_angle
            else:
                # 计算轴位面和矢状面上的角度
                if hasattr(self, 'axial_viewer') and self.axial_viewer:
                    axial_angle = self.axial_viewer.calculate_angle(axial_p1, axial_p2, axial_p3)
                else:
                    axial_angle = 0
                    
                if hasattr(self, 'sag_viewer') and self.sag_viewer:
                    sag_angle = self.sag_viewer.calculate_angle(sag_p1, sag_p2, sag_p3)
                else:
                    sag_angle = 0
            
            # 更新其他视图
            if hasattr(self, 'axial_viewer') and self.axial_viewer:
                self.axial_viewer.add_corresponding_angle(axial_p1, axial_p2, axial_p3, axial_angle)
            if hasattr(self, 'sag_viewer') and self.sag_viewer:
                self.sag_viewer.add_corresponding_angle(sag_p1, sag_p2, sag_p3, sag_angle)
        
        # 获取当前切片索引
        if source_view == 'axial':
            z_index = self.axial_viewer.slider.value()
            
            # 在轴位面(Axial)上，坐标为(x, y)，对应3D空间中的(x, y, z)
            # 其中z是当前切片索引
            
            # 打印调试信息
            print(f"轴位面角度转换: 点1=({p1_x}, {p1_y}), 点2=({p2_x}, {p2_y}), 点3=({p3_x}, {p3_y}), z={z_index}")
            
            # 在矢状面(Sagittal)上，需要显示垂直线段
            # 矢状面显示(z, y)平面，x是当前切片索引
            sag_x = self.sag_viewer.slider.value() if hasattr(self, 'sag_viewer') else 0
            
            # 在矢状面上显示线段
            # 在矢状面上，x坐标表示z轴，y坐标表示y轴
            # 因此，我们将轴位面上的z坐标和y坐标映射到矢状面上
            sag_start = QtCore.QPoint(z_index, start_y)
            sag_end = QtCore.QPoint(z_index, end_y)
            
            # 使用原始距离或计算距离
            if original_angle is not None:
                # 使用原始角度，确保所有视图中的角度值一致
                axial_angle = original_angle
                cor_angle = original_angle
                print(f"使用原始角度: {original_angle}")
            else:
                # 计算线段在矢状面上的距离
                sag_distance = math.sqrt((sag_end.x() - sag_start.x())**2 + (sag_end.y() - sag_start.y())**2)
            
            # 在冠状面(Coronal)上，需要显示水平线段
            # 冠状面显示(x, z)平面，y是当前切片索引
            cor_y = self.cor_viewer.slider.value() if hasattr(self, 'cor_viewer') else 0
            
            # 在冠状面上显示线段
            # 在冠状面上，x坐标表示x轴，y坐标表示z轴
            # 因此，我们将轴位面上的x坐标和z坐标映射到冠状面上
            cor_start = QtCore.QPoint(start_x, z_index)
            cor_end = QtCore.QPoint(end_x, z_index)
            
            # 打印调试信息
            print(f"轴位面到冠状面转换: 冠状面起点=({cor_start.x()}, {cor_start.y()}), 终点=({cor_end.x()}, {cor_end.y()})")
            
            if original_distance is None:
                # 计算线段在冠状面上的距离
                cor_distance = math.sqrt((cor_end.x() - cor_start.x())**2 + (cor_end.y() - cor_start.y())**2)
            
            # 更新其他视图
            if hasattr(self, 'sag_viewer') and self.sag_viewer:
                self.sag_viewer.add_corresponding_line(sag_start, sag_end, sag_distance)
            if hasattr(self, 'cor_viewer') and self.cor_viewer:
                self.cor_viewer.add_corresponding_line(cor_start, cor_end, cor_distance)
                
        elif source_view == 'sagittal':
            # 在矢状面(Sagittal)上，坐标为(z, y)，对应3D空间中的(x, y, z)
            # 其中x是当前切片索引
            x_index = self.sag_viewer.slider.value()
            
            # 打印调试信息
            print(f"矢状面角度转换: 点1=({p1_x}, {p1_y}), 点2=({p2_x}, {p2_y}), 点3=({p3_x}, {p3_y}), x={x_index}")
            
            # 在轴位面(Axial)上显示线段
            # 轴位面显示(x, y)平面，z是当前切片索引
            axial_z = self.axial_viewer.slider.value() if hasattr(self, 'axial_viewer') else 0
            
            # 在矢状面上，x坐标表示z轴，y坐标表示y轴
            # 在轴位面上，x坐标表示x轴，y坐标表示y轴
            # 因此，将矢状面上的y坐标映射到轴位面的y坐标，x坐标固定为当前矢状面的切片索引
            axial_start = QtCore.QPoint(x_index, start_y)
            axial_end = QtCore.QPoint(x_index, end_y)
            
            # 打印调试信息
            print(f"矢状面角度转换: 点1=({axial_p1.x()}, {axial_p1.y()}), 点2=({axial_p2.x()}, {axial_p2.y()}), 点3=({axial_p3.x()}, {axial_p3.y()})")
            
            # 使用原始距离或计算距离
            if original_angle is not None:
                # 使用原始角度，确保所有视图中的角度值一致
                axial_angle = original_angle
                cor_angle = original_angle
                print(f"使用原始角度: {original_angle}")
            else:
                # 计算线段在轴位面上的距离
                axial_distance = math.sqrt((axial_end.x() - axial_start.x())**2 + (axial_end.y() - axial_start.y())**2)
            
            if hasattr(self, 'axial_viewer') and self.axial_viewer:
                self.axial_viewer.add_corresponding_line(axial_start, axial_end, axial_distance)
            
            # 在冠状面(Coronal)上显示线段
            # 冠状面显示(x, z)平面，y是当前切片索引
            cor_y = self.cor_viewer.slider.value() if hasattr(self, 'cor_viewer') else 0
            
            # 在矢状面上，x坐标表示z轴，y坐标表示y轴
            # 在冠状面上，x坐标表示x轴，y坐标表示z轴
            # 因此，将矢状面上的x坐标(z轴)映射到冠状面的y坐标(z轴)，x坐标固定为当前矢状面的切片索引
            cor_start = QtCore.QPoint(x_index, start_x)
            cor_end = QtCore.QPoint(x_index, end_x)
            
            # 打印调试信息
            print(f"矢状面到冠状面角度转换: 点1=({cor_p1.x()}, {cor_p1.y()}), 点2=({cor_p2.x()}, {cor_p2.y()}), 点3=({cor_p3.x()}, {cor_p3.y()})")
            
            if original_distance is None:
                # 计算线段在冠状面上的距离
                cor_distance = math.sqrt((cor_end.x() - cor_start.x())**2 + (cor_end.y() - cor_start.y())**2)
            
            if hasattr(self, 'cor_viewer') and self.cor_viewer:
                self.cor_viewer.add_corresponding_line(cor_start, cor_end, cor_distance)
                
        elif source_view == 'coronal':
            # 在冠状面(Coronal)上，坐标为(x, z)，对应3D空间中的(x, y, z)
            # 其中y是当前切片索引
            y_index = self.cor_viewer.slider.value()
            
            # 打印调试信息
            print(f"冠状面角度转换: 点1=({p1_x}, {p1_y}), 点2=({p2_x}, {p2_y}), 点3=({p3_x}, {p3_y}), y={y_index}")
            
            # 在轴位面(Axial)上显示线段
            # 轴位面显示(x, y)平面，z是当前切片索引
            axial_z = self.axial_viewer.slider.value() if hasattr(self, 'axial_viewer') else 0
            
            # 在冠状面上，x坐标表示x轴，y坐标表示z轴
            # 在轴位面上，x坐标表示x轴，y坐标表示y轴
            # 因此，将冠状面上的x坐标映射到轴位面的x坐标，y坐标固定为当前冠状面的切片索引
            axial_start = QtCore.QPoint(start_x, y_index)
            axial_end = QtCore.QPoint(end_x, y_index)
            
            # 打印调试信息
            print(f"冠状面到轴位面角度转换: 点1=({axial_p1.x()}, {axial_p1.y()}), 点2=({axial_p2.x()}, {axial_p2.y()}), 点3=({axial_p3.x()}, {axial_p3.y()})")
            
            # 使用原始距离或计算距离
            if original_angle is not None:
                # 使用原始角度，确保所有视图中的角度值一致
                axial_angle = original_angle
                sag_angle = original_angle
                print(f"使用原始角度: {original_angle}")
            else:
                # 计算线段在轴位面上的距离
                axial_distance = math.sqrt((axial_end.x() - axial_start.x())**2 + (axial_end.y() - axial_start.y())**2)
            
            if hasattr(self, 'axial_viewer') and self.axial_viewer:
                self.axial_viewer.add_corresponding_line(axial_start, axial_end, axial_distance)
            
            # 在矢状面(Sagittal)上显示线段
            # 矢状面显示(z, y)平面，x是当前切片索引
            sag_x = self.sag_viewer.slider.value() if hasattr(self, 'sag_viewer') else 0
            
            # 在冠状面上，x坐标表示x轴，y坐标表示z轴
            # 在矢状面上，x坐标表示z轴，y坐标表示y轴
            # 因此，将冠状面上的y坐标(z轴)映射到矢状面的x坐标(z轴)，y坐标固定为当前冠状面的切片索引
            sag_start = QtCore.QPoint(start_y, y_index)
            sag_end = QtCore.QPoint(end_y, y_index)
            
            # 打印调试信息
            print(f"冠状面到矢状面角度转换: 点1=({sag_p1.x()}, {sag_p1.y()}), 点2=({sag_p2.x()}, {sag_p2.y()}), 点3=({sag_p3.x()}, {sag_p3.y()})")
            
            if original_distance is None:
                # 计算线段在矢状面上的距离
                sag_distance = math.sqrt((sag_end.x() - sag_start.x())**2 + (sag_end.y() - sag_start.y())**2)
            
            if hasattr(self, 'sag_viewer') and self.sag_viewer:
                self.sag_viewer.add_corresponding_line(sag_start, sag_end, sag_distance)
