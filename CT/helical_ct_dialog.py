# -*- coding: utf-8 -*-
"""螺旋CT重建对话框"""

from PyQt5 import QtWidgets, QtCore
import time
import numpy as np


class HelicalCTReconstructionDialog(QtWidgets.QDialog):
    """螺旋CT重建对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("CT螺旋重建")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        # 创建布局
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # 创建参数输入区域
        param_group = QtWidgets.QGroupBox("重建参数")
        param_layout = QtWidgets.QGridLayout()
        param_group.setLayout(param_layout)
        
        # 添加使用模拟数据的复选框
        self.use_simulated_data = QtWidgets.QCheckBox("使用模拟数据")
        self.use_simulated_data.setChecked(True)  # 默认使用模拟数据
        param_layout.addWidget(self.use_simulated_data, 0, 0, 1, 4)
        
        # 探测器参数
        row = 1
        param_layout.addWidget(QtWidgets.QLabel("探测器列数:"), row, 0)
        self.num_cols_input = QtWidgets.QSpinBox()
        self.num_cols_input.setRange(32, 2048)
        self.num_cols_input.setValue(512)
        param_layout.addWidget(self.num_cols_input, row, 1)
        
        param_layout.addWidget(QtWidgets.QLabel("旋转圈数:"), row, 2)
        self.num_turns_input = QtWidgets.QSpinBox()
        self.num_turns_input.setRange(1, 100)
        self.num_turns_input.setValue(10)
        param_layout.addWidget(self.num_turns_input, row, 3)
        
        # 投影角度
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("投影角度数量:"), row, 0)
        self.num_angles_input = QtWidgets.QSpinBox()
        self.num_angles_input.setRange(100, 10000)
        self.num_angles_input.setValue(2*2*int(360*512/1024)*10)
        self.num_angles_input.setEnabled(False)  # 自动计算
        param_layout.addWidget(self.num_angles_input, row, 1)
        
        param_layout.addWidget(QtWidgets.QLabel("像素大小:"), row, 2)
        self.pixel_size_input = QtWidgets.QDoubleSpinBox()
        self.pixel_size_input.setRange(0.01, 5.0)
        self.pixel_size_input.setValue(0.65*512/512)
        self.pixel_size_input.setDecimals(4)
        self.pixel_size_input.setEnabled(False)  # 自动计算
        param_layout.addWidget(self.pixel_size_input, row, 3)
        
        # 探测器行数
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("探测器行数:"), row, 0)
        self.num_rows_input = QtWidgets.QSpinBox()
        self.num_rows_input.setRange(1, 1024)
        self.num_rows_input.setValue(512//4)
        self.num_rows_input.setEnabled(False)  # 自动计算
        param_layout.addWidget(self.num_rows_input, row, 1)
        
        # 几何参数
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("源到物体距离:"), row, 0)
        self.sod_input = QtWidgets.QDoubleSpinBox()
        self.sod_input.setRange(10.0, 2000.0)
        self.sod_input.setValue(1100)
        param_layout.addWidget(self.sod_input, row, 1)
        
        param_layout.addWidget(QtWidgets.QLabel("源到探测器距离:"), row, 2)
        self.sdd_input = QtWidgets.QDoubleSpinBox()
        self.sdd_input.setRange(10.0, 2000.0)
        self.sdd_input.setValue(1400)
        param_layout.addWidget(self.sdd_input, row, 3)
        
        # 螺旋螺距
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("归一化螺旋螺距:"), row, 0)
        self.helical_pitch_input = QtWidgets.QDoubleSpinBox()
        self.helical_pitch_input.setRange(0.1, 10.0)
        self.helical_pitch_input.setValue(0.5)
        self.helical_pitch_input.setDecimals(2)
        param_layout.addWidget(self.helical_pitch_input, row, 1)
        
        param_layout.addWidget(QtWidgets.QLabel("重建方法:"), row, 2)
        self.recon_method_combo = QtWidgets.QComboBox()
        self.recon_method_combo.addItems(["FBP", "ASDPOCS", "SART", "OSEM", "LS"])
        param_layout.addWidget(self.recon_method_combo, row, 3)
        
        # 连接信号以自动更新计算值
        self.num_cols_input.valueChanged.connect(self.update_dependent_values)
        self.num_turns_input.valueChanged.connect(self.update_dependent_values)
        
        # 调用一次更新函数来初始化值
        self.update_dependent_values()
        
        # 将参数区域添加到主布局
        main_layout.addWidget(param_group)
        
        # 创建实际数据输入区域
        data_group = QtWidgets.QGroupBox("实际数据")
        data_layout = QtWidgets.QGridLayout()
        data_group.setLayout(data_layout)
        
        data_layout.addWidget(QtWidgets.QLabel("投影数据文件:"), 0, 0)
        self.projection_file_path = QtWidgets.QLineEdit()
        data_layout.addWidget(self.projection_file_path, 0, 1)
        
        self.browse_button = QtWidgets.QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_projection_file)
        data_layout.addWidget(self.browse_button, 0, 2)
        
        # 禁用实际数据输入区域（默认使用模拟数据）
        data_group.setEnabled(False)
        
        # 连接复选框状态变化信号
        self.use_simulated_data.stateChanged.connect(lambda state: data_group.setEnabled(not state))
        
        # 将实际数据区域添加到主布局
        main_layout.addWidget(data_group)
        
        # 创建按钮区域
        button_layout = QtWidgets.QHBoxLayout()
        
        self.run_button = QtWidgets.QPushButton("运行重建")
        self.run_button.clicked.connect(self.run_reconstruction)
        button_layout.addWidget(self.run_button)
        
        self.close_button = QtWidgets.QPushButton("关闭")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        main_layout.addLayout(button_layout)
    
    def update_dependent_values(self):
        """更新依赖于用户输入的计算值"""
        num_cols = self.num_cols_input.value()
        num_turns = self.num_turns_input.value()
        
        # 更新投影角度数量
        self.num_angles_input.setValue(2*2*int(360*num_cols/1024)*num_turns)
        
        # 更新像素大小
        self.pixel_size_input.setValue(0.65*512/num_cols)
        
        # 更新探测器行数
        self.num_rows_input.setValue(num_cols//4)
    
    def browse_projection_file(self):
        """浏览选择投影数据文件"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 
            "选择投影数据文件",
            "",
            "NumPy文件 (*.npy);;所有文件 (*)"
        )
        
        if file_path:
            self.projection_file_path.setText(file_path)
    
    def run_reconstruction(self):
        """运行螺旋CT重建并将结果显示在主视图中"""
        try:
            from leapctype import tomographicModels, filterSequence, TV
            
            # 创建进度对话框
            progress = QtWidgets.QProgressDialog("正在进行螺旋CT重建...", "取消", 0, 100, self)
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            progress.show()
            QtWidgets.QApplication.processEvents()
            
            # 获取界面输入参数
            numCols = self.num_cols_input.value()
            numTurns = self.num_turns_input.value()
            numAngles = self.num_angles_input.value()
            pixelSize = self.pixel_size_input.value()
            numRows = self.num_rows_input.value()
            sod = self.sod_input.value()
            sdd = self.sdd_input.value()
            helicalPitch = self.helical_pitch_input.value()
            reconMethod = self.recon_method_combo.currentText()
            
            progress.setValue(10)
            progress.setLabelText("初始化CT系统参数...")
            QtWidgets.QApplication.processEvents()
            
            # 初始化LEAP CT系统
            leapct = tomographicModels()
            
            # 设置扫描几何参数
            leapct.set_conebeam(numAngles, numRows, numCols, pixelSize, pixelSize, 
                               0.5*(numRows-1), 0.5*(numCols-1), 
                               leapct.setAngleArray(numAngles, 360.0*numTurns), 
                               sod, sdd)
            
            # 设置螺旋螺距
            leapct.set_normalizedHelicalPitch(helicalPitch)
            
            # 设置体素参数
            leapct.set_default_volume()
            
            progress.setValue(20)
            progress.setLabelText("分配内存空间...")
            QtWidgets.QApplication.processEvents()
            
            # 分配投影数据和体素数据空间
            g = leapct.allocateProjections()
            f = leapct.allocateVolume()
            
            progress.setValue(30)
            
            if self.use_simulated_data.isChecked():
                # 使用模拟数据
                progress.setLabelText("生成模拟数据...")
                QtWidgets.QApplication.processEvents()
                
                # 使用FORBILD头模体作为模拟数据
                leapct.set_FORBILD(f, True)
                
                progress.setValue(40)
                progress.setLabelText("正向投影生成数据...")
                QtWidgets.QApplication.processEvents()
                
                # 正向投影生成投影数据
                startTime = time.time()
                leapct.project(g, f)
                projection_time = time.time() - startTime
                
                progress.setValue(60)
                progress.setLabelText(f"正向投影完成，耗时: {projection_time:.2f}秒")
                QtWidgets.QApplication.processEvents()
                
            else:
                # 使用实际数据
                projection_file = self.projection_file_path.text()
                if not projection_file:
                    progress.close()
                    QtWidgets.QMessageBox.warning(self, "警告", "请选择投影数据文件")
                    return
                
                progress.setLabelText("加载实际投影数据...")
                QtWidgets.QApplication.processEvents()
                
                try:
                    g_loaded = np.load(projection_file)
                    # 确保数据形状匹配
                    if g_loaded.shape == g.shape:
                        g[:] = g_loaded[:]
                        progress.setValue(60)
                        progress.setLabelText("投影数据已加载")
                        QtWidgets.QApplication.processEvents()
                    else:
                        progress.close()
                        QtWidgets.QMessageBox.warning(
                            self, 
                            "错误", 
                            f"投影数据形状不匹配！\n期望形状: {g.shape}\n实际形状: {g_loaded.shape}"
                        )
                        return
                except Exception as e:
                    progress.close()
                    QtWidgets.QMessageBox.critical(self, "错误", f"加载投影数据时出错: {str(e)}")
                    return
            
            # 重置体素数组
            f[:] = 0.0
            
            progress.setValue(70)
            progress.setLabelText("正在进行重建...")
            QtWidgets.QApplication.processEvents()
            
            # 重建数据
            startTime = time.time()
            
            # 根据选择的重建方法执行重建
            if reconMethod == "FBP":
                leapct.FBP(g, f)
            elif reconMethod == "ASDPOCS":
                filters = filterSequence(1.0e0)
                filters.append(TV(leapct, delta=0.02/20.0))
                leapct.ASDPOCS(g, f, 10, 10, 1, filters)
            elif reconMethod == "SART":
                leapct.SART(g, f, 10, 10)
            elif reconMethod == "OSEM":
                leapct.OSEM(g, f, 10, 10)
            elif reconMethod == "LS":
                leapct.LS(g, f, 50, "SQS")
            
            reconstruction_time = time.time() - startTime
            
            progress.setValue(90)
            progress.setLabelText(f"重建完成，耗时: {reconstruction_time:.2f}秒")
            QtWidgets.QApplication.processEvents()
            
            # 获取重建结果的NumPy数组
            reconstructed_volume = np.array(f, copy=True)
            
            progress.setValue(95)
            progress.setLabelText("正在更新视图...")
            QtWidgets.QApplication.processEvents()
            
            # 关闭对话框
            self.accept()
            
            # 更新CTViewer4视图
            if self.parent:
                # 获取LEAP重建的体素间距
                try:
                    # 获取体素大小
                    voxel_size = leapct.get_voxelWidth()  # 假设体素是立方体
                    spacing = (voxel_size, voxel_size, voxel_size)
                except:
                    # 如果无法获取，则使用默认体素间距
                    spacing = (pixelSize, pixelSize, pixelSize)
                
                # 通过SimpleITKImage类创建SimpleITK图像
                from File.DataTransform import SimpleITKImage
                
                # 检查重建结果数组
                print(f"重建数组形状: {reconstructed_volume.shape}")
                print(f"重建数组范围: 最小值={reconstructed_volume.min()}, 最大值={reconstructed_volume.max()}")
                
                # 创建SimpleITK图像
                sitk_image = SimpleITKImage.from_numpy(reconstructed_volume, spacing)
                
                # 更新父窗口视图
                self.parent.load_reconstructed_data(sitk_image, reconstructed_volume, 
                                                  f"螺旋CT重建 ({reconMethod})")
                
            progress.setValue(100)
            progress.close()
                
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"运行重建时出错: {str(e)}")
