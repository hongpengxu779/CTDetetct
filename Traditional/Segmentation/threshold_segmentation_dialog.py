# -*- coding: utf-8 -*-
"""阈值分割对话框 — 带直方图实时预览"""

import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui

# matplotlib 嵌入 Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class HistogramCanvas(FigureCanvas):
    """嵌入式直方图画布，带阈值线实时更新"""

    def __init__(self, parent=None, width=5, height=2.6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

        # 缓存
        self._hist_counts = None
        self._hist_edges = None
        self._lower_line = None
        self._upper_line = None
        self._fill = None

    # ---------- public API ----------
    def set_histogram(self, array: np.ndarray, bins: int = 256):
        """计算并绘制灰度直方图（下采样大数组以加速）"""
        self.ax.clear()

        # 下采样：若体素数 > 5M 则随机采样 5M 点
        flat = array.ravel()
        if flat.size > 5_000_000:
            rng = np.random.default_rng(42)
            flat = rng.choice(flat, size=5_000_000, replace=False)

        counts, edges = np.histogram(flat, bins=bins)
        self._hist_counts = counts
        self._hist_edges = edges
        centers = 0.5 * (edges[:-1] + edges[1:])

        self.ax.bar(centers, counts, width=(edges[1] - edges[0]),
                    color='#78909C', edgecolor='none', alpha=0.85)
        self.ax.set_xlabel('灰度值', fontsize=9)
        self.ax.set_ylabel('频数', fontsize=9)
        self.ax.set_title('灰度直方图', fontsize=10)
        self.ax.ticklabel_format(axis='y', style='sci', scilimits=(0, 0))
        self.fig.tight_layout()
        self.draw()

    def update_threshold_lines(self, lower: float, upper: float):
        """更新两条阈值竖线和填充区域（高效局部刷新）"""
        # 移除旧元素
        if self._lower_line is not None:
            self._lower_line.remove()
        if self._upper_line is not None:
            self._upper_line.remove()
        if self._fill is not None:
            self._fill.remove()

        ymin, ymax = self.ax.get_ylim()
        self._lower_line = self.ax.axvline(lower, color='#E53935', linewidth=1.5,
                                           linestyle='--', label=f'下限 {lower:.0f}')
        self._upper_line = self.ax.axvline(upper, color='#1E88E5', linewidth=1.5,
                                           linestyle='--', label=f'上限 {upper:.0f}')
        self._fill = self.ax.axvspan(lower, upper, alpha=0.15, color='#43A047')
        self.ax.legend(fontsize=8, loc='upper right')
        self.draw_idle()  # draw_idle 比 draw 更高效，仅在空闲时刷新

    def get_data_range(self):
        """返回直方图数据的 (min, max)"""
        if self._hist_edges is not None:
            return float(self._hist_edges[0]), float(self._hist_edges[-1])
        return 0.0, 1.0


class ThresholdSegmentationDialog(QtWidgets.QDialog):
    """手动阈值分割对话框
    
    功能
    ----
    - 显示灰度直方图，直观选择阈值范围
    - 支持单阈值（二分类）和双阈值（区间提取）
    - 实时预览阈值线在直方图上的位置
    - 分割结果可选择融合到原始图像显示
    """

    def __init__(self, parent=None, current_data=None):
        super().__init__(parent)
        self.parent_viewer = parent
        self.current_data = current_data
        self.setWindowTitle("传统分割检测 - 阈值分割")
        self.setMinimumWidth(680)
        self.setMinimumHeight(580)

        self._build_ui()
        self._connect_signals()

        # 如果有数据，初始化直方图
        if current_data is not None and 'array' in current_data:
            arr = current_data['array']
            self.histogram_canvas.set_histogram(arr)
            dmin, dmax = float(arr.min()), float(arr.max())
            self._data_min = dmin
            self._data_max = dmax
            self._init_sliders(dmin, dmax)
        else:
            self._data_min = 0
            self._data_max = 65535

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        # ---- 数据状态 ----
        if self.current_data is not None:
            info = QtWidgets.QLabel("✅ 将对当前已加载的数据进行阈值分割")
            info.setStyleSheet("color:#2196F3; font-weight:bold; padding:5px;")
        else:
            info = QtWidgets.QLabel("⚠ 请先在主界面加载数据")
            info.setStyleSheet("color:#F44336; font-weight:bold; padding:5px;")
        main_layout.addWidget(info)

        # ---- 直方图 ----
        hist_group = QtWidgets.QGroupBox("灰度直方图（红线=下限，蓝线=上限，绿色=选中区间）")
        hist_layout = QtWidgets.QVBoxLayout(hist_group)
        self.histogram_canvas = HistogramCanvas(self)
        hist_layout.addWidget(self.histogram_canvas)
        main_layout.addWidget(hist_group)

        # ---- 阈值参数 ----
        param_group = QtWidgets.QGroupBox("阈值参数")
        param_grid = QtWidgets.QGridLayout(param_group)
        row = 0

        # 分割模式
        param_grid.addWidget(QtWidgets.QLabel("分割模式:"), row, 0)
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems([
            "双阈值（区间提取）",
            "单阈值（大于下限即为前景）",
        ])
        param_grid.addWidget(self.mode_combo, row, 1, 1, 3)
        row += 1

        # 下阈值
        param_grid.addWidget(QtWidgets.QLabel("下阈值:"), row, 0)
        self.lower_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.lower_slider.setMinimum(0)
        self.lower_slider.setMaximum(10000)  # 映射到 0‑10000 再换算
        param_grid.addWidget(self.lower_slider, row, 1)
        self.lower_spin = QtWidgets.QDoubleSpinBox()
        self.lower_spin.setDecimals(1)
        self.lower_spin.setMinimumWidth(100)
        param_grid.addWidget(self.lower_spin, row, 2)
        row += 1

        # 上阈值
        self.upper_label = QtWidgets.QLabel("上阈值:")
        param_grid.addWidget(self.upper_label, row, 0)
        self.upper_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.upper_slider.setMinimum(0)
        self.upper_slider.setMaximum(10000)
        param_grid.addWidget(self.upper_slider, row, 1)
        self.upper_spin = QtWidgets.QDoubleSpinBox()
        self.upper_spin.setDecimals(1)
        self.upper_spin.setMinimumWidth(100)
        param_grid.addWidget(self.upper_spin, row, 2)
        row += 1

        # 前景/背景值
        val_layout = QtWidgets.QHBoxLayout()
        val_layout.addWidget(QtWidgets.QLabel("前景值:"))
        self.fg_spin = QtWidgets.QSpinBox()
        self.fg_spin.setRange(0, 65535)
        self.fg_spin.setValue(255)
        val_layout.addWidget(self.fg_spin)
        val_layout.addSpacing(20)
        val_layout.addWidget(QtWidgets.QLabel("背景值:"))
        self.bg_spin = QtWidgets.QSpinBox()
        self.bg_spin.setRange(0, 65535)
        self.bg_spin.setValue(0)
        val_layout.addWidget(self.bg_spin)
        val_layout.addStretch()
        param_grid.addLayout(val_layout, row, 0, 1, 3)
        row += 1

        # 像素统计
        self.stats_label = QtWidgets.QLabel("")
        self.stats_label.setStyleSheet("color:#666; font-size:9pt; padding:4px;")
        param_grid.addWidget(self.stats_label, row, 0, 1, 3)
        main_layout.addWidget(param_group)

        # ---- 显示选项 ----
        disp_group = QtWidgets.QGroupBox("显示选项")
        disp_layout = QtWidgets.QVBoxLayout(disp_group)

        self.overlay_cb = QtWidgets.QCheckBox("与原始图像融合显示（推荐）")
        self.overlay_cb.setChecked(True)
        disp_layout.addWidget(self.overlay_cb)

        ov_layout = QtWidgets.QHBoxLayout()
        ov_layout.addWidget(QtWidgets.QLabel("透明度:"))
        self.alpha_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.alpha_slider.setRange(10, 100)
        self.alpha_slider.setValue(50)
        ov_layout.addWidget(self.alpha_slider)
        self.alpha_label = QtWidgets.QLabel("50%")
        self.alpha_slider.valueChanged.connect(lambda v: self.alpha_label.setText(f"{v}%"))
        ov_layout.addWidget(self.alpha_label)
        ov_layout.addSpacing(10)
        ov_layout.addWidget(QtWidgets.QLabel("颜色:"))
        self.color_combo = QtWidgets.QComboBox()
        self.color_combo.addItems(["红色", "绿色", "蓝色", "黄色", "青色", "品红"])
        self.color_combo.setCurrentIndex(1)
        ov_layout.addWidget(self.color_combo)
        disp_layout.addLayout(ov_layout)
        main_layout.addWidget(disp_group)

        # ---- 按钮 ----
        main_layout.addStretch()
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        self.run_btn = QtWidgets.QPushButton("🔬 开始分割")
        self.run_btn.setMinimumWidth(110)
        self.run_btn.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(self.run_btn)
        self.cancel_btn = QtWidgets.QPushButton("取消")
        self.cancel_btn.setMinimumWidth(90)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_layout)

    # ------------------------------------------------------------------ 信号
    def _connect_signals(self):
        self.lower_slider.valueChanged.connect(self._on_lower_slider)
        self.upper_slider.valueChanged.connect(self._on_upper_slider)
        self.lower_spin.valueChanged.connect(self._on_lower_spin)
        self.upper_spin.valueChanged.connect(self._on_upper_spin)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)

    # ------------------------------------------------------------------ 初始化
    def _init_sliders(self, dmin, dmax):
        """根据数据范围初始化滑块和输入框"""
        self.lower_spin.setRange(dmin, dmax)
        self.upper_spin.setRange(dmin, dmax)

        # 默认：下限=25% 分位，上限=75% 分位
        default_lower = dmin + (dmax - dmin) * 0.25
        default_upper = dmin + (dmax - dmin) * 0.75

        # 阻塞信号避免初始化时反复触发
        for w in (self.lower_slider, self.upper_slider,
                  self.lower_spin, self.upper_spin):
            w.blockSignals(True)

        self.lower_spin.setValue(default_lower)
        self.upper_spin.setValue(default_upper)
        self.lower_slider.setValue(self._val_to_slider(default_lower))
        self.upper_slider.setValue(self._val_to_slider(default_upper))

        for w in (self.lower_slider, self.upper_slider,
                  self.lower_spin, self.upper_spin):
            w.blockSignals(False)

        self._refresh_preview()

    # ------------------------------------------------------------------ 映射
    def _val_to_slider(self, val):
        """将实际灰度值映射到 0‑10000 滑块整数"""
        span = self._data_max - self._data_min
        if span == 0:
            return 0
        return int((val - self._data_min) / span * 10000)

    def _slider_to_val(self, s):
        """将滑块整数映射为实际灰度值"""
        span = self._data_max - self._data_min
        return self._data_min + s / 10000.0 * span

    # ------------------------------------------------------------------ 回调
    def _on_lower_slider(self, s):
        val = self._slider_to_val(s)
        self.lower_spin.blockSignals(True)
        self.lower_spin.setValue(val)
        self.lower_spin.blockSignals(False)
        # 保证下限 ≤ 上限
        if val > self.upper_spin.value():
            self.upper_spin.setValue(val)
        self._refresh_preview()

    def _on_upper_slider(self, s):
        val = self._slider_to_val(s)
        self.upper_spin.blockSignals(True)
        self.upper_spin.setValue(val)
        self.upper_spin.blockSignals(False)
        if val < self.lower_spin.value():
            self.lower_spin.setValue(val)
        self._refresh_preview()

    def _on_lower_spin(self, val):
        self.lower_slider.blockSignals(True)
        self.lower_slider.setValue(self._val_to_slider(val))
        self.lower_slider.blockSignals(False)
        if val > self.upper_spin.value():
            self.upper_spin.setValue(val)
        self._refresh_preview()

    def _on_upper_spin(self, val):
        self.upper_slider.blockSignals(True)
        self.upper_slider.setValue(self._val_to_slider(val))
        self.upper_slider.blockSignals(False)
        if val < self.lower_spin.value():
            self.lower_spin.setValue(val)
        self._refresh_preview()

    def _on_mode_changed(self, idx):
        is_dual = (idx == 0)
        self.upper_label.setVisible(is_dual)
        self.upper_slider.setVisible(is_dual)
        self.upper_spin.setVisible(is_dual)
        self._refresh_preview()

    # ------------------------------------------------------------------ 预览
    def _refresh_preview(self):
        """更新直方图阈值线 + 像素统计"""
        lower = self.lower_spin.value()
        upper = self.upper_spin.value() if self.mode_combo.currentIndex() == 0 else self._data_max

        self.histogram_canvas.update_threshold_lines(lower, upper)

        if self.current_data is not None and 'array' in self.current_data:
            arr = self.current_data['array']
            total = arr.size
            selected = int(np.count_nonzero((arr >= lower) & (arr <= upper)))
            pct = selected / total * 100 if total > 0 else 0
            self.stats_label.setText(
                f"选中体素: {selected:,} / {total:,}  ({pct:.2f}%)")
        else:
            self.stats_label.setText("")

    # ------------------------------------------------------------------ 验证
    def _validate_and_accept(self):
        if self.current_data is None:
            QtWidgets.QMessageBox.warning(self, "输入错误",
                                          "当前没有已加载的数据！请先在主界面加载数据。")
            return

        lower = self.lower_spin.value()
        upper = self.upper_spin.value() if self.mode_combo.currentIndex() == 0 else self._data_max
        if lower > upper:
            QtWidgets.QMessageBox.warning(self, "参数错误", "下阈值不能大于上阈值。")
            return

        self.accept()

    # ------------------------------------------------------------------ 参数
    def get_parameters(self):
        """返回参数字典，供外部执行分割"""
        color_map = {
            "红色": (255, 0, 0),
            "绿色": (0, 255, 0),
            "蓝色": (0, 0, 255),
            "黄色": (255, 255, 0),
            "青色": (0, 255, 255),
            "品红": (255, 0, 255),
        }

        is_dual = (self.mode_combo.currentIndex() == 0)
        return {
            'current_data': self.current_data,
            'lower_threshold': self.lower_spin.value(),
            'upper_threshold': self.upper_spin.value() if is_dual else self._data_max,
            'mode': 'dual' if is_dual else 'single',
            'foreground_value': self.fg_spin.value(),
            'background_value': self.bg_spin.value(),
            'overlay_with_original': self.overlay_cb.isChecked(),
            'overlay_alpha': self.alpha_slider.value() / 100.0,
            'overlay_color': color_map[self.color_combo.currentText()],
        }
