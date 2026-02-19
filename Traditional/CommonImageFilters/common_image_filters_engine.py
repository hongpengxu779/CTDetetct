import csv
import os
from typing import Dict, Tuple

import numpy as np
import SimpleITK as sitk
from scipy import signal, ndimage


class CommonImageFiltersEngine:
    """Common Image Filters 算法后端。"""

    @staticmethod
    def _to_float_image(image: sitk.Image) -> sitk.Image:
        return sitk.Cast(image, sitk.sitkFloat32)

    @staticmethod
    def _copy_info(src: sitk.Image, dst: sitk.Image) -> sitk.Image:
        dst.CopyInformation(src)
        return dst

    @staticmethod
    def _rescale_to_uint16(image: sitk.Image) -> sitk.Image:
        return sitk.Cast(sitk.RescaleIntensity(image, 0, 65535), sitk.sitkUInt16)

    @staticmethod
    def _numpy_kernel_from_text(kernel_text: str) -> np.ndarray:
        """
        支持格式：
        - 2D: "1 0 -1; 1 0 -1; 1 0 -1"
        - 3D: 用空行分层
          "1 0 1\n0 0 0\n-1 0 -1\n\n1 1 1\n0 0 0\n-1 -1 -1"
        """
        text = (kernel_text or "").strip()
        if not text:
            return np.ones((3, 3, 3), dtype=np.float32) / 27.0

        if "\n\n" in text:
            blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
            slices = []
            for block in blocks:
                rows = [r.strip() for r in block.splitlines() if r.strip()]
                arr2 = np.array([[float(x) for x in row.replace(',', ' ').split()] for row in rows], dtype=np.float32)
                slices.append(arr2)
            shape0 = slices[0].shape
            for s in slices:
                if s.shape != shape0:
                    raise ValueError("3D 核每一层尺寸必须一致")
            return np.stack(slices, axis=0)

        if ";" in text:
            rows = [r.strip() for r in text.split(";") if r.strip()]
        else:
            rows = [r.strip() for r in text.splitlines() if r.strip()]

        arr2 = np.array([[float(x) for x in row.replace(',', ' ').split()] for row in rows], dtype=np.float32)
        if arr2.ndim != 2:
            raise ValueError("核解析失败")

        return arr2[np.newaxis, :, :]

    @staticmethod
    def connected_component(binary_image: sitk.Image, fully_connected: bool = False) -> sitk.Image:
        img = sitk.Cast(binary_image > 0, sitk.sitkUInt8)
        f = sitk.ConnectedComponentImageFilter()
        f.SetFullyConnected(bool(fully_connected))
        out = f.Execute(img)
        return sitk.Cast(out, sitk.sitkUInt32)

    @staticmethod
    def scalar_connected_component(image: sitk.Image, distance_threshold: float = 10.0, fully_connected: bool = False) -> sitk.Image:
        img = CommonImageFiltersEngine._to_float_image(image)
        f = sitk.ScalarConnectedComponentImageFilter()
        f.SetDistanceThreshold(float(distance_threshold))
        f.SetFullyConnected(bool(fully_connected))
        out = f.Execute(img)
        return sitk.Cast(out, sitk.sitkUInt32)

    @staticmethod
    def relabel_components(label_image: sitk.Image, minimum_object_size: int = 0,
                           export_stats_path: str = "") -> Tuple[sitk.Image, Dict[int, int]]:
        relabel = sitk.RelabelComponentImageFilter()
        relabel.SetMinimumObjectSize(int(max(0, minimum_object_size)))
        out = relabel.Execute(sitk.Cast(label_image, sitk.sitkUInt32))

        stats = sitk.LabelShapeStatisticsImageFilter()
        stats.Execute(out)

        voxel_count = {}
        for label in stats.GetLabels():
            voxel_count[int(label)] = int(stats.GetNumberOfPixels(label))

        if export_stats_path:
            with open(export_stats_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["label", "voxel_count", "physical_size"])
                for label in sorted(voxel_count.keys()):
                    writer.writerow([
                        label,
                        voxel_count[label],
                        float(stats.GetPhysicalSize(label)),
                    ])

        return sitk.Cast(out, sitk.sitkUInt32), voxel_count

    @staticmethod
    def convolution(image: sitk.Image, kernel_text: str) -> sitk.Image:
        arr = sitk.GetArrayFromImage(CommonImageFiltersEngine._to_float_image(image))
        kernel = CommonImageFiltersEngine._numpy_kernel_from_text(kernel_text)
        out = signal.convolve(arr, kernel, mode="same", method="direct")
        img = sitk.GetImageFromArray(out.astype(np.float32))
        return CommonImageFiltersEngine._copy_info(image, img)

    @staticmethod
    def fft_convolution(image: sitk.Image, kernel_text: str) -> sitk.Image:
        arr = sitk.GetArrayFromImage(CommonImageFiltersEngine._to_float_image(image))
        kernel = CommonImageFiltersEngine._numpy_kernel_from_text(kernel_text)
        out = signal.fftconvolve(arr, kernel, mode="same")
        img = sitk.GetImageFromArray(out.astype(np.float32))
        return CommonImageFiltersEngine._copy_info(image, img)

    @staticmethod
    def _ncc_spatial(arr: np.ndarray, tpl: np.ndarray, use_fft: bool = False) -> np.ndarray:
        eps = 1e-8
        tpl = tpl.astype(np.float32)
        arr = arr.astype(np.float32)
        n = float(tpl.size)

        tpl_mean = float(tpl.mean())
        tpl0 = tpl - tpl_mean
        tpl_std = float(np.sqrt(np.sum(tpl0 * tpl0))) + eps

        kernel_ones = np.ones_like(tpl, dtype=np.float32)

        if use_fft:
            corr_func = lambda a, b: signal.fftconvolve(a, b, mode="same")
        else:
            corr_func = lambda a, b: signal.correlate(a, b, mode="same", method="direct")

        num = corr_func(arr, tpl0[::-1, ::-1, ::-1])
        sum_i = corr_func(arr, kernel_ones[::-1, ::-1, ::-1])
        sum_i2 = corr_func(arr * arr, kernel_ones[::-1, ::-1, ::-1])

        var_i = np.maximum(sum_i2 - (sum_i * sum_i) / n, 0.0)
        den = np.sqrt(var_i) * tpl_std + eps
        return (num / den).astype(np.float32)

    @staticmethod
    def correlation_ncc(image: sitk.Image, template_text: str) -> sitk.Image:
        arr = sitk.GetArrayFromImage(CommonImageFiltersEngine._to_float_image(image))
        tpl = CommonImageFiltersEngine._numpy_kernel_from_text(template_text)
        out = CommonImageFiltersEngine._ncc_spatial(arr, tpl, use_fft=False)
        img = sitk.GetImageFromArray(out)
        return CommonImageFiltersEngine._copy_info(image, img)

    @staticmethod
    def fft_correlation_ncc(image: sitk.Image, template_text: str) -> sitk.Image:
        arr = sitk.GetArrayFromImage(CommonImageFiltersEngine._to_float_image(image))
        tpl = CommonImageFiltersEngine._numpy_kernel_from_text(template_text)
        out = CommonImageFiltersEngine._ncc_spatial(arr, tpl, use_fft=True)
        img = sitk.GetImageFromArray(out)
        return CommonImageFiltersEngine._copy_info(image, img)

    @staticmethod
    def streaming_fft_correlation_ncc(image: sitk.Image, template_text: str, chunk_depth: int = 64) -> sitk.Image:
        arr = sitk.GetArrayFromImage(CommonImageFiltersEngine._to_float_image(image))
        tpl = CommonImageFiltersEngine._numpy_kernel_from_text(template_text)

        z = arr.shape[0]
        cz = max(8, int(chunk_depth))
        overlap = max(1, tpl.shape[0] // 2)

        out = np.zeros_like(arr, dtype=np.float32)
        start = 0
        while start < z:
            end = min(z, start + cz)
            ext0 = max(0, start - overlap)
            ext1 = min(z, end + overlap)

            chunk = arr[ext0:ext1]
            chunk_ncc = CommonImageFiltersEngine._ncc_spatial(chunk, tpl, use_fft=True)

            in0 = start - ext0
            in1 = in0 + (end - start)
            out[start:end] = chunk_ncc[in0:in1]
            start = end

        img = sitk.GetImageFromArray(out)
        return CommonImageFiltersEngine._copy_info(image, img)

    @staticmethod
    def signed_maurer_distance_map(image: sitk.Image, squared_distance: bool = False,
                                   use_image_spacing: bool = True,
                                   inside_is_positive: bool = False,
                                   clamp_nonnegative: bool = False) -> sitk.Image:
        binary = sitk.Cast(image > 0, sitk.sitkUInt8)
        f = sitk.SignedMaurerDistanceMapImageFilter()
        f.SetSquaredDistance(bool(squared_distance))
        f.SetUseImageSpacing(bool(use_image_spacing))
        f.SetInsideIsPositive(bool(inside_is_positive))
        out = f.Execute(binary)
        if clamp_nonnegative:
            out = sitk.Maximum(out, 0.0)
        return sitk.Cast(out, sitk.sitkFloat32)

    @staticmethod
    def danielsson_distance_map(image: sitk.Image, input_is_binary: bool = True,
                                squared_distance: bool = False,
                                use_image_spacing: bool = True,
                                rescale_to_uchar: bool = False) -> sitk.Image:
        src = sitk.Cast(image > 0, sitk.sitkUInt8) if input_is_binary else CommonImageFiltersEngine._to_float_image(image)
        f = sitk.DanielssonDistanceMapImageFilter()
        f.SetInputIsBinary(bool(input_is_binary))
        f.SetSquaredDistance(bool(squared_distance))
        f.SetUseImageSpacing(bool(use_image_spacing))
        out = f.Execute(src)
        out = sitk.Cast(out, sitk.sitkFloat32)
        if rescale_to_uchar:
            out = sitk.Cast(sitk.RescaleIntensity(out, 0, 255), sitk.sitkUInt8)
        return out

    @staticmethod
    def canny(image: sitk.Image, variance: float = 1.0,
              lower_threshold: float = 10.0, upper_threshold: float = 30.0) -> sitk.Image:
        img = CommonImageFiltersEngine._to_float_image(image)
        f = sitk.CannyEdgeDetectionImageFilter()
        f.SetVariance(float(variance))
        f.SetLowerThreshold(float(lower_threshold))
        f.SetUpperThreshold(float(upper_threshold))
        return sitk.Cast(f.Execute(img), sitk.sitkFloat32)

    @staticmethod
    def sobel(image: sitk.Image) -> sitk.Image:
        img = CommonImageFiltersEngine._to_float_image(image)
        out = sitk.SobelEdgeDetection(img)
        return sitk.Cast(out, sitk.sitkFloat32)

    @staticmethod
    def gradient_magnitude(image: sitk.Image, use_image_spacing: bool = True) -> sitk.Image:
        img = CommonImageFiltersEngine._to_float_image(image)
        f = sitk.GradientMagnitudeImageFilter()
        f.SetUseImageSpacing(bool(use_image_spacing))
        return sitk.Cast(f.Execute(img), sitk.sitkFloat32)

    @staticmethod
    def gradient_magnitude_recursive_gaussian(image: sitk.Image, sigma: float = 1.0,
                                              use_image_spacing: bool = True) -> sitk.Image:
        img = CommonImageFiltersEngine._to_float_image(image)
        f = sitk.GradientMagnitudeRecursiveGaussianImageFilter()
        f.SetSigma(float(sigma))
        f.SetUseImageSpacing(bool(use_image_spacing))
        return sitk.Cast(f.Execute(img), sitk.sitkFloat32)

    @staticmethod
    def derivative(image: sitk.Image, direction: int = 0, order: int = 1,
                   use_image_spacing: bool = True) -> sitk.Image:
        img = CommonImageFiltersEngine._to_float_image(image)
        f = sitk.DerivativeImageFilter()
        f.SetDirection(int(direction))
        f.SetOrder(int(order))
        f.SetUseImageSpacing(bool(use_image_spacing))
        return sitk.Cast(f.Execute(img), sitk.sitkFloat32)

    @staticmethod
    def higher_order_accurate_derivative(image: sitk.Image, direction: int = 0, order: int = 1,
                                         use_image_spacing: bool = True) -> sitk.Image:
        if not hasattr(sitk, "HigherOrderAccurateDerivativeImageFilter"):
            raise RuntimeError("当前 SimpleITK 构建未启用 HigherOrderAccurateDerivativeImageFilter")

        img = CommonImageFiltersEngine._to_float_image(image)
        f = sitk.HigherOrderAccurateDerivativeImageFilter()
        f.SetDirection(int(direction))
        f.SetOrder(int(order))
        f.SetUseImageSpacing(bool(use_image_spacing))
        return sitk.Cast(f.Execute(img), sitk.sitkFloat32)

    @staticmethod
    def hessian_eigen_analysis(image: sitk.Image, sigma: float = 1.0):
        arr = sitk.GetArrayFromImage(CommonImageFiltersEngine._to_float_image(image)).astype(np.float32)

        dxx = ndimage.gaussian_filter(arr, sigma=sigma, order=(0, 0, 2))
        dyy = ndimage.gaussian_filter(arr, sigma=sigma, order=(0, 2, 0))
        dzz = ndimage.gaussian_filter(arr, sigma=sigma, order=(2, 0, 0))
        dxy = ndimage.gaussian_filter(arr, sigma=sigma, order=(0, 1, 1))
        dxz = ndimage.gaussian_filter(arr, sigma=sigma, order=(1, 0, 1))
        dyz = ndimage.gaussian_filter(arr, sigma=sigma, order=(1, 1, 0))

        h = np.zeros(arr.shape + (3, 3), dtype=np.float32)
        h[..., 0, 0] = dxx
        h[..., 1, 1] = dyy
        h[..., 2, 2] = dzz
        h[..., 0, 1] = dxy
        h[..., 1, 0] = dxy
        h[..., 0, 2] = dxz
        h[..., 2, 0] = dxz
        h[..., 1, 2] = dyz
        h[..., 2, 1] = dyz

        eigvals = np.linalg.eigvalsh(h)  # (..., 3), 升序

        e1 = sitk.GetImageFromArray(eigvals[..., 0].astype(np.float32))
        e2 = sitk.GetImageFromArray(eigvals[..., 1].astype(np.float32))
        e3 = sitk.GetImageFromArray(eigvals[..., 2].astype(np.float32))
        e1 = CommonImageFiltersEngine._copy_info(image, e1)
        e2 = CommonImageFiltersEngine._copy_info(image, e2)
        e3 = CommonImageFiltersEngine._copy_info(image, e3)
        return e1, e2, e3

    @staticmethod
    def laplacian_of_gaussian(image: sitk.Image, sigma: float = 1.0,
                              use_image_spacing: bool = True) -> sitk.Image:
        img = CommonImageFiltersEngine._to_float_image(image)
        f = sitk.LaplacianRecursiveGaussianImageFilter()
        f.SetSigma(float(sigma))
        f.SetUseImageSpacing(bool(use_image_spacing))
        return sitk.Cast(f.Execute(img), sitk.sitkFloat32)
