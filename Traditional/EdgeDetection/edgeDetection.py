import SimpleITK as sitk
import numpy as np
import cv2 as cv
from File.DataTransform import to_float255_fixed, to_uint16_fixed
import itk
from scipy import ndimage

class EdgeDetection:
    def __init__(self):
        self.canny_sitk = None

    def canny2D(self, image_array):
        """
        输入: numpy array (2D 或 3D)
        输出: numpy array (2D 或 3D, uint16)
        """
        image_array = to_float255_fixed(image_array)
        if image_array.ndim == 2:
            edges = cv.Canny(image_array.astype(np.uint8), 40, 120)
            self.canny_sitk = to_uint16_fixed(edges)
            return self.canny_sitk

        elif image_array.ndim == 3:
            # 向量化方式：用列表推导再堆叠
            edges_stack = [
                (cv.Canny(image_array[z, :, :].astype(np.uint8), 10, 30).astype(np.uint16) * 257)
                for z in range(image_array.shape[0])
            ]
            self.canny_sitk = to_uint16_fixed(np.stack(edges_stack, axis=0))
            return self.canny_sitk

        else:
            raise ValueError("输入必须是 2D 或 3D numpy array")


    def canny3D(self, image_array, sigma=2.5, low_thresh=0.008, high_thresh=0.05):
        image_array = image_array / 65535.0
        itk_image = itk.GetImageFromArray(image_array.astype(np.float32))

        # 定义 Canny 过滤器
        canny_filter = itk.CannyEdgeDetectionImageFilter.New(itk_image)
        canny_filter.SetVariance(sigma ** 2)  # Gaussian smoothing
        canny_filter.SetLowerThreshold(low_thresh)
        canny_filter.SetUpperThreshold(high_thresh)

        # 执行
        canny_filter.Update()
        edges_itk = canny_filter.GetOutput()

        # 转回 numpy
        self.canny_sitk = itk.GetArrayFromImage(edges_itk)  # 还是 [z,y,x]

        # 筛选轮廓
        self.canny_sitk = self.filter_edges_3d(self.canny_sitk, 1000, 100000)
        # self.canny_sitk = (self.canny_sitk / self.canny_sitk.max() * 65535).astype(np.uint16)

        return self.canny_sitk

    def filter_edges_3d(self, edges_np, min_voxels=1000, max_voxels=10000):
        """
        输入: edges_np = 3D numpy array (0/255/65535)
        输出: 只保留大连通区域的 edges
        """
        mask = edges_np > 0
        labeled, num = ndimage.label(mask)
        sizes = ndimage.sum(mask, labeled, range(1, num + 1))

        # 筛选
        keep_labels = [i + 1 for i, s in enumerate(sizes) if s >= min_voxels and s<= max_voxels]
        filtered = np.isin(labeled, keep_labels).astype(np.uint16) * 65535

        return filtered



