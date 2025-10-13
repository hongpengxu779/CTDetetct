import os
import torch
import nibabel as nib
import numpy as np
import time
from monai.transforms import (
    Compose, LoadImage, ScaleIntensity, EnsureChannelFirst,
    Activations, AsDiscrete
)
from monai.networks.nets import UNet
from monai.inferers import sliding_window_inference


class UnetSegmentationInference:
    """
    用于3D医学图像分割推理的类，使用滑窗推理处理完整图像

    Args:
        checkpoint_path (str): 训练好的模型权重文件路径
        output_dir (str): 输出预测结果的目录
        roi_size (tuple, optional): 滑窗尺寸，默认为(128, 128, 128)
        sw_batch_size (int, optional): 滑窗批量大小，默认为1
        device (str, optional): 运行设备，默认自动选择
    """

    def __init__(self, checkpoint_path, output_dir,
                 roi_size=(128, 128, 128), sw_batch_size=1, device=None):
        self.checkpoint_path = checkpoint_path
        self.output_dir = output_dir
        self.roi_size = roi_size
        self.sw_batch_size = sw_batch_size

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 设置设备
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu") if device is None else device
        print(f"使用设备: {self.device}")

        # 初始化变换和模型
        self._setup_transforms()
        self._initialize_model()

    def _setup_transforms(self):
        """设置数据预处理和后处理变换"""
        # 预处理：保持原始尺寸，不进行裁剪
        self.transform = Compose([
            LoadImage(image_only=True),
            ScaleIntensity(),
            EnsureChannelFirst(),
        ])

        # 后处理：使用较低的阈值以保留更多细节
        self.post_pred = Compose([
            Activations(sigmoid=True),
            AsDiscrete(threshold=0.0005)
        ])

    def _initialize_model(self):
        """初始化并加载模型"""
        self.net = UNet(
            spatial_dims=3,
            in_channels=1,
            out_channels=1,
            channels=(16, 32, 64, 128, 256),
            strides=(2, 2, 2, 2),
            num_res_units=2,
        ).to(self.device)

        # 加载预训练权重
        checkpoint = torch.load(self.checkpoint_path, map_location=self.device)
        self.net.load_state_dict(checkpoint["net"])
        self.net.eval()
        print("✅ 模型加载成功")

    def preprocess(self, input_path):
        """
        预处理输入图像

        Args:
            input_path (str): 输入NIfTI文件路径

        Returns:
            tuple: (预处理后的张量, 原始图像的affine矩阵)
        """
        input_img = self.transform(input_path)
        input_tensor = input_img.unsqueeze(0).to(torch.float32)  # (1, C, D, H, W)
        # 获取原图的affine矩阵用于保存配准
        affine = nib.load(input_path).affine
        return input_tensor, affine

    def inference(self, input_tensor):
        """
        使用滑窗推理执行模型推理

        Args:
            input_tensor (torch.Tensor): 预处理后的输入张量

        Returns:
            numpy.ndarray: 模型输出的预测结果
        """
        with torch.no_grad():
            start_time = time.time()
            
            # 使用滑窗推理处理完整图像
            output = sliding_window_inference(
                input_tensor.to(self.device),
                roi_size=self.roi_size,
                sw_batch_size=self.sw_batch_size,
                predictor=self.net,
            )
            
            # 后处理
            output_post = self.post_pred(output)
            output_np = output_post.cpu().numpy()[0, 0]
            
            end_time = time.time()
            print(f"推理时间：{end_time - start_time:.4f}秒")
            print(f"输出形状：{output_np.shape}")
            print(f"输出范围：[{output_np.min():.4f}, {output_np.max():.4f}]")
            
            return output_np

    def save_result(self, output_np, affine, output_filename="pred_single.nii.gz"):
        """
        保存推理结果

        Args:
            output_np (numpy.ndarray): 推理结果数组（二值：0或1）
            affine (numpy.ndarray): 原始图像的affine矩阵
            output_filename (str): 输出文件名

        Returns:
            str: 保存的预测结果文件路径
        """
        save_path = os.path.join(self.output_dir, output_filename)
        
        # 统计分割结果
        num_positive = np.sum(output_np > 0)
        total_voxels = output_np.size
        positive_ratio = num_positive / total_voxels * 100
        
        print(f"分割统计：{num_positive}/{total_voxels} 体素被标记为前景 ({positive_ratio:.2f}%)")
        
        # 将二值结果（0/1）缩放到可视化范围（0/255）
        # 这样在CT查看器中更容易看到分割结果
        output_scaled = (output_np * 255).astype(np.uint8)
        
        nib.save(nib.Nifti1Image(output_scaled, affine), save_path)
        print(f"✅ 推理结果已保存：{save_path}")
        
        if num_positive == 0:
            print("⚠️ 警告：未检测到任何前景区域，可能需要调整模型或阈值参数")
        
        return save_path

    def run(self, input_path, output_filename="pred_single.nii.gz"):
        """
        完整的推理过程：预处理、推理和保存结果

        Args:
            input_path (str): 输入NIfTI文件路径
            output_filename (str): 输出文件名

        Returns:
            str: 保存的预测结果文件路径
        """
        # 预处理
        input_tensor, affine = self.preprocess(input_path)

        # 推理
        output_np = self.inference(input_tensor)

        # 保存结果
        return self.save_result(output_np, affine, output_filename)


# 使用示例
if __name__ == "__main__":
    root_dir = r"E:\xu\DataSets\liulian"
    check_points = r"E:\xu\CT\MONAI\3d_segmentation\checkpoints\model_epoch_1000.pth"
    output_dir = os.path.join(root_dir, "predictions")

    # 初始化推理器（使用滑窗推理）
    inferencer = UnetSegmentationInference(
        checkpoint_path=check_points,
        output_dir=output_dir,
        roi_size=(128, 128, 128),  # 滑窗尺寸
        sw_batch_size=1  # 滑窗批量大小
    )

    # 对单个文件进行推理
    input_file = os.path.join(root_dir, "470_333_310_0.3.nii.gz")
    result_path = inferencer.run(input_file)

