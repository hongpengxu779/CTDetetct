"""
投影相关操作（MIP / MinIP）

MIP  – Maximum Intensity Projection（最大密度投影）
MinIP – Minimum Intensity Projection（最小密度投影）

核心算法：
  沿指定轴对三维体数据取 np.max / np.min，得到一张 2D 投影图。

显示方式：
  投影结果是 2D 图像，用独立对话框窗口展示，支持窗宽窗位 + 缩放 + 保存。

支持 slab 投影：
  如果用户在 ROI 中选择了有效 3D 边界，则只对 ROI 范围内的数据做投影。
  未选 ROI 时，对全体数据做投影。

数据约定：体数据数组维度为 (z, y, x)
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui


# =====================================================================
#  投影预览对话框（独立窗口）
# =====================================================================
class ProjectionPreviewDialog(QtWidgets.QDialog):
    """用于展示 2D 投影图的独立窗口，支持窗宽窗位、缩放和保存。"""

    def __init__(self, title: str, image_2d: np.ndarray, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(600, 500)
        self.resize(900, 700)

        # 保留原始数据（float64 方便做窗宽窗位）
        self.raw_image = image_2d.astype(np.float64)
        self.data_min = float(self.raw_image.min())
        self.data_max = float(self.raw_image.max())

        # 默认窗宽窗位：全范围
        self.window_width = self.data_max - self.data_min if self.data_max > self.data_min else 1.0
        self.window_level = (self.data_max + self.data_min) / 2.0

        self._display_buffer = None  # 防止 QImage buffer 被 GC

        self._build_ui()
        self._fit_to_window()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # 图像显示区
        self.scene = QtWidgets.QGraphicsScene()
        self.view = QtWidgets.QGraphicsView(self.scene)
        self.view.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        self.view.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        self.view.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.pixmap_item = QtWidgets.QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        layout.addWidget(self.view, stretch=1)

        # 信息栏
        self.info_label = QtWidgets.QLabel()
        self.info_label.setAlignment(QtCore.Qt.AlignCenter)
        self.info_label.setStyleSheet("QLabel { color: #555; padding: 2px; }")
        layout.addWidget(self.info_label)

        # 窗宽窗位控制
        ww_wl_layout = QtWidgets.QHBoxLayout()

        ww_wl_layout.addWidget(QtWidgets.QLabel("窗宽:"))
        self.ww_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.ww_slider.setMinimum(1)
        self.ww_slider.setMaximum(max(1, int(self.data_max - self.data_min) * 2))
        self.ww_slider.setValue(int(self.window_width))
        self.ww_slider.valueChanged.connect(self._on_ww_wl_changed)
        ww_wl_layout.addWidget(self.ww_slider)
        self.ww_value_label = QtWidgets.QLabel(f"{int(self.window_width)}")
        self.ww_value_label.setMinimumWidth(60)
        ww_wl_layout.addWidget(self.ww_value_label)

        ww_wl_layout.addWidget(QtWidgets.QLabel("窗位:"))
        self.wl_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.wl_slider.setMinimum(int(self.data_min))
        self.wl_slider.setMaximum(max(int(self.data_min) + 1, int(self.data_max)))
        self.wl_slider.setValue(int(self.window_level))
        self.wl_slider.valueChanged.connect(self._on_ww_wl_changed)
        ww_wl_layout.addWidget(self.wl_slider)
        self.wl_value_label = QtWidgets.QLabel(f"{int(self.window_level)}")
        self.wl_value_label.setMinimumWidth(60)
        ww_wl_layout.addWidget(self.wl_value_label)

        layout.addLayout(ww_wl_layout)

        # 按钮栏
        btn_layout = QtWidgets.QHBoxLayout()

        fit_btn = QtWidgets.QPushButton("适应窗口")
        fit_btn.clicked.connect(self._fit_to_window)
        btn_layout.addWidget(fit_btn)

        reset_wl_btn = QtWidgets.QPushButton("重置窗宽窗位")
        reset_wl_btn.clicked.connect(self._reset_ww_wl)
        btn_layout.addWidget(reset_wl_btn)

        save_btn = QtWidgets.QPushButton("保存图像…")
        save_btn.clicked.connect(self._save_image)
        btn_layout.addWidget(save_btn)

        btn_layout.addStretch()

        close_btn = QtWidgets.QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _update_display(self):
        ww_min = self.window_level - self.window_width / 2.0
        ww_max = self.window_level + self.window_width / 2.0
        if ww_max <= ww_min:
            ww_max = ww_min + 1.0

        display = (self.raw_image - ww_min) / (ww_max - ww_min) * 255.0
        display = np.clip(display, 0, 255).astype(np.uint8)
        # 确保内存连续
        self._display_buffer = np.ascontiguousarray(display)

        h, w = self._display_buffer.shape
        qimg = QtGui.QImage(self._display_buffer.data, w, h, w,
                            QtGui.QImage.Format_Grayscale8)
        pixmap = QtGui.QPixmap.fromImage(qimg)
        self.pixmap_item.setPixmap(pixmap)
        self.scene.setSceneRect(self.pixmap_item.boundingRect())

        self.info_label.setText(
            f"图像大小: {w}\u00d7{h}  |  "
            f"数据范围: [{self.data_min:.1f}, {self.data_max:.1f}]  |  "
            f"窗宽: {int(self.window_width)}  窗位: {int(self.window_level)}"
        )

    def _on_ww_wl_changed(self):
        self.window_width = self.ww_slider.value()
        self.window_level = self.wl_slider.value()
        self.ww_value_label.setText(f"{int(self.window_width)}")
        self.wl_value_label.setText(f"{int(self.window_level)}")
        self._update_display()

    def _reset_ww_wl(self):
        self.window_width = self.data_max - self.data_min if self.data_max > self.data_min else 1.0
        self.window_level = (self.data_max + self.data_min) / 2.0
        self.ww_slider.setValue(int(self.window_width))
        self.wl_slider.setValue(int(self.window_level))

    def _fit_to_window(self):
        self._update_display()
        self.view.fitInView(self.scene.sceneRect(), QtCore.Qt.KeepAspectRatio)

    def _save_image(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "保存投影图像", "",
            "PNG 图像 (*.png);;TIFF 图像 (*.tif);;所有文件 (*)"
        )
        if path:
            pixmap = self.pixmap_item.pixmap()
            pixmap.save(path)
            QtWidgets.QMessageBox.information(self, "保存成功", f"已保存到:\n{path}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QtCore.QTimer.singleShot(0, lambda: self.view.fitInView(
            self.scene.sceneRect(), QtCore.Qt.KeepAspectRatio))


# =====================================================================
#  ProjectionOperations  Mixin
# =====================================================================
class ProjectionOperations:
    """投影操作类，作为 CTViewer4 的 Mixin 使用。"""

    # ----------------------- public API -----------------------
    def create_mip_projection(self, axis: int, use_roi: bool = True):
        """创建最大密度投影 (MIP)"""
        self._do_projection('mip', axis, use_roi)

    def create_minip_projection(self, axis: int, use_roi: bool = True):
        """创建最小密度投影 (MinIP)"""
        self._do_projection('minip', axis, use_roi)

    # ----------------------- core -----------------------
    def _do_projection(self, mode: str, axis: int, use_roi: bool):
        """
        执行投影计算并弹出预览窗口。

        参数
        ----
        mode : 'mip' | 'minip'
        axis : 0(Z) / 1(Y) / 2(X)
        use_roi : 是否优先使用 ROI slab
        """
        if not hasattr(self, 'raw_array') or self.raw_array is None:
            QtWidgets.QMessageBox.warning(self, "提示", "请先导入数据")
            return

        vol = self.raw_array  # (z, y, x)

        # 若有 ROI，裁剪 slab
        slab = None
        if use_roi:
            slab = self._get_roi_slab(vol)
            if slab is not None:
                vol = slab

        axis_label = {0: 'Z (Axial)', 1: 'Y (Coronal)', 2: 'X (Sagittal)'}.get(axis, str(axis))
        mode_label = 'MIP (最大密度投影)' if mode == 'mip' else 'MinIP (最小密度投影)'

        try:
            if mode == 'mip':
                proj2d = np.max(vol, axis=axis)
            else:
                proj2d = np.min(vol, axis=axis)

            # proj2d 的维度含义:
            #   axis=0  沿Z投影  结果 (y, x)  俯视图
            #   axis=1  沿Y投影  结果 (z, x)  冠状位
            #   axis=2  沿X投影  结果 (z, y)  矢状位

            shape_info = f"{proj2d.shape[0]}\u00d7{proj2d.shape[1]}"
            roi_tag = " [ROI slab]" if (use_roi and slab is not None) else ""

            title = f"{mode_label} \u2014 沿{axis_label}  ({shape_info}){roi_tag}"

            # 弹出预览窗口
            dialog = ProjectionPreviewDialog(title, proj2d, parent=self)
            # 保持引用防止被 GC
            if not hasattr(self, '_projection_dialogs'):
                self._projection_dialogs = []
            self._projection_dialogs.append(dialog)
            dialog.show()

        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "错误", f"生成投影失败：{str(e)}")

    # ----------------------- ROI slab -----------------------
    def _get_roi_slab(self, vol: np.ndarray) -> Optional[np.ndarray]:
        """
        如果存在有效 ROI 3D 边界，返回裁剪后的 slab；否则返回 None。

        兼容两种 roi_3d_bounds 格式:
        - list/tuple: [x_min, x_max, y_min, y_max, z_min, z_max]
        - dict:       {'x_min':, 'x_max':, 'y_min':, 'y_max':, 'z_min':, 'z_max':}
        """
        if not hasattr(self, 'roi_3d_bounds') or self.roi_3d_bounds is None:
            return None

        b = self.roi_3d_bounds

        if isinstance(b, dict):
            try:
                x_min, x_max = int(b['x_min']), int(b['x_max'])
                y_min, y_max = int(b['y_min']), int(b['y_max'])
                z_min, z_max = int(b['z_min']), int(b['z_max'])
            except (KeyError, TypeError):
                return None
        elif isinstance(b, (list, tuple)) and len(b) == 6:
            x_min, x_max, y_min, y_max, z_min, z_max = [int(v) for v in b]
        else:
            return None

        # 防御性裁剪
        z_min = max(0, min(z_min, vol.shape[0] - 1))
        z_max = max(z_min, min(z_max, vol.shape[0] - 1))
        y_min = max(0, min(y_min, vol.shape[1] - 1))
        y_max = max(y_min, min(y_max, vol.shape[1] - 1))
        x_min = max(0, min(x_min, vol.shape[2] - 1))
        x_max = max(x_min, min(x_max, vol.shape[2] - 1))

        if z_min >= z_max or y_min >= y_max or x_min >= x_max:
            return None

        return vol[z_min:z_max + 1, y_min:y_max + 1, x_min:x_max + 1]
