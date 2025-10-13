import numpy as np
from PyQt5 import QtGui
import SimpleITK as sitk

def array_to_qpixmap(arr: np.ndarray):
    """
    将二维 NumPy 数组转换为 Qt 的 QPixmap，用于在 QLabel 等控件中显示。
    支持灰度图像和RGB彩色图像。

    处理流程：
    1. 检测输入是灰度图像 (H, W) 还是RGB图像 (H, W, 3/4)；
    2. 对于灰度图像：归一化到 [0, 255] 并使用 Format_Grayscale8；
    3. 对于RGB图像：确保是uint8类型并使用 Format_RGB888；
    4. 转换为 QPixmap 用于显示。

    参数
    ----
    arr : np.ndarray
        输入的二维图像数组
        - 灰度: (height, width)，像素范围 [0, 65535]
        - RGB: (height, width, 3)，像素范围 [0, 255]，dtype=uint8

    返回
    ----
    QtGui.QPixmap
        转换后的 Qt Pixmap，可用于 QLabel.setPixmap() 显示。
    """
    # 检查是否为RGB图像
    if len(arr.shape) == 3 and arr.shape[2] in [3, 4]:
        # RGB或RGBA图像
        h, w, channels = arr.shape
        
        # 确保数据类型为uint8
        if arr.dtype != np.uint8:
            arr = np.clip(arr, 0, 255).astype(np.uint8)
        
        # 只使用前3个通道（忽略alpha通道）
        if channels == 4:
            arr = arr[:, :, :3]
            channels = 3
        
        # 创建RGB图像
        # 注意：QImage需要连续的内存布局
        arr = np.ascontiguousarray(arr)
        
        bytes_per_line = w * channels
        qimg = QtGui.QImage(arr.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        
    else:
        # 灰度图像（原有逻辑）
        # 确保数据类型为 uint16
        arr = arr.astype(np.uint16)

        # 归一化到 [0,255] 并转为 uint8
        arr = (arr / 65535.0 * 255).astype(np.uint8)

        # 获取图像尺寸
        h, w = arr.shape

        # 构造 Qt 灰度图像 (单通道8位灰度)
        qimg = QtGui.QImage(arr.data, w, h, w, QtGui.QImage.Format_Grayscale8)

    # 转换为 QPixmap 返回
    return QtGui.QPixmap.fromImage(qimg)

def to_float255_fixed(img_uint16):
    return (img_uint16.astype(np.float32) / 65535.0) * 255.0

def to_uint16_fixed(img_float):
    return (img_float / 255.0 * 65535.0).astype(np.uint16)


class SimpleITKImage:
    """SimpleITK图像工具类"""
    
    @staticmethod
    def from_numpy(array, spacing=(1.0, 1.0, 1.0), origin=(0.0, 0.0, 0.0), downscale=False):
        """
        将NumPy数组转换为SimpleITK图像
        
        参数
        ----
        array : np.ndarray
            三维数组，形状为(z, y, x)
        spacing : tuple
            体素间距，形式为(sx, sy, sz)
        origin : tuple
            原点坐标，形式为(ox, oy, oz)
        downscale : bool
            是否降采样以节省内存，默认为False
            
        返回
        ----
        sitk.Image
            SimpleITK图像对象
        """
        # 如果数组尺寸太大且开启了降采样选项，进行降采样
        if downscale and max(array.shape) > 500:
            # 计算降采样因子，确保最大维度不超过500
            z, y, x = array.shape
            scale = max(1, int(max(array.shape) / 500))
            
            # 使用简单的步长采样进行降采样
            array = array[::scale, ::scale, ::scale]
            
            # 更新间距以反映降采样
            spacing = (spacing[0]*scale, spacing[1]*scale, spacing[2]*scale)
            print(f"数组已降采样: 从 {(z,y,x)} 到 {array.shape}, 间距调整为 {spacing}")
        
        # 数据归一化 - 与原始代码一致
        # 确保数据范围适合显示
        if array.min() < 0:
            # 如果有负值，将所有值平移到正值区间
            array = array - array.min()
        
        # 归一化到0-1范围
        if array.max() > 0:
            array = array / array.max()
        
        # 转换到16位整型范围(0-65535)
        array = (array * 65535.0).astype(np.uint16)
        
        # 确保数组是float32类型，SimpleITK更喜欢这种类型
        array = array.astype(np.float32)
        
        # 注意: SimpleITK.GetImageFromArray会将NumPy的轴顺序z,y,x转为SimpleITK的轴顺序x,y,z
        # 所以不需要手动调整轴顺序
        sitk_image = sitk.GetImageFromArray(array)
        
        # 设置元数据
        sitk_image.SetSpacing(spacing)
        sitk_image.SetOrigin(origin)
        
        return sitk_image
