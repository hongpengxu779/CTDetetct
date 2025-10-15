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
            # 简化渲染模式 - 使用标准体渲染但简化传输函数
            # 这样可以保留3D结构同时提高清晰度
            
            # 使用GPU光线投射映射器，优化CT数据的体绘制
            volume_mapper = vtk.vtkGPUVolumeRayCastMapper()
            volume_mapper.SetInputConnection(importer.GetOutputPort())  # 输入数据
            volume_mapper.SetBlendModeToComposite()  # 使用复合模式进行体渲染
            volume_mapper.SetSampleDistance(0.5)     # 设置较小的采样距离，提高质量
            volume_mapper.SetAutoAdjustSampleDistances(True)  # 自动调整采样距离
            
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

