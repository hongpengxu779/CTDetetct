import itk
from PyQt5 import QtWidgets, QtCore
from File.DataTransform import to_float255_fixed, to_uint16_fixed


class Filter_op:
    def __init__(self):
        self.output = None
    
    def apply_anisotropic_filter(self, image_array, spacing=None, parent=None):
        """
        应用各向异性平滑滤波
        
        参数
        ----
        image_array : numpy.ndarray
            输入的三维图像数据
        spacing : tuple, optional
            像素间距 (sx, sy, sz)
        parent : QWidget, optional
            父窗口，用于显示进度对话框
        
        返回
        ----
        numpy.ndarray
            滤波后的图像数据
        """
        if image_array is None:
            if parent:
                QtWidgets.QMessageBox.warning(parent, "警告", "请先加载数据")
            return None

        try:
            # 在这里不显示进度对话框，由调用者负责
            # 进度和UI更新由主界面处理

            image_array = to_float255_fixed(image_array)

            # 转换 numpy -> ITK
            Dimension = 3
            InputImageType = itk.Image[itk.F, Dimension]
            itk_image = itk.GetImageFromArray(image_array)  # 自动变成 3D ITK Image
            
            # 如果提供了spacing，设置到ITK图像
            if spacing:
                itk_image.SetSpacing(spacing)

            # 应用曲率各向异性扩散
            FilterType = itk.CurvatureAnisotropicDiffusionImageFilter[InputImageType, InputImageType]
            filter = FilterType.New(
                Input=itk_image,
                NumberOfIterations=5,
                TimeStep=0.0625,
                ConductanceParameter=3.0,
            )
            filter.Update()
              # 转换回 numpy
            output_itk = filter.GetOutput()
            output_np = itk.GetArrayFromImage(output_itk)  # shape 还是 (z, y, x)
            self.output = to_uint16_fixed(output_np)
            # 由调用者关闭进度对话框
            return self.output

        except Exception as e:
            if parent:
                QtWidgets.QMessageBox.critical(parent, "错误", f"应用滤波时出错：{str(e)}")
            return None

    def apply_curvature_flow_filter(self, image_array, num_iterations=10, time_step=0.0625, spacing=None, parent=None):
        """
        应用曲率流滤波去噪
        
        参数
        ----
        image_array : numpy.ndarray
            输入的三维图像数据
        num_iterations : int
            迭代次数，默认10次
        time_step : float
            时间步长，默认0.0625
        spacing : tuple, optional
            像素间距 (sx, sy, sz)
        parent : QWidget, optional
            父窗口，用于显示进度对话框
        
        返回
        ----
        numpy.ndarray
            滤波后的图像数据
        """
        if image_array is None:
            if parent:
                QtWidgets.QMessageBox.warning(parent, "警告", "请先加载数据")
            return None

        try:
            # 转换为浮点数据
            image_array = to_float255_fixed(image_array)

            # 转换 numpy -> ITK
            Dimension = 3
            InputImageType = itk.Image[itk.F, Dimension]
            itk_image = itk.GetImageFromArray(image_array)  # 自动变成 3D ITK Image
            
            # 如果提供了spacing，设置到ITK图像
            if spacing:
                itk_image.SetSpacing(spacing)

            # 应用曲率流滤波器
            FilterType = itk.CurvatureFlowImageFilter[InputImageType, InputImageType]
            curvature_flow = FilterType.New(
                Input=itk_image,
                NumberOfIterations=num_iterations,
                TimeStep=time_step
            )
            curvature_flow.Update()
            
            # 转换回 numpy
            output_itk = curvature_flow.GetOutput()
            output_np = itk.GetArrayFromImage(output_itk)
            self.output = to_uint16_fixed(output_np)
            
            return self.output

        except Exception as e:
            if parent:
                QtWidgets.QMessageBox.critical(parent, "错误", f"应用曲率去噪时出错：{str(e)}")
            return None
