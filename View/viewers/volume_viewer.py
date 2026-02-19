"""
3D体渲染查看器组件
基于VTK的三维体渲染视图，可以嵌入到PyQt界面中
"""

import math
import numpy as np
import vtk
from PyQt5 import QtWidgets
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor


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
            # 简化渲染模式（稳定版）
            # 使用稳健的百分位传输函数，避免硬阈值造成的层状伪影与错误表面

            volume_mapper = vtk.vtkGPUVolumeRayCastMapper()
            volume_mapper.SetInputConnection(importer.GetOutputPort())
            volume_mapper.SetBlendModeToComposite()
            volume_mapper.SetAutoAdjustSampleDistances(True)
            volume_mapper.SetSampleDistance(max(spacing) * 0.7)

            # 稳健范围估计：去除极端值
            try:
                flat_data = volume_array.reshape(-1).astype(np.float32)
                p01 = float(np.percentile(flat_data, 1.0))
                p99 = float(np.percentile(flat_data, 99.5))
                data_min = float(flat_data.min())
                data_max = float(flat_data.max())

                if not np.isfinite(p01) or not np.isfinite(p99) or p99 <= p01:
                    p01, p99 = data_min, data_max

                # 对于低动态范围数据（如分割），退回全范围映射
                if (p99 - p01) < 32:
                    p01, p99 = data_min, data_max

                print(f"3D稳定渲染范围: [{p01:.2f}, {p99:.2f}] (全范围 [{data_min:.2f}, {data_max:.2f}])")
            except Exception as e:
                print(f"3D范围估计失败: {e}")
                p01, p99 = 0.0, 65535.0

            # 灰度颜色映射（连续）
            color_func = vtk.vtkColorTransferFunction()
            color_func.AddRGBPoint(p01, 0.0, 0.0, 0.0)
            color_func.AddRGBPoint(p01 + (p99 - p01) * 0.35, 0.35, 0.35, 0.35)
            color_func.AddRGBPoint(p01 + (p99 - p01) * 0.70, 0.70, 0.70, 0.70)
            color_func.AddRGBPoint(p99, 1.0, 1.0, 1.0)

            # 不透明度映射（平滑）
            opacity_func = vtk.vtkPiecewiseFunction()
            opacity_func.AddPoint(p01, 0.00)
            opacity_func.AddPoint(p01 + (p99 - p01) * 0.10, 0.00)
            opacity_func.AddPoint(p01 + (p99 - p01) * 0.35, 0.08)
            opacity_func.AddPoint(p01 + (p99 - p01) * 0.65, 0.35)
            opacity_func.AddPoint(p99, 0.85)

            # 体渲染属性
            volume_property = vtk.vtkVolumeProperty()
            volume_property.SetColor(color_func)
            volume_property.SetScalarOpacity(opacity_func)
            volume_property.SetInterpolationTypeToLinear()
            volume_property.ShadeOn()
            volume_property.SetAmbient(0.25)
            volume_property.SetDiffuse(0.75)
            volume_property.SetSpecular(0.15)
            volume_property.SetSpecularPower(10)
            
            # 注意：禁用激进梯度不透明度，避免分层/环纹伪影
            
            # 创建体数据对象
            volume = vtk.vtkVolume()
            volume.SetMapper(volume_mapper)
            volume.SetProperty(volume_property)
            
            # 创建渲染器
            renderer = vtk.vtkRenderer()
            renderer.AddVolume(volume)
            renderer.SetBackground(0.1, 0.1, 0.2)
            renderer.ResetCamera()
            
            camera = renderer.GetActiveCamera()
            camera.Elevation(20)
            camera.Azimuth(35)
            camera.Zoom(1.15)
            camera.Roll(0)

            renWin = self.vtkWidget.GetRenderWindow()
            renWin.SetMultiSamples(4)
            renderer.SetUseFXAA(True)
            renderer.SetTwoSidedLighting(True)

            camera_range = camera.GetClippingRange()
            camera.SetClippingRange(camera_range[0] * 0.2, camera_range[1] * 1.8)

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

    def set_background_color(self, rgb):
        """设置3D渲染背景颜色"""
        if not hasattr(self, 'renderer') or self.renderer is None:
            return
        try:
            r, g, b = rgb
            self.renderer.SetBackground(float(r), float(g), float(b))
            self.renderer.GetRenderWindow().Render()
        except Exception:
            pass

