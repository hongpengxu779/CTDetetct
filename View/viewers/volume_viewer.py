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
            default_sample_distance = max(spacing) * 1.0
        else:
            # 简化渲染模式（稳定版）
            # 使用稳健的百分位传输函数，避免硬阈值造成的层状伪影与错误表面

            volume_mapper = vtk.vtkGPUVolumeRayCastMapper()
            volume_mapper.SetInputConnection(importer.GetOutputPort())
            volume_mapper.SetBlendModeToComposite()
            volume_mapper.SetAutoAdjustSampleDistances(True)
            volume_mapper.SetSampleDistance(max(spacing) * 0.7)
            default_sample_distance = max(spacing) * 0.7

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

        # 默认不覆写VTK内建光照，避免改变原有3D外观

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
        self.volume = volume if 'volume' in locals() else None
        self.light = None
        self.default_sample_distance = float(default_sample_distance)
        self.current_render_mode = "默认"
        self.default_color_func = None
        self.default_opacity_func = None
        self.default_material = None
        self.light_settings = {
            'light_position': 50,
            'light_intensity': 60,
            'shadow_strength': 40,
            'shadow_alpha': 50,
            'brightness': 50,
            'spot': 30,
            'specular': 35,
            'scatter': 45,
        }
        self.advanced_3d_settings = {
            'solidity': 80,
            'diffuse': 75,
            'specular': 20,
            'shininess': 35,
            'tone_mapping': False,
            'unsharp': False,
            'specular_boost': False,
            'noise_reduction': False,
            'edge_contrast': False,
            'filtered_gradient': False,
            'high_quality': True,
            'median': False,
            'lut_3d': 'grayscale',
            'absolute_lut': False,
            'flip_roi_lut': False,
            'gamma_enhance': False,
            'interpolation_3d': 'Linear',
        }
        if self.property is not None:
            try:
                self.default_color_func = vtk.vtkColorTransferFunction()
                self.default_color_func.DeepCopy(self.property.GetRGBTransferFunction())
                self.default_opacity_func = vtk.vtkPiecewiseFunction()
                self.default_opacity_func.DeepCopy(self.property.GetScalarOpacity())
                self.default_material = {
                    'ambient': float(self.property.GetAmbient()),
                    'diffuse': float(self.property.GetDiffuse()),
                    'specular': float(self.property.GetSpecular()),
                    'specular_power': float(self.property.GetSpecularPower()),
                    'shade': bool(self.property.GetShade()),
                    'scalar_opacity_unit_distance': float(self.property.GetScalarOpacityUnitDistance()),
                }
            except Exception:
                self.default_color_func = None
                self.default_opacity_func = None
                self.default_material = None

    def _build_lut_color_func(self, lut_name, vmin, vmax, flip=False, gamma=1.0, tone_mapping=False):
        lut = str(lut_name or 'grayscale').lower()
        span = max(1e-6, float(vmax - vmin))

        color_func = vtk.vtkColorTransferFunction()

        def add_point(t, r, g, b):
            t = float(max(0.0, min(1.0, t)))
            if tone_mapping:
                t = math.sqrt(t)
            if gamma != 1.0:
                t = math.pow(max(1e-6, t), gamma)
            x = vmin + span * (1.0 - t if flip else t)
            color_func.AddRGBPoint(float(x), float(max(0.0, min(1.0, r))), float(max(0.0, min(1.0, g))), float(max(0.0, min(1.0, b))))

        if lut == 'bone':
            add_point(0.0, 0.00, 0.00, 0.00)
            add_point(0.35, 0.38, 0.38, 0.45)
            add_point(0.70, 0.78, 0.80, 0.85)
            add_point(1.0, 1.00, 1.00, 1.00)
        elif lut == 'coolwarm':
            add_point(0.0, 0.23, 0.30, 0.75)
            add_point(0.5, 0.86, 0.86, 0.86)
            add_point(1.0, 0.75, 0.25, 0.23)
        else:
            add_point(0.0, 0.0, 0.0, 0.0)
            add_point(0.35, 0.35, 0.35, 0.35)
            add_point(0.70, 0.70, 0.70, 0.70)
            add_point(1.0, 1.0, 1.0, 1.0)
        return color_func

    def configure_advanced_3d(self, **kwargs):
        if not hasattr(self, 'advanced_3d_settings'):
            self.advanced_3d_settings = {}
        self.advanced_3d_settings.update(kwargs)
        self._apply_advanced_3d_settings(render=True)

    def _apply_advanced_3d_settings(self, render=False):
        if self.property is None or self.mapper is None:
            return

        cfg = self.advanced_3d_settings if hasattr(self, 'advanced_3d_settings') else {}

        vmin, vmax = self._safe_scalar_range()
        use_abs = bool(cfg.get('absolute_lut', False))
        lut_min, lut_max = (0.0, 65535.0) if use_abs else (vmin, vmax)

        gamma = 0.8 if bool(cfg.get('gamma_enhance', False)) else 1.0
        tone_mapping = bool(cfg.get('tone_mapping', False))
        flip_lut = bool(cfg.get('flip_roi_lut', False))
        lut_name = cfg.get('lut_3d', 'grayscale')

        is_default_cfg = (
            int(cfg.get('solidity', 80)) == 80 and
            int(cfg.get('diffuse', 75)) == 75 and
            int(cfg.get('specular', 20)) == 20 and
            int(cfg.get('shininess', 35)) == 35 and
            not bool(cfg.get('tone_mapping', False)) and
            not bool(cfg.get('unsharp', False)) and
            not bool(cfg.get('specular_boost', False)) and
            not bool(cfg.get('noise_reduction', False)) and
            not bool(cfg.get('edge_contrast', False)) and
            not bool(cfg.get('filtered_gradient', False)) and
            bool(cfg.get('high_quality', True)) and
            not bool(cfg.get('median', False)) and
            str(cfg.get('lut_3d', 'grayscale')).lower() == 'grayscale' and
            not bool(cfg.get('absolute_lut', False)) and
            not bool(cfg.get('flip_roi_lut', False)) and
            not bool(cfg.get('gamma_enhance', False)) and
            str(cfg.get('interpolation_3d', 'Linear')).lower().startswith('lin')
        )

        if is_default_cfg and self.current_render_mode in ("默认", "体渲染") and self.default_color_func is not None and self.default_opacity_func is not None:
            color_func = vtk.vtkColorTransferFunction()
            color_func.DeepCopy(self.default_color_func)
            opacity_func = vtk.vtkPiecewiseFunction()
            opacity_func.DeepCopy(self.default_opacity_func)
        else:
            color_func = self._build_lut_color_func(lut_name, lut_min, lut_max, flip=flip_lut, gamma=gamma, tone_mapping=tone_mapping)
            solidity_n = max(0.0, min(1.0, float(cfg.get('solidity', 80)) / 100.0))
            opacity_func = vtk.vtkPiecewiseFunction()
            opacity_func.AddPoint(vmin, 0.0)
            opacity_func.AddPoint(vmin + (vmax - vmin) * 0.15, 0.04 * solidity_n)
            opacity_func.AddPoint(vmin + (vmax - vmin) * 0.45, 0.30 * solidity_n)
            opacity_func.AddPoint(vmin + (vmax - vmin) * 0.75, 0.68 * solidity_n)
            opacity_func.AddPoint(vmax, min(1.0, 0.98 * solidity_n + 0.02))

        self.property.SetColor(color_func)
        self.property.SetScalarOpacity(opacity_func)

        light_cfg = self.light_settings if hasattr(self, 'light_settings') else {}
        light_intensity_n = max(0.0, min(1.0, float(light_cfg.get('light_intensity', 60)) / 100.0))
        brightness_n = max(0.0, min(1.0, float(light_cfg.get('brightness', 50)) / 100.0))
        light_specular_n = max(0.0, min(1.0, float(light_cfg.get('specular', 35)) / 100.0))
        scatter_n = max(0.0, min(1.0, float(light_cfg.get('scatter', 45)) / 100.0))
        spot_n = max(0.0, min(1.0, float(light_cfg.get('spot', 30)) / 100.0))
        shadow_alpha_n = max(0.0, min(1.0, float(light_cfg.get('shadow_alpha', 50)) / 100.0))

        is_default_light = (
            abs(float(light_cfg.get('light_position', 50)) - 50.0) < 1e-6 and
            abs(float(light_cfg.get('light_intensity', 60)) - 60.0) < 1e-6 and
            abs(float(light_cfg.get('shadow_strength', 40)) - 40.0) < 1e-6 and
            abs(float(light_cfg.get('shadow_alpha', 50)) - 50.0) < 1e-6 and
            abs(float(light_cfg.get('brightness', 50)) - 50.0) < 1e-6 and
            abs(float(light_cfg.get('spot', 30)) - 30.0) < 1e-6 and
            abs(float(light_cfg.get('specular', 35)) - 35.0) < 1e-6 and
            abs(float(light_cfg.get('scatter', 45)) - 45.0) < 1e-6
        )

        if is_default_cfg and is_default_light and self.current_render_mode in ("默认", "体渲染") and self.default_material is not None:
            self.property.SetAmbient(float(self.default_material.get('ambient', 0.25)))
            self.property.SetDiffuse(float(self.default_material.get('diffuse', 0.75)))
            self.property.SetSpecular(float(self.default_material.get('specular', 0.15)))
            self.property.SetSpecularPower(float(self.default_material.get('specular_power', 10.0)))
            if bool(self.default_material.get('shade', True)):
                self.property.ShadeOn()
            else:
                self.property.ShadeOff()
            self.property.SetScalarOpacityUnitDistance(float(self.default_material.get('scalar_opacity_unit_distance', 1.0)))
        else:
            base_diffuse = max(0.0, min(1.0, float(cfg.get('diffuse', 75)) / 100.0))
            base_specular = max(0.0, min(1.0, float(cfg.get('specular', 20)) / 100.0))
            light_diffuse_scale = 0.65 + 0.55 * light_intensity_n + 0.35 * brightness_n
            diffuse = max(0.0, min(1.0, base_diffuse * light_diffuse_scale))
            specular = max(0.0, min(1.0, base_specular * (0.60 + 0.80 * light_specular_n)))
            shininess = max(1.0, min(100.0, float(cfg.get('shininess', 35))))
            if bool(cfg.get('specular_boost', False)):
                specular = min(1.0, specular * 1.55)

            ambient = 0.05 + 0.35 * scatter_n
            if bool(cfg.get('noise_reduction', False)):
                ambient = min(1.0, ambient + 0.08)
                specular = max(0.0, specular * 0.85)

            if bool(cfg.get('edge_contrast', False)):
                specular = min(1.0, specular * 1.15)
                diffuse = min(1.0, diffuse * 1.06)

            shade_on = bool(cfg.get('high_quality', True)) or bool(cfg.get('edge_contrast', False)) or specular > 0.05
            if self.current_render_mode in ("MIP", "MinIP"):
                shade_on = False
            if shade_on:
                self.property.ShadeOn()
            else:
                self.property.ShadeOff()

            self.property.SetAmbient(ambient)
            self.property.SetDiffuse(diffuse)
            self.property.SetSpecular(specular)
            self.property.SetSpecularPower(5.0 + shininess * (0.65 + 0.55 * spot_n))
            self.property.SetScalarOpacityUnitDistance(0.2 + (1.0 - shadow_alpha_n) * 2.2)

        interp_mode = str(cfg.get('interpolation_3d', 'Linear')).lower()
        if interp_mode.startswith('near'):
            self.property.SetInterpolationTypeToNearest()
        else:
            self.property.SetInterpolationTypeToLinear()

        edge_contrast = bool(cfg.get('edge_contrast', False))
        filtered_gradient = bool(cfg.get('filtered_gradient', False))
        hard_gradient = bool(cfg.get('unsharp', False))
        gradient_enhance = bool(cfg.get('unsharp', False))
        noise_reduction = bool(cfg.get('noise_reduction', False))
        median = bool(cfg.get('median', False))

        grad_max = max(64.0, float(vmax - vmin) * 0.18)
        g1 = grad_max * 0.12
        g2 = grad_max * 0.36
        g3 = grad_max * 0.70

        grad_func = vtk.vtkPiecewiseFunction()
        if edge_contrast or gradient_enhance:
            if hard_gradient:
                grad_func.AddPoint(0.0, 0.0)
                grad_func.AddPoint(g1 * 0.8, 0.0)
                grad_func.AddPoint(g2, 0.85)
                grad_func.AddPoint(grad_max, 1.0)
            elif filtered_gradient:
                grad_func.AddPoint(0.0, 0.0)
                grad_func.AddPoint(g1, 0.08)
                grad_func.AddPoint(g2, 0.45)
                grad_func.AddPoint(grad_max, 0.82)
            else:
                grad_func.AddPoint(0.0, 0.0)
                grad_func.AddPoint(g1, 0.0)
                grad_func.AddPoint(g3, 0.72)
                grad_func.AddPoint(grad_max, 1.0)
        else:
            grad_func.AddPoint(0.0, 0.0)
            grad_func.AddPoint(grad_max, 1.0)

        if noise_reduction or median:
            # 降噪/中值时整体减弱梯度响应，减少噪点闪烁
            grad_smooth = vtk.vtkPiecewiseFunction()
            grad_smooth.AddPoint(0.0, 0.0)
            grad_smooth.AddPoint(g1, 0.0)
            grad_smooth.AddPoint(g2, 0.32 if median else 0.40)
            grad_smooth.AddPoint(grad_max, 0.60 if median else 0.72)
            grad_func = grad_smooth

        self.property.SetGradientOpacity(grad_func)

        high_quality = bool(cfg.get('high_quality', True))

        self.mapper.SetAutoAdjustSampleDistances(not high_quality)
        base_distance = self.default_sample_distance
        image_sample_distance = 1.0
        if high_quality:
            base_distance = max(self.default_sample_distance * 0.55, 0.05)
            image_sample_distance = 1.0
        else:
            base_distance = max(self.default_sample_distance, 0.08)
            image_sample_distance = 1.45

        if noise_reduction:
            base_distance *= 1.80
            image_sample_distance += 0.40
        if median:
            base_distance *= 1.60
            image_sample_distance += 0.45
            self.property.SetInterpolationTypeToLinear()
        if str(cfg.get('interpolation_3d', 'Linear')).lower().startswith('cubic'):
            base_distance *= 0.80
        if hard_gradient or edge_contrast:
            base_distance *= 0.88

        self.mapper.SetImageSampleDistance(max(0.7, float(image_sample_distance)))

        self.mapper.SetSampleDistance(max(0.03, float(base_distance)))

        if render:
            self._render()

    def _render(self):
        if hasattr(self, 'renderer') and self.renderer is not None:
            self.renderer.GetRenderWindow().Render()

    def _safe_scalar_range(self):
        if self.mapper is not None:
            input_data = self.mapper.GetInput()
            if input_data is not None:
                rng = input_data.GetScalarRange()
                if rng is not None and len(rng) == 2 and np.isfinite(rng[0]) and np.isfinite(rng[1]) and rng[1] > rng[0]:
                    return float(rng[0]), float(rng[1])
        return 0.0, 65535.0

    def _build_default_transfer(self):
        vmin, vmax = self._safe_scalar_range()
        color_func = vtk.vtkColorTransferFunction()
        color_func.AddRGBPoint(vmin, 0.0, 0.0, 0.0)
        color_func.AddRGBPoint(vmin + (vmax - vmin) * 0.35, 0.35, 0.35, 0.35)
        color_func.AddRGBPoint(vmin + (vmax - vmin) * 0.70, 0.70, 0.70, 0.70)
        color_func.AddRGBPoint(vmax, 1.0, 1.0, 1.0)

        opacity_func = vtk.vtkPiecewiseFunction()
        opacity_func.AddPoint(vmin, 0.00)
        opacity_func.AddPoint(vmin + (vmax - vmin) * 0.10, 0.00)
        opacity_func.AddPoint(vmin + (vmax - vmin) * 0.35, 0.08)
        opacity_func.AddPoint(vmin + (vmax - vmin) * 0.65, 0.35)
        opacity_func.AddPoint(vmax, 0.85)
        return color_func, opacity_func

    def set_projection_mode(self, orthographic=False):
        if not hasattr(self, 'renderer') or self.renderer is None:
            return
        camera = self.renderer.GetActiveCamera()
        camera.SetParallelProjection(1 if orthographic else 0)
        self._render()

    def set_interaction_quality(self, reduce_quality=False, best_quality=True):
        if self.mapper is None:
            return
        if reduce_quality:
            self.mapper.SetAutoAdjustSampleDistances(True)
            self.mapper.SetSampleDistance(self.default_sample_distance * 2.2)
            self.mapper.SetImageSampleDistance(2.0)
        elif best_quality:
            self.mapper.SetAutoAdjustSampleDistances(False)
            self.mapper.SetSampleDistance(max(self.default_sample_distance * 0.55, 0.05))
            self.mapper.SetImageSampleDistance(1.0)
        else:
            self.mapper.SetAutoAdjustSampleDistances(True)
            self.mapper.SetSampleDistance(self.default_sample_distance)
            self.mapper.SetImageSampleDistance(1.25)
        self._render()

    def set_render_mode(self, mode):
        if self.mapper is None or self.property is None:
            return

        mode = str(mode or "默认")
        self.current_render_mode = mode
        color_func, opacity_func = self._build_default_transfer()
        vmin, vmax = self._safe_scalar_range()

        if mode == "MIP":
            self.mapper.SetBlendModeToMaximumIntensity()
            self.property.ShadeOff()
            opacity_func = vtk.vtkPiecewiseFunction()
            opacity_func.AddPoint(vmin, 0.0)
            opacity_func.AddPoint(vmax, 1.0)
        elif mode == "MinIP":
            self.mapper.SetBlendModeToMinimumIntensity()
            self.property.ShadeOff()
            opacity_func = vtk.vtkPiecewiseFunction()
            opacity_func.AddPoint(vmin, 1.0)
            opacity_func.AddPoint(vmax, 0.0)
        elif mode in ("表面渲染", "ISO"):
            self.mapper.SetBlendModeToComposite()
            self.property.ShadeOn()
            iso_value = vmin + 0.62 * (vmax - vmin)
            opacity_func = vtk.vtkPiecewiseFunction()
            opacity_func.AddPoint(vmin, 0.0)
            opacity_func.AddPoint(iso_value - 0.06 * (vmax - vmin), 0.0)
            opacity_func.AddPoint(iso_value, 0.55)
            opacity_func.AddPoint(vmax, 0.92)
        elif mode in ("默认", "体渲染"):
            self.mapper.SetBlendModeToComposite()
            self.property.ShadeOn()
            if self.default_color_func is not None and self.default_opacity_func is not None:
                color_func = vtk.vtkColorTransferFunction()
                color_func.DeepCopy(self.default_color_func)
                opacity_func = vtk.vtkPiecewiseFunction()
                opacity_func.DeepCopy(self.default_opacity_func)
        else:
            self.mapper.SetBlendModeToComposite()
            self.property.ShadeOn()

        self.property.SetColor(color_func)
        self.property.SetScalarOpacity(opacity_func)
        self._apply_advanced_3d_settings(render=False)
        self._render()

    def set_light_settings(self, light_position=50, light_intensity=60, shadow_strength=40,
                           shadow_alpha=50, brightness=50, spot=30, specular=35, scatter=45):
        if self.property is None or self.renderer is None:
            return

        self.light_settings = {
            'light_position': float(light_position),
            'light_intensity': float(light_intensity),
            'shadow_strength': float(shadow_strength),
            'shadow_alpha': float(shadow_alpha),
            'brightness': float(brightness),
            'spot': float(spot),
            'specular': float(specular),
            'scatter': float(scatter),
        }

        if self.light is None:
            self.light = vtk.vtkLight()
            self.light.SetLightTypeToSceneLight()
            self.light.SetPositional(True)
            self.light.SetPosition(1.0, 1.0, 1.2)
            self.light.SetFocalPoint(0.0, 0.0, 0.0)
            self.light.SetConeAngle(45.0)
            self.light.SetIntensity(0.8)
            self.renderer.AddLight(self.light)

        light_intensity_n = max(0.0, min(1.0, float(light_intensity) / 100.0))
        brightness_n = max(0.0, min(1.0, float(brightness) / 100.0))
        spot_n = max(0.0, min(1.0, float(spot) / 100.0))
        shadow_strength_n = max(0.0, min(1.0, float(shadow_strength) / 100.0))

        if hasattr(self.renderer, 'SetUseShadows'):
            self.renderer.SetUseShadows(shadow_strength_n > 0.05)

        if self.light is not None:
            angle = (float(light_position) / 100.0) * (2.0 * math.pi)
            radius = 1.6
            self.light.SetPosition(radius * math.cos(angle), radius * math.sin(angle), 1.2)
            self.light.SetIntensity(0.15 + 1.35 * light_intensity_n)
            self.light.SetConeAngle(15.0 + 60.0 * spot_n)

        self._apply_advanced_3d_settings(render=True)

    def set_focus_settings(self, auto_focus=True, focus_distance=40, depth_of_field=30):
        if self.renderer is None:
            return
        camera = self.renderer.GetActiveCamera()
        if camera is None:
            return

        if auto_focus:
            self.renderer.ResetCamera()

        near, far = camera.GetClippingRange()
        near = max(0.01, float(near))
        far = max(near + 0.1, float(far))

        if not auto_focus:
            distance_target = near + (far - near) * max(0.0, min(1.0, float(focus_distance) / 100.0))
            cam_pos = np.array(camera.GetPosition(), dtype=float)
            focal = np.array(camera.GetFocalPoint(), dtype=float)
            direction = focal - cam_pos
            norm = float(np.linalg.norm(direction))
            if norm > 1e-6:
                new_focal = cam_pos + direction / norm * distance_target
                camera.SetFocalPoint(float(new_focal[0]), float(new_focal[1]), float(new_focal[2]))

        dof_n = max(0.0, min(1.0, float(depth_of_field) / 100.0))
        if not camera.GetParallelProjection():
            camera.SetViewAngle(12.0 + (1.0 - dof_n) * 36.0)

        span = far - near
        near_new = max(0.01, near + span * 0.10 * dof_n)
        far_new = max(near_new + 0.1, far - span * 0.05 * dof_n)
        camera.SetClippingRange(near_new, far_new)
        self._render()

    def save_screenshot(self, filepath):
        if self.renderer is None or not filepath:
            return False
        try:
            window = self.renderer.GetRenderWindow()
            w2if = vtk.vtkWindowToImageFilter()
            w2if.SetInput(window)
            w2if.ReadFrontBufferOff()
            w2if.Update()

            writer = vtk.vtkPNGWriter()
            writer.SetFileName(filepath)
            writer.SetInputConnection(w2if.GetOutputPort())
            writer.Write()
            return True
        except Exception:
            return False
        
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
        self._render()

    def set_background_color(self, rgb):
        """设置3D渲染背景颜色"""
        if not hasattr(self, 'renderer') or self.renderer is None:
            return
        try:
            r, g, b = rgb
            self.renderer.SetBackground(float(r), float(g), float(b))
            self._render()
        except Exception:
            pass

