"""
使用 mUSICA (ImageMaster.dll) 批量处理 TIFF 文件
用法：
    python process_tiff_musica.py <输入目录或文件> [输出目录] [--level 8] [--strength 100]
"""

import os
import sys
import argparse
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Traditional.Enhancement.enhancement_ops import EnhancementOps


def process_single_tiff(input_path, output_path, level=8, strength=100):
    """处理单个 TIFF 文件"""
    import imageio.v2 as imageio
    
    # 读取
    img = imageio.imread(input_path)
    print(f"  输入: {input_path}")
    print(f"    dtype={img.dtype}, shape={img.shape}, range=[{img.min()}, {img.max()}]")
    
    # 确保是 uint16
    if img.dtype != np.uint16:
        print(f"    警告: 数据类型为 {img.dtype}，转换为 uint16")
        if img.dtype == np.uint8:
            img = (img.astype(np.uint16) * 257)
        else:
            img = img.astype(np.uint16)
    
    # 检查 DLL 是否可用
    func = EnhancementOps._load_imagemaster_musica_func()
    if func is None:
        print("    错误: ImageMaster.dll 未找到或加载失败")
        return False
    
    # 调用 DLL 处理
    try:
        result = EnhancementOps._musica_slice_imagemaster(img, level, strength)
        print(f"    DLL处理完成: range=[{result.min()}, {result.max()}]")
    except Exception as e:
        print(f"    DLL调用失败: {e}")
        return False
    
    # 保存
    imageio.imwrite(output_path, result)
    print(f"  输出: {output_path}")
    return True


def process_directory(input_dir, output_dir, level=8, strength=100):
    """处理目录中的所有 TIFF 文件"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    tiff_files = [f for f in os.listdir(input_dir) 
                  if f.lower().endswith(('.tiff', '.tif'))]
    
    if not tiff_files:
        print(f"目录 {input_dir} 中没有找到 TIFF 文件")
        return
    
    print(f"找到 {len(tiff_files)} 个 TIFF 文件")
    print(f"参数: Level={level}, Strength={strength}")
    print("-" * 50)
    
    success_count = 0
    for i, filename in enumerate(sorted(tiff_files), 1):
        print(f"[{i}/{len(tiff_files)}] 处理: {filename}")
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)
        
        if process_single_tiff(input_path, output_path, level, strength):
            success_count += 1
        print()
    
    print("-" * 50)
    print(f"完成: {success_count}/{len(tiff_files)} 个文件处理成功")


def main():
    parser = argparse.ArgumentParser(description='使用 mUSICA (ImageMaster.dll) 处理 TIFF 文件')
    parser.add_argument('input', help='输入 TIFF 文件或目录')
    parser.add_argument('output', nargs='?', help='输出目录（默认在输入目录下创建 musica_output）')
    parser.add_argument('--level', type=int, default=8, help='Level 参数 (1-8, 默认 8)')
    parser.add_argument('--strength', type=int, default=100, help='Strength 参数 (0-100, 默认 100)')
    
    args = parser.parse_args()
    
    # DLL 检查
    print("检查 ImageMaster.dll...")
    func = EnhancementOps._load_imagemaster_musica_func()
    if func:
        print("ImageMaster.dll 加载成功!")
    else:
        print("错误: ImageMaster.dll 加载失败")
        sys.exit(1)
    print()
    
    if os.path.isfile(args.input):
        # 处理单个文件
        if args.output:
            output_path = args.output
        else:
            base, ext = os.path.splitext(args.input)
            output_path = f"{base}_musica{ext}"
        
        process_single_tiff(args.input, output_path, args.level, args.strength)
    
    elif os.path.isdir(args.input):
        # 处理目录
        if args.output:
            output_dir = args.output
        else:
            output_dir = os.path.join(args.input, 'musica_output')
        
        process_directory(args.input, output_dir, args.level, args.strength)
    
    else:
        print(f"错误: 输入路径不存在: {args.input}")
        sys.exit(1)


if __name__ == '__main__':
    main()
