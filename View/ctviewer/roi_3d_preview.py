"""
ROI 3D 预览对话框
使用PyVista显示3D ROI立方体
"""

import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
import math

import pyvista as pv
from pyvistaqt import QtInteractor
PYVISTA_AVAILABLE = True

class ROI3DPreviewDialog(QtWidgets.QDialog):
    """3D ROI预览对话框"""
    
    def __init__(self, parent, volume_data, roi_bounds):
        """
        参数
        ----
        parent : QWidget
            父窗口
        volume_data : np.ndarray
            3D体积数据 (z, y, x)
        roi_bounds : dict
            ROI边界 {'x_min', 'x_max', 'y_min', 'y_max', 'z_min', 'z_max'}
        """
        if not PYVISTA_AVAILABLE:
            QtWidgets.QMessageBox.critical(
                parent, 
                "错误", 
                "PyVista库未安装。\n\n"
                "请安装PyVista：\n"
                "pip install pyvista pyvistaqt\n\n"
                "3D ROI预览功能暂不可用。"
            )
            return
        
        super().__init__(parent)
        self.setWindowTitle("3D ROI预览")
        self.setGeometry(100, 100, 1000, 800)
        self.volume_data = volume_data
        self.roi_bounds = roi_bounds
        
        # 验证数据
        if self.volume_data is None:
            print("错误: volume_data 为 None")
            QtWidgets.QMessageBox.critical(
                parent,
                "错误",
                "无法进行3D预览：数据为空。\n\n"
                "请确保已加载医学影像文件。"
            )
            return
        
        if self.roi_bounds is None:
            print("错误: roi_bounds 为 None")
            QtWidgets.QMessageBox.critical(
                parent,
                "错误",
                "无法进行3D预览：ROI边界为空。\n\n"
                "请先选择ROI。"
            )
            return
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # 创建PyVista渲染窗口
        print("使用PyVista进行3D渲染")
        self.plotter = QtInteractor(self)
        layout.addWidget(self.plotter.interactor)
        
        # 底部按钮栏
        button_layout = QtWidgets.QHBoxLayout()
        
        export_btn = QtWidgets.QPushButton("导出ROI体积")
        export_btn.clicked.connect(self.export_roi_volume)
        button_layout.addWidget(export_btn)
        
        close_btn = QtWidgets.QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 初始化PyVista渲染
        self.setup_pyvista()
    
    def setup_pyvista(self):
        """使用PyVista设置渲染环境"""
        try:
            # 获取ROI数据
            roi_volume = self._get_sample_volume()
            
            if roi_volume is None:
                print("警告: ROI数据为空")
                return
            
            print(f"\nPyVista 3D渲染:")
            print(f"  数据形状: {roi_volume.shape}")
            print(f"  数据范围: [{roi_volume.min()}, {roi_volume.max()}]")
            
            # 创建PyVista的ImageData
            # PyVista期望shape为 (nx, ny, nz)，对应 (X, Y, Z)
            grid = pv.ImageData()
            
            # ROI数据是 (Z, Y, X) 格式，需要转置为 (X, Y, Z)
            roi_transposed = roi_volume.transpose(2, 1, 0)
            print(f"  转置后形状: {roi_transposed.shape}")
            
            # 设置维度 (X, Y, Z)
            grid.dimensions = roi_transposed.shape
            
            # 设置数据 - PyVista自动处理Flatten
            grid.point_data['values'] = roi_transposed.flatten(order='F')
            
            # 添加到场景
            self.plotter.add_volume(
                grid,
                cmap='gray',  # 灰度colormap
                opacity='linear',  # 线性透明度
                shade=True,  # 启用阴影
                show_scalar_bar=True  # 显示colorbar
            )
            
            # 添加ROI边界框
            bounds = self.roi_bounds
            x_size = bounds['x_max'] - bounds['x_min']
            y_size = bounds['y_max'] - bounds['y_min']
            z_size = bounds['z_max'] - bounds['z_min']
            
            # 创建边界框
            box = pv.Box(bounds=(0, x_size, 0, y_size, 0, z_size))
            self.plotter.add_mesh(box, style='wireframe', color='cyan', line_width=2)
            
            # 设置相机和背景
            self.plotter.set_background('black')
            self.plotter.reset_camera()
            
            print("PyVista渲染成功！")
            
        except Exception as e:
            print(f"PyVista渲染失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_sample_volume(self):
        """
        获取采样后的体积数据
        """
        try:
            # 获取ROI边界
            bounds = self.roi_bounds
            z_min = int(bounds['z_min'])
            z_max = int(bounds['z_max'])
            y_min = int(bounds['y_min'])
            y_max = int(bounds['y_max'])
            x_min = int(bounds['x_min'])
            x_max = int(bounds['x_max'])
            
            print(f"提取ROI数据（原始边界）: z=[{z_min}:{z_max}], y=[{y_min}:{y_max}], x=[{x_min}:{x_max}]")
            print(f"体积数据形状: {self.volume_data.shape}")
            print(f"体积数据范围: min={self.volume_data.min()}, max={self.volume_data.max()}")
            
            # *** 诊断：检查坐标是否在数据范围内 ***
            print(f"\n坐标有效性检查:")
            print(f"  Z范围 [{z_min}:{z_max}] vs 数据大小 {self.volume_data.shape[0]}")
            print(f"  Y范围 [{y_min}:{y_max}] vs 数据大小 {self.volume_data.shape[1]}")
            print(f"  X范围 [{x_min}:{x_max}] vs 数据大小 {self.volume_data.shape[2]}")
            
            # 确保边界有效并在数据范围内
            z_min = max(0, int(z_min))
            z_max = min(int(z_max) + 1, self.volume_data.shape[0])
            y_min = max(0, int(y_min))
            y_max = min(int(y_max) + 1, self.volume_data.shape[1])
            x_min = max(0, int(x_min))
            x_max = min(int(x_max) + 1, self.volume_data.shape[2])
            
            print(f"提取ROI数据（修正边界）: z=[{z_min}:{z_max}], y=[{y_min}:{y_max}], x=[{x_min}:{x_max}]")
            
            # 数据维度检查
            print(f"数据维度检查:")
            print(f"  Z范围 [{z_min}:{z_max}] vs 数据大小 {self.volume_data.shape[0]}")
            print(f"  Y范围 [{y_min}:{y_max}] vs 数据大小 {self.volume_data.shape[1]}")
            print(f"  X范围 [{x_min}:{x_max}] vs 数据大小 {self.volume_data.shape[2]}")
            
            if z_max > self.volume_data.shape[0]:
                print(f"⚠️  警告: Z超出范围！ {z_max} > {self.volume_data.shape[0]}")
            if y_max > self.volume_data.shape[1]:
                print(f"⚠️  警告: Y超出范围！ {y_max} > {self.volume_data.shape[1]}")
            if x_max > self.volume_data.shape[2]:
                print(f"⚠️  警告: X超出范围！ {x_max} > {self.volume_data.shape[2]}")
            
            # 提取ROI区域
            roi_volume = self.volume_data[z_min:z_max, y_min:y_max, x_min:x_max]
            
            print(f"\n提取的ROI形状: {roi_volume.shape}")
            print(f"提取前全局数据信息: min={self.volume_data.min()}, max={self.volume_data.max()}, mean={self.volume_data.mean():.2f}")
            print(f"提取后ROI数据信息: min={roi_volume.min()}, max={roi_volume.max()}, mean={roi_volume.mean():.2f}")
            
            # *** 关键验证：检查ROI是否包含有意义的数据 ***
            roi_nonzero = np.count_nonzero(roi_volume)
            roi_percent = 100.0 * roi_nonzero / roi_volume.size
            
            print(f"\nROI数据统计:")
            print(f"  总像素数: {roi_volume.size}")
            print(f"  非零像素数: {roi_nonzero}")
            print(f"  非零比例: {roi_percent:.2f}%")
            
            # 与全局数据对比
            global_nonzero = np.count_nonzero(self.volume_data)
            global_percent = 100.0 * global_nonzero / self.volume_data.size
            print(f"  全局数据非零比例: {global_percent:.2f}%")
            
            print(f"\n坐标映射诊断:")
            print(f"  Axial视图显示: array[z_slice, y_min:y_max, x_min:x_max]")
            print(f"  选取的ROI是Axial视图中的矩形，应该对应:")
            print(f"    - 屏幕X轴(左右) → 数据X轴 ✓")
            print(f"    - 屏幕Y轴(上下) → 数据Y轴 ✓")
            
            # *** 关键诊断：验证坐标映射是否正确 ***
            # 检查Axial切片中心点的值
            try:
                z_center = z_min
                y_center = (y_min + y_max) // 2
                x_center = (x_min + x_max) // 2
                
                sample_value = self.volume_data[z_center, y_center, x_center]
                global_mean = self.volume_data.mean()
                roi_mean = roi_volume.mean()
                
                print(f"\n  坐标有效性验证:")
                print(f"    Axial第一层切片中心点 [{z_center}, {y_center}, {x_center}] = {sample_value}")
                print(f"    ROI均值: {roi_mean:.1f}")
                print(f"    全局均值: {global_mean:.1f}")
                
                if sample_value < global_mean * 0.3:
                    print(f"    ⚠️ 警告: 中心点值({sample_value})远低于全局均值({global_mean:.1f})")
                    print(f"    可能原因: Y和X坐标互换了！")
                elif sample_value > global_mean:
                    print(f"    ✓ 中心点值({sample_value})高于全局均值，坐标似乎正确")
                else:
                    print(f"    ℹ️  中心点值({sample_value})接近全局均值")
            except Exception as e:
                print(f"  采样验证失败: {e}")
            
            # 如果非零比例异常低，提示可能的坐标问题
            if roi_percent < 1.0:
                print(f"\n⚠️  警告: ROI非零比例极低({roi_percent:.2f}%)")
                print(f"  可能原因:")
                print(f"  1. ROI选在了背景/无数据区域")
                print(f"  2. 坐标轴映射有问题（X和Y反了）")
                print(f"  3. 选取的ROI超出了有数据的范围")
            elif roi_percent > 99.0:
                print(f"\n⚠️  信息: ROI非零比例很高({roi_percent:.2f}%)")
                print(f"  这表示选取的区域数据很密集，是正常的医学影像特征")
            
            if roi_volume.max() == roi_volume.min():
                print(f"⚠️  警告: ROI数据所有值都相同 ({roi_volume.max()})")
                print(f"   这可能表示坐标映射错误或ROI选在了无数据区域")
            
            if roi_volume.size == 0:
                print("错误: 提取的ROI为空，边界可能超出数据范围")
                return None
            
            # 检查数据是否全为0
            if roi_volume.max() == 0:
                print("警告: 提取的ROI数据全为0，无法进行体积渲染")
                return None
            
            # ========== 采样已禁用，用于调试 ==========
            # max_size = 128  # 最大尺寸以保留细节同时保持性能
            # if (roi_volume.shape[0] > max_size or roi_volume.shape[1] > max_size or 
            #     roi_volume.shape[2] > max_size):
            #     # 计算采样步长
            #     step_z = max(1, roi_volume.shape[0] // max_size)
            #     step_y = max(1, roi_volume.shape[1] // max_size)
            #     step_x = max(1, roi_volume.shape[2] // max_size)
                
            #     print(f"数据过大，进行采样。采样步长: z={step_z}, y={step_y}, x={step_x}")
            #     roi_volume = roi_volume[::step_z, ::step_y, ::step_x]
            #     print(f"采样后形状: {roi_volume.shape}")
            print(f"注意: 采样已禁用（调试模式），使用原始数据：{roi_volume.shape}")
            
            # ========== 禁用标准化，保持原始数据范围 ==========
            # 原来的代码会把所有值压缩到0-255，这会损失数据细节
            # 现在直接使用原始数据范围
            
            print(f"原始数据范围: [{roi_volume.min():.1f}, {roi_volume.max():.1f}]")
            print(f"注意: 不进行标准化，保留原始数据范围用于VTK渲染")
            
            # 确保数据类型为uint16（支持0-65535范围）
            return roi_volume.astype(np.uint16)
        
        except Exception as e:
            print(f"获取采样体积失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def export_roi_volume(self):
        """导出ROI体积数据"""
        try:
            # 打开文件对话框
            filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "保存ROI体积", "", "医学影像文件 (*.nii.gz);;Raw文件 (*.raw);;Numpy文件 (*.npy)"
            )
            
            if not filepath:
                return
            
            # 提取ROI体积
            bounds = self.roi_bounds
            roi_volume = self.volume_data[
                bounds['z_min']:bounds['z_max'],
                bounds['y_min']:bounds['y_max'],
                bounds['x_min']:bounds['x_max']
            ]
            
            # 根据文件扩展名保存
            if filepath.endswith('.npy'):
                np.save(filepath, roi_volume)
            elif filepath.endswith('.raw'):
                roi_volume.tofile(filepath)
            elif filepath.endswith('.nii.gz'):
                try:
                    import nibabel as nib
                    img = nib.Nifti1Image(roi_volume, np.eye(4))
                    nib.save(img, filepath)
                except ImportError:
                    QtWidgets.QMessageBox.warning(
                        self, "警告", 
                        "需要安装nibabel库来支持NIfTI格式。请使用其他格式或安装nibabel。"
                    )
                    return
            
            QtWidgets.QMessageBox.information(self, "成功", f"ROI体积已保存到：{filepath}")
        
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"导出ROI体积失败：{str(e)}")
