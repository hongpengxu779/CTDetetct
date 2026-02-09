"""
3D图像增强算法实现
包含：
1. 直方图均衡化 (Histogram Equalization)
2. 限制对比度自适应直方图均衡化 (CLAHE)
3. Retinex SSR (Single Scale Retinex)
4. 去雾 (Dark Channel Prior Dehazing)
"""

import numpy as np
import cv2


class EnhancementOps:
    """3D图像增强操作类"""

    @staticmethod
    def _normalize_to_uint8(volume: np.ndarray) -> tuple:
        """
        将3D体数据归一化到 [0, 255] uint8 范围

        返回
        ----
        (uint8_volume, vmin, vmax) : 归一化后的数据、原始最小值、最大值
        """
        vmin = float(volume.min())
        vmax = float(volume.max())
        if vmax - vmin < 1e-8:
            return np.zeros(volume.shape, dtype=np.uint8), vmin, vmax
        norm = (volume.astype(np.float64) - vmin) / (vmax - vmin) * 255.0
        return norm.astype(np.uint8), vmin, vmax

    @staticmethod
    def _rescale_to_original(volume_uint8: np.ndarray, vmin: float, vmax: float, 
                              target_dtype: np.dtype) -> np.ndarray:
        """
        将 uint8 处理结果映射回原始数据范围和类型
        """
        result = volume_uint8.astype(np.float64) / 255.0 * (vmax - vmin) + vmin
        if np.issubdtype(target_dtype, np.integer):
            result = np.clip(result, np.iinfo(target_dtype).min, np.iinfo(target_dtype).max)
        return result.astype(target_dtype)

    @staticmethod
    def histogram_equalization_3d(volume: np.ndarray, progress_callback=None) -> np.ndarray:
        """
        对3D体数据逐切片应用直方图均衡化

        参数
        ----
        volume : np.ndarray
            输入的三维图像数据 (Z, Y, X)
        progress_callback : callable, optional
            进度回调函数，接收 (current, total) 两个参数

        返回
        ----
        np.ndarray : 均衡化后的三维数据，与输入类型一致
        """
        original_dtype = volume.dtype
        vol_u8, vmin, vmax = EnhancementOps._normalize_to_uint8(volume)
        result = np.zeros_like(vol_u8)

        depth = vol_u8.shape[0]
        for z in range(depth):
            result[z] = cv2.equalizeHist(vol_u8[z])
            if progress_callback and z % max(1, depth // 20) == 0:
                progress_callback(z, depth)

        return EnhancementOps._rescale_to_original(result, vmin, vmax, original_dtype)

    @staticmethod
    def clahe_3d(volume: np.ndarray, clip_limit: float = 2.0, 
                 tile_grid_size: tuple = (8, 8), progress_callback=None) -> np.ndarray:
        """
        对3D体数据逐切片应用限制对比度自适应直方图均衡化 (CLAHE)

        参数
        ----
        volume : np.ndarray
            输入的三维图像数据 (Z, Y, X)
        clip_limit : float
            对比度限制阈值，默认2.0
        tile_grid_size : tuple
            直方图均衡化的网格大小，默认(8, 8)
        progress_callback : callable, optional
            进度回调函数

        返回
        ----
        np.ndarray : CLAHE处理后的三维数据
        """
        original_dtype = volume.dtype
        vol_u8, vmin, vmax = EnhancementOps._normalize_to_uint8(volume)
        result = np.zeros_like(vol_u8)

        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)

        depth = vol_u8.shape[0]
        for z in range(depth):
            result[z] = clahe.apply(vol_u8[z])
            if progress_callback and z % max(1, depth // 20) == 0:
                progress_callback(z, depth)

        return EnhancementOps._rescale_to_original(result, vmin, vmax, original_dtype)

    @staticmethod
    def retinex_ssr_3d(volume: np.ndarray, sigma: float = 80.0, 
                       progress_callback=None) -> np.ndarray:
        """
        对3D体数据逐切片应用单尺度 Retinex (SSR)

        SSR 算法原理：
        R(x,y) = log(I(x,y)) - log(I(x,y) * G(x,y))
        其中 G 是高斯核，* 表示卷积

        参数
        ----
        volume : np.ndarray
            输入的三维图像数据 (Z, Y, X)
        sigma : float
            高斯核的标准差，控制环绕光估计的尺度，默认80.0
            较小的sigma强调细节，较大的sigma强调动态范围压缩
        progress_callback : callable, optional
            进度回调函数

        返回
        ----
        np.ndarray : Retinex SSR处理后的三维数据
        """
        original_dtype = volume.dtype
        vol_u8, vmin, vmax = EnhancementOps._normalize_to_uint8(volume)
        result_f = np.zeros(vol_u8.shape, dtype=np.float64)

        depth = vol_u8.shape[0]
        for z in range(depth):
            slice_f = vol_u8[z].astype(np.float64) + 1.0  # 避免 log(0)
            # 高斯模糊估计光照分量
            blur = cv2.GaussianBlur(slice_f, (0, 0), sigma)
            blur = np.maximum(blur, 1.0)
            # SSR: log(原始) - log(光照)
            retinex = np.log10(slice_f) - np.log10(blur)
            result_f[z] = retinex
            if progress_callback and z % max(1, depth // 20) == 0:
                progress_callback(z, depth)

        # 全局归一化到 [0, 255]
        rmin, rmax = result_f.min(), result_f.max()
        if rmax - rmin > 1e-8:
            result_f = (result_f - rmin) / (rmax - rmin) * 255.0
        result_u8 = np.clip(result_f, 0, 255).astype(np.uint8)

        return EnhancementOps._rescale_to_original(result_u8, vmin, vmax, original_dtype)

    @staticmethod
    def dehaze_3d(volume: np.ndarray, omega: float = 0.95, t_min: float = 0.1,
                  patch_size: int = 15, progress_callback=None) -> np.ndarray:
        """
        对3D体数据逐切片应用暗通道先验去雾算法

        基于 He Kaiming 的暗通道先验去雾方法，适配为灰度图像处理。

        参数
        ----
        volume : np.ndarray
            输入的三维图像数据 (Z, Y, X)
        omega : float
            去雾程度参数，0~1之间，默认0.95。值越大去雾越彻底
        t_min : float
            透射率下限，防止过度增强，默认0.1
        patch_size : int
            暗通道计算的邻域大小，默认15
        progress_callback : callable, optional
            进度回调函数

        返回
        ----
        np.ndarray : 去雾后的三维数据
        """
        original_dtype = volume.dtype
        vol_u8, vmin, vmax = EnhancementOps._normalize_to_uint8(volume)
        result = np.zeros_like(vol_u8)

        depth = vol_u8.shape[0]
        for z in range(depth):
            result[z] = EnhancementOps._dehaze_slice(vol_u8[z], omega, t_min, patch_size)
            if progress_callback and z % max(1, depth // 20) == 0:
                progress_callback(z, depth)

        return EnhancementOps._rescale_to_original(result, vmin, vmax, original_dtype)

    @staticmethod
    def _dehaze_slice(img_u8: np.ndarray, omega: float, t_min: float, 
                      patch_size: int) -> np.ndarray:
        """
        对单张灰度切片进行去雾处理

        参数
        ----
        img_u8 : np.ndarray
            uint8灰度图像
        omega, t_min, patch_size : 去雾参数
        """
        img_f = img_u8.astype(np.float64) / 255.0

        # 暗通道（灰度图像的暗通道 = 局部最小值）
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (patch_size, patch_size))
        dark_channel = cv2.erode(img_f, kernel)

        # 估计大气光值A（取暗通道最亮的0.1%像素对应原图的最大值）
        num_pixels = dark_channel.size
        num_brightest = max(int(num_pixels * 0.001), 1)
        flat_dark = dark_channel.ravel()
        flat_img = img_f.ravel()
        indices = np.argsort(flat_dark)[-num_brightest:]
        atm_light = np.max(flat_img[indices])
        atm_light = max(atm_light, 0.01)  # 避免除以0

        # 估计透射率 t(x)
        normalized = img_f / atm_light
        dark_normalized = cv2.erode(normalized, kernel)
        transmission = 1.0 - omega * dark_normalized
        transmission = np.maximum(transmission, t_min)

        # 使用导向滤波细化透射率（用原图作为引导）
        # 使用OpenCV的GuidedFilter近似：boxFilter
        guide = img_f
        r = patch_size * 4
        eps = 0.001
        transmission = EnhancementOps._guided_filter(guide, transmission, r, eps)
        transmission = np.maximum(transmission, t_min)

        # 恢复场景辐射度 J(x) = (I(x) - A) / t(x) + A
        recovered = (img_f - atm_light) / transmission + atm_light
        recovered = np.clip(recovered, 0, 1)

        return (recovered * 255).astype(np.uint8)

    @staticmethod
    def _guided_filter(guide: np.ndarray, src: np.ndarray, 
                       radius: int, eps: float) -> np.ndarray:
        """
        导向滤波实现

        参数
        ----
        guide : np.ndarray  引导图像
        src : np.ndarray    输入图像
        radius : int        滤波半径
        eps : float         正则化参数
        """
        ksize = (2 * radius + 1, 2 * radius + 1)

        mean_guide = cv2.boxFilter(guide, -1, ksize)
        mean_src = cv2.boxFilter(src, -1, ksize)
        mean_guide_src = cv2.boxFilter(guide * src, -1, ksize)
        mean_guide2 = cv2.boxFilter(guide * guide, -1, ksize)

        cov = mean_guide_src - mean_guide * mean_src
        var = mean_guide2 - mean_guide * mean_guide

        a = cov / (var + eps)
        b = mean_src - a * mean_guide

        mean_a = cv2.boxFilter(a, -1, ksize)
        mean_b = cv2.boxFilter(b, -1, ksize)

        return mean_a * guide + mean_b
