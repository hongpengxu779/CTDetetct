# -*- coding: utf-8 -*-
"""图像融合工具 - 将分割结果叠加到原始图像上"""

import numpy as np
import nibabel as nib


def overlay_segmentation(original_array, mask_array, color=(255, 0, 0), alpha=0.5):
    """
    将分割mask以半透明彩色叠加到原始图像上，生成RGB彩色图像
    
    Args:
        original_array (np.ndarray): 原始图像数组 (Z, Y, X)，通常是uint16
        mask_array (np.ndarray): 分割mask数组 (Z, Y, X)，二值或uint8
        color (tuple): RGB颜色，范围0-255，例如(255, 0, 0)表示红色
        alpha (float): 透明度，范围0-1，0表示完全透明，1表示完全不透明
    
    Returns:
        np.ndarray: 融合后的RGB数组 (Z, Y, X, 3)，dtype=uint8
    """
    print(f"开始融合图像...")
    print(f"原始图像: shape={original_array.shape}, dtype={original_array.dtype}, range=[{original_array.min()}, {original_array.max()}]")
    print(f"分割mask: shape={mask_array.shape}, dtype={mask_array.dtype}, range=[{mask_array.min()}, {mask_array.max()}]")
    print(f"融合参数: color={color}, alpha={alpha}")
    
    # 确保数组形状匹配
    if original_array.shape != mask_array.shape:
        raise ValueError(f"原始图像和mask形状不匹配: {original_array.shape} vs {mask_array.shape}")
    
    # 归一化原始图像到0-255 (uint8范围)
    original_min = float(original_array.min())
    original_max = float(original_array.max())
    
    if original_max > original_min:
        original_norm = ((original_array.astype(np.float32) - original_min) / 
                        (original_max - original_min) * 255.0)
    else:
        original_norm = np.zeros_like(original_array, dtype=np.float32)
    
    # 归一化mask到0-1
    if mask_array.max() > 0:
        mask_norm = mask_array.astype(np.float32) / float(mask_array.max())
    else:
        mask_norm = np.zeros_like(mask_array, dtype=np.float32)
    
    # 创建RGB图像 (Z, Y, X, 3)
    z, y, x = original_array.shape
    rgb_image = np.zeros((z, y, x, 3), dtype=np.float32)
    
    # 将灰度图像复制到RGB三个通道
    for c in range(3):
        rgb_image[:, :, :, c] = original_norm
    
    # 创建彩色mask
    color_norm = np.array(color, dtype=np.float32)  # RGB颜色
    
    # 在mask区域进行颜色混合
    # RGB融合公式: result = original * (1 - alpha * mask) + color * alpha * mask
    for c in range(3):
        rgb_image[:, :, :, c] = (rgb_image[:, :, :, c] * (1 - alpha * mask_norm) + 
                                 color_norm[c] * alpha * mask_norm)
    
    # 裁剪到有效范围并转换为uint8
    rgb_image = np.clip(rgb_image, 0, 255).astype(np.uint8)
    
    print(f"融合完成: output shape={rgb_image.shape}, dtype={rgb_image.dtype}")
    print(f"RGB通道范围: R=[{rgb_image[:,:,:,0].min()}, {rgb_image[:,:,:,0].max()}], "
          f"G=[{rgb_image[:,:,:,1].min()}, {rgb_image[:,:,:,1].max()}], "
          f"B=[{rgb_image[:,:,:,2].min()}, {rgb_image[:,:,:,2].max()}]")
    
    return rgb_image


def create_overlay_from_files(original_path, mask_path, output_path, 
                               color=(255, 0, 0), alpha=0.5):
    """
    从文件读取图像和mask，创建融合图像并保存
    
    Args:
        original_path (str): 原始图像文件路径
        mask_path (str): 分割mask文件路径
        output_path (str): 输出融合图像路径
        color (tuple): RGB颜色
        alpha (float): 透明度
    
    Returns:
        str: 输出文件路径
    """
    # 加载原始图像
    print(f"加载原始图像: {original_path}")
    original_nii = nib.load(original_path)
    original_array = original_nii.get_fdata()
    
    # 加载mask
    print(f"加载分割mask: {mask_path}")
    mask_nii = nib.load(mask_path)
    mask_array = mask_nii.get_fdata()
    
    # 执行融合
    overlay_array = overlay_segmentation(original_array, mask_array, color, alpha)
    
    # 保存结果（使用原始图像的affine）
    # 注意：NIfTI格式需要特殊处理RGB图像
    # 我们需要将(Z,Y,X,3)转换为NIfTI的RGB格式
    overlay_nii = nib.Nifti1Image(overlay_array, original_nii.affine)
    
    # 设置为RGB图像类型
    overlay_nii.header.set_data_dtype(np.uint8)
    
    nib.save(overlay_nii, output_path)
    
    print(f"✅ 融合图像已保存: {output_path}")
    
    return output_path


def overlay_multi_label_segmentation(original_array, label_array, color_map=None, alpha=0.5):
    """
    将多标签分割结果以多种颜色叠加到原始图像上
    
    Args:
        original_array (np.ndarray): 原始图像数组 (Z, Y, X)
        label_array (np.ndarray): 多标签数组 (Z, Y, X)，标签值为0, 1, 2, 3...
        color_map (dict or None): 标签到颜色的映射 {label: (R, G, B)}
                                  如果为None，使用默认颜色方案
        alpha (float): 透明度，范围0-1
    
    Returns:
        np.ndarray: 融合后的RGB数组 (Z, Y, X, 3)，dtype=uint8
    """
    print(f"开始多标签融合...")
    print(f"原始图像: shape={original_array.shape}, dtype={original_array.dtype}")
    print(f"标签图像: shape={label_array.shape}, dtype={label_array.dtype}")
    
    # 将标签数组转换为整数类型（避免float64索引错误）
    label_array = label_array.astype(np.int32)
    
    # 获取所有标签值
    unique_labels = np.unique(label_array)
    print(f"标签值: {unique_labels}")
    
    # 默认颜色方案（排除标签0作为背景）
    if color_map is None:
        default_colors = [
            (255, 0, 0),     # 标签1: 红色
            (0, 255, 0),     # 标签2: 绿色
            (0, 0, 255),     # 标签3: 蓝色
            (255, 255, 0),   # 标签4: 黄色
            (255, 0, 255),   # 标签5: 品红
            (0, 255, 255),   # 标签6: 青色
            (255, 128, 0),   # 标签7: 橙色
            (128, 0, 255),   # 标签8: 紫色
        ]
        color_map = {}
        for i, label in enumerate(unique_labels):
            # 确保label是整数
            label = int(label)
            if label == 0:  # 跳过背景
                continue
            color_idx = (label - 1) % len(default_colors)
            color_map[label] = default_colors[color_idx]
    
    print(f"颜色映射: {color_map}")
    
    # 确保数组形状匹配
    if original_array.shape != label_array.shape:
        raise ValueError(f"原始图像和标签图像形状不匹配: {original_array.shape} vs {label_array.shape}")
    
    # 归一化原始图像到0-255
    original_min = float(original_array.min())
    original_max = float(original_array.max())
    
    if original_max > original_min:
        original_norm = ((original_array.astype(np.float32) - original_min) / 
                        (original_max - original_min) * 255.0)
    else:
        original_norm = np.zeros_like(original_array, dtype=np.float32)
    
    # 创建RGB图像
    z, y, x = original_array.shape
    rgb_image = np.zeros((z, y, x, 3), dtype=np.float32)
    
    # 初始化为灰度图像
    for c in range(3):
        rgb_image[:, :, :, c] = original_norm
    
    # 为每个标签添加颜色
    for label, color in color_map.items():
        # 确保label是整数
        label = int(label)
        
        if label == 0:  # 跳过背景
            continue
        
        # 创建当前标签的mask
        mask = (label_array == label).astype(np.float32)
        
        if mask.sum() > 0:  # 如果该标签存在
            color_norm = np.array(color, dtype=np.float32)
            
            # 在mask区域进行颜色混合
            for c in range(3):
                rgb_image[:, :, :, c] = (rgb_image[:, :, :, c] * (1 - alpha * mask) + 
                                         color_norm[c] * alpha * mask)
            
            pixel_count = int(mask.sum())
            print(f"  标签 {label}: 颜色={color}, 像素数={pixel_count}")
    
    # 裁剪到有效范围并转换为uint8
    rgb_image = np.clip(rgb_image, 0, 255).astype(np.uint8)
    
    print(f"多标签融合完成: output shape={rgb_image.shape}, dtype={rgb_image.dtype}")
    
    return rgb_image


def create_multi_label_overlay_from_files(original_path, label_path, output_path, 
                                          color_map=None, alpha=0.5):
    """
    从文件读取图像和多标签，创建多颜色融合图像并保存
    
    Args:
        original_path (str): 原始图像文件路径
        label_path (str): 多标签文件路径
        output_path (str): 输出融合图像路径
        color_map (dict or None): 标签到颜色的映射
        alpha (float): 透明度
    
    Returns:
        str: 输出文件路径
    """
    # 加载原始图像
    print(f"加载原始图像: {original_path}")
    original_nii = nib.load(original_path)
    original_array = original_nii.get_fdata()
    
    # 加载标签图像
    print(f"加载标签图像: {label_path}")
    label_nii = nib.load(label_path)
    label_array = label_nii.get_fdata()
    
    # 执行多标签融合
    overlay_array = overlay_multi_label_segmentation(original_array, label_array, color_map, alpha)
    
    # 保存结果
    overlay_nii = nib.Nifti1Image(overlay_array, original_nii.affine)
    overlay_nii.header.set_data_dtype(np.uint8)
    nib.save(overlay_nii, output_path)
    
    print(f"✅ 多标签融合图像已保存: {output_path}")
    
    return output_path


# 使用示例
if __name__ == "__main__":
    original_path = r"E:\xu\DataSets\liulian\470_333_310_0.3.nii.gz"
    mask_path = r"E:\xu\DataSets\liulian\predictions\470_333_310_0.3_segmented.nii.gz"
    output_path = r"E:\xu\DataSets\liulian\predictions\470_333_310_0.3_overlay.nii.gz"
    
    create_overlay_from_files(
        original_path, 
        mask_path, 
        output_path,
        color=(255, 0, 0),  # 红色
        alpha=0.5  # 50%透明度
    )

