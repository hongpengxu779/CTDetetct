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
    def _normalize_radius(radius, ndim: int):
        if isinstance(radius, (int, float)):
            r = int(max(0, radius))
            return tuple([r] * ndim)
        values = list(radius)
        if len(values) != ndim:
            if len(values) == 1:
                return tuple([int(max(0, values[0]))] * ndim)
            raise ValueError(f"radius 维度不匹配，期望 {ndim} 维")
        return tuple(int(max(0, v)) for v in values)

    @staticmethod
    def _polygon_mask_2d(shape, radius: int, sides: int):
        h, w = shape
        cy = (h - 1) / 2.0
        cx = (w - 1) / 2.0
        angles = np.linspace(0, 2 * np.pi, max(3, int(sides)), endpoint=False)
        vy = cy + radius * np.sin(angles)
        vx = cx + radius * np.cos(angles)

        yy, xx = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        inside = np.zeros((h, w), dtype=bool)
        n = len(vx)
        eps = 1e-12

        for i in range(n):
            j = (i - 1) % n
            xi, yi = vx[i], vy[i]
            xj, yj = vx[j], vy[j]
            cond = ((yi > yy) != (yj > yy))
            x_inter = (xj - xi) * (yy - yi) / (yj - yi + eps) + xi
            inside ^= cond & (xx < x_inter)

        return inside

    @staticmethod
    def _reconstruct_by_dilation(marker: np.ndarray, mask: np.ndarray, footprint: np.ndarray, max_iter: int = 2048):
        prev = marker.astype(np.float32, copy=True)
        for _ in range(max_iter):
            curr = np.minimum(ndimage.grey_dilation(prev, footprint=footprint), mask)
            if np.array_equal(curr, prev):
                break
            prev = curr
        return prev

    @staticmethod
    def _reconstruct_by_erosion(marker: np.ndarray, mask: np.ndarray, footprint: np.ndarray, max_iter: int = 2048):
        prev = marker.astype(np.float32, copy=True)
        for _ in range(max_iter):
            curr = np.maximum(ndimage.grey_erosion(prev, footprint=footprint), mask)
            if np.array_equal(curr, prev):
                break
            prev = curr
        return prev

    @staticmethod
    def _make_footprint(ndim: int, radius=(1, 1, 1), shape: str = "ball", polygon_sides: int = 6):
        radius = CommonImageFiltersEngine._normalize_radius(radius, ndim)
        shape = (shape or "ball").lower()
        shape_alias = {
            "ball": "ball", "sphere": "ball", "球": "ball",
            "box": "box", "cube": "box", "盒": "box", "方": "box",
            "cross": "cross", "十字": "cross",
            "polygon": "polygon", "多边形": "polygon",
        }
        shape = shape_alias.get(shape, shape)

        dims = tuple(2 * r + 1 for r in radius)

        if shape == "box":
            return np.ones(dims, dtype=bool)

        if shape == "cross":
            grid = np.indices(dims)
            center = np.array(radius).reshape((ndim,) + (1,) * ndim)
            non_center = np.sum(grid != center, axis=0)
            return non_center <= 1

        if shape == "polygon":
            if ndim == 2:
                rr = max(radius)
                return CommonImageFiltersEngine._polygon_mask_2d(dims, rr, polygon_sides)
            rr = max(radius[1], radius[2]) if ndim >= 3 else max(radius)
            poly2d = CommonImageFiltersEngine._polygon_mask_2d((dims[-2], dims[-1]), rr, polygon_sides)
            if ndim == 3:
                return np.repeat(poly2d[np.newaxis, :, :], dims[0], axis=0)
            return np.ones(dims, dtype=bool)

        # 默认 ball/ellipsoid
        grid = np.indices(dims).astype(np.float32)
        center = np.array(radius, dtype=np.float32).reshape((ndim,) + (1,) * ndim)
        rr = np.array([max(r, 1) for r in radius], dtype=np.float32).reshape((ndim,) + (1,) * ndim)
        dist = np.sum(((grid - center) / rr) ** 2, axis=0)
        return dist <= 1.0

    @staticmethod
    def _arr_to_sitk_with_info(arr: np.ndarray, ref: sitk.Image) -> sitk.Image:
        img = sitk.GetImageFromArray(arr)
        return CommonImageFiltersEngine._copy_info(ref, img)

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

    @staticmethod
    def dilation(image: sitk.Image, radius: int = 1, kernel_shape: str = "ball", polygon_sides: int = 6) -> sitk.Image:
        arr = sitk.GetArrayFromImage(CommonImageFiltersEngine._to_float_image(image)).astype(np.float32)
        fp = CommonImageFiltersEngine._make_footprint(arr.ndim, radius, kernel_shape, polygon_sides)
        out = ndimage.grey_dilation(arr, footprint=fp)
        return CommonImageFiltersEngine._arr_to_sitk_with_info(out.astype(np.float32), image)

    @staticmethod
    def erosion(image: sitk.Image, radius: int = 1, kernel_shape: str = "ball", polygon_sides: int = 6) -> sitk.Image:
        arr = sitk.GetArrayFromImage(CommonImageFiltersEngine._to_float_image(image)).astype(np.float32)
        fp = CommonImageFiltersEngine._make_footprint(arr.ndim, radius, kernel_shape, polygon_sides)
        out = ndimage.grey_erosion(arr, footprint=fp)
        return CommonImageFiltersEngine._arr_to_sitk_with_info(out.astype(np.float32), image)

    @staticmethod
    def opening(image: sitk.Image, radius: int = 1, kernel_shape: str = "ball", polygon_sides: int = 6) -> sitk.Image:
        arr = sitk.GetArrayFromImage(CommonImageFiltersEngine._to_float_image(image)).astype(np.float32)
        fp = CommonImageFiltersEngine._make_footprint(arr.ndim, radius, kernel_shape, polygon_sides)
        out = ndimage.grey_opening(arr, footprint=fp)
        return CommonImageFiltersEngine._arr_to_sitk_with_info(out.astype(np.float32), image)

    @staticmethod
    def closing(image: sitk.Image, radius: int = 1, kernel_shape: str = "ball", polygon_sides: int = 6) -> sitk.Image:
        arr = sitk.GetArrayFromImage(CommonImageFiltersEngine._to_float_image(image)).astype(np.float32)
        fp = CommonImageFiltersEngine._make_footprint(arr.ndim, radius, kernel_shape, polygon_sides)
        out = ndimage.grey_closing(arr, footprint=fp)
        return CommonImageFiltersEngine._arr_to_sitk_with_info(out.astype(np.float32), image)

    @staticmethod
    def opening_by_reconstruction(image: sitk.Image, radius: int = 1,
                                  kernel_shape: str = "ball", polygon_sides: int = 6) -> sitk.Image:
        arr = sitk.GetArrayFromImage(CommonImageFiltersEngine._to_float_image(image)).astype(np.float32)
        fp = CommonImageFiltersEngine._make_footprint(arr.ndim, radius, kernel_shape, polygon_sides)
        marker = ndimage.grey_erosion(arr, footprint=fp)
        out = CommonImageFiltersEngine._reconstruct_by_dilation(marker, arr, fp)
        return CommonImageFiltersEngine._arr_to_sitk_with_info(out.astype(np.float32), image)

    @staticmethod
    def closing_by_reconstruction(image: sitk.Image, radius: int = 1,
                                  kernel_shape: str = "ball", polygon_sides: int = 6) -> sitk.Image:
        arr = sitk.GetArrayFromImage(CommonImageFiltersEngine._to_float_image(image)).astype(np.float32)
        fp = CommonImageFiltersEngine._make_footprint(arr.ndim, radius, kernel_shape, polygon_sides)
        marker = ndimage.grey_dilation(arr, footprint=fp)
        out = CommonImageFiltersEngine._reconstruct_by_erosion(marker, arr, fp)
        return CommonImageFiltersEngine._arr_to_sitk_with_info(out.astype(np.float32), image)

    @staticmethod
    def binary_thinning(image: sitk.Image) -> sitk.Image:
        arr = sitk.GetArrayFromImage(image)
        binary = arr > 0
        skel = None
        if hasattr(sitk, "BinaryThinning"):
            try:
                sitk_bin = sitk.Cast(image > 0, sitk.sitkUInt8)
                thin = sitk.BinaryThinning(sitk_bin)
                skel = sitk.GetArrayFromImage(thin) > 0
            except Exception:
                skel = None

        if skel is None:
            skel = np.zeros_like(binary, dtype=bool)
            work = binary.copy()
            fp = ndimage.generate_binary_structure(binary.ndim, 1)
            while np.any(work):
                eroded = ndimage.binary_erosion(work, structure=fp)
                opened = ndimage.binary_dilation(eroded, structure=fp)
                skel |= work & (~opened)
                if np.array_equal(eroded, work):
                    break
                work = eroded

        out = (skel.astype(np.uint8) * 255).astype(np.uint8)
        return CommonImageFiltersEngine._arr_to_sitk_with_info(out, image)

    @staticmethod
    def fill_hole_binary(image: sitk.Image) -> sitk.Image:
        arr = sitk.GetArrayFromImage(image)
        binary = arr > 0
        filled = ndimage.binary_fill_holes(binary)
        out = (filled.astype(np.uint8) * 255).astype(np.uint8)
        return CommonImageFiltersEngine._arr_to_sitk_with_info(out, image)

    @staticmethod
    def fill_hole_grayscale(image: sitk.Image) -> sitk.Image:
        arr = sitk.GetArrayFromImage(CommonImageFiltersEngine._to_float_image(image)).astype(np.float32)
        seed = arr.copy()
        interior = tuple(slice(1, -1) if s > 2 else slice(0, s) for s in arr.shape)
        seed[interior] = np.max(arr)
        fp = np.ones(tuple([3] * arr.ndim), dtype=bool)
        filled = CommonImageFiltersEngine._reconstruct_by_erosion(seed, arr, fp)
        return CommonImageFiltersEngine._arr_to_sitk_with_info(filled.astype(np.float32), image)

    @staticmethod
    def vessel_enhancement(image: sitk.Image, sigma_min: float = 1.0, sigma_max: float = 4.0,
                           sigma_step: float = 1.0, alpha: float = 0.5,
                           beta: float = 0.5, gamma: float = 15.0,
                           black_ridges: bool = False) -> sitk.Image:
        arr = sitk.GetArrayFromImage(CommonImageFiltersEngine._to_float_image(image)).astype(np.float32)
        amin = float(arr.min())
        amax = float(arr.max())
        if amax > amin:
            arr_n = (arr - amin) / (amax - amin)
        else:
            arr_n = np.zeros_like(arr, dtype=np.float32)

        sigma_min = max(0.1, float(sigma_min))
        sigma_max = max(sigma_min, float(sigma_max))
        sigma_step = max(0.1, float(sigma_step))
        sigmas = np.arange(sigma_min, sigma_max + 1e-6, sigma_step, dtype=np.float32)

        alpha = max(float(alpha), 1e-6)
        beta = max(float(beta), 1e-6)
        gamma = max(float(gamma), 1e-6)

        vessel = np.zeros_like(arr_n, dtype=np.float32)
        for sigma in sigmas:
            dxx = ndimage.gaussian_filter(arr_n, sigma=sigma, order=(0, 0, 2))
            dyy = ndimage.gaussian_filter(arr_n, sigma=sigma, order=(0, 2, 0))
            dzz = ndimage.gaussian_filter(arr_n, sigma=sigma, order=(2, 0, 0))
            dxy = ndimage.gaussian_filter(arr_n, sigma=sigma, order=(0, 1, 1))
            dxz = ndimage.gaussian_filter(arr_n, sigma=sigma, order=(1, 0, 1))
            dyz = ndimage.gaussian_filter(arr_n, sigma=sigma, order=(1, 1, 0))

            h = np.zeros(arr_n.shape + (3, 3), dtype=np.float32)
            h[..., 0, 0] = dxx
            h[..., 1, 1] = dyy
            h[..., 2, 2] = dzz
            h[..., 0, 1] = dxy
            h[..., 1, 0] = dxy
            h[..., 0, 2] = dxz
            h[..., 2, 0] = dxz
            h[..., 1, 2] = dyz
            h[..., 2, 1] = dyz

            evals = np.linalg.eigvalsh(h)
            idx = np.argsort(np.abs(evals), axis=-1)
            l1 = np.take_along_axis(evals, idx[..., 0:1], axis=-1)[..., 0]
            l2 = np.take_along_axis(evals, idx[..., 1:2], axis=-1)[..., 0]
            l3 = np.take_along_axis(evals, idx[..., 2:3], axis=-1)[..., 0]

            eps = 1e-12
            ra = np.abs(l2) / (np.abs(l3) + eps)
            rb = np.abs(l1) / (np.sqrt(np.abs(l2 * l3)) + eps)
            s = np.sqrt(l1 * l1 + l2 * l2 + l3 * l3)

            v = (1.0 - np.exp(-(ra * ra) / (2.0 * alpha * alpha)))
            v *= np.exp(-(rb * rb) / (2.0 * beta * beta))
            v *= (1.0 - np.exp(-(s * s) / (2.0 * gamma * gamma)))

            if black_ridges:
                valid = (l2 > 0) & (l3 > 0)
            else:
                valid = (l2 < 0) & (l3 < 0)

            v = np.where(valid, v, 0.0).astype(np.float32)
            vessel = np.maximum(vessel, v)

        return CommonImageFiltersEngine._arr_to_sitk_with_info(vessel, image)
