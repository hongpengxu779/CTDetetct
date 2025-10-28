"""
ROI (Region of Interest) 操作模块
提供交互式ROI选取、三视图联动、3D体积ROI可视化等功能
"""

import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
import json
import os
from datetime import datetime


class ROIOperations:
    """ROI操作类，作为Mixin使用"""
    
    def setup_roi(self):
        """初始化ROI相关的变量"""
        # 当前ROI模式
        self.roi_mode = None
        # 存储所有视图中的ROI
        self.roi_rects = {
            'axial': [],
            'sagittal': [],
            'coronal': []
        }
        # 当前活动的ROI
        self.active_roi = {
            'axial': None,
            'sagittal': None,
            'coronal': None
        }
        # 当前正在绘制的ROI
        self.current_roi = None
        # 当前正在拖动的ROI端点
        self.dragging_roi = None
        # 3D ROI立方体坐标 [x_min, x_max, y_min, y_max, z_min, z_max]
        self.roi_3d_bounds = None
        # ROI变更信号
        self.roi_changed_callbacks = []
        # 当前选取ROI的视图类型（用于限制只能在一个视图中选取）
        self.roi_selection_view = None
    
    def roi_selection_start(self):
        """启动ROI选取模式"""
        if self.roi_mode == 'selection':
            self.exit_roi_mode()
            return
        
        self.roi_mode = 'selection'
        # 清空之前的ROI，只能有一个ROI
        self.roi_rects = {
            'axial': [],
            'sagittal': [],
            'coronal': []
        }
        self.roi_selection_view = None  # 重置选取视图
        
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage("ROI选取模式：在任意一个视图中点击并拖动鼠标来选择ROI")
        
        # 为所有切片视图启用ROI选取模式
        if hasattr(self, 'axial_viewer') and self.axial_viewer:
            self.axial_viewer.enable_roi_mode('selection', self)
        if hasattr(self, 'sag_viewer') and self.sag_viewer:
            self.sag_viewer.enable_roi_mode('selection', self)
        if hasattr(self, 'cor_viewer') and self.cor_viewer:
            self.cor_viewer.enable_roi_mode('selection', self)
    
    def roi_selection_clear(self):
        """清除所有ROI"""
        self.roi_rects = {
            'axial': [],
            'sagittal': [],
            'coronal': []
        }
        self.roi_3d_bounds = None
        self.current_roi = None
        self.active_roi = {
            'axial': None,
            'sagittal': None,
            'coronal': None
        }
        
        # 清除所有视图中的ROI
        if hasattr(self, 'axial_viewer') and self.axial_viewer:
            self.axial_viewer.roi_rects = []
            self.axial_viewer.current_roi = None
            self.axial_viewer.redraw_roi()
        if hasattr(self, 'sag_viewer') and self.sag_viewer:
            self.sag_viewer.roi_rects = []
            self.sag_viewer.current_roi = None
            self.sag_viewer.redraw_roi()
        if hasattr(self, 'cor_viewer') and self.cor_viewer:
            self.cor_viewer.roi_rects = []
            self.cor_viewer.current_roi = None
            self.cor_viewer.redraw_roi()
        
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage("ROI已清除")
        
        self._fire_roi_changed()
    
    def exit_roi_mode(self):
        """退出ROI选取模式"""
        self.roi_mode = None
        
        # 禁用所有视图的ROI模式
        if hasattr(self, 'axial_viewer') and self.axial_viewer:
            self.axial_viewer.disable_roi_mode()
        if hasattr(self, 'sag_viewer') and self.sag_viewer:
            self.sag_viewer.disable_roi_mode()
        if hasattr(self, 'cor_viewer') and self.cor_viewer:
            self.cor_viewer.disable_roi_mode()
        
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage("已退出ROI选取模式")
    
    def register_roi_changed_callback(self, callback):
        """注册ROI变更回调函数"""
        if callback not in self.roi_changed_callbacks:
            self.roi_changed_callbacks.append(callback)
    
    def _fire_roi_changed(self):
        """触发ROI变更回调"""
        for callback in self.roi_changed_callbacks:
            try:
                callback(self.roi_3d_bounds)
            except Exception as e:
                print(f"ROI变更回调错误: {e}")
    
    def add_roi_to_view(self, view_type, roi_rect, slice_index):
        """向指定视图添加ROI"""
        if view_type not in self.roi_rects:
            return
        
        roi_data = {
            'rect': roi_rect,  # (x1, y1, x2, y2)
            'slice_index': slice_index,
            'id': len(self.roi_rects[view_type])
        }
        self.roi_rects[view_type].append(roi_data)
        
        # 如果还没有3D ROI，则创建
        if self.roi_3d_bounds is None:
            self.roi_3d_bounds = self._calculate_3d_bounds()
        else:
            self.roi_3d_bounds = self._calculate_3d_bounds()
        
        self._fire_roi_changed()
        
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage(f"ROI已添加到{view_type}视图")
    
    def _calculate_3d_bounds(self):
        """根据选取的视图ROI和深度滑动条计算3D立方体边界
        
        数据格式：array[z, y, x]
        
        支持三种情况：
        - 在Axial选取（x-y平面）：x,y来自ROI矩形，z来自深度滑动条
        - 在Sagittal选取（z-y平面）：z,y来自ROI矩形，x来自深度滑动条
        - 在Coronal选取（x-z平面）：x,z来自ROI矩形，y来自深度滑动条
        """
        # 确定在哪个视图中选取了ROI
        roi_view = None
        for view_type in ['axial', 'sagittal', 'coronal']:
            if self.roi_rects[view_type]:
                roi_view = view_type
                break
        
        if roi_view is None:
            print("警告: 没有在任何视图中选取ROI")
            return None
        
        # 获取选取的ROI矩形
        roi = self.roi_rects[roi_view][-1]
        rect = roi['rect']
        
        print(f"从{roi_view}视图中选取的ROI: [{rect.left()}, {rect.right()}, {rect.top()}, {rect.bottom()}]")
        
        # 获取深度范围（无论在哪个视图，深度值都是一样的）
        if hasattr(self, 'roi_depth_min_slider'):
            depth_min = self.roi_depth_min_slider.value()
            depth_max = self.roi_depth_max_slider.value()
        else:
            depth_min, depth_max = 0, 50
        
        # 根据选取的视图来解析坐标
        if roi_view == 'axial':
            # Axial显示array[z, :, :] 返回形状(333, 310) = (Y, X)
            # 所以屏幕坐标的映射应该是：
            # rect.left/right 对应的是X轴（像素的水平方向 = 数组的列）→ 数据的X轴
            # rect.top/bottom 对应的是Y轴（像素的竖直方向 = 数组的行）→ 数据的Y轴
            
            # 但是等等，让我们重新思考：
            # numpy array[z, :, :] 返回的是 (333, 310)
            # - 第0维（333） = Y方向（行）
            # - 第1维（310） = X方向（列）
            # 当显示为pixmap时：
            # - 屏幕X方向（左右）= pixmap宽度 = 310 = 数据的第1维(X) ✓
            # - 屏幕Y方向（上下）= pixmap高度 = 333 = 数据的第0维(Y) ✓
            
            # 所以rect的映射应该是：
            # rect.left/right（屏幕X）→ 数据X轴
            # rect.top/bottom（屏幕Y）→ 数据Y轴
            
            x_min = int(rect.left())
            x_max = int(rect.right())
            y_min = int(rect.top())
            y_max = int(rect.bottom())
            z_min = depth_min
            z_max = depth_max
            
            print(f"Axial ROI坐标映射:")
            print(f"  rect: left={rect.left()}, right={rect.right()}, top={rect.top()}, bottom={rect.bottom()}")
            print(f"  x: [{x_min}, {x_max}]")
            print(f"  y: [{y_min}, {y_max}]")
            print(f"  z: [{z_min}, {z_max}]")
            
            # 检查是否可能是缩放问题
            if hasattr(self, 'axial_viewer') and self.axial_viewer:
                arr = self.axial_viewer.get_slice(self.axial_viewer.slider.value())
                print(f"  Axial切片实际大小: {arr.shape}")
                if x_max > arr.shape[1] or y_max > arr.shape[0]:
                    print(f"  ⚠️ 警告: ROI坐标超出切片范围！需要进行坐标变换")
                
                # *** 关键诊断：检查是否存在缩放问题 ***
                # 获取pixmap的实际大小和显示大小
                pixmap = self.axial_viewer.pixmap_item.pixmap()
                if not pixmap.isNull():
                    pixmap_width = pixmap.width()
                    pixmap_height = pixmap.height()
                    image_rect = self.axial_viewer.pixmap_item.boundingRect()
                    displayed_width = image_rect.width()
                    displayed_height = image_rect.height()
                    
                    print(f"  缩放诊断:")
                    print(f"    Pixmap实际大小: {pixmap_width}×{pixmap_height}")
                    print(f"    显示大小: {displayed_width}×{displayed_height}")
                    
                    scale_x = displayed_width / pixmap_width if pixmap_width > 0 else 1.0
                    scale_y = displayed_height / pixmap_height if pixmap_height > 0 else 1.0
                    
                    print(f"    缩放因子: X={scale_x:.3f}, Y={scale_y:.3f}")
                    
                    # 关键对应关系诊断
                    print(f"  坐标系统诊断:")
                    print(f"    数据切片形状: (高={arr.shape[0]}, 宽={arr.shape[1]})")
                    print(f"    Pixmap尺寸: 宽={pixmap_width}, 高={pixmap_height}")
                    
                    # 判断对应关系
                    if arr.shape[1] == pixmap_width and arr.shape[0] == pixmap_height:
                        print(f"    ✓ 数据和Pixmap对应正确:")
                        print(f"      - 数据第1维(X,宽{arr.shape[1]}) = Pixmap宽({pixmap_width})")
                        print(f"      - 数据第0维(Y,高{arr.shape[0]}) = Pixmap高({pixmap_height})")
                        print(f"      - rect.left/right映射到X轴 ✓")
                        print(f"      - rect.top/bottom映射到Y轴 ✓")
                    elif arr.shape[0] == pixmap_width and arr.shape[1] == pixmap_height:
                        print(f"    ⚠️ 数据被转置了！")
                        print(f"      - 数据第0维(Y,高{arr.shape[0]}) = Pixmap宽({pixmap_width})")
                        print(f"      - 数据第1维(X,宽{arr.shape[1]}) = Pixmap高({pixmap_height})")
                        print(f"      - 需要交换X和Y坐标！")
                        # 交换坐标
                        x_min, y_min = y_min, x_min
                        x_max, y_max = y_max, x_max
                        print(f"      - 交换后: x=[{x_min}, {x_max}], y=[{y_min}, {y_max}]")
                    else:
                        print(f"    ⚠️ 坐标对应关系不明确！")
                    
                    # 如果缩放因子不是1.0，需要调整坐标
                    if abs(scale_x - 1.0) > 0.01 or abs(scale_y - 1.0) > 0.01:
                        print(f"  ⚠️ 检测到图像缩放!")
                        print(f"    原始ROI坐标: x=[{x_min}, {x_max}], y=[{y_min}, {y_max}]")
                        
                        # 调整坐标
                        x_min = int(x_min / scale_x)
                        x_max = int(x_max / scale_x)
                        y_min = int(y_min / scale_y)
                        y_max = int(y_max / scale_y)
                        
                        print(f"    调整后ROI坐标: x=[{x_min}, {x_max}], y=[{y_min}, {y_max}]")
                    else:
                        print(f"  ✓ 图像未缩放，坐标无需调整")
        
        elif roi_view == 'sagittal':
            # Sagittal显示array[:, :, x] 的所有 z-y切片
            # rect.left/right -> z, rect.top/bottom -> y
            z_min = int(rect.left())
            z_max = int(rect.right())
            y_min = int(rect.top())
            y_max = int(rect.bottom())
            x_min = depth_min
            x_max = depth_max
            
            print(f"Sagittal ROI坐标映射:")
            print(f"  z: [{z_min}, {z_max}]")
            print(f"  y: [{y_min}, {y_max}]")
            print(f"  x: [{x_min}, {x_max}]")
        
        elif roi_view == 'coronal':
            # Coronal显示array[:, y, :] 的所有 x-z切片
            # rect.left/right -> x, rect.top/bottom -> z
            x_min = int(rect.left())
            x_max = int(rect.right())
            z_min = int(rect.top())
            z_max = int(rect.bottom())
            y_min = depth_min
            y_max = depth_max
            
            print(f"Coronal ROI坐标映射:")
            print(f"  x: [{x_min}, {x_max}]")
            print(f"  z: [{z_min}, {z_max}]")
            print(f"  y: [{y_min}, {y_max}]")
        
        # 验证边界的有效性
        if x_min >= x_max or y_min >= y_max or z_min >= z_max:
            print("警告: ROI边界无效")
            print(f"  x: [{x_min}, {x_max}]")
            print(f"  y: [{y_min}, {y_max}]")
            print(f"  z: [{z_min}, {z_max}]")
            return None
        
        bounds = {
            'x_min': x_min,
            'x_max': x_max,
            'y_min': y_min,
            'y_max': y_max,
            'z_min': z_min,
            'z_max': z_max
        }
        
        print(f"3D ROI边界计算成功:")
        print(f"  x: [{bounds['x_min']}, {bounds['x_max']}] (范围: {bounds['x_max'] - bounds['x_min']})")
        print(f"  y: [{bounds['y_min']}, {bounds['y_max']}] (范围: {bounds['y_max'] - bounds['y_min']})")
        print(f"  z: [{bounds['z_min']}, {bounds['z_max']}] (范围: {bounds['z_max'] - bounds['z_min']})")
        
        return bounds
    
    def update_depth_slider_for_view(self, view_type):
        """根据选取的视图更新深度滑动条的范围和标签"""
        if view_type == 'axial':
            # Axial选取后，深度是Z方向
            depth_label = "Z 方向（深度）"
            max_depth = self.depth_z - 1 if hasattr(self, 'depth_z') else 100
            current_slice = self.axial_viewer.slider.value() if hasattr(self, 'axial_viewer') else 0
            viewer = self.axial_viewer
        elif view_type == 'sagittal':
            # Sagittal选取后，深度是X方向
            depth_label = "X 方向（深度）"
            max_depth = self.depth_x - 1 if hasattr(self, 'depth_x') else 100
            current_slice = self.sag_viewer.slider.value() if hasattr(self, 'sag_viewer') else 0
            viewer = self.sag_viewer
        elif view_type == 'coronal':
            # Coronal选取后，深度是Y方向
            depth_label = "Y 方向（深度）"
            max_depth = self.depth_y - 1 if hasattr(self, 'depth_y') else 100
            current_slice = self.cor_viewer.slider.value() if hasattr(self, 'cor_viewer') else 0
            viewer = self.cor_viewer
        else:
            return
        
        # 更新UI标签和滑动条范围
        if hasattr(self, 'roi_depth_label'):
            self.roi_depth_label.setText(f"（在 {view_type.upper()} 选取 - {depth_label}）")
        
        if hasattr(self, 'roi_depth_min_slider'):
            self.roi_depth_min_slider.setMaximum(max_depth)
            self.roi_depth_max_slider.setMaximum(max_depth)
            
            # 以当前切片为中心，设置默认范围（前后各25层）
            range_half = min(25, max_depth // 2)
            min_val = max(0, current_slice - range_half)
            max_val = min(max_depth, current_slice + range_half)
            
            self.roi_depth_min_slider.setValue(min_val)
            self.roi_depth_max_slider.setValue(max_val)
            
            print(f"深度滑动条已更新（{view_type}）: 0 - {max_depth}")
            print(f"  当前切片: {current_slice}, 默认范围: [{min_val}, {max_val}]")
        
        # 连接切片滑动条到深度范围的更新（单向联动）
        if viewer and hasattr(viewer, 'slider'):
            # 断开旧的连接（如果存在）
            try:
                viewer.slider.valueChanged.disconnect(self.sync_view_to_depth)
            except:
                pass
            # 连接新的
            viewer.slider.valueChanged.connect(self.sync_view_to_depth)
    
    def sync_view_to_depth(self, slice_value):
        """当视图切片滑动条改变时，更新ROI深度范围（单向联动）"""
        if not hasattr(self, 'roi_selection_view') or self.roi_selection_view is None:
            return
        
        if not hasattr(self, 'roi_depth_min_slider') or not hasattr(self, 'roi_depth_max_slider'):
            return
        
        # 以新的切片位置为中心，更新Min和Max
        range_half = min(25, self.roi_depth_max_slider.maximum() // 2)
        min_val = max(0, slice_value - range_half)
        max_val = min(self.roi_depth_max_slider.maximum(), slice_value + range_half)
        
        # 直接设置值，让valueChanged信号自动更新Label显示
        self.roi_depth_min_slider.setValue(min_val)
        self.roi_depth_max_slider.setValue(max_val)
    
    def preview_roi_3d(self):
        """预览3D ROI立方体"""
        if self.roi_3d_bounds is None:
            QtWidgets.QMessageBox.warning(self, "警告", "请先在三视图中选择ROI")
            return
        
        # 检查原始数据是否可用
        if not hasattr(self, 'raw_array') or self.raw_array is None:
            QtWidgets.QMessageBox.warning(self, "错误", "原始数据未加载，无法进行3D预览")
            print("错误: self.raw_array 为 None")
            return
        
        print(f"开始3D预览，数据形状: {self.raw_array.shape}")
        
        # 导入3D预览对话框
        from .roi_3d_preview import ROI3DPreviewDialog
        
        dialog = ROI3DPreviewDialog(self, self.raw_array, self.roi_3d_bounds)
        dialog.exec_()
    
    def get_roi_volume(self):
        """提取ROI对应的体积数据"""
        if self.roi_3d_bounds is None:
            return None
        
        if self.raw_array is None:
            return None
        
        bounds = self.roi_3d_bounds
        roi_volume = self.raw_array[
            bounds['z_min']:bounds['z_max'],
            bounds['y_min']:bounds['y_max'],
            bounds['x_min']:bounds['x_max']
        ]
        
        return roi_volume
    
    def export_roi_info(self, filepath):
        """导出ROI信息到JSON文件"""
        if self.roi_3d_bounds is None:
            QtWidgets.QMessageBox.warning(self, "警告", "没有ROI信息可导出")
            return
        
        roi_info = {
            'timestamp': datetime.now().isoformat(),
            'roi_3d_bounds': self.roi_3d_bounds,
            'roi_rects': {},
            'image_shape': self.raw_array.shape if self.raw_array is not None else None
        }
        
        # 转换roi_rects中的QPointF为普通格式
        for view_type, rects in self.roi_rects.items():
            roi_info['roi_rects'][view_type] = []
            for roi in rects:
                roi_dict = {
                    'slice_index': roi['slice_index'],
                    'rect': [
                        (roi['rect'].x(), roi['rect'].y(), 
                         roi['rect'].x() + roi['rect'].width(), 
                         roi['rect'].y() + roi['rect'].height())
                    ]
                }
                roi_info['roi_rects'][view_type].append(roi_dict)
        
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(roi_info, f, indent=2)
            QtWidgets.QMessageBox.information(self, "成功", f"ROI信息已保存到：{filepath}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"保存ROI信息失败：{str(e)}")
    
    def import_roi_info(self, filepath):
        """从JSON文件导入ROI信息"""
        try:
            with open(filepath, 'r') as f:
                roi_info = json.load(f)
            
            self.roi_3d_bounds = roi_info.get('roi_3d_bounds')
            
            # 重新构建roi_rects
            self.roi_rects = {
                'axial': [],
                'sagittal': [],
                'coronal': []
            }
            
            for view_type, rects in roi_info.get('roi_rects', {}).items():
                for roi_dict in rects:
                    rect = roi_dict['rect'][0]
                    roi_data = {
                        'rect': QtCore.QRectF(rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1]),
                        'slice_index': roi_dict['slice_index'],
                        'id': len(self.roi_rects[view_type])
                    }
                    self.roi_rects[view_type].append(roi_data)
            
            # 更新所有视图
            self._update_roi_display()
            self._fire_roi_changed()
            
            QtWidgets.QMessageBox.information(self, "成功", "ROI信息已导入")
        
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"导入ROI信息失败：{str(e)}")
    
    def _update_roi_display(self):
        """更新所有视图的ROI显示"""
        if hasattr(self, 'axial_viewer') and self.axial_viewer:
            self.axial_viewer.roi_rects = self.roi_rects['axial']
            self.axial_viewer.redraw_roi()
        if hasattr(self, 'sag_viewer') and self.sag_viewer:
            self.sag_viewer.roi_rects = self.roi_rects['sagittal']
            self.sag_viewer.redraw_roi()
        if hasattr(self, 'cor_viewer') and self.cor_viewer:
            self.cor_viewer.roi_rects = self.roi_rects['coronal']
            self.cor_viewer.redraw_roi()
