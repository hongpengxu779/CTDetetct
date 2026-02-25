"""
3D图像增强算法实现
包含：
1. 直方图均衡化 (Histogram Equalization)
2. 限制对比度自适应直方图均衡化 (CLAHE)
3. Retinex SSR (Single Scale Retinex)
4. 去雾 (Dark Channel Prior Dehazing)
5. mUSICA 增强 (Multi-scale Unsharp + Intelligent Contrast Adaptation)
"""

import numpy as np
import cv2
import os
import ctypes
from pathlib import Path


class EnhancementOps:
    """3D图像增强操作类"""

    _imagemaster_dll = None
    _imagemaster_musica_func = None
    _imagemaster_load_failed = False

    @staticmethod
    def _resolve_imagemaster_dll_path() -> Path:
        """解析 ImageMaster.dll 路径（支持环境变量与默认候选路径）"""
        env_dll = os.environ.get("IMAGEMASTER_DLL_PATH", "").strip()
        if env_dll:
            p = Path(env_dll)
            if p.is_file():
                return p

        env_dir = os.environ.get("IMAGEMASTER_DLL_DIR", "").strip()
        if env_dir:
            p = Path(env_dir) / "ImageMaster.dll"
            if p.is_file():
                return p

        project_root = Path(__file__).resolve().parents[2]
        candidates = [
            project_root / "3rdParty" / "ImageMaster.dll",
            Path(r"E:\xu\GTDRDetecion\3rdParty\ImageMaster.dll"),
            Path(r"E:\xu\GTDRDetection\3rdParty\ImageMaster.dll"),
            Path(r"E:\xu\GTDRDetecion\3rdParty") / "ImageMaster.dll",
        ]

        for p in candidates:
            if p.is_file():
                return p

        raise FileNotFoundError("未找到 ImageMaster.dll")

    @staticmethod
    def _load_imagemaster_musica_func():
        """加载 IM_MUSCIA_SSE 函数指针（仅Windows）"""
        if EnhancementOps._imagemaster_musica_func is not None:
            return EnhancementOps._imagemaster_musica_func
        if EnhancementOps._imagemaster_load_failed:
            return None
        if os.name != "nt":
            EnhancementOps._imagemaster_load_failed = True
            return None

        try:
            dll_path = EnhancementOps._resolve_imagemaster_dll_path()
            dll_dir = dll_path.parent

            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(str(dll_dir))
                for sub in ("lib", "opencv", "qBreakpad", "QxOrm"):
                    sub_dir = dll_dir / sub
                    if sub_dir.is_dir():
                        os.add_dll_directory(str(sub_dir))

            dll = ctypes.WinDLL(str(dll_path))
            func = dll.IM_MUSCIA_SSE
            func.argtypes = [
                ctypes.POINTER(ctypes.c_ushort),
                ctypes.POINTER(ctypes.c_ushort),
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
            ]
            func.restype = ctypes.c_int

            EnhancementOps._imagemaster_dll = dll
            EnhancementOps._imagemaster_musica_func = func
            return func
        except Exception:
            EnhancementOps._imagemaster_load_failed = True
            return None

    @staticmethod
    def _musica_slice_imagemaster(img_u16: np.ndarray, level: int, strength: int) -> np.ndarray:
        """调用 ImageMaster.dll 的 IM_MUSCIA_SSE（失败抛异常）"""
        func = EnhancementOps._load_imagemaster_musica_func()
        if func is None:
            raise RuntimeError("IM_MUSCIA_SSE 不可用")

        src = np.ascontiguousarray(img_u16, dtype=np.uint16)
        dst = np.zeros_like(src, dtype=np.uint16)
        height, width = src.shape

        src_ptr = src.ctypes.data_as(ctypes.POINTER(ctypes.c_ushort))
        dst_ptr = dst.ctypes.data_as(ctypes.POINTER(ctypes.c_ushort))
        status = int(func(src_ptr, dst_ptr, int(width), int(height), 1, int(level), int(strength)))
        if status != 0:
            raise RuntimeError(f"IM_MUSCIA_SSE 返回状态码: {status}")

        return dst

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

    @staticmethod
    def musica_3d(volume: np.ndarray,
                  level: int = 8,
                  strength: int = 100,
                  progress_callback=None) -> np.ndarray:
        """
        mUSICA增强（Level/Strength 语义兼容版）

        说明
        ----
        - 参数语义对齐 C++ 接口：mUSCIA(input, Level, Strength)
        - 默认参数与 C++ 版本一致：Level=8, Strength=100
        - 16位灰度优先处理，与 C++ reinterpret_cast<unsigned short*> 行为一致
        - int16 数据直接按位解释为 uint16（等效于 +32768 偏移），不做线性缩放
        - 逐切片进行多尺度细节增强
        """
        level = int(np.clip(level, 1, 8))
        strength = int(np.clip(strength, 0, 100))

        original_dtype = volume.dtype

        # 与 C++ reinterpret_cast 行为一致
        if original_dtype == np.uint16:
            vol_u16 = np.asarray(volume, dtype=np.uint16)
            conversion_mode = "direct"
        elif original_dtype == np.int16:
            # int16 -> uint16: 按位解释（等效于 C++ reinterpret_cast）
            vol_u16 = volume.view(np.uint16)
            conversion_mode = "view_int16"
        else:
            # 其他类型：尝试安全转换到 uint16 范围
            vmin = float(volume.min())
            vmax = float(volume.max())
            if vmax - vmin < 1e-8:
                vol_u16 = np.zeros(volume.shape, dtype=np.uint16)
            else:
                vol_u16 = ((volume.astype(np.float64) - vmin) / (vmax - vmin) * 65535.0).astype(np.uint16)
            conversion_mode = "normalize"

        result_u16 = np.zeros_like(vol_u16, dtype=np.uint16)
        depth = vol_u16.shape[0]

        musica_via_dll = EnhancementOps._load_imagemaster_musica_func()
        use_dll = musica_via_dll is not None

        # 调试输出
        print("[mUSICA] 参数: Level=%d, Strength=%d" % (level, strength))
        print("[mUSICA] 输入: dtype=%s, shape=%s" % (original_dtype, volume.shape))
        print("[mUSICA] 转换模式: %s" % conversion_mode)
        print("[mUSICA] 处理数据(uint16): min=%d, max=%d" % (vol_u16.min(), vol_u16.max()))
        print("[mUSICA] 使用DLL: %s" % ("是" if use_dll else "否(回退Python实现)"))

        for z in range(depth):
            if use_dll:
                try:
                    result_u16[z] = EnhancementOps._musica_slice_imagemaster(vol_u16[z], level, strength)
                except Exception:
                    use_dll = False
                    result_u16[z] = EnhancementOps._musica_slice_u16(vol_u16[z], level, strength)
            else:
                result_u16[z] = EnhancementOps._musica_slice_u16(vol_u16[z], level, strength)
            if progress_callback and z % max(1, depth // 20) == 0:
                progress_callback(z, depth)

        # 根据转换模式还原到原始类型
        if conversion_mode == "direct":
            # uint16 直接返回
            return result_u16
        elif conversion_mode == "view_int16":
            # int16: 按位解释回去（与输入对称）
            return result_u16.view(np.int16)
        else:
            # normalize 模式：线性映射回原始范围
            if vmax - vmin < 1e-8:
                restored = np.full(volume.shape, vmin, dtype=np.float64)
            else:
                restored = result_u16.astype(np.float64) / 65535.0 * (vmax - vmin) + vmin

            if np.issubdtype(original_dtype, np.integer):
                info = np.iinfo(original_dtype)
                restored = np.clip(restored, info.min, info.max)
            return restored.astype(original_dtype)

    @staticmethod
    def _musica_slice_u16(img_u16: np.ndarray, level: int, strength: int) -> np.ndarray:
        """单张16位灰度切片的 mUSICA 近似实现（Level/Strength 驱动）"""
        src = img_u16.astype(np.float32) / 65535.0

        # Level: 控制参与的尺度数量
        # Strength: 控制细节增益
        gain = 0.15 + (strength / 100.0) * 1.35

        detail_acc = np.zeros_like(src, dtype=np.float32)
        for idx in range(level):
            sigma = 0.8 * (2.0 ** idx)
            blur = cv2.GaussianBlur(src, (0, 0), sigma)
            detail = src - blur
            detail_acc += detail / float(idx + 1)

        # 轻度局部对比度提升，避免过冲
        local_sigma = 1.5 + level * 0.8
        local_mean = cv2.GaussianBlur(src, (0, 0), local_sigma)
        local_component = src - local_mean

        out = src + gain * detail_acc + 0.25 * gain * local_component
        out = np.clip(out, 0.0, 1.0)
        return (out * 65535.0).astype(np.uint16)
