"""
表面积测定操作模块
提供表面积测定功能入口，作为 CTViewer4 的 Mixin 使用
"""

from PyQt5 import QtWidgets


class SurfaceAreaOperations:
    """表面积测定操作类，作为Mixin使用"""

    def run_surface_area_measurement(self):
        """启动表面积测定功能"""
        # 检查数据是否可用
        if not hasattr(self, 'array') or self.array is None:
            QtWidgets.QMessageBox.warning(
                self,
                "数据不可用",
                "当前没有可用的体数据。\n\n"
                "请先通过 [文件] → [导入文件] 加载 CT 数据。"
            )
            return

        # 检查数据是否为3D
        if len(self.array.shape) != 3:
            QtWidgets.QMessageBox.warning(
                self,
                "数据格式错误",
                f"表面积测定需要 3D 体数据，\n"
                f"当前数据维度: {self.array.shape}"
            )
            return

        # 获取 ROI 边界（如果有）
        roi_bounds = None
        if hasattr(self, 'roi_3d_bounds') and self.roi_3d_bounds is not None:
            roi_bounds = self.roi_3d_bounds

        # 获取 spacing
        spacing = (1.0, 1.0, 1.0)
        if hasattr(self, 'spacing') and self.spacing is not None:
            sp = self.spacing
            if len(sp) >= 3:
                spacing = (float(sp[0]), float(sp[1]), float(sp[2]))
            elif len(sp) == 2:
                spacing = (float(sp[0]), float(sp[1]), 1.0)

        # 打开表面积测定对话框
        from .surface_area_dialog import SurfaceAreaDialog

        dialog = SurfaceAreaDialog(
            parent=self,
            volume_data=self.array,
            spacing=spacing,
            roi_bounds=roi_bounds
        )
        dialog.exec_()
