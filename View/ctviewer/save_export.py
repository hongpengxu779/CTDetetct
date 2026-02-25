"""
save_export.py - 数据保存和导出功能模块

支持的功能：
- 会话保存/加载 (.ctsession)
- NIfTI 导出 (.nii, .nii.gz)
- DICOM 序列导出
- RAW/MHD 导出 (.raw + .mhd)
- 切片图片导出 (PNG, JPEG, TIFF, BMP)
"""

import os
import json
import gzip
import pickle
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union

import numpy as np
import SimpleITK as sitk

from PyQt5 import QtWidgets, QtCore


class SessionManager:
    """会话管理器 - 保存和恢复工作状态"""
    
    SESSION_VERSION = "1.0"
    SESSION_EXTENSION = ".ctsession"
    
    @staticmethod
    def save_session(
        viewer_instance,
        filepath: str,
        include_data: bool = True,
        compress: bool = True
    ) -> bool:
        """保存当前会话状态
        
        参数
        ----
        viewer_instance: CTViewer 实例
        filepath: 保存路径
        include_data: 是否包含原始数据（大文件）
        compress: 是否压缩
        
        返回
        ----
        bool: 成功返回 True
        """
        session_data = {
            'version': SessionManager.SESSION_VERSION,
            'timestamp': datetime.now().isoformat(),
            'window_level': {},
            'view_state': {},
            'data_list_items': [],
            'current_data_index': None,
            'roi_data': {},
            'spacing': None,
            'origin': None,
        }
        
        # 保存窗宽窗位
        if hasattr(viewer_instance, 'window_width') and hasattr(viewer_instance, 'window_center'):
            session_data['window_level'] = {
                'width': float(viewer_instance.window_width) if viewer_instance.window_width else None,
                'center': float(viewer_instance.window_center) if viewer_instance.window_center else None,
            }
        
        # 保存间距和原点
        if hasattr(viewer_instance, 'spacing') and viewer_instance.spacing is not None:
            session_data['spacing'] = [float(s) for s in viewer_instance.spacing]
        if hasattr(viewer_instance, 'image') and viewer_instance.image is not None:
            try:
                session_data['origin'] = list(viewer_instance.image.GetOrigin())
                session_data['direction'] = list(viewer_instance.image.GetDirection())
            except:
                pass
        
        # 保存数据列表项
        if hasattr(viewer_instance, 'data_list_widget') and viewer_instance.data_list_widget is not None:
            for i in range(viewer_instance.data_list_widget.count()):
                item = viewer_instance.data_list_widget.item(i)
                data_item = item.data(QtCore.Qt.UserRole)
                
                item_info = {
                    'name': item.text(),
                    'type': data_item.get('type', 'volume') if isinstance(data_item, dict) else 'volume',
                    'is_label': data_item.get('is_label', False) if isinstance(data_item, dict) else False,
                }
                
                if include_data and isinstance(data_item, dict) and 'array' in data_item:
                    arr = data_item['array']
                    item_info['array_dtype'] = str(arr.dtype)
                    item_info['array_shape'] = list(arr.shape)
                    item_info['array_data'] = arr.tobytes()
                
                session_data['data_list_items'].append(item_info)
            
            # 当前选中索引
            current_item = viewer_instance.data_list_widget.currentItem()
            if current_item:
                session_data['current_data_index'] = viewer_instance.data_list_widget.row(current_item)
        
        # 保存 ROI 数据
        if hasattr(viewer_instance, 'roi') and viewer_instance.roi is not None:
            session_data['roi_data'] = {
                'z_range': viewer_instance.roi.get('z_range'),
                'y_range': viewer_instance.roi.get('y_range'),
                'x_range': viewer_instance.roi.get('x_range'),
            }
        
        # 写入文件
        try:
            if compress:
                with gzip.open(filepath, 'wb') as f:
                    pickle.dump(session_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            else:
                with open(filepath, 'wb') as f:
                    pickle.dump(session_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            return True
        except Exception as e:
            print(f"[SessionManager] 保存会话失败: {e}")
            return False
    
    @staticmethod
    def load_session(viewer_instance, filepath: str) -> Tuple[bool, str]:
        """加载会话
        
        返回
        ----
        (success, message)
        """
        try:
            # 尝试 gzip 解压
            try:
                with gzip.open(filepath, 'rb') as f:
                    session_data = pickle.load(f)
            except:
                with open(filepath, 'rb') as f:
                    session_data = pickle.load(f)
            
            version = session_data.get('version', '0.0')
            
            # 恢复数据列表
            if 'data_list_items' in session_data and hasattr(viewer_instance, 'data_list_widget'):
                viewer_instance.data_list_widget.clear()
                
                for item_info in session_data['data_list_items']:
                    data_item = {
                        'type': item_info.get('type', 'volume'),
                        'is_label': item_info.get('is_label', False),
                    }
                    
                    # 恢复数组数据
                    if 'array_data' in item_info:
                        dtype = np.dtype(item_info['array_dtype'])
                        shape = tuple(item_info['array_shape'])
                        arr = np.frombuffer(item_info['array_data'], dtype=dtype).reshape(shape)
                        data_item['array'] = arr.copy()
                    
                    list_item = QtWidgets.QListWidgetItem(item_info['name'])
                    list_item.setData(QtCore.Qt.UserRole, data_item)
                    viewer_instance.data_list_widget.addItem(list_item)
                
                # 恢复选中索引
                idx = session_data.get('current_data_index')
                if idx is not None and idx < viewer_instance.data_list_widget.count():
                    viewer_instance.data_list_widget.setCurrentRow(idx)
                    # 触发切换
                    if hasattr(viewer_instance, 'switch_to_data'):
                        viewer_instance.switch_to_data(viewer_instance.data_list_widget.item(idx))
            
            # 恢复窗宽窗位
            if 'window_level' in session_data:
                wl = session_data['window_level']
                if wl.get('width') is not None:
                    viewer_instance.window_width = wl['width']
                if wl.get('center') is not None:
                    viewer_instance.window_center = wl['center']
                if hasattr(viewer_instance, 'update_all_slices'):
                    viewer_instance.update_all_slices()
            
            # 恢复 ROI
            if 'roi_data' in session_data and session_data['roi_data']:
                viewer_instance.roi = session_data['roi_data']
            
            # 恢复间距
            if 'spacing' in session_data and session_data['spacing']:
                viewer_instance.spacing = tuple(session_data['spacing'])
            
            return True, f"会话已加载（版本 {version}）"
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"加载会话失败: {str(e)}"


class DataExporter:
    """数据导出器 - 支持多种格式"""
    
    @staticmethod
    def export_nifti(
        array: np.ndarray,
        filepath: str,
        spacing: Optional[Tuple[float, float, float]] = None,
        origin: Optional[Tuple[float, float, float]] = None,
        direction: Optional[Tuple] = None,
        reference_image: Optional[sitk.Image] = None
    ) -> bool:
        """导出 NIfTI 格式
        
        参数
        ----
        array: 3D numpy 数组
        filepath: 输出路径 (.nii 或 .nii.gz)
        spacing: 体素间距 (z, y, x) 或 (x, y, z)
        origin: 原点坐标
        direction: 方向矩阵
        reference_image: 参考 SimpleITK 图像（复制元信息）
        """
        try:
            image = sitk.GetImageFromArray(array)
            
            if reference_image is not None:
                image.CopyInformation(reference_image)
            else:
                if spacing is not None:
                    # SimpleITK 使用 (x, y, z) 顺序
                    if len(spacing) == 3:
                        image.SetSpacing(tuple(float(s) for s in spacing[::-1]))
                if origin is not None:
                    image.SetOrigin(tuple(float(o) for o in origin))
                if direction is not None:
                    image.SetDirection(tuple(float(d) for d in direction))
            
            sitk.WriteImage(image, filepath)
            return True
        except Exception as e:
            print(f"[DataExporter] NIfTI 导出失败: {e}")
            return False
    
    @staticmethod
    def export_dicom_series(
        array: np.ndarray,
        output_dir: str,
        spacing: Optional[Tuple[float, float, float]] = None,
        patient_name: str = "Anonymous",
        patient_id: str = "000000",
        study_description: str = "CT Viewer Export",
        series_description: str = "Exported Series",
        progress_callback: Optional[callable] = None
    ) -> Tuple[bool, str]:
        """导出 DICOM 序列
        
        参数
        ----
        array: 3D numpy 数组 (Z, Y, X)
        output_dir: 输出目录
        spacing: 体素间距 (z, y, x)
        patient_name: 患者姓名
        patient_id: 患者 ID
        study_description: 检查描述
        series_description: 序列描述
        progress_callback: 进度回调 (current, total)
        
        返回
        ----
        (success, message)
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # 转换为 SimpleITK 图像
            image = sitk.GetImageFromArray(array.astype(np.int16))
            
            if spacing is not None:
                # 转换为 (x, y, z) 顺序
                image.SetSpacing(tuple(float(s) for s in spacing[::-1]))
            else:
                image.SetSpacing((1.0, 1.0, 1.0))
            
            # 获取 DICOM 写入器
            writer = sitk.ImageFileWriter()
            writer.KeepOriginalImageUIDOn()
            
            # 生成唯一标识
            import time
            import random
            
            modification_time = time.strftime("%H%M%S")
            modification_date = time.strftime("%Y%m%d")
            
            # 生成 UID（简化版，实际应用需要更规范的 UID 生成）
            uid_prefix = "1.2.826.0.1.3680043.8.498."
            study_uid = f"{uid_prefix}{modification_date}.{modification_time}.{random.randint(1000, 9999)}"
            series_uid = f"{uid_prefix}{modification_date}.{modification_time}.{random.randint(10000, 99999)}"
            frame_of_ref_uid = f"{uid_prefix}{modification_date}.{modification_time}.{random.randint(100000, 999999)}"
            
            num_slices = array.shape[0]
            
            for i in range(num_slices):
                if progress_callback:
                    progress_callback(i + 1, num_slices)
                
                # 提取单个切片
                slice_image = image[:, :, i]
                
                # 设置 DICOM 标签
                sop_uid = f"{uid_prefix}{modification_date}.{modification_time}.{random.randint(1000000, 9999999)}.{i}"
                
                # 基本 DICOM 标签
                slice_image.SetMetaData("0008|0016", "1.2.840.10008.5.1.4.1.1.2")  # CT Image Storage SOP Class
                slice_image.SetMetaData("0008|0018", sop_uid)  # SOP Instance UID
                slice_image.SetMetaData("0008|0020", modification_date)  # Study Date
                slice_image.SetMetaData("0008|0030", modification_time)  # Study Time
                slice_image.SetMetaData("0008|0050", "")  # Accession Number
                slice_image.SetMetaData("0008|0060", "CT")  # Modality
                slice_image.SetMetaData("0008|1030", study_description)  # Study Description
                slice_image.SetMetaData("0008|103e", series_description)  # Series Description
                
                slice_image.SetMetaData("0010|0010", patient_name)  # Patient Name
                slice_image.SetMetaData("0010|0020", patient_id)  # Patient ID
                
                slice_image.SetMetaData("0020|000d", study_uid)  # Study Instance UID
                slice_image.SetMetaData("0020|000e", series_uid)  # Series Instance UID
                slice_image.SetMetaData("0020|0010", "1")  # Study ID
                slice_image.SetMetaData("0020|0011", "1")  # Series Number
                slice_image.SetMetaData("0020|0013", str(i + 1))  # Instance Number
                slice_image.SetMetaData("0020|0052", frame_of_ref_uid)  # Frame of Reference UID
                
                # 位置信息
                z_pos = float(i * (spacing[0] if spacing else 1.0))
                slice_image.SetMetaData("0020|0032", f"0\\0\\{z_pos}")  # Image Position Patient
                slice_image.SetMetaData("0020|0037", "1\\0\\0\\0\\1\\0")  # Image Orientation Patient
                slice_image.SetMetaData("0018|0050", str(spacing[0] if spacing else 1.0))  # Slice Thickness
                
                # 像素信息
                slice_image.SetMetaData("0028|0010", str(array.shape[1]))  # Rows
                slice_image.SetMetaData("0028|0011", str(array.shape[2]))  # Columns
                slice_image.SetMetaData("0028|0030", f"{spacing[1] if spacing else 1.0}\\{spacing[2] if spacing else 1.0}")  # Pixel Spacing
                slice_image.SetMetaData("0028|0100", "16")  # Bits Allocated
                slice_image.SetMetaData("0028|0101", "16")  # Bits Stored
                slice_image.SetMetaData("0028|0102", "15")  # High Bit
                slice_image.SetMetaData("0028|0103", "1")  # Pixel Representation (signed)
                
                # 保存
                filename = os.path.join(output_dir, f"IM{i+1:06d}.dcm")
                writer.SetFileName(filename)
                writer.Execute(slice_image)
            
            return True, f"已导出 {num_slices} 张 DICOM 切片"
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"DICOM 导出失败: {str(e)}"
    
    @staticmethod
    def export_raw_mhd(
        array: np.ndarray,
        filepath: str,
        spacing: Optional[Tuple[float, float, float]] = None,
        origin: Optional[Tuple[float, float, float]] = None,
        compress: bool = False
    ) -> Tuple[bool, str]:
        """导出 RAW + MHD 格式
        
        参数
        ----
        array: 3D numpy 数组
        filepath: MHD 文件路径
        spacing: 体素间距
        origin: 原点
        compress: 是否压缩 RAW 文件
        
        返回
        ----
        (success, message)
        """
        try:
            # 确定文件路径
            if filepath.lower().endswith('.mhd'):
                mhd_path = filepath
                raw_path = filepath[:-4] + ('.zraw' if compress else '.raw')
            else:
                mhd_path = filepath + '.mhd'
                raw_path = filepath + ('.zraw' if compress else '.raw')
            
            # 数据类型映射
            dtype_map = {
                'int8': 'MET_CHAR',
                'uint8': 'MET_UCHAR',
                'int16': 'MET_SHORT',
                'uint16': 'MET_USHORT',
                'int32': 'MET_INT',
                'uint32': 'MET_UINT',
                'int64': 'MET_LONG',
                'uint64': 'MET_ULONG',
                'float32': 'MET_FLOAT',
                'float64': 'MET_DOUBLE',
            }
            
            element_type = dtype_map.get(str(array.dtype), 'MET_FLOAT')
            
            # 写入 RAW 数据
            if compress:
                with gzip.open(raw_path, 'wb') as f:
                    f.write(array.tobytes())
            else:
                array.tofile(raw_path)
            
            # 构建 MHD 头文件
            mhd_content = [
                "ObjectType = Image",
                f"NDims = {array.ndim}",
                f"DimSize = {' '.join(str(s) for s in array.shape[::-1])}",  # X Y Z
                f"ElementType = {element_type}",
            ]
            
            if spacing is not None:
                mhd_content.append(f"ElementSpacing = {' '.join(str(s) for s in spacing[::-1])}")
            else:
                mhd_content.append(f"ElementSpacing = 1.0 1.0 1.0")
            
            if origin is not None:
                mhd_content.append(f"Offset = {' '.join(str(o) for o in origin)}")
            else:
                mhd_content.append("Offset = 0 0 0")
            
            mhd_content.extend([
                "BinaryData = True",
                "BinaryDataByteOrderMSB = False",
                f"CompressedData = {'True' if compress else 'False'}",
                f"ElementDataFile = {os.path.basename(raw_path)}",
            ])
            
            # 写入 MHD 头文件
            with open(mhd_path, 'w') as f:
                f.write('\n'.join(mhd_content))
            
            raw_size = os.path.getsize(raw_path) / (1024 * 1024)
            return True, f"已导出 MHD + RAW ({raw_size:.1f} MB)"
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"RAW/MHD 导出失败: {str(e)}"
    
    @staticmethod
    def export_slices_as_images(
        array: np.ndarray,
        output_dir: str,
        axis: int = 0,
        format: str = "png",
        prefix: str = "slice",
        window_width: Optional[float] = None,
        window_center: Optional[float] = None,
        bit_depth: int = 8,
        progress_callback: Optional[callable] = None
    ) -> Tuple[bool, str]:
        """导出切片为图片序列
        
        参数
        ----
        array: 3D numpy 数组
        output_dir: 输出目录
        axis: 切片轴 (0=Z, 1=Y, 2=X)
        format: 图片格式 ("png", "jpeg", "tiff", "bmp")
        prefix: 文件名前缀
        window_width: 窗宽（用于归一化）
        window_center: 窗位（用于归一化）
        bit_depth: 位深 (8 或 16)
        progress_callback: 进度回调
        
        返回
        ----
        (success, message)
        """
        try:
            import imageio
            
            os.makedirs(output_dir, exist_ok=True)
            
            num_slices = array.shape[axis]
            format = format.lower()
            
            if format == "jpeg":
                ext = "jpg"
            elif format == "tiff":
                ext = "tiff"
            else:
                ext = format
            
            count = 0
            for i in range(num_slices):
                if progress_callback:
                    progress_callback(i + 1, num_slices)
                
                # 提取切片
                if axis == 0:
                    slice2d = array[i, :, :]
                elif axis == 1:
                    slice2d = array[:, i, :]
                else:
                    slice2d = array[:, :, i]
                
                # 归一化
                if window_width is not None and window_center is not None:
                    # 应用窗宽窗位
                    low = window_center - window_width / 2
                    high = window_center + window_width / 2
                    slice2d = np.clip(slice2d, low, high)
                    slice2d = (slice2d - low) / (high - low)
                else:
                    # 自动归一化
                    min_val = slice2d.min()
                    max_val = slice2d.max()
                    if max_val > min_val:
                        slice2d = (slice2d - min_val) / (max_val - min_val)
                    else:
                        slice2d = np.zeros_like(slice2d, dtype=np.float32)
                
                # 转换位深
                if bit_depth == 16 and format in ("png", "tiff"):
                    slice2d = (slice2d * 65535).astype(np.uint16)
                else:
                    slice2d = (slice2d * 255).astype(np.uint8)
                
                # 保存
                filename = os.path.join(output_dir, f"{prefix}_{i:06d}.{ext}")
                
                if format == "jpeg":
                    imageio.imwrite(filename, slice2d, quality=95)
                elif format == "tiff" and bit_depth == 16:
                    imageio.imwrite(filename, slice2d)
                else:
                    imageio.imwrite(filename, slice2d)
                
                count += 1
            
            return True, f"已导出 {count} 张 {format.upper()} 图片"
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"图片导出失败: {str(e)}"


class ExportDialogs:
    """导出对话框集合"""
    
    @staticmethod
    def show_dicom_export_dialog(
        parent,
        array: np.ndarray,
        spacing: Optional[Tuple] = None
    ) -> Optional[str]:
        """显示 DICOM 导出对话框"""
        dialog = QtWidgets.QDialog(parent)
        dialog.setWindowTitle("导出 DICOM 序列")
        dialog.setMinimumWidth(400)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # 患者信息
        form = QtWidgets.QFormLayout()
        
        patient_name_edit = QtWidgets.QLineEdit("Anonymous")
        patient_id_edit = QtWidgets.QLineEdit("000000")
        study_desc_edit = QtWidgets.QLineEdit("CT Viewer Export")
        series_desc_edit = QtWidgets.QLineEdit("Exported Series")
        
        form.addRow("患者姓名:", patient_name_edit)
        form.addRow("患者 ID:", patient_id_edit)
        form.addRow("检查描述:", study_desc_edit)
        form.addRow("序列描述:", series_desc_edit)
        
        layout.addLayout(form)
        
        # 输出目录
        dir_layout = QtWidgets.QHBoxLayout()
        dir_edit = QtWidgets.QLineEdit()
        dir_btn = QtWidgets.QPushButton("浏览...")
        dir_btn.clicked.connect(lambda: dir_edit.setText(
            QtWidgets.QFileDialog.getExistingDirectory(dialog, "选择输出目录") or dir_edit.text()
        ))
        dir_layout.addWidget(QtWidgets.QLabel("输出目录:"))
        dir_layout.addWidget(dir_edit)
        dir_layout.addWidget(dir_btn)
        layout.addLayout(dir_layout)
        
        # 按钮
        btn_layout = QtWidgets.QHBoxLayout()
        ok_btn = QtWidgets.QPushButton("导出")
        cancel_btn = QtWidgets.QPushButton("取消")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            out_dir = dir_edit.text()
            if not out_dir:
                QtWidgets.QMessageBox.warning(parent, "错误", "请选择输出目录")
                return None
            
            # 创建进度对话框
            progress = QtWidgets.QProgressDialog("正在导出 DICOM...", "取消", 0, array.shape[0], parent)
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.show()
            
            def update_progress(current, total):
                progress.setValue(current)
                QtWidgets.QApplication.processEvents()
                return not progress.wasCanceled()
            
            success, msg = DataExporter.export_dicom_series(
                array=array,
                output_dir=out_dir,
                spacing=spacing,
                patient_name=patient_name_edit.text(),
                patient_id=patient_id_edit.text(),
                study_description=study_desc_edit.text(),
                series_description=series_desc_edit.text(),
                progress_callback=update_progress
            )
            
            progress.close()
            
            if success:
                QtWidgets.QMessageBox.information(parent, "导出完成", msg)
            else:
                QtWidgets.QMessageBox.critical(parent, "导出失败", msg)
            
            return out_dir if success else None
        
        return None
    
    @staticmethod
    def show_raw_mhd_export_dialog(
        parent,
        array: np.ndarray,
        spacing: Optional[Tuple] = None
    ) -> Optional[str]:
        """显示 RAW/MHD 导出对话框"""
        dialog = QtWidgets.QDialog(parent)
        dialog.setWindowTitle("导出 RAW/MHD")
        dialog.setMinimumWidth(350)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # 信息显示
        info_label = QtWidgets.QLabel(
            f"数据形状: {array.shape}\n"
            f"数据类型: {array.dtype}\n"
            f"间距: {spacing if spacing else '未知'}"
        )
        layout.addWidget(info_label)
        
        # 压缩选项
        compress_check = QtWidgets.QCheckBox("压缩 RAW 数据 (gzip)")
        layout.addWidget(compress_check)
        
        # 按钮
        btn_layout = QtWidgets.QHBoxLayout()
        ok_btn = QtWidgets.QPushButton("选择保存位置...")
        cancel_btn = QtWidgets.QPushButton("取消")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
                parent,
                "保存 MHD 文件",
                "exported.mhd",
                "MetaImage (*.mhd)"
            )
            
            if not filepath:
                return None
            
            success, msg = DataExporter.export_raw_mhd(
                array=array,
                filepath=filepath,
                spacing=spacing,
                compress=compress_check.isChecked()
            )
            
            if success:
                QtWidgets.QMessageBox.information(parent, "导出完成", msg)
            else:
                QtWidgets.QMessageBox.critical(parent, "导出失败", msg)
            
            return filepath if success else None
        
        return None
    
    @staticmethod
    def show_image_export_dialog(
        parent,
        array: np.ndarray,
        window_width: Optional[float] = None,
        window_center: Optional[float] = None
    ) -> Optional[str]:
        """显示图片序列导出对话框"""
        dialog = QtWidgets.QDialog(parent)
        dialog.setWindowTitle("导出切片图片")
        dialog.setMinimumWidth(400)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # 格式选择
        form = QtWidgets.QFormLayout()
        
        format_combo = QtWidgets.QComboBox()
        format_combo.addItems(["PNG", "JPEG", "TIFF", "BMP"])
        form.addRow("图片格式:", format_combo)
        
        axis_combo = QtWidgets.QComboBox()
        axis_combo.addItems(["Z (轴位)", "Y (冠状)", "X (矢状)"])
        form.addRow("切片方向:", axis_combo)
        
        bit_combo = QtWidgets.QComboBox()
        bit_combo.addItems(["8位", "16位"])
        form.addRow("位深:", bit_combo)
        
        prefix_edit = QtWidgets.QLineEdit("slice")
        form.addRow("文件前缀:", prefix_edit)
        
        layout.addLayout(form)
        
        # 窗宽窗位选项
        wl_check = QtWidgets.QCheckBox("使用当前窗宽窗位")
        wl_check.setChecked(window_width is not None)
        layout.addWidget(wl_check)
        
        # 输出目录
        dir_layout = QtWidgets.QHBoxLayout()
        dir_edit = QtWidgets.QLineEdit()
        dir_btn = QtWidgets.QPushButton("浏览...")
        dir_btn.clicked.connect(lambda: dir_edit.setText(
            QtWidgets.QFileDialog.getExistingDirectory(dialog, "选择输出目录") or dir_edit.text()
        ))
        dir_layout.addWidget(QtWidgets.QLabel("输出目录:"))
        dir_layout.addWidget(dir_edit)
        dir_layout.addWidget(dir_btn)
        layout.addLayout(dir_layout)
        
        # 按钮
        btn_layout = QtWidgets.QHBoxLayout()
        ok_btn = QtWidgets.QPushButton("导出")
        cancel_btn = QtWidgets.QPushButton("取消")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            out_dir = dir_edit.text()
            if not out_dir:
                QtWidgets.QMessageBox.warning(parent, "错误", "请选择输出目录")
                return None
            
            axis = axis_combo.currentIndex()
            fmt = format_combo.currentText().lower()
            bit = 16 if bit_combo.currentIndex() == 1 else 8
            prefix = prefix_edit.text() or "slice"
            
            ww = window_width if wl_check.isChecked() else None
            wc = window_center if wl_check.isChecked() else None
            
            # 进度对话框
            num_slices = array.shape[axis]
            progress = QtWidgets.QProgressDialog("正在导出图片...", "取消", 0, num_slices, parent)
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.show()
            
            def update_progress(current, total):
                progress.setValue(current)
                QtWidgets.QApplication.processEvents()
                return not progress.wasCanceled()
            
            success, msg = DataExporter.export_slices_as_images(
                array=array,
                output_dir=out_dir,
                axis=axis,
                format=fmt,
                prefix=prefix,
                window_width=ww,
                window_center=wc,
                bit_depth=bit,
                progress_callback=update_progress
            )
            
            progress.close()
            
            if success:
                QtWidgets.QMessageBox.information(parent, "导出完成", msg)
            else:
                QtWidgets.QMessageBox.critical(parent, "导出失败", msg)
            
            return out_dir if success else None
        
        return None
