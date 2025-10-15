# -*- coding: utf-8 -*-
"""圆轨迹CT重建对话框"""

from PyQt5 import QtWidgets, QtCore
import os
import time
import numpy as np


class CircleCTReconstructionDialog(QtWidgets.QDialog):
    """圆轨迹CT重建对话框 - 简化版"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("CT圆轨迹重建")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        # 创建布局
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # 创建数据路径输入区域
        data_group = QtWidgets.QGroupBox("数据路径")
        data_layout = QtWidgets.QGridLayout()
        data_group.setLayout(data_layout)
        
        data_layout.addWidget(QtWidgets.QLabel("DICOM数据文件夹:"), 0, 0)
        self.data_path = QtWidgets.QLineEdit()
        data_layout.addWidget(self.data_path, 0, 1)
        
        self.browse_button = QtWidgets.QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_data_folder)
        data_layout.addWidget(self.browse_button, 0, 2)
        
        # 将数据路径区域添加到主布局
        main_layout.addWidget(data_group)
        
        # 创建参数输入区域
        param_group = QtWidgets.QGroupBox("重建参数")
        param_layout = QtWidgets.QGridLayout()
        param_group.setLayout(param_layout)
        
        # 基本参数
        row = 0
        param_layout.addWidget(QtWidgets.QLabel("投影角度数量:"), row, 0)
        self.num_angles_input = QtWidgets.QSpinBox()
        self.num_angles_input.setRange(100, 10000)
        self.num_angles_input.setValue(1440)
        param_layout.addWidget(self.num_angles_input, row, 1)
        
        param_layout.addWidget(QtWidgets.QLabel("探测器行数:"), row, 2)
        self.num_rows_input = QtWidgets.QSpinBox()
        self.num_rows_input.setRange(1, 4096)
        self.num_rows_input.setValue(1536)
        param_layout.addWidget(self.num_rows_input, row, 3)
        
        # 探测器参数
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("探测器列数:"), row, 0)
        self.num_cols_input = QtWidgets.QSpinBox()
        self.num_cols_input.setRange(1, 4096)
        self.num_cols_input.setValue(1536)
        param_layout.addWidget(self.num_cols_input, row, 1)
        
        param_layout.addWidget(QtWidgets.QLabel("像素高度:"), row, 2)
        self.pixel_height_input = QtWidgets.QDoubleSpinBox()
        self.pixel_height_input.setRange(0.001, 10.0)
        self.pixel_height_input.setValue(0.278)
        self.pixel_height_input.setDecimals(6)
        param_layout.addWidget(self.pixel_height_input, row, 3)
        
        # 像素宽度和中心点
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("像素宽度:"), row, 0)
        self.pixel_width_input = QtWidgets.QDoubleSpinBox()
        self.pixel_width_input.setRange(0.001, 10.0)
        self.pixel_width_input.setValue(0.278)
        self.pixel_width_input.setDecimals(6)
        param_layout.addWidget(self.pixel_width_input, row, 1)
        
        param_layout.addWidget(QtWidgets.QLabel("中心行:"), row, 2)
        self.center_row_input = QtWidgets.QDoubleSpinBox()
        self.center_row_input.setRange(0.0, 4096.0)
        self.center_row_input.setValue(762.183)
        self.center_row_input.setDecimals(3)
        param_layout.addWidget(self.center_row_input, row, 3)
        
        # 中心列和SOD
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("中心列:"), row, 0)
        self.center_col_input = QtWidgets.QDoubleSpinBox()
        self.center_col_input.setRange(0.0, 4096.0)
        self.center_col_input.setValue(781.493)
        self.center_col_input.setDecimals(3)
        param_layout.addWidget(self.center_col_input, row, 1)
        
        param_layout.addWidget(QtWidgets.QLabel("源到物体距离(SOD):"), row, 2)
        self.sod_input = QtWidgets.QDoubleSpinBox()
        self.sod_input.setRange(1.0, 2000.0)
        self.sod_input.setValue(501.39)
        self.sod_input.setDecimals(2)
        param_layout.addWidget(self.sod_input, row, 3)
        
        # SDD
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("源到探测器距离(SDD):"), row, 0)
        self.sdd_input = QtWidgets.QDoubleSpinBox()
        self.sdd_input.setRange(1.0, 2000.0)
        self.sdd_input.setValue(1195.0)
        self.sdd_input.setDecimals(2)
        param_layout.addWidget(self.sdd_input, row, 1)
        
        # 体素参数
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("体素X维度:"), row, 0)
        self.num_x_input = QtWidgets.QSpinBox()
        self.num_x_input.setRange(1, 2048)
        self.num_x_input.setValue(1780)
        param_layout.addWidget(self.num_x_input, row, 1)
        
        param_layout.addWidget(QtWidgets.QLabel("体素Y维度:"), row, 2)
        self.num_y_input = QtWidgets.QSpinBox()
        self.num_y_input.setRange(1, 2048)
        self.num_y_input.setValue(977)
        param_layout.addWidget(self.num_y_input, row, 3)
        
        # 体素Z维度和体素宽度
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("体素Z维度:"), row, 0)
        self.num_z_input = QtWidgets.QSpinBox()
        self.num_z_input.setRange(1, 2048)
        self.num_z_input.setValue(1990)
        param_layout.addWidget(self.num_z_input, row, 1)
        
        param_layout.addWidget(QtWidgets.QLabel("体素宽度:"), row, 2)
        self.voxel_width_input = QtWidgets.QDoubleSpinBox()
        self.voxel_width_input.setRange(0.001, 1.0)
        self.voxel_width_input.setValue(0.09)
        self.voxel_width_input.setDecimals(6)
        param_layout.addWidget(self.voxel_width_input, row, 3)
        
        # 体素高度和X偏移
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("体素高度:"), row, 0)
        self.voxel_height_input = QtWidgets.QDoubleSpinBox()
        self.voxel_height_input.setRange(0.001, 1.0)
        self.voxel_height_input.setValue(0.09)
        self.voxel_height_input.setDecimals(6)
        param_layout.addWidget(self.voxel_height_input, row, 1)
        
        param_layout.addWidget(QtWidgets.QLabel("X偏移:"), row, 2)
        self.offset_x_input = QtWidgets.QDoubleSpinBox()
        self.offset_x_input.setRange(-100.0, 100.0)
        self.offset_x_input.setValue(3.856697)
        self.offset_x_input.setDecimals(6)
        param_layout.addWidget(self.offset_x_input, row, 3)
        
        # Y偏移和Z偏移
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("Y偏移:"), row, 0)
        self.offset_y_input = QtWidgets.QDoubleSpinBox()
        self.offset_y_input.setRange(-100.0, 100.0)
        self.offset_y_input.setValue(-9.466439)
        self.offset_y_input.setDecimals(6)
        param_layout.addWidget(self.offset_y_input, row, 1)
        
        param_layout.addWidget(QtWidgets.QLabel("Z偏移:"), row, 2)
        self.offset_z_input = QtWidgets.QDoubleSpinBox()
        self.offset_z_input.setRange(-100.0, 100.0)
        self.offset_z_input.setValue(0.0)
        self.offset_z_input.setDecimals(6)
        param_layout.addWidget(self.offset_z_input, row, 3)
        
        # ROI参数
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("ROI [min_row, max_row, min_col, max_col]:"), row, 0)
        self.roi_layout = QtWidgets.QHBoxLayout()
        
        self.roi_min_row = QtWidgets.QSpinBox()
        self.roi_min_row.setRange(0, 4096)
        self.roi_min_row.setValue(15)
        self.roi_layout.addWidget(self.roi_min_row)
        
        self.roi_max_row = QtWidgets.QSpinBox()
        self.roi_max_row.setRange(0, 4096)
        self.roi_max_row.setValue(1521)
        self.roi_layout.addWidget(self.roi_max_row)
        
        self.roi_min_col = QtWidgets.QSpinBox()
        self.roi_min_col.setRange(0, 4096)
        self.roi_min_col.setValue(111)
        self.roi_layout.addWidget(self.roi_min_col)
        
        self.roi_max_col = QtWidgets.QSpinBox()
        self.roi_max_col.setRange(0, 4096)
        self.roi_max_col.setValue(1493)
        self.roi_layout.addWidget(self.roi_max_col)
        
        param_layout.addLayout(self.roi_layout, row, 1, 1, 3)
        
        # 将参数区域添加到主布局
        main_layout.addWidget(param_group)
        
        # 创建按钮区域
        button_layout = QtWidgets.QHBoxLayout()
        
        self.run_button = QtWidgets.QPushButton("运行重建")
        self.run_button.clicked.connect(self.run_reconstruction)
        button_layout.addWidget(self.run_button)
        
        self.close_button = QtWidgets.QPushButton("关闭")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        main_layout.addLayout(button_layout)
    
    def browse_data_folder(self):
        """浏览选择DICOM数据文件夹"""
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, 
            "选择DICOM数据文件夹",
            ""
        )
        
        if folder_path:
            self.data_path.setText(folder_path)
    
    def run_reconstruction(self):
        """运行圆轨迹CT重建 - 严格按照提供的代码实现"""
        try:
            # 检查数据路径是否已填写
            data_path = self.data_path.text().strip()
            if not data_path:
                QtWidgets.QMessageBox.warning(self, "警告", "请选择DICOM数据文件夹")
                return
            
            # 检查路径是否存在
            if not os.path.exists(data_path):
                QtWidgets.QMessageBox.critical(self, "错误", f"指定的路径不存在: {data_path}")
                return
            
            # 创建进度对话框
            progress = QtWidgets.QProgressDialog("正在进行圆轨迹CT重建...", "取消", 0, 100, self)
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            progress.show()
            QtWidgets.QApplication.processEvents()
            
            # 导入必要的库
            from leapctype import tomographicModels
            
            # 初始化LEAP CT系统
            progress.setValue(10)
            progress.setLabelText("初始化CT系统...")
            QtWidgets.QApplication.processEvents()
            
            leapct = tomographicModels()
            leapct.about()
            
            # 获取界面输入参数
            numAngles1 = self.num_angles_input.value()
            numRows = self.num_rows_input.value()
            numCols = self.num_cols_input.value()
            pixelHeight = self.pixel_height_input.value()
            pixelWidth = self.pixel_width_input.value()
            centerRow = self.center_row_input.value()
            centerCol = self.center_col_input.value()
            sod = self.sod_input.value()
            sdd = self.sdd_input.value()
            
            # 体素参数
            numX = self.num_x_input.value()
            numY = self.num_y_input.value()
            numZ = self.num_z_input.value()
            voxelWidth = self.voxel_width_input.value()
            voxelHeight = self.voxel_height_input.value()
            offsetX = self.offset_x_input.value()
            offsetY = self.offset_y_input.value()
            offsetZ = self.offset_z_input.value()
            
            # ROI参数
            roi = [
                self.roi_min_row.value(),
                self.roi_max_row.value(),
                self.roi_min_col.value(),
                self.roi_max_col.value()
            ]
            
            progress.setValue(20)
            progress.setLabelText("设置CT扫描几何参数...")
            QtWidgets.QApplication.processEvents()
            
            # 设置扫描几何参数（严格按照提供的代码）
            phis = leapct.setAngleArray(numAngles1, 360)
            leapct.set_conebeam(numAngles1, numRows, numCols, pixelHeight, pixelWidth, centerRow, centerCol, phis, sod, sdd)
            
            # 设置体积参数
            leapct.set_volume(numX, numY, numZ, voxelWidth, voxelHeight, offsetX, offsetY, offsetZ)
            
            progress.setValue(30)
            progress.setLabelText("分配内存空间...")
            QtWidgets.QApplication.processEvents()
            
            # 分配投影数据和体素数据空间
            g = leapct.allocate_projections()  # 形状是 numAngles, numRows, numCols
            f = leapct.allocate_volume()  # 形状是 numZ, numY, numX
            
            progress.setValue(40)
            progress.setLabelText("加载DICOM数据...")
            QtWidgets.QApplication.processEvents()
            
            # 从FileOperation模块导入加载DICOM图像的函数
            from File.FileOperation import loadDICOMImages
            
            # 加载DICOM图像
            g_loaded, dicom_info = loadDICOMImages(data_path)
            
            # 确保数据形状匹配
            if g_loaded.shape != g.shape:
                progress.close()
                # 释放已加载的数据
                del g_loaded, g, f
                import gc
                gc.collect()
                QtWidgets.QMessageBox.warning(
                    self, 
                    "错误", 
                    f"DICOM数据形状不匹配！\n期望形状: {g.shape}\n实际形状: {g_loaded.shape}"
                )
                return
            
            # 复制数据
            g[:] = g_loaded[:]
            
            # 立即释放g_loaded以节省内存
            del g_loaded
            import gc
            gc.collect()
            print("已释放DICOM加载数据内存")
            
            progress.setValue(50)
            progress.setLabelText("处理投影数据...")
            QtWidgets.QApplication.processEvents()
            
            # 导入makeAttenuationRadiographs函数
            from user_query import makeAttenuationRadiographs
            
            # 应用makeAttenuationRadiographs处理（严格按照提供的代码）
            makeAttenuationRadiographs(leapct, g, ROI=roi)
            
            progress.setValue(60)
            progress.setLabelText("打印CT系统参数...")
            QtWidgets.QApplication.processEvents()
            
            # 打印参数
            leapct.print_parameters()
            
            progress.setValue(70)
            progress.setLabelText("开始重建数据（FBP）...")
            QtWidgets.QApplication.processEvents()
            
            # 重建数据（严格按照提供的代码，只使用FBP）
            startTime = time.time()
            f = leapct.FBP(g)
            reconstruction_time = time.time() - startTime
            
            print('Reconstruction Elapsed Time: ' + str(reconstruction_time))
            
            progress.setValue(80)
            progress.setLabelText(f"重建完成，耗时: {reconstruction_time:.2f}秒")
            QtWidgets.QApplication.processEvents()
            
            # 释放投影数据以节省内存
            del g
            import gc
            gc.collect()
            print("已释放投影数据内存")
            
            progress.setValue(90)
            progress.setLabelText("使用LEAP显示重建结果...")
            QtWidgets.QApplication.processEvents()
            
            # 使用LEAP自带的显示功能（严格按照提供的代码）
            try:
                leapct.display(f)
            except Exception as e:
                print(f"使用LEAP显示重建结果失败: {str(e)}")
            
            progress.setValue(95)
            progress.setLabelText("在GUI中显示重建结果...")
            QtWidgets.QApplication.processEvents()
            
            # 同时在GUI中显示
            if self.parent:
                try:
                    # 打印重建结果信息（使用f直接访问，避免创建副本）
                    print(f"重建数组形状: {f.shape}")
                    print(f"重建数组数据类型: {f.dtype}")
                    
                    # 使用体素尺寸
                    spacing = (voxelWidth, voxelHeight, voxelHeight)
                    
                    # 直接传递f而不是创建副本
                    # 注意：load_reconstructed_data_no_copy会直接使用数据，不创建副本
                    self.parent.load_reconstructed_data_no_copy(f, spacing, "圆轨迹CT重建 (FBP)")
                    
                except Exception as e:
                    import traceback
                    print(f"在GUI中显示时出错: {str(e)}")
                    traceback.print_exc()
                    QtWidgets.QMessageBox.warning(self, "警告", f"在GUI中显示失败，但LEAP显示窗口应该已打开。\n错误: {str(e)}")
            
            progress.setValue(100)
            progress.close()
            
            # 释放所有无关数据以节省内存
            print("开始释放重建相关的临时数据...")
            
            # 释放重建后的数据f（已经在load_reconstructed_data_no_copy中处理了）
            # 注意：不能直接删除f，因为它可能仍在GUI中被引用
            # 但我们可以释放leapct对象和其他临时变量
            
            # 删除leapct对象
            del leapct
            
            # 删除其他大型临时变量
            try:
                del phis
            except:
                pass
            
            # 强制垃圾回收
            import gc
            gc.collect()
            print("已释放重建临时数据内存")
            
            # 关闭对话框
            self.accept()
            
            # 显示完成消息
            QtWidgets.QMessageBox.information(self, "完成", "CT圆轨迹重建完成！\n已释放所有临时数据。")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "错误", f"运行重建时出错: {str(e)}")


