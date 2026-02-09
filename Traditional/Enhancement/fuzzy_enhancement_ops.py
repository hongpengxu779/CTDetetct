"""
基于光照补偿的模糊增强方法 (Fuzzy Enhancement with Illumination Compensation)

针对CT图像特征，构建由以下步骤组成的模糊增强方法：
1. 形态学预处理 —— 顶帽/底帽变换锐化
2. 模糊域映射 —— 三角形隶属度函数
3. 轮廓识别 —— 高斯低通滤波 + Prewitt梯度 + 非极大值抑制 + 双阈值
4. 光照补偿 —— 滤除场效应 B'(x)
5. 反模糊化 —— 模糊域逆变换回空间域

参考公式：
  (15) that(x,y) = f(x,y) - [f(x,y) ⊙ B'(x,y)] ⊕ B'(x,y)
       bhat(x,y) = [f(x,y) ⊕ B'(x,y)] ⊙ B'(x,y) - f(x,y)
       γ(x,y) = [f(x,y) + that(x,y)] - bhat(x,y)
  (16) μ_ij = (x_ij - x_min) / (x_max - x_min)
  (17) H(u,v) = exp(-D(u,v)^2 / (2σ^2))    高斯低通
  (18) Prewitt梯度 + 非极大值抑制 + 双阈值连接
  (19) x_ij = μ'_ij * (x_max - x_min) + x_min
"""

import numpy as np
import cv2
from scipy import ndimage


class FuzzyEnhancementOps:
    """基于光照补偿的模糊增强操作类"""

    # ------------------------------------------------------------------ #
    #  步骤 1 : 形态学预处理  (公式 15)
    # ------------------------------------------------------------------ #
    @staticmethod
    def morphological_sharpen(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
        """
        利用顶帽 (top-hat) 和底帽 (bottom-hat) 变换进行形态学锐化。

        公式 (15):
            that(x,y)  = f - (f ⊙ B') ⊕ B'       (顶帽: 突出亮细节)
            bhat(x,y)  = (f ⊕ B') ⊙ B' - f        (底帽: 突出暗细节)
            γ(x,y)     = [f + that] - bhat          (增强结果)

        其中 ⊙ 为腐蚀(erode)，⊕ 为膨胀(dilate)，B' 为结构元素。

        参数
        ----
        image : np.ndarray (float64, 2D)
            输入灰度图像
        kernel_size : int
            结构元素大小，默认5

        返回
        ----
        np.ndarray : 形态学锐化后的图像
        """
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
        )
        # 顶帽变换: f - opening(f) = f - dilate(erode(f, B), B)
        top_hat = cv2.morphologyEx(image, cv2.MORPH_TOPHAT, kernel)
        # 底帽变换: closing(f) - f = erode(dilate(f, B), B) - f
        bottom_hat = cv2.morphologyEx(image, cv2.MORPH_BLACKHAT, kernel)
        # γ(x,y) = f + top_hat - bottom_hat
        enhanced = image.astype(np.float64) + top_hat.astype(np.float64) - bottom_hat.astype(np.float64)
        return enhanced

    # ------------------------------------------------------------------ #
    #  步骤 2 : 模糊域映射  (公式 16)
    # ------------------------------------------------------------------ #
    @staticmethod
    def fuzzy_transform(image: np.ndarray) -> tuple:
        """
        将空间域图像映射到模糊域 [0, 1]，使用三角形隶属度函数。

        公式 (16):  μ_ij = (x_ij - x_min) / (x_max - x_min)

        参数
        ----
        image : np.ndarray
            输入图像（任意范围）

        返回
        ----
        (fuzzy_image, x_min, x_max) : 模糊域图像 [0,1], 原始极值
        """
        x_min = float(image.min())
        x_max = float(image.max())
        if x_max - x_min < 1e-8:
            return np.zeros_like(image, dtype=np.float64), x_min, x_max
        fuzzy = (image.astype(np.float64) - x_min) / (x_max - x_min)
        return fuzzy, x_min, x_max

    # ------------------------------------------------------------------ #
    #  步骤 3 : 轮廓识别 — 高斯低通 + Prewitt + NMS + 双阈值
    # ------------------------------------------------------------------ #
    @staticmethod
    def gaussian_lowpass_filter(image: np.ndarray, sigma: float = 1.5) -> np.ndarray:
        """
        使用高斯低通滤波器对图像进行平滑，抑制噪点。

        公式 (17):  H(u,v) = exp(-D(u,v)^2 / (2σ^2))

        在空间域等效于高斯模糊。

        参数
        ----
        image : np.ndarray
            输入图像
        sigma : float
            高斯标准差

        返回
        ----
        np.ndarray : 滤波后的图像
        """
        # 高斯核大小自动根据sigma确定，确保奇数
        ksize = int(np.ceil(sigma * 6)) | 1  # 保证奇数
        ksize = max(ksize, 3)
        return cv2.GaussianBlur(image, (ksize, ksize), sigma)

    @staticmethod
    def prewitt_edge_detection(image: np.ndarray,
                                low_threshold: float = 0.05,
                                high_threshold: float = 0.15) -> tuple:
        """
        通过一阶微分 Prewitt 算子计算梯度幅值和方向，
        然后进行非极大值抑制和双阈值连接。

        公式 (18):
            ∇f = [∂f/∂x, ∂f/∂y]
            mag(∇f) = sqrt((∂f/∂x)^2 + (∂f/∂y)^2)
            θ(x,y)  = arctan(∂f/∂y / ∂f/∂x)

        参数
        ----
        image : np.ndarray (float64)
            输入图像（已经过高斯平滑）
        low_threshold : float
            双阈值中的低阈值 (相对于梯度最大值的比例)
        high_threshold : float
            双阈值中的高阈值 (相对于梯度最大值的比例)

        返回
        ----
        (edge_map, gradient_magnitude) : 二值边缘图, 梯度幅值
        """
        # Prewitt 算子
        prewitt_x = np.array([[-1, 0, 1],
                               [-1, 0, 1],
                               [-1, 0, 1]], dtype=np.float64)
        prewitt_y = np.array([[ 1,  1,  1],
                               [ 0,  0,  0],
                               [-1, -1, -1]], dtype=np.float64)

        gx = cv2.filter2D(image, cv2.CV_64F, prewitt_x)
        gy = cv2.filter2D(image, cv2.CV_64F, prewitt_y)

        # 梯度幅值和方向
        magnitude = np.sqrt(gx ** 2 + gy ** 2)
        direction = np.arctan2(gy, gx)  # [-π, π]

        # 非极大值抑制 (NMS)
        nms = FuzzyEnhancementOps._non_maximum_suppression(magnitude, direction)

        # 双阈值连接
        mag_max = nms.max()
        if mag_max < 1e-8:
            return np.zeros_like(image, dtype=np.uint8), magnitude

        low_val = low_threshold * mag_max
        high_val = high_threshold * mag_max

        edge_map = FuzzyEnhancementOps._hysteresis_threshold(nms, low_val, high_val)

        return edge_map, magnitude

    @staticmethod
    def _non_maximum_suppression(magnitude: np.ndarray, direction: np.ndarray) -> np.ndarray:
        """
        非极大值抑制：沿梯度方向保留极值点，抑制非极值。
        """
        h, w = magnitude.shape
        nms = np.zeros_like(magnitude)

        # 将角度转为 0-180 度
        angle = np.rad2deg(direction) % 180

        for i in range(1, h - 1):
            for j in range(1, w - 1):
                a = angle[i, j]
                m = magnitude[i, j]

                # 确定插值邻居
                if (0 <= a < 22.5) or (157.5 <= a <= 180):
                    n1, n2 = magnitude[i, j - 1], magnitude[i, j + 1]
                elif 22.5 <= a < 67.5:
                    n1, n2 = magnitude[i - 1, j + 1], magnitude[i + 1, j - 1]
                elif 67.5 <= a < 112.5:
                    n1, n2 = magnitude[i - 1, j], magnitude[i + 1, j]
                else:
                    n1, n2 = magnitude[i - 1, j - 1], magnitude[i + 1, j + 1]

                if m >= n1 and m >= n2:
                    nms[i, j] = m

        return nms

    @staticmethod
    def _hysteresis_threshold(nms: np.ndarray,
                               low: float, high: float) -> np.ndarray:
        """
        双阈值滞后连接：
        - 高于 high 的像素确定为边缘
        - 介于 low ~ high 之间的像素，若与强边缘 8-邻接则保留
        """
        strong = (nms >= high).astype(np.uint8)
        weak = ((nms >= low) & (nms < high)).astype(np.uint8)

        # 8-连通标记强边缘区域
        labeled, num_features = ndimage.label(strong, structure=np.ones((3, 3)))

        # 将与强边缘相连的弱边缘加入
        edge = strong.copy()
        # 膨胀强边缘一次来找到 8-邻域连接的弱边缘
        dilated_strong = cv2.dilate(strong, np.ones((3, 3), np.uint8), iterations=1)
        edge[np.logical_and(weak == 1, dilated_strong == 1)] = 1

        return (edge * 255).astype(np.uint8)

    # ------------------------------------------------------------------ #
    #  步骤 4 : 光照补偿  (2.4 节)
    # ------------------------------------------------------------------ #
    @staticmethod
    def illumination_compensation(fuzzy_image: np.ndarray,
                                   edge_map: np.ndarray,
                                   compensation_sigma: float = 30.0,
                                   compensation_strength: float = 0.5) -> np.ndarray:
        """
        光照补偿：估计并滤除场效应 B'(x)。

        利用大尺度高斯模糊估计低频光照分量（场效应），
        再结合边缘信息进行自适应补偿，避免边缘区域过度平滑。

        算法：
            B'(x) = GaussianBlur(fuzzy_image, large_sigma)   # 场效应估计
            补偿后 = fuzzy_image - strength * B'(x) * (1 - edge_weight)
            归一化回 [0, 1]

        参数
        ----
        fuzzy_image : np.ndarray (float64, [0,1])
            模糊域图像
        edge_map : np.ndarray (uint8, 0/255)
            边缘二值图
        compensation_sigma : float
            场效应估计的高斯核标准差（越大估计越平滑）
        compensation_strength : float
            补偿强度 [0, 1]

        返回
        ----
        np.ndarray : 光照补偿后的模糊域图像 [0, 1]
        """
        # 估计场效应 (低频光照分量)
        ksize = int(np.ceil(compensation_sigma * 6)) | 1
        ksize = max(ksize, 3)
        field_effect = cv2.GaussianBlur(fuzzy_image, (ksize, ksize), compensation_sigma)

        # 边缘权重：边缘区域不做过度补偿
        edge_weight = edge_map.astype(np.float64) / 255.0
        # 稍微扩展边缘影响区域
        edge_weight = cv2.GaussianBlur(edge_weight, (5, 5), 1.0)

        # 光照补偿：减去场效应的非边缘部分
        # 补偿后 = fuzzy_image - strength * field_effect * (1 - edge_weight) + strength * 0.5
        # 加 0.5 * strength 是为了保持整体亮度均衡
        compensated = fuzzy_image - compensation_strength * field_effect * (1 - edge_weight) \
                      + compensation_strength * 0.5

        # 裁剪回 [0, 1]
        compensated = np.clip(compensated, 0.0, 1.0)
        return compensated

    # ------------------------------------------------------------------ #
    #  步骤 5 : 反模糊化  (公式 19)
    # ------------------------------------------------------------------ #
    @staticmethod
    def inverse_fuzzy_transform(fuzzy_image: np.ndarray,
                                 x_min: float, x_max: float) -> np.ndarray:
        """
        模糊域逆变换，将隶属度映射回空间域。

        公式 (19):  x_ij = μ'_ij * (x_max - x_min) + x_min

        参数
        ----
        fuzzy_image : np.ndarray (float64, [0,1])
            模糊域图像
        x_min, x_max : float
            原始空间域的极值

        返回
        ----
        np.ndarray : 空间域图像
        """
        return fuzzy_image * (x_max - x_min) + x_min

    # ================================================================== #
    #   完整流水线 —— 单切片处理
    # ================================================================== #
    @staticmethod
    def enhance_slice(image: np.ndarray,
                      morph_kernel_size: int = 5,
                      gauss_sigma: float = 1.5,
                      prewitt_low: float = 0.05,
                      prewitt_high: float = 0.15,
                      comp_sigma: float = 30.0,
                      comp_strength: float = 0.5) -> np.ndarray:
        """
        对单张2D灰度切片执行完整的光照补偿模糊增强流水线。

        参数
        ----
        image : np.ndarray
            输入2D灰度图像
        morph_kernel_size : int
            形态学结构元素大小
        gauss_sigma : float
            高斯低通滤波标准差（用于噪点抑制）
        prewitt_low : float
            Prewitt双阈值 - 低阈值比例
        prewitt_high : float
            Prewitt双阈值 - 高阈值比例
        comp_sigma : float
            光照补偿高斯核标准差
        comp_strength : float
            光照补偿强度

        返回
        ----
        np.ndarray : 增强后的图像（与输入同范围）
        """
        img_f = image.astype(np.float64)

        # 步骤 1: 形态学预处理 (公式 15)
        morphed = FuzzyEnhancementOps.morphological_sharpen(img_f, morph_kernel_size)

        # 步骤 2: 模糊域映射 (公式 16)
        fuzzy, x_min, x_max = FuzzyEnhancementOps.fuzzy_transform(morphed)

        # 步骤 3: 轮廓识别 (公式 17, 18)
        # 3a. 高斯低通滤波抑制噪点
        smoothed = FuzzyEnhancementOps.gaussian_lowpass_filter(fuzzy, gauss_sigma)
        # 3b. Prewitt边缘检测 + NMS + 双阈值
        edge_map, gradient_mag = FuzzyEnhancementOps.prewitt_edge_detection(
            smoothed, prewitt_low, prewitt_high
        )

        # 步骤 4: 光照补偿 (2.4节)
        compensated = FuzzyEnhancementOps.illumination_compensation(
            fuzzy, edge_map, comp_sigma, comp_strength
        )

        # 步骤 5: 反模糊化 (公式 19)
        result = FuzzyEnhancementOps.inverse_fuzzy_transform(compensated, x_min, x_max)

        return result

    # ================================================================== #
    #   3D 体数据处理
    # ================================================================== #
    @staticmethod
    def fuzzy_enhancement_3d(volume: np.ndarray,
                              morph_kernel_size: int = 5,
                              gauss_sigma: float = 1.5,
                              prewitt_low: float = 0.05,
                              prewitt_high: float = 0.15,
                              comp_sigma: float = 30.0,
                              comp_strength: float = 0.5,
                              progress_callback=None) -> np.ndarray:
        """
        对3D体数据逐切片应用基于光照补偿的模糊增强方法。

        参数
        ----
        volume : np.ndarray (Z, Y, X)
            输入的三维图像数据
        morph_kernel_size : int
            形态学结构元素大小，默认5
        gauss_sigma : float
            高斯低通滤波标准差，默认1.5
        prewitt_low : float
            Prewitt双阈值 - 低阈值比例，默认0.05
        prewitt_high : float
            Prewitt双阈值 - 高阈值比例，默认0.15
        comp_sigma : float
            光照补偿高斯核标准差，默认30.0
        comp_strength : float
            光照补偿强度，默认0.5
        progress_callback : callable, optional
            进度回调函数 (current, total)

        返回
        ----
        np.ndarray : 增强后的三维数据，与输入类型一致
        """
        original_dtype = volume.dtype
        result = np.zeros_like(volume, dtype=np.float64)

        depth = volume.shape[0]
        for z in range(depth):
            result[z] = FuzzyEnhancementOps.enhance_slice(
                volume[z],
                morph_kernel_size=morph_kernel_size,
                gauss_sigma=gauss_sigma,
                prewitt_low=prewitt_low,
                prewitt_high=prewitt_high,
                comp_sigma=comp_sigma,
                comp_strength=comp_strength,
            )
            if progress_callback and z % max(1, depth // 20) == 0:
                progress_callback(z, depth)

        # 映射回原始数据类型
        if np.issubdtype(original_dtype, np.integer):
            info = np.iinfo(original_dtype)
            result = np.clip(result, info.min, info.max)
        return result.astype(original_dtype)
