import numpy as np
import SimpleITK as sitk


class CTImageData:
    """负责 CT 数据的读取和管理"""

    def __init__(self, filename, shape=None, spacing=None, dtype=np.uint16):
        """
        初始化并读取 CT 数据

        参数
        ----
        filename : str
            输入影像文件路径 (.nii, .mhd, .dcm, .raw)
        shape : tuple, optional
            如果是 .raw 文件，必须提供 (z, y, x)
        spacing : tuple, optional
            体素间距 (sx, sy, sz)，如果是 .raw 文件需要传入
        dtype : numpy.dtype, default=np.uint16
            数据类型，默认 16 位无符号整型
        """
        self.filename = filename
        self.shape = shape
        self.spacing = spacing
        self.dtype = dtype

        self.image = None   # SimpleITK Image
        self.array = None   # NumPy ndarray (z, y, x)

        self.load_image()

    def load_image(self):
        """根据文件类型读取 CT 数据"""
        if self.filename.endswith(".raw"):
            if self.shape is None:
                raise ValueError("读取 .raw 必须提供 shape=(z,y,x)")
            data = np.fromfile(self.filename, dtype=self.dtype).reshape(self.shape)
            self.image = sitk.GetImageFromArray(data)
            if self.spacing:
                self.image.SetSpacing(self.spacing)
        else:
            self.image = sitk.ReadImage(self.filename)

        # 转为 NumPy
        self.array = sitk.GetArrayFromImage(self.image)
        self.shape = self.array.shape
        self.spacing = self.image.GetSpacing()

    def get_slice(self, axis, index):
        """
        获取某个方向的切片

        参数
        ----
        axis : int
            0=Axial (横断), 1=Coronal (冠状), 2=Sagittal (矢状)
        index : int
            切片索引

        返回
        ----
        np.ndarray
            对应的 2D 切片 (uint16)
        """
        if axis == 0:  # Axial
            return self.array[index, :, :]
        elif axis == 1:  # Coronal
            return self.array[:, index, :]
        elif axis == 2:  # Sagittal
            return self.array[:, :, index]
        else:
            raise ValueError("axis 必须是 0(Axial), 1(Coronal), 2(Sagittal)")

    def get_mip(self, axis=0):
        """
        最大强度投影 (MIP)

        参数
        ----
        axis : int
            投影方向 (0=z, 1=y, 2=x)

        返回
        ----
        np.ndarray
            MIP 图像 (uint16)
        """
        return np.max(self.array, axis=axis)
