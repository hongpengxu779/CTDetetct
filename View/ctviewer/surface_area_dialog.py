"""
表面积测定对话框
提供阈值设定、表面积计算、3D等值面可视化等功能
类似 Dragonfly 的表面积测定（Surface Area Determination）功能
"""

import numpy as np
import vtk
from PyQt5 import QtWidgets, QtCore, QtGui
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

try:
    from skimage.measure import marching_cubes, mesh_surface_area
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False


class SurfaceAreaDialog(QtWidgets.QDialog):
    """
    表面积测定对话框

    功能：
    1. 阈值设定（手动 / Otsu 自动）
    2. Marching Cubes 等值面提取
    3. 表面积 & 体积计算
    4. 3D 等值面可视化
    5. 支持 ROI 区域分析
    """

    def __init__(self, parent=None, volume_data=None, spacing=None, roi_bounds=None):
        """
        参数
        ----
        parent : QWidget
            父窗口
        volume_data : np.ndarray
            3D 体数据 (z, y, x)，uint16
        spacing : tuple
            像素间距 (sx, sy, sz)
        roi_bounds : list, optional
            ROI 边界 [x_min, x_max, y_min, y_max, z_min, z_max]
        """
        super().__init__(parent)
        self.setWindowTitle("表面积测定")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        self.volume_data = volume_data
        self.spacing = spacing if spacing else (1.0, 1.0, 1.0)
        self.roi_bounds = roi_bounds

        # 存储计算结果
        self.vertices = None
        self.faces = None
        self.surface_area_value = 0.0
        self.volume_value = 0.0
        self.voxel_count = 0

        # 提取工作数据（考虑ROI）
        self.work_data = self._extract_work_data()

        self._init_ui()
        self._update_threshold_range()

    def _extract_work_data(self):
        """提取工作数据，考虑ROI边界"""
        if self.volume_data is None:
            return None

        if self.roi_bounds is not None:
            x_min, x_max, y_min, y_max, z_min, z_max = self.roi_bounds
            # 确保边界合法
            z_min = max(0, int(z_min))
            z_max = min(self.volume_data.shape[0], int(z_max))
            y_min = max(0, int(y_min))
            y_max = min(self.volume_data.shape[1], int(y_max))
            x_min = max(0, int(x_min))
            x_max = min(self.volume_data.shape[2], int(x_max))
            return self.volume_data[z_min:z_max, y_min:y_max, x_min:x_max].copy()
        else:
            return self.volume_data.copy()

    def _init_ui(self):
        """初始化界面"""
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setSpacing(10)

        # ============ 左侧控制面板 ============
        control_panel = QtWidgets.QWidget()
        control_panel.setMaximumWidth(320)
        control_panel.setMinimumWidth(280)
        control_layout = QtWidgets.QVBoxLayout(control_panel)
        control_layout.setContentsMargins(5, 5, 5, 5)
        control_layout.setSpacing(8)

        # --- 数据信息 ---
        info_group = QtWidgets.QGroupBox("数据信息")
        info_layout = QtWidgets.QVBoxLayout(info_group)

        if self.work_data is not None:
            shape = self.work_data.shape
            data_min = int(self.work_data.min())
            data_max = int(self.work_data.max())
            info_text = (
                f"体数据大小: {shape[2]} × {shape[1]} × {shape[0]}\n"
                f"像素间距: {self.spacing[0]:.4f} × {self.spacing[1]:.4f} × {self.spacing[2]:.4f}\n"
                f"灰度范围: [{data_min}, {data_max}]\n"
            )
            if self.roi_bounds is not None:
                info_text += f"ROI 区域: 已启用"
            else:
                info_text += f"ROI 区域: 全局"
        else:
            info_text = "无数据"

        info_label = QtWidgets.QLabel(info_text)
        info_label.setStyleSheet("font-size: 9pt; color: #333;")
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        control_layout.addWidget(info_group)

        # --- 阈值设定 ---
        threshold_group = QtWidgets.QGroupBox("阈值设定")
        threshold_layout = QtWidgets.QVBoxLayout(threshold_group)

        # 阈值模式选择
        mode_layout = QtWidgets.QHBoxLayout()
        self.manual_radio = QtWidgets.QRadioButton("手动")
        self.manual_radio.setChecked(True)
        self.otsu_radio = QtWidgets.QRadioButton("Otsu 自动")
        self.manual_radio.toggled.connect(self._on_threshold_mode_changed)
        mode_layout.addWidget(self.manual_radio)
        mode_layout.addWidget(self.otsu_radio)
        threshold_layout.addLayout(mode_layout)

        # 下限阈值
        lower_layout = QtWidgets.QHBoxLayout()
        lower_label = QtWidgets.QLabel("下限:")
        lower_label.setMinimumWidth(35)
        lower_layout.addWidget(lower_label)
        self.lower_threshold_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.lower_threshold_slider.setMinimum(0)
        self.lower_threshold_slider.setMaximum(65535)
        self.lower_threshold_slider.setValue(10000)
        self.lower_threshold_slider.valueChanged.connect(self._on_lower_threshold_changed)
        lower_layout.addWidget(self.lower_threshold_slider)
        self.lower_threshold_value = QtWidgets.QSpinBox()
        self.lower_threshold_value.setRange(0, 65535)
        self.lower_threshold_value.setValue(10000)
        self.lower_threshold_value.setMinimumWidth(70)
        self.lower_threshold_value.valueChanged.connect(self._on_lower_spinbox_changed)
        lower_layout.addWidget(self.lower_threshold_value)
        threshold_layout.addLayout(lower_layout)

        # 上限阈值
        upper_layout = QtWidgets.QHBoxLayout()
        upper_label = QtWidgets.QLabel("上限:")
        upper_label.setMinimumWidth(35)
        upper_layout.addWidget(upper_label)
        self.upper_threshold_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.upper_threshold_slider.setMinimum(0)
        self.upper_threshold_slider.setMaximum(65535)
        self.upper_threshold_slider.setValue(65535)
        self.upper_threshold_slider.valueChanged.connect(self._on_upper_threshold_changed)
        upper_layout.addWidget(self.upper_threshold_slider)
        self.upper_threshold_value = QtWidgets.QSpinBox()
        self.upper_threshold_value.setRange(0, 65535)
        self.upper_threshold_value.setValue(65535)
        self.upper_threshold_value.setMinimumWidth(70)
        self.upper_threshold_value.valueChanged.connect(self._on_upper_spinbox_changed)
        upper_layout.addWidget(self.upper_threshold_value)
        threshold_layout.addLayout(upper_layout)

        # 等值面阈值（Marching Cubes level）
        level_layout = QtWidgets.QHBoxLayout()
        level_label = QtWidgets.QLabel("等值面:")
        level_label.setMinimumWidth(35)
        level_label.setToolTip("Marching Cubes 等值面级别 (0.0 ~ 1.0)")
        level_layout.addWidget(level_label)
        self.level_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.level_slider.setMinimum(1)
        self.level_slider.setMaximum(100)
        self.level_slider.setValue(50)
        self.level_slider.setToolTip("等值面级别，0.5 表示在二值化数据的中间")
        level_layout.addWidget(self.level_slider)
        self.level_value_label = QtWidgets.QLabel("0.50")
        self.level_value_label.setMinimumWidth(40)
        self.level_slider.valueChanged.connect(
            lambda v: self.level_value_label.setText(f"{v/100:.2f}")
        )
        level_layout.addWidget(self.level_value_label)
        threshold_layout.addLayout(level_layout)

        control_layout.addWidget(threshold_group)

        # --- Marching Cubes 参数 ---
        mc_group = QtWidgets.QGroupBox("网格参数")
        mc_layout = QtWidgets.QVBoxLayout(mc_group)

        # 步长
        step_layout = QtWidgets.QHBoxLayout()
        step_label = QtWidgets.QLabel("步长:")
        step_label.setToolTip("Marching Cubes 步长，越大速度越快但精度越低")
        step_layout.addWidget(step_label)
        self.step_spinbox = QtWidgets.QSpinBox()
        self.step_spinbox.setRange(1, 10)
        self.step_spinbox.setValue(1)
        self.step_spinbox.setToolTip("值为1时精度最高；大于1时会跳过部分体素以加速计算")
        step_layout.addWidget(self.step_spinbox)
        mc_layout.addLayout(step_layout)

        # 平滑选项
        self.smooth_checkbox = QtWidgets.QCheckBox("表面高斯平滑")
        self.smooth_checkbox.setChecked(False)
        self.smooth_checkbox.setToolTip("对提取的网格进行 Laplacian 平滑（建议用于工业CT）")
        mc_layout.addWidget(self.smooth_checkbox)

        # 平滑迭代次数
        smooth_iter_layout = QtWidgets.QHBoxLayout()
        smooth_iter_label = QtWidgets.QLabel("平滑迭代:")
        smooth_iter_layout.addWidget(smooth_iter_label)
        self.smooth_iter_spinbox = QtWidgets.QSpinBox()
        self.smooth_iter_spinbox.setRange(1, 100)
        self.smooth_iter_spinbox.setValue(10)
        self.smooth_iter_spinbox.setEnabled(False)
        smooth_iter_layout.addWidget(self.smooth_iter_spinbox)
        mc_layout.addLayout(smooth_iter_layout)

        self.smooth_checkbox.toggled.connect(self.smooth_iter_spinbox.setEnabled)

        control_layout.addWidget(mc_group)

        # --- 计算按钮 ---
        self.compute_btn = QtWidgets.QPushButton("▶  计算表面积")
        self.compute_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #90CAF9;
            }
        """)
        self.compute_btn.clicked.connect(self._compute_surface_area)
        control_layout.addWidget(self.compute_btn)

        # 进度条
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)

        # --- 结果显示 ---
        result_group = QtWidgets.QGroupBox("计算结果")
        result_layout = QtWidgets.QVBoxLayout(result_group)

        self.result_text = QtWidgets.QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(200)
        self.result_text.setStyleSheet("""
            QTextEdit {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
            }
        """)
        self.result_text.setPlainText("等待计算...")
        result_layout.addWidget(self.result_text)

        # 导出按钮
        export_layout = QtWidgets.QHBoxLayout()
        self.export_stl_btn = QtWidgets.QPushButton("导出 STL")
        self.export_stl_btn.setEnabled(False)
        self.export_stl_btn.clicked.connect(self._export_stl)
        export_layout.addWidget(self.export_stl_btn)

        self.export_report_btn = QtWidgets.QPushButton("导出报告")
        self.export_report_btn.setEnabled(False)
        self.export_report_btn.clicked.connect(self._export_report)
        export_layout.addWidget(self.export_report_btn)
        result_layout.addLayout(export_layout)

        control_layout.addWidget(result_group)
        control_layout.addStretch()

        main_layout.addWidget(control_panel)

        # ============ 右侧3D可视化面板 ============
        vtk_group = QtWidgets.QGroupBox("3D 等值面预览")
        vtk_layout = QtWidgets.QVBoxLayout(vtk_group)
        vtk_layout.setContentsMargins(2, 15, 2, 2)

        self.vtk_widget = QVTKRenderWindowInteractor(vtk_group)
        vtk_layout.addWidget(self.vtk_widget)

        # 初始化VTK渲染器
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(0.1, 0.1, 0.15)
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)

        # 添加坐标轴
        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(30, 30, 30)
        self.renderer.AddActor(axes)

        # 显示提示
        self.status_text_actor = vtk.vtkTextActor()
        self.status_text_actor.SetInput("请设置阈值后点击 [计算表面积]")
        self.status_text_actor.GetTextProperty().SetFontSize(16)
        self.status_text_actor.GetTextProperty().SetColor(0.8, 0.8, 0.8)
        self.status_text_actor.SetPosition(20, 20)
        self.renderer.AddActor2D(self.status_text_actor)

        self.renderer.ResetCamera()

        main_layout.addWidget(vtk_group, stretch=1)

    def _update_threshold_range(self):
        """根据数据范围更新阈值滑动条"""
        if self.work_data is None:
            return
        data_min = int(self.work_data.min())
        data_max = int(self.work_data.max())

        self.lower_threshold_slider.setMinimum(data_min)
        self.lower_threshold_slider.setMaximum(data_max)
        self.upper_threshold_slider.setMinimum(data_min)
        self.upper_threshold_slider.setMaximum(data_max)
        self.lower_threshold_value.setRange(data_min, data_max)
        self.upper_threshold_value.setRange(data_min, data_max)

        # 默认阈值设为数据范围的中间偏上
        mid = (data_min + data_max) // 2
        self.lower_threshold_slider.setValue(mid)
        self.lower_threshold_value.setValue(mid)
        self.upper_threshold_slider.setValue(data_max)
        self.upper_threshold_value.setValue(data_max)

    def _on_threshold_mode_changed(self, manual_checked):
        """阈值模式切换"""
        self.lower_threshold_slider.setEnabled(manual_checked)
        self.lower_threshold_value.setEnabled(manual_checked)
        self.upper_threshold_slider.setEnabled(manual_checked)
        self.upper_threshold_value.setEnabled(manual_checked)

        if not manual_checked:
            # Otsu 自动阈值
            self._compute_otsu_threshold()

    def _on_lower_threshold_changed(self, value):
        """下限滑动条变化"""
        self.lower_threshold_value.blockSignals(True)
        self.lower_threshold_value.setValue(value)
        self.lower_threshold_value.blockSignals(False)

    def _on_upper_threshold_changed(self, value):
        """上限滑动条变化"""
        self.upper_threshold_value.blockSignals(True)
        self.upper_threshold_value.setValue(value)
        self.upper_threshold_value.blockSignals(False)

    def _on_lower_spinbox_changed(self, value):
        """下限数字框变化"""
        self.lower_threshold_slider.blockSignals(True)
        self.lower_threshold_slider.setValue(value)
        self.lower_threshold_slider.blockSignals(False)

    def _on_upper_spinbox_changed(self, value):
        """上限数字框变化"""
        self.upper_threshold_slider.blockSignals(True)
        self.upper_threshold_slider.setValue(value)
        self.upper_threshold_slider.blockSignals(False)

    def _compute_otsu_threshold(self):
        """使用 Otsu 方法自动计算阈值"""
        if self.work_data is None:
            return

        try:
            from skimage.filters import threshold_otsu
            # 对数据进行采样以加速 Otsu 计算
            sample_data = self.work_data.ravel()
            if len(sample_data) > 1000000:
                indices = np.random.choice(len(sample_data), 1000000, replace=False)
                sample_data = sample_data[indices]

            otsu_val = threshold_otsu(sample_data)
            otsu_val = int(otsu_val)

            self.lower_threshold_slider.setValue(otsu_val)
            self.lower_threshold_value.setValue(otsu_val)
            self.upper_threshold_slider.setValue(int(self.work_data.max()))
            self.upper_threshold_value.setValue(int(self.work_data.max()))

            self.result_text.setPlainText(f"Otsu 自动阈值: {otsu_val}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "错误", f"Otsu 阈值计算失败:\n{str(e)}")

    def _compute_surface_area(self):
        """计算表面积（核心功能）"""
        if not HAS_SKIMAGE:
            QtWidgets.QMessageBox.critical(
                self, "依赖缺失",
                "需要 scikit-image 库才能进行表面积计算。\n"
                "请运行: pip install scikit-image"
            )
            return

        if self.work_data is None:
            QtWidgets.QMessageBox.warning(self, "错误", "没有可用的体数据")
            return

        self.compute_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.result_text.setPlainText("正在计算...")
        QtWidgets.QApplication.processEvents()

        try:
            # Step 1: 阈值分割 → 二值化
            self.progress_bar.setValue(10)
            QtWidgets.QApplication.processEvents()

            lower = self.lower_threshold_value.value()
            upper = self.upper_threshold_value.value()
            binary = ((self.work_data >= lower) & (self.work_data <= upper)).astype(np.float32)

            self.voxel_count = int(binary.sum())
            if self.voxel_count == 0:
                self.result_text.setPlainText(
                    "⚠ 在当前阈值范围内没有找到任何体素。\n"
                    "请调整阈值范围后重试。"
                )
                self.compute_btn.setEnabled(True)
                self.progress_bar.setVisible(False)
                return

            # Step 2: Marching Cubes 提取等值面
            self.progress_bar.setValue(30)
            QtWidgets.QApplication.processEvents()

            level = self.level_slider.value() / 100.0
            step_size = self.step_spinbox.value()

            self.vertices, self.faces, normals, values = marching_cubes(
                binary,
                level=level,
                spacing=self.spacing,
                step_size=step_size
            )

            if len(self.vertices) == 0 or len(self.faces) == 0:
                self.result_text.setPlainText(
                    "⚠ Marching Cubes 未提取到任何等值面。\n"
                    "请调整阈值或等值面级别后重试。"
                )
                self.compute_btn.setEnabled(True)
                self.progress_bar.setVisible(False)
                return

            # Step 3: 可选的 Laplacian 平滑
            self.progress_bar.setValue(50)
            QtWidgets.QApplication.processEvents()

            if self.smooth_checkbox.isChecked():
                self.vertices = self._laplacian_smooth(
                    self.vertices, self.faces,
                    iterations=self.smooth_iter_spinbox.value()
                )

            # Step 4: 计算表面积
            self.progress_bar.setValue(70)
            QtWidgets.QApplication.processEvents()

            self.surface_area_value = mesh_surface_area(self.vertices, self.faces)

            # Step 5: 计算体积（使用体素计数法）
            voxel_volume = self.spacing[0] * self.spacing[1] * self.spacing[2]
            self.volume_value = self.voxel_count * voxel_volume

            # 也用网格计算封闭体积（如果网格是封闭的）
            mesh_volume = self._compute_mesh_volume(self.vertices, self.faces)

            # Step 6: 3D 可视化
            self.progress_bar.setValue(85)
            QtWidgets.QApplication.processEvents()
            self._visualize_surface()

            # Step 7: 显示结果
            self.progress_bar.setValue(100)
            QtWidgets.QApplication.processEvents()

            # 确定单位
            sx, sy, sz = self.spacing
            if sx < 0.01:
                unit = "m"
                area_unit = "m²"
                vol_unit = "m³"
            elif sx < 1.0:
                unit = "mm"
                area_unit = "mm²"
                vol_unit = "mm³"
            else:
                unit = "像素"
                area_unit = "像素²"
                vol_unit = "像素³"

            result = (
                f"═══════════════════════════\n"
                f"  表面积测定结果\n"
                f"═══════════════════════════\n\n"
                f"  阈值范围:  [{lower}, {upper}]\n"
                f"  有效体素数: {self.voxel_count:,}\n\n"
                f"  ■ 表面积: {self.surface_area_value:,.4f} {area_unit}\n"
                f"  ■ 体积 (体素法): {self.volume_value:,.4f} {vol_unit}\n"
            )
            if mesh_volume is not None:
                result += f"  ■ 体积 (网格法): {abs(mesh_volume):,.4f} {vol_unit}\n"

            result += (
                f"\n"
                f"  ■ 球度: {self._compute_sphericity():.4f}\n"
                f"  ■ 三角面片数: {len(self.faces):,}\n"
                f"  ■ 顶点数: {len(self.vertices):,}\n"
                f"\n"
                f"  像素间距: ({sx}, {sy}, {sz}) {unit}\n"
            )

            self.result_text.setPlainText(result)
            self.export_stl_btn.setEnabled(True)
            self.export_report_btn.setEnabled(True)

        except Exception as e:
            import traceback
            self.result_text.setPlainText(f"计算失败:\n{str(e)}\n\n{traceback.format_exc()}")
        finally:
            self.compute_btn.setEnabled(True)
            self.progress_bar.setVisible(False)

    def _laplacian_smooth(self, vertices, faces, iterations=10, relaxation=0.1):
        """Laplacian 平滑

        参数
        ----
        vertices : np.ndarray (N, 3)
        faces : np.ndarray (M, 3)
        iterations : int
        relaxation : float

        返回
        ----
        smoothed_vertices : np.ndarray (N, 3)
        """
        verts = vertices.copy()
        n_verts = len(verts)

        # 构建邻接表
        adjacency = [set() for _ in range(n_verts)]
        for f in faces:
            adjacency[f[0]].add(f[1])
            adjacency[f[0]].add(f[2])
            adjacency[f[1]].add(f[0])
            adjacency[f[1]].add(f[2])
            adjacency[f[2]].add(f[0])
            adjacency[f[2]].add(f[1])

        for _ in range(iterations):
            new_verts = verts.copy()
            for i in range(n_verts):
                if len(adjacency[i]) == 0:
                    continue
                neighbor_mean = np.mean(verts[list(adjacency[i])], axis=0)
                new_verts[i] = verts[i] + relaxation * (neighbor_mean - verts[i])
            verts = new_verts

        return verts

    def _compute_mesh_volume(self, vertices, faces):
        """使用散度定理计算网格封闭体积

        V = (1/6) * Σ (v0 · (v1 × v2))
        """
        try:
            v0 = vertices[faces[:, 0]]
            v1 = vertices[faces[:, 1]]
            v2 = vertices[faces[:, 2]]
            cross = np.cross(v1, v2)
            volume = np.sum(v0 * cross) / 6.0
            return volume
        except Exception:
            return None

    def _compute_sphericity(self):
        """计算球度（Sphericity）

        Ψ = (π^{1/3} * (6V)^{2/3}) / A

        球度越接近1，形状越接近球形
        """
        if self.surface_area_value <= 0 or self.volume_value <= 0:
            return 0.0
        V = self.volume_value
        A = self.surface_area_value
        sphericity = (np.pi ** (1.0 / 3.0) * (6.0 * V) ** (2.0 / 3.0)) / A
        return min(sphericity, 1.0)  # 不应超过1

    def _visualize_surface(self):
        """使用VTK可视化等值面"""
        if self.vertices is None or self.faces is None:
            return

        # 清除旧 actor
        self.renderer.RemoveAllViewProps()

        # 创建 VTK PolyData
        points = vtk.vtkPoints()
        for v in self.vertices:
            points.InsertNextPoint(float(v[0]), float(v[1]), float(v[2]))

        triangles = vtk.vtkCellArray()
        for f in self.faces:
            triangle = vtk.vtkTriangle()
            triangle.GetPointIds().SetId(0, int(f[0]))
            triangle.GetPointIds().SetId(1, int(f[1]))
            triangle.GetPointIds().SetId(2, int(f[2]))
            triangles.InsertNextCell(triangle)

        polydata = vtk.vtkPolyData()
        polydata.SetPoints(points)
        polydata.SetPolys(triangles)

        # 计算法线以获得更好的光照效果
        normals_filter = vtk.vtkPolyDataNormals()
        normals_filter.SetInputData(polydata)
        normals_filter.ComputePointNormalsOn()
        normals_filter.ComputeCellNormalsOn()
        normals_filter.SplittingOff()
        normals_filter.Update()

        # Mapper
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(normals_filter.GetOutputPort())

        # Actor
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.4, 0.7, 1.0)  # 浅蓝色
        actor.GetProperty().SetOpacity(0.85)
        actor.GetProperty().SetSpecular(0.3)
        actor.GetProperty().SetSpecularPower(20)
        actor.GetProperty().SetAmbient(0.2)
        actor.GetProperty().SetDiffuse(0.8)

        self.renderer.AddActor(actor)

        # 添加边界框
        outline = vtk.vtkOutlineFilter()
        outline.SetInputData(polydata)
        outline.Update()

        outline_mapper = vtk.vtkPolyDataMapper()
        outline_mapper.SetInputConnection(outline.GetOutputPort())

        outline_actor = vtk.vtkActor()
        outline_actor.SetMapper(outline_mapper)
        outline_actor.GetProperty().SetColor(1.0, 1.0, 1.0)
        outline_actor.GetProperty().SetLineWidth(1.5)
        self.renderer.AddActor(outline_actor)

        # 添加坐标轴
        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(30, 30, 30)
        self.renderer.AddActor(axes)

        # 更新显示状态文本
        status = vtk.vtkTextActor()
        status.SetInput(f"表面积: {self.surface_area_value:,.2f}  |  三角面: {len(self.faces):,}")
        status.GetTextProperty().SetFontSize(14)
        status.GetTextProperty().SetColor(0.9, 0.9, 0.3)
        status.SetPosition(20, 20)
        self.renderer.AddActor2D(status)

        # 重置相机
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()

    def _export_stl(self):
        """导出 STL 文件"""
        if self.vertices is None or self.faces is None:
            QtWidgets.QMessageBox.warning(self, "错误", "请先计算表面积")
            return

        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出 STL 文件", "", "STL 文件 (*.stl)"
        )
        if not filename:
            return

        try:
            # 创建 VTK PolyData
            points = vtk.vtkPoints()
            for v in self.vertices:
                points.InsertNextPoint(float(v[0]), float(v[1]), float(v[2]))

            triangles = vtk.vtkCellArray()
            for f in self.faces:
                triangle = vtk.vtkTriangle()
                triangle.GetPointIds().SetId(0, int(f[0]))
                triangle.GetPointIds().SetId(1, int(f[1]))
                triangle.GetPointIds().SetId(2, int(f[2]))
                triangles.InsertNextCell(triangle)

            polydata = vtk.vtkPolyData()
            polydata.SetPoints(points)
            polydata.SetPolys(triangles)

            # 写入 STL
            writer = vtk.vtkSTLWriter()
            writer.SetFileName(filename)
            writer.SetInputData(polydata)
            writer.Write()

            QtWidgets.QMessageBox.information(
                self, "导出成功",
                f"STL 文件已保存到:\n{filename}\n\n"
                f"顶点数: {len(self.vertices):,}\n"
                f"三角面片数: {len(self.faces):,}"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "导出失败", str(e))

    def _export_report(self):
        """导出测量报告"""
        if self.surface_area_value <= 0:
            QtWidgets.QMessageBox.warning(self, "错误", "请先计算表面积")
            return

        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出测量报告", "", "文本文件 (*.txt);;CSV 文件 (*.csv)"
        )
        if not filename:
            return

        try:
            from datetime import datetime
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if filename.endswith('.csv'):
                lines = [
                    "项目,值,单位",
                    f"测量时间,{now},",
                    f"数据尺寸,{self.work_data.shape},",
                    f"像素间距,\"{self.spacing}\",",
                    f"阈值下限,{self.lower_threshold_value.value()},",
                    f"阈值上限,{self.upper_threshold_value.value()},",
                    f"有效体素数,{self.voxel_count},",
                    f"表面积,{self.surface_area_value:.6f},",
                    f"体积(体素法),{self.volume_value:.6f},",
                    f"球度,{self._compute_sphericity():.6f},",
                    f"三角面片数,{len(self.faces)},",
                    f"顶点数,{len(self.vertices)},",
                ]
            else:
                lines = [
                    "=" * 50,
                    "  工业CT表面积测定报告",
                    "=" * 50,
                    f"  生成时间:     {now}",
                    "",
                    "--- 数据信息 ---",
                    f"  数据尺寸:     {self.work_data.shape}",
                    f"  像素间距:     {self.spacing}",
                    "",
                    "--- 阈值设定 ---",
                    f"  阈值范围:     [{self.lower_threshold_value.value()}, {self.upper_threshold_value.value()}]",
                    f"  等值面级别:   {self.level_slider.value() / 100:.2f}",
                    f"  Marching Cubes 步长: {self.step_spinbox.value()}",
                    f"  平滑:         {'是 (迭代' + str(self.smooth_iter_spinbox.value()) + '次)' if self.smooth_checkbox.isChecked() else '否'}",
                    "",
                    "--- 测量结果 ---",
                    f"  有效体素数:   {self.voxel_count:,}",
                    f"  表面积:       {self.surface_area_value:,.6f}",
                    f"  体积 (体素法): {self.volume_value:,.6f}",
                    f"  球度:         {self._compute_sphericity():.6f}",
                    "",
                    "--- 网格信息 ---",
                    f"  三角面片数:   {len(self.faces):,}",
                    f"  顶点数:       {len(self.vertices):,}",
                    "",
                    "=" * 50,
                ]

            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            QtWidgets.QMessageBox.information(
                self, "导出成功", f"报告已保存到:\n{filename}"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "导出失败", str(e))

    def closeEvent(self, event):
        """关闭对话框时清理VTK"""
        try:
            self.vtk_widget.GetRenderWindow().Finalize()
            del self.vtk_widget
        except Exception:
            pass
        super().closeEvent(event)

    def showEvent(self, event):
        """显示对话框时初始化VTK交互器"""
        super().showEvent(event)
        try:
            self.vtk_widget.GetRenderWindow().Render()
            interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
            if interactor:
                interactor.Initialize()
        except Exception:
            pass
