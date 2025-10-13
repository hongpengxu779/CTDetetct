#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ITK曲率流去噪示例脚本

使用方法:
python curvature_flow_filter.py input_image.mhd output_image.mhd 10 0.0625

参数:
1. 输入图像路径
2. 输出图像路径
3. 迭代次数（整数）
4. 时间步长（浮点数）
"""

import itk
import argparse
import numpy as np
import SimpleITK as sitk

def apply_curvature_flow_filter(input_file, output_file, num_iterations, time_step):
    """
    应用ITK曲率流滤波器进行图像去噪
    
    参数:
    ----
    input_file : str
        输入图像文件路径
    output_file : str
        输出图像文件路径
    num_iterations : int
        迭代次数
    time_step : float
        时间步长
    """
    print(f"正在处理: {input_file}")
    print(f"迭代次数: {num_iterations}, 时间步长: {time_step}")
    
    # 设置图像类型
    InputPixelType = itk.F
    OutputPixelType = itk.F  # 保持浮点输出，避免精度损失
    Dimension = 3  # 处理3D图像
    
    InputImageType = itk.Image[InputPixelType, Dimension]
    OutputImageType = itk.Image[OutputPixelType, Dimension]
    
    # 读取图像
    print("正在读取图像...")
    ReaderType = itk.ImageFileReader[InputImageType]
    reader = ReaderType.New()
    reader.SetFileName(input_file)
    
    # 应用曲率流滤波器
    print("应用曲率流滤波器...")
    FilterType = itk.CurvatureFlowImageFilter[InputImageType, InputImageType]
    curvatureFlowFilter = FilterType.New()
    
    curvatureFlowFilter.SetInput(reader.GetOutput())
    curvatureFlowFilter.SetNumberOfIterations(num_iterations)
    curvatureFlowFilter.SetTimeStep(time_step)
    
    # 如果需要将输出缩放到特定范围，可以使用RescaleIntensityImageFilter
    RescaleFilterType = itk.RescaleIntensityImageFilter[InputImageType, OutputImageType]
    rescaler = RescaleFilterType.New()
    rescaler.SetInput(curvatureFlowFilter.GetOutput())
    
    # 设置输出范围，这里保持原始范围
    rescaler.SetOutputMinimum(0)
    rescaler.SetOutputMaximum(255)
    
    # 写入结果
    print(f"写入结果到: {output_file}")
    WriterType = itk.ImageFileWriter[OutputImageType]
    writer = WriterType.New()
    writer.SetFileName(output_file)
    writer.SetInput(rescaler.GetOutput())
    
    try:
        writer.Update()
        print("处理完成!")
        return True
    except Exception as e:
        print(f"处理过程中出错: {str(e)}")
        return False

def main():
    # 命令行参数解析
    parser = argparse.ArgumentParser(description="应用ITK曲率流滤波器进行图像去噪")
    parser.add_argument("input_image", help="输入图像文件路径")
    parser.add_argument("output_image", help="输出图像文件路径")
    parser.add_argument("number_of_iterations", type=int, help="迭代次数")
    parser.add_argument("time_step", type=float, help="时间步长")
    args = parser.parse_args()
    
    # 应用滤波器
    success = apply_curvature_flow_filter(
        args.input_image, 
        args.output_image,
        args.number_of_iterations,
        args.time_step
    )
    
    # 返回状态码
    return 0 if success else 1

if __name__ == "__main__":
    main()