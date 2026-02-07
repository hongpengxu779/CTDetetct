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
            # RAW 文件没有元信息，需要用户提供 shape, 可选提供 spacing 和 dtype
            if self.shape is None:
                raise ValueError("读取 .raw 必须提供 shape=(z,y,x)")

            # 先尝试用提供的 dtype 读取，并对文件大小/shape 做校验和容错处理
            import os
            file_size = os.path.getsize(self.filename)
            expected_voxels = int(np.prod(self.shape))
            provided_dtype = np.dtype(self.dtype)
            expected_bytes = expected_voxels * provided_dtype.itemsize

            # 如果文件大小与期望不匹配，尝试常见 dtype 自动匹配
            dtype_to_use = provided_dtype
            if file_size != expected_bytes:
                common = [np.uint16, np.uint8, np.float32]
                for dt in common:
                    if file_size == expected_voxels * np.dtype(dt).itemsize:
                        dtype_to_use = np.dtype(dt)
                        break

            # 读取原始数据
            raw = np.fromfile(self.filename, dtype=dtype_to_use)

            # 尝试按 C-order 重塑为 (z,y,x)，若失败则尝试 Fortran-order（很多 raw 以 X 快速变化）
            try:
                data = raw.reshape(self.shape)
            except Exception:
                try:
                    data = raw.reshape(self.shape, order='F')
                except Exception as e:
                    raise ValueError(
                        f"无法将 RAW 文件重塑为给定 shape={self.shape} (dtype={dtype_to_use}). "
                        f"文件大小={file_size} 字节, 期望 {expected_voxels} voxels * {dtype_to_use.itemsize} bytes"
                    ) from e

            # 将 NumPy 数组转换为 SimpleITK Image
            self.image = sitk.GetImageFromArray(data)

            # 如果用户提供了 spacing，就设置；否则设为默认 (1.0,1.0,1.0)
            if self.spacing:
                self.image.SetSpacing(self.spacing)
            else:
                self.image.SetSpacing((1.0, 1.0, 1.0))

            # RAW 没有方向信息，显式设置为单位方向矩阵，避免与 NIfTI 行为差异
            try:
                self.image.SetDirection((1.0, 0.0, 0.0,
                                         0.0, 1.0, 0.0,
                                         0.0, 0.0, 1.0))
            except Exception:
                # 如果 SimpleITK 版本/平台不支持设置方向则忽略
                pass
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
