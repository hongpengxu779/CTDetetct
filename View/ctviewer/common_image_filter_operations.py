"""
Common Image Filters 操作入口（UI + 调度）
"""

import os
import tempfile
from datetime import datetime

import numpy as np
import SimpleITK as sitk
from PyQt5 import QtWidgets, QtCore

from Traditional.CommonImageFilters.common_image_filters_engine import CommonImageFiltersEngine


class CommonImageFilterOperations:
    """Common Image Filters Mixin"""

    FILTER_SPECS = {
        "connected_component": {
            "title": "连通域标记",
            "fields": [
                {"name": "fully_connected", "label": "完全连通邻接", "type": "bool", "default": False},
            ],
        },
        "scalar_connected_component": {
            "title": "灰度连通域",
            "fields": [
                {"name": "distance_threshold", "label": "强度差阈值", "type": "float", "default": 10.0, "min": 0.0, "max": 1e6, "decimals": 4},
                {"name": "fully_connected", "label": "完全连通邻接", "type": "bool", "default": False},
            ],
        },
        "relabel_components": {
            "title": "按大小重排标签",
            "fields": [
                {"name": "minimum_object_size", "label": "最小体素数过滤", "type": "int", "default": 0, "min": 0, "max": 2_000_000_000},
                {"name": "export_stats", "label": "导出对象统计 CSV", "type": "bool", "default": False},
            ],
        },
        "convolution": {
            "title": "空间域卷积",
            "fields": [
                {"name": "kernel_text", "label": "卷积核（2D/3D）", "type": "text", "default": "0 -1 0; -1 5 -1; 0 -1 0"},
            ],
        },
        "fft_convolution": {
            "title": "频域卷积(FFT)",
            "fields": [
                {"name": "kernel_text", "label": "卷积核（2D/3D）", "type": "text", "default": "1 1 1; 1 1 1; 1 1 1"},
            ],
        },
        "correlation_ncc": {
            "title": "归一化相关(NCC)",
            "fields": [
                {"name": "template_text", "label": "模板（2D/3D）", "type": "text", "default": "1 0 -1; 1 0 -1; 1 0 -1"},
            ],
        },
        "fft_correlation_ncc": {
            "title": "频域归一化相关(FFT NCC)",
            "fields": [
                {"name": "template_text", "label": "模板（2D/3D）", "type": "text", "default": "1 0 -1; 1 0 -1; 1 0 -1"},
            ],
        },
        "streaming_fft_correlation_ncc": {
            "title": "流式频域归一化相关",
            "fields": [
                {"name": "template_text", "label": "模板（2D/3D）", "type": "text", "default": "1 0 -1; 1 0 -1; 1 0 -1"},
                {"name": "chunk_depth", "label": "流式块深度 (Z)", "type": "int", "default": 64, "min": 8, "max": 4096},
            ],
        },
        "signed_maurer_distance_map": {
            "title": "有符号 Maurer 距离图",
            "fields": [
                {"name": "squared_distance", "label": "平方距离", "type": "bool", "default": False},
                {"name": "inside_is_positive", "label": "内部为正", "type": "bool", "default": False},
                {"name": "use_image_spacing", "label": "按 spacing 计算", "type": "bool", "default": True},
                {"name": "clamp_nonnegative", "label": "去负值（截断到 >=0）", "type": "bool", "default": False},
            ],
        },
        "danielsson_distance_map": {
            "title": "Danielsson 距离图",
            "fields": [
                {"name": "input_is_binary", "label": "输入视为二值", "type": "bool", "default": True},
                {"name": "squared_distance", "label": "平方距离", "type": "bool", "default": False},
                {"name": "use_image_spacing", "label": "按 spacing 计算", "type": "bool", "default": True},
                {"name": "rescale_to_uchar", "label": "重标定到 uchar", "type": "bool", "default": False},
            ],
        },
        "canny": {
            "title": "Canny 边缘检测",
            "fields": [
                {"name": "variance", "label": "高斯方差", "type": "float", "default": 1.0, "min": 1e-6, "max": 1e6, "decimals": 6},
                {"name": "lower_threshold", "label": "低阈值", "type": "float", "default": 10.0, "min": 0.0, "max": 1e9, "decimals": 6},
                {"name": "upper_threshold", "label": "高阈值", "type": "float", "default": 30.0, "min": 0.0, "max": 1e9, "decimals": 6},
            ],
        },
        "sobel": {
            "title": "Sobel 梯度边缘",
            "fields": [],
        },
        "gradient_magnitude": {
            "title": "梯度幅值",
            "fields": [
                {"name": "use_image_spacing", "label": "按物理 spacing", "type": "bool", "default": True},
            ],
        },
        "gradient_magnitude_recursive_gaussian": {
            "title": "递归高斯梯度幅值",
            "fields": [
                {"name": "sigma", "label": "Sigma", "type": "float", "default": 1.0, "min": 1e-6, "max": 1e6, "decimals": 6},
                {"name": "use_image_spacing", "label": "按物理 spacing", "type": "bool", "default": True},
            ],
        },
        "derivative": {
            "title": "导数",
            "fields": [
                {"name": "direction", "label": "方向 (0:X,1:Y,2:Z)", "type": "int", "default": 0, "min": 0, "max": 2},
                {"name": "order", "label": "阶数", "type": "int", "default": 1, "min": 1, "max": 5},
                {"name": "use_image_spacing", "label": "按物理 spacing", "type": "bool", "default": True},
            ],
        },
        "higher_order_accurate_derivative": {
            "title": "高阶精确导数",
            "fields": [
                {"name": "direction", "label": "方向 (0:X,1:Y,2:Z)", "type": "int", "default": 0, "min": 0, "max": 2},
                {"name": "order", "label": "阶数", "type": "int", "default": 1, "min": 1, "max": 5},
                {"name": "use_image_spacing", "label": "按物理 spacing", "type": "bool", "default": True},
            ],
        },
        "hessian_eigen_analysis": {
            "title": "Hessian 特征值分析",
            "fields": [
                {"name": "sigma", "label": "Hessian Sigma", "type": "float", "default": 1.0, "min": 1e-6, "max": 1e6, "decimals": 6},
            ],
        },
        "laplacian_of_gaussian": {
            "title": "高斯拉普拉斯(LoG)",
            "fields": [
                {"name": "sigma", "label": "LoG Sigma", "type": "float", "default": 1.0, "min": 1e-6, "max": 1e6, "decimals": 6},
                {"name": "use_image_spacing", "label": "按物理 spacing", "type": "bool", "default": True},
            ],
        },
    }

    def _ensure_common_filter_variables(self):
        """确保通用滤波输出变量存在。"""
        if not hasattr(self, "common_filter_outputs") or not isinstance(self.common_filter_outputs, dict):
            self.common_filter_outputs = {
                "相关": {
                    "归一化相关(NCC)": [],
                    "频域归一化相关(FFT NCC)": [],
                    "流式频域归一化相关": [],
                }
            }

        if not hasattr(self, "correlation_ncc_output"):
            self.correlation_ncc_output = None
        if not hasattr(self, "fft_correlation_ncc_output"):
            self.fft_correlation_ncc_output = None
        if not hasattr(self, "streaming_fft_correlation_ncc_output"):
            self.streaming_fft_correlation_ncc_output = None

        if not hasattr(self, "correlation_ncc_outputs"):
            self.correlation_ncc_outputs = []
        if not hasattr(self, "fft_correlation_ncc_outputs"):
            self.fft_correlation_ncc_outputs = []
        if not hasattr(self, "streaming_fft_correlation_ncc_outputs"):
            self.streaming_fft_correlation_ncc_outputs = []

    def _ensure_input_image(self):
        if hasattr(self, "image") and self.image is not None:
            return sitk.Cast(self.image, sitk.sitkFloat32)

        if not hasattr(self, "array") or self.array is None:
            QtWidgets.QMessageBox.warning(self, "警告", "请先加载数据")
            return None

        img = sitk.GetImageFromArray(self.array.astype(np.float32))
        if hasattr(self, "spacing") and self.spacing is not None:
            try:
                img.SetSpacing(tuple(float(v) for v in self.spacing))
            except Exception:
                pass
        return img

    def _image_to_view_array(self, image: sitk.Image) -> np.ndarray:
        arr = sitk.GetArrayFromImage(image)

        if np.issubdtype(arr.dtype, np.integer):
            if arr.min() >= 0 and arr.max() <= 65535:
                return arr.astype(np.uint16)

        arr = arr.astype(np.float32)
        amin = float(np.min(arr))
        amax = float(np.max(arr))
        if amax <= amin:
            return np.zeros_like(arr, dtype=np.uint16)

        scaled = (arr - amin) / (amax - amin)
        return np.clip(scaled * 65535.0, 0, 65535).astype(np.uint16)

    def _save_common_filter_output(self, group_name: str, method_title: str, result_image: sitk.Image):
        """将结果保存为图层与层级输出变量。"""
        self._ensure_common_filter_variables()
        if group_name not in self.common_filter_outputs:
            self.common_filter_outputs[group_name] = {}

        timestamp = datetime.now().strftime("%H%M%S")
        layer_name = f"通用滤波/{group_name}/{method_title}_{timestamp}"
        layer_array = self._image_to_view_array(result_image)

        data_item = {
            "image": result_image,
            "array": layer_array,
            "shape": layer_array.shape,
            "spacing": result_image.GetSpacing(),
            "rgb_array": None,
            "is_segmentation": False,
        }

        method_store = self.common_filter_outputs[group_name].setdefault(method_title, [])
        method_store.append(data_item)

        if method_title == "归一化相关(NCC)":
            self.correlation_ncc_output = data_item
            self.correlation_ncc_outputs.append(data_item)
        elif method_title == "频域归一化相关(FFT NCC)":
            self.fft_correlation_ncc_output = data_item
            self.fft_correlation_ncc_outputs.append(data_item)
        elif method_title == "流式频域归一化相关":
            self.streaming_fft_correlation_ncc_output = data_item
            self.streaming_fft_correlation_ncc_outputs.append(data_item)

        if hasattr(self, "add_data_to_list"):
            self.add_data_to_list(layer_name, data_item)

        return layer_name, data_item

    def _save_and_show_result_as_layer(self, group_name: str, method_title: str, result_image: sitk.Image, show_message: bool = True):
        layer_name, data_item = self._save_common_filter_output(group_name, method_title, result_image)

        if hasattr(self, "switch_to_data"):
            self.switch_to_data(data_item, layer_name)
        else:
            self._apply_result_image(result_image, method_title)

        if show_message:
            QtWidgets.QMessageBox.information(self, "完成", f"{method_title} 执行完成\n已输出新图层：{layer_name}")

    def _apply_result_image(self, result_image: sitk.Image, title: str):
        self.image = result_image
        self.array = self._image_to_view_array(result_image)
        self.raw_array = self.array
        self.is_segmentation = False
        self.update_viewers()
        QtWidgets.QMessageBox.information(self, "完成", f"{title} 执行完成")

    def _build_param_dialog(self, title, fields):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(title)
        layout = QtWidgets.QFormLayout(dialog)

        widgets = {}
        for field in fields:
            t = field["type"]
            name = field["name"]
            label = field["label"]
            default = field.get("default")

            if t == "bool":
                w = QtWidgets.QCheckBox()
                w.setChecked(bool(default))
                layout.addRow(label, w)
            elif t == "int":
                w = QtWidgets.QSpinBox()
                w.setRange(field.get("min", -2147483647), field.get("max", 2147483647))
                w.setValue(int(default))
                layout.addRow(label, w)
            elif t == "float":
                w = QtWidgets.QDoubleSpinBox()
                w.setRange(field.get("min", -1e12), field.get("max", 1e12))
                w.setDecimals(field.get("decimals", 6))
                w.setSingleStep(field.get("step", 0.1))
                w.setValue(float(default))
                layout.addRow(label, w)
            elif t == "text":
                w = QtWidgets.QTextEdit()
                w.setMinimumHeight(100)
                w.setPlainText(str(default or ""))
                layout.addRow(label, w)
            else:
                continue

            widgets[name] = (t, w)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return None

        values = {}
        for name, (t, w) in widgets.items():
            if t == "bool":
                values[name] = w.isChecked()
            elif t == "int":
                values[name] = int(w.value())
            elif t == "float":
                values[name] = float(w.value())
            elif t == "text":
                values[name] = w.toPlainText().strip()
        return values

    def run_common_image_filter(self, key: str):
        self._ensure_common_filter_variables()

        if key not in self.FILTER_SPECS:
            QtWidgets.QMessageBox.warning(self, "错误", f"未知算法键: {key}")
            return

        input_image = self._ensure_input_image()
        if input_image is None:
            return

        spec = self.FILTER_SPECS[key]
        params = self._build_param_dialog(spec["title"], spec.get("fields", []))
        if params is None:
            return

        progress = QtWidgets.QProgressDialog(f"正在执行 {spec['title']}...", None, 0, 0, self)
        progress.setWindowTitle("处理中")
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.show()
        QtWidgets.QApplication.processEvents()

        try:
            if key == "connected_component":
                result = CommonImageFiltersEngine.connected_component(input_image, **params)
                self._save_and_show_result_as_layer("连通域", spec["title"], result)

            elif key == "scalar_connected_component":
                result = CommonImageFiltersEngine.scalar_connected_component(input_image, **params)
                self._save_and_show_result_as_layer("连通域", spec["title"], result)

            elif key == "relabel_components":
                export_path = ""
                if params.get("export_stats", False):
                    export_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                        self, "保存对象统计", "component_stats.csv", "CSV 文件 (*.csv)"
                    )
                result, voxel_stats = CommonImageFiltersEngine.relabel_components(
                    input_image,
                    minimum_object_size=params.get("minimum_object_size", 0),
                    export_stats_path=export_path,
                )
                self._save_and_show_result_as_layer("连通域", spec["title"], result, show_message=False)
                QtWidgets.QMessageBox.information(
                    self,
                    "Relabel 统计",
                    f"对象数量: {len(voxel_stats)}\n"
                    f"最大对象体素数: {max(voxel_stats.values()) if voxel_stats else 0}\n"
                    f"统计导出: {export_path if export_path else '未导出'}",
                )

            elif key == "convolution":
                result = CommonImageFiltersEngine.convolution(input_image, params.get("kernel_text", ""))
                self._save_and_show_result_as_layer("卷积与相关", spec["title"], result)

            elif key == "fft_convolution":
                result = CommonImageFiltersEngine.fft_convolution(input_image, params.get("kernel_text", ""))
                self._save_and_show_result_as_layer("卷积与相关", spec["title"], result)

            elif key == "correlation_ncc":
                result = CommonImageFiltersEngine.correlation_ncc(input_image, params.get("template_text", ""))
                self._save_and_show_result_as_layer("相关", spec["title"], result)

            elif key == "fft_correlation_ncc":
                result = CommonImageFiltersEngine.fft_correlation_ncc(input_image, params.get("template_text", ""))
                self._save_and_show_result_as_layer("相关", spec["title"], result)

            elif key == "streaming_fft_correlation_ncc":
                result = CommonImageFiltersEngine.streaming_fft_correlation_ncc(
                    input_image,
                    template_text=params.get("template_text", ""),
                    chunk_depth=params.get("chunk_depth", 64),
                )
                self._save_and_show_result_as_layer("相关", spec["title"], result)

            elif key == "signed_maurer_distance_map":
                result = CommonImageFiltersEngine.signed_maurer_distance_map(input_image, **params)
                self._save_and_show_result_as_layer("距离图", spec["title"], result)

            elif key == "danielsson_distance_map":
                result = CommonImageFiltersEngine.danielsson_distance_map(input_image, **params)
                self._save_and_show_result_as_layer("距离图", spec["title"], result)

            elif key == "canny":
                result = CommonImageFiltersEngine.canny(input_image, **params)
                self._save_and_show_result_as_layer("边缘检测", spec["title"], result)

            elif key == "sobel":
                result = CommonImageFiltersEngine.sobel(input_image)
                self._save_and_show_result_as_layer("边缘检测", spec["title"], result)

            elif key == "gradient_magnitude":
                result = CommonImageFiltersEngine.gradient_magnitude(input_image, **params)
                self._save_and_show_result_as_layer("梯度与导数", spec["title"], result)

            elif key == "gradient_magnitude_recursive_gaussian":
                result = CommonImageFiltersEngine.gradient_magnitude_recursive_gaussian(input_image, **params)
                self._save_and_show_result_as_layer("梯度与导数", spec["title"], result)

            elif key == "derivative":
                result = CommonImageFiltersEngine.derivative(input_image, **params)
                self._save_and_show_result_as_layer("梯度与导数", spec["title"], result)

            elif key == "higher_order_accurate_derivative":
                result = CommonImageFiltersEngine.higher_order_accurate_derivative(input_image, **params)
                self._save_and_show_result_as_layer("梯度与导数", spec["title"], result)

            elif key == "hessian_eigen_analysis":
                e1, e2, e3 = CommonImageFiltersEngine.hessian_eigen_analysis(input_image, sigma=params.get("sigma", 1.0))

                temp_dir = tempfile.gettempdir()
                p1 = os.path.join(temp_dir, "hessian_eigen_1.nii.gz")
                p2 = os.path.join(temp_dir, "hessian_eigen_2.nii.gz")
                p3 = os.path.join(temp_dir, "hessian_eigen_3.nii.gz")
                sitk.WriteImage(e1, p1)
                sitk.WriteImage(e2, p2)
                sitk.WriteImage(e3, p3)

                choice = QtWidgets.QInputDialog.getItem(
                    self,
                    "Hessian 特征值输出",
                    "选择要加载显示的特征值图：",
                    ["Eigen1(最小)", "Eigen2", "Eigen3(最大)"],
                    0,
                    False,
                )
                if choice[1]:
                    if choice[0].startswith("Eigen1"):
                        self._save_and_show_result_as_layer("Hessian", "Hessian特征值1", e1, show_message=False)
                    elif choice[0].startswith("Eigen2"):
                        self._save_and_show_result_as_layer("Hessian", "Hessian特征值2", e2, show_message=False)
                    else:
                        self._save_and_show_result_as_layer("Hessian", "Hessian特征值3", e3, show_message=False)

                QtWidgets.QMessageBox.information(
                    self,
                    "Hessian 输出",
                    f"3 个特征值图已导出到临时目录:\n{p1}\n{p2}\n{p3}",
                )

            elif key == "laplacian_of_gaussian":
                result = CommonImageFiltersEngine.laplacian_of_gaussian(input_image, **params)
                self._save_and_show_result_as_layer("Hessian/LoG", spec["title"], result)

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "执行失败", f"{spec['title']} 执行失败:\n{str(e)}")
        finally:
            progress.close()

    # 具体入口方法（用于菜单直接绑定）
    def run_connected_component(self):
        self.run_common_image_filter("connected_component")

    def run_scalar_connected_component(self):
        self.run_common_image_filter("scalar_connected_component")

    def run_relabel_components(self):
        self.run_common_image_filter("relabel_components")

    def run_convolution(self):
        self.run_common_image_filter("convolution")

    def run_fft_convolution(self):
        self.run_common_image_filter("fft_convolution")

    def run_correlation_ncc(self):
        self.run_common_image_filter("correlation_ncc")

    def run_fft_correlation_ncc(self):
        self.run_common_image_filter("fft_correlation_ncc")

    def run_streaming_fft_correlation_ncc(self):
        self.run_common_image_filter("streaming_fft_correlation_ncc")

    def run_signed_maurer_distance_map(self):
        self.run_common_image_filter("signed_maurer_distance_map")

    def run_danielsson_distance_map(self):
        self.run_common_image_filter("danielsson_distance_map")

    def run_canny_edge(self):
        self.run_common_image_filter("canny")

    def run_sobel_edge(self):
        self.run_common_image_filter("sobel")

    def run_gradient_magnitude(self):
        self.run_common_image_filter("gradient_magnitude")

    def run_gradient_magnitude_recursive_gaussian(self):
        self.run_common_image_filter("gradient_magnitude_recursive_gaussian")

    def run_derivative(self):
        self.run_common_image_filter("derivative")

    def run_higher_order_accurate_derivative(self):
        self.run_common_image_filter("higher_order_accurate_derivative")

    def run_hessian_eigen_analysis(self):
        self.run_common_image_filter("hessian_eigen_analysis")

    def run_laplacian_of_gaussian(self):
        self.run_common_image_filter("laplacian_of_gaussian")
