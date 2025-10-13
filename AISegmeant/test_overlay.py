# -*- coding: utf-8 -*-
"""测试图像融合功能"""

from image_overlay import create_overlay_from_files
import os

if __name__ == "__main__":
    # 测试路径（请根据实际情况修改）
    root_dir = r"E:\xu\DataSets\liulian"
    predictions_dir = os.path.join(root_dir, "predictions")
    
    original_path = os.path.join(root_dir, "470_333_310_0.3.nii.gz")
    mask_path = os.path.join(predictions_dir, "470_333_310_0.3_segmented.nii.gz")
    output_path = os.path.join(predictions_dir, "470_333_310_0.3_overlay_test.nii.gz")
    
    print("="*60)
    print("测试图像融合功能")
    print("="*60)
    print(f"原始图像: {original_path}")
    print(f"分割mask: {mask_path}")
    print(f"输出路径: {output_path}")
    print("="*60)
    
    # 测试不同颜色
    colors = [
        ("红色", (255, 0, 0)),
        ("绿色", (0, 255, 0)),
        ("蓝色", (0, 0, 255)),
    ]
    
    for color_name, color_rgb in colors:
        print(f"\n测试 {color_name} 融合...")
        test_output = output_path.replace('_test.nii', f'_test_{color_name}.nii')
        
        try:
            result = create_overlay_from_files(
                original_path,
                mask_path,
                test_output,
                color=color_rgb,
                alpha=0.5
            )
            print(f"✅ {color_name} 融合成功: {result}")
        except Exception as e:
            print(f"❌ {color_name} 融合失败: {e}")
    
    print("\n" + "="*60)
    print("测试完成！请在CT Viewer中查看融合结果。")
    print("="*60)

