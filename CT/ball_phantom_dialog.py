# -*- coding: utf-8 -*-
"""球体标定对话框"""

from PyQt5 import QtWidgets, QtCore
import tempfile
import os
import sys
import subprocess


class BallPhantomCalibrationDialog(QtWidgets.QDialog):
    """球体标定对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("多球标定")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        # 创建布局
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # 创建参数输入区域
        param_group = QtWidgets.QGroupBox("标定参数")
        param_layout = QtWidgets.QGridLayout()
        param_group.setLayout(param_layout)
        
        # 添加使用模拟数据的复选框
        self.use_simulated_data = QtWidgets.QCheckBox("使用模拟数据")
        self.use_simulated_data.setChecked(True)  # 默认使用模拟数据
        param_layout.addWidget(self.use_simulated_data, 0, 0, 1, 4)
        
        # 几何参数输入
        row = 1  # 第一行是复选框
        
        # 数据维度
        param_layout.addWidget(QtWidgets.QLabel("数据尺寸调整因子 (L):"), row, 0)
        self.L_input = QtWidgets.QSpinBox()
        self.L_input.setRange(1, 10)
        self.L_input.setValue(1)
        param_layout.addWidget(self.L_input, row, 1)
        
        param_layout.addWidget(QtWidgets.QLabel("投影角度数量:"), row, 2)
        self.num_angles_input = QtWidgets.QSpinBox()
        self.num_angles_input.setRange(10, 1000)
        self.num_angles_input.setValue(36)
        param_layout.addWidget(self.num_angles_input, row, 3)
        
        # 几何参数
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("源到物体距离 (SOD):"), row, 0)
        self.sod_input = QtWidgets.QDoubleSpinBox()
        self.sod_input.setRange(10.0, 3000.0)
        self.sod_input.setValue(669)
        self.sod_input.setDecimals(2)
        param_layout.addWidget(self.sod_input, row, 1)
        
        param_layout.addWidget(QtWidgets.QLabel("源到探测器距离 (SDD):"), row, 2)
        self.sdd_input = QtWidgets.QDoubleSpinBox()
        self.sdd_input.setRange(10.0, 3000.0)
        self.sdd_input.setValue(1470)
        self.sdd_input.setDecimals(2)
        param_layout.addWidget(self.sdd_input, row, 3)
        
        # 球体参数
        row += 1
        param_layout.addWidget(QtWidgets.QLabel("球半径:"), row, 0)
        self.ball_radius_input = QtWidgets.QDoubleSpinBox()
        self.ball_radius_input.setRange(0.1, 10.0)
        self.ball_radius_input.setValue(0.5*1.0/2.0)
        self.ball_radius_input.setDecimals(4)
        param_layout.addWidget(self.ball_radius_input, row, 1)
        
        param_layout.addWidget(QtWidgets.QLabel("球体间距 (T_z):"), row, 2)
        self.Tz_input = QtWidgets.QDoubleSpinBox()
        self.Tz_input.setRange(0.1, 20.0)
        self.Tz_input.setValue(4*0.5*1.0/2.0)  # 默认为4倍球半径
        self.Tz_input.setDecimals(4)
        self.Tz_input.setEnabled(False)  # 自动计算
        param_layout.addWidget(self.Tz_input, row, 3)
        
        # 更新T_z自动计算
        self.ball_radius_input.valueChanged.connect(self.update_Tz)
        
        # 将参数区域添加到主布局
        main_layout.addWidget(param_group)
        
        # 创建实际数据输入区域
        data_group = QtWidgets.QGroupBox("实际数据与分割参数")
        data_layout = QtWidgets.QGridLayout()
        data_group.setLayout(data_layout)
        
        data_layout.addWidget(QtWidgets.QLabel("投影数据文件夹:"), 0, 0)
        self.projection_file_path = QtWidgets.QLineEdit()
        data_layout.addWidget(self.projection_file_path, 0, 1)
        
        self.browse_button = QtWidgets.QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_projection_folder)
        data_layout.addWidget(self.browse_button, 0, 2)
        
        # 添加分割参数
        data_layout.addWidget(QtWidgets.QLabel("分割阈值:"), 1, 0)
        self.segmentation_threshold_input = QtWidgets.QDoubleSpinBox()
        self.segmentation_threshold_input.setRange(0.0, 100000.0)
        self.segmentation_threshold_input.setValue(1000.0)  # 默认值
        self.segmentation_threshold_input.setDecimals(2)
        self.segmentation_threshold_input.setSingleStep(10.0)
        data_layout.addWidget(self.segmentation_threshold_input, 1, 1)
        
        threshold_note = QtWidgets.QLabel("(用于球体分割的阈值)")
        threshold_note.setStyleSheet("color: gray; font-size: 9pt;")
        data_layout.addWidget(threshold_note, 1, 2)
        
        # 添加min_size参数
        data_layout.addWidget(QtWidgets.QLabel("最小球体尺寸 (min_size):"), 2, 0)
        self.min_size_input = QtWidgets.QSpinBox()
        self.min_size_input.setRange(1, 10000)
        self.min_size_input.setValue(50)  # 默认值
        data_layout.addWidget(self.min_size_input, 2, 1)
        
        min_size_note = QtWidgets.QLabel("(最小连通区域像素数)")
        min_size_note.setStyleSheet("color: gray; font-size: 9pt;")
        data_layout.addWidget(min_size_note, 2, 2)
        
        # 添加max_size参数
        data_layout.addWidget(QtWidgets.QLabel("最大球体尺寸 (max_size):"), 3, 0)
        self.max_size_input = QtWidgets.QSpinBox()
        self.max_size_input.setRange(1, 100000)
        self.max_size_input.setValue(5000)  # 默认值
        data_layout.addWidget(self.max_size_input, 3, 1)
        
        max_size_note = QtWidgets.QLabel("(最大连通区域像素数)")
        max_size_note.setStyleSheet("color: gray; font-size: 9pt;")
        data_layout.addWidget(max_size_note, 3, 2)
        
        # 添加数据旋转选项
        data_layout.addWidget(QtWidgets.QLabel("数据旋转:"), 4, 0)
        self.rotation_combo = QtWidgets.QComboBox()
        self.rotation_combo.addItems(["不旋转", "顺时针90度", "逆时针90度"])
        data_layout.addWidget(self.rotation_combo, 4, 1)
        
        rotation_note = QtWidgets.QLabel("(投影数据旋转)")
        rotation_note.setStyleSheet("color: gray; font-size: 9pt;")
        data_layout.addWidget(rotation_note, 4, 2)
        
        # 添加归一化处理选项
        self.apply_preprocessing = QtWidgets.QCheckBox("应用数据归一化")
        self.apply_preprocessing.setChecked(True)  # 默认启用
        data_layout.addWidget(self.apply_preprocessing, 5, 0, 1, 3)
        
        # 禁用实际数据输入区域（默认使用模拟数据）
        data_group.setEnabled(False)
        
        # 连接复选框状态变化信号
        self.use_simulated_data.stateChanged.connect(lambda state: data_group.setEnabled(not state))
        
        # 将实际数据区域添加到主布局
        main_layout.addWidget(data_group)
        
        # 创建按钮区域
        button_layout = QtWidgets.QHBoxLayout()
        
        self.run_button = QtWidgets.QPushButton("运行标定")
        self.run_button.clicked.connect(self.run_calibration)
        button_layout.addWidget(self.run_button)
        
        self.close_button = QtWidgets.QPushButton("关闭")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        main_layout.addLayout(button_layout)
        
        # 不再需要在对话框中存储变量，因为标定在单独的进程中运行
        
    def update_Tz(self):
        """更新球体间距，默认为球半径的4倍"""
        self.Tz_input.setValue(4 * self.ball_radius_input.value())
        
    def browse_projection_folder(self):
        """浏览选择投影数据文件夹"""
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, 
            "选择包含DICOM文件的文件夹",
            ""
        )
        
        if folder_path:
            self.projection_file_path.setText(folder_path)
    
    def run_calibration(self):
        """运行标定"""
        try:
            # 创建一个临时Python脚本文件，包含多球标定代码
            with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w', encoding='utf-8') as f:
                script_path = f.name
                
                # 获取界面输入参数
                L = self.L_input.value()
                numAngles = self.num_angles_input.value()
                pixelSize = 11.62/1000.0*L
                numCols = 4000//L
                numRows = 2096//L
                sod = self.sod_input.value()
                sdd = self.sdd_input.value()
                ballRadius = self.ball_radius_input.value()
                # T_z = self.Tz_input.value()
                T_z = 17
                segmentation_threshold = self.segmentation_threshold_input.value()
                min_size = self.min_size_input.value()
                max_size = self.max_size_input.value()
                rotation_option = self.rotation_combo.currentIndex()  # 0: 不旋转, 1: 顺时针90度, 2: 逆时针90度
                apply_preprocessing = self.apply_preprocessing.isChecked()
                
                # 写入标定脚本
                f.write('# -*- coding: utf-8 -*-\n')  # 添加编码声明
                f.write('from leap_preprocessing_algorithms import *\n')
                f.write('from leapctype import *\n')
                f.write('import matplotlib\n')
                f.write('matplotlib.use("TKAGG")\n')
                f.write('import numpy as np\n\n')
                
                if self.use_simulated_data.isChecked():
                    # 使用模拟数据 - 使用界面参数设置几何
                    f.write('# Set nominal geometry from UI parameters\n')
                    f.write(f'L = {L}\n')
                    f.write(f'numCols = {numCols}\n')
                    f.write(f'numAngles = {numAngles}\n')
                    f.write(f'pixelSize = {pixelSize}\n')
                    f.write(f'numRows = {numRows}\n')
                    f.write(f'sod = {sod}\n')
                    f.write(f'sdd = {sdd}\n')
                    f.write(f'centerRow = {0.5*(numRows-1)}\n')
                    f.write(f'centerCol = {0.5*(numCols-1) + 60.0}\n')
                    f.write('leapct = tomographicModels()\n')
                    f.write('leapct.set_conebeam(numAngles, numRows, numCols, pixelSize, pixelSize, centerRow, centerCol, leapct.setAngleArray(numAngles, 360.0), sod, sdd)\n')
                    f.write('leapct.set_default_volume()\n\n')
                    
                    # 写入模拟数据生成代码
                    f.write('# Set "true" geometry (perturbation)\n')
                    f.write('leapct_true = tomographicModels()\n')
                    f.write('leapct_true.copy_parameters(leapct)\n')
                    f.write('leapct_true.set_sod(leapct_true.get_sod()+10.0)\n')
                    f.write('leapct_true.set_sdd(leapct_true.get_sdd()+20.0)\n')
                    f.write('leapct_true.set_centerRow(leapct_true.get_centerRow()-10.0)\n')
                    f.write('leapct_true.set_centerCol(leapct_true.get_centerCol()-15.0)\n')
                    f.write('leapct_true.convert_to_modularbeam()\n')
                    f.write('leapct_true.rotate_detector(1.0)\n\n')
                    
                    f.write('# Simulate data using "true" geometry\n')
                    f.write(f'ballRadius = {ballRadius}\n')
                    f.write('r = 10.0\n')
                    f.write(f'T_z = {T_z}\n')
                    f.write(f'numBalls = int(15.0/T_z)\n')
                    f.write('z_0 = -T_z*0.5*(numBalls-1.0)\n')
                    f.write('alpha = 5.0*np.pi/180.0\n\n')
                    
                    f.write('leapct_true.addObject(None, 4, 0.0, np.array([11.0, 11.0, 8.0]), 0.04, oversampling=1)\n')
                    f.write('leapct_true.addObject(None, 4, 0.0, np.array([9.0, 9.0, 8.0]), 0.00, oversampling=1)\n')
                    f.write('for k in range(numBalls):\n')
                    f.write('    leapct_true.addObject(None, 0, np.array([r*np.cos(alpha), r*np.sin(alpha), T_z*k+z_0]), ballRadius, 2.25, oversampling=3)\n')
                    f.write('g = leapct_true.allocate_projections()\n')
                    f.write('leapct_true.rayTrace(g, oversampling=1)\n')
                    f.write('print("Simulated data has been generated for calibration")\n\n')
                else:
                    # 使用实际数据
                    projection_folder = self.projection_file_path.text()
                    if not projection_folder:
                        QtWidgets.QMessageBox.warning(self, "警告", "请选择投影数据文件夹")
                        os.unlink(script_path)  # 删除临时文件
                        return
                    
                    # 检查文件夹是否存在
                    if not os.path.isdir(projection_folder):
                        QtWidgets.QMessageBox.warning(self, "警告", "所选路径不是有效的文件夹")
                        os.unlink(script_path)  # 删除临时文件
                        return
                    
                    # 将路径转换为Windows格式的字符串，避免转义问题
                    projection_folder_escaped = projection_folder.replace('\\', '/')
                    
                    # 先创建leapct对象用于后续的negLog操作
                    f.write(f'# Initialize leapct object for preprocessing\n')
                    f.write(f'leapct = tomographicModels()\n\n')
                    
                    # 先加载实际数据
                    f.write(f'# Load actual projection data from DICOM folder\n')
                    f.write(f'import sys\n')
                    f.write(f'sys.path.append("{os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), "/")}")\n')
                    f.write(f'from File.FileOperation import loadDICOMImages\n')
                    f.write(f'g, dicom_info = loadDICOMImages("{projection_folder_escaped}")\n')
                    f.write(f'print("DICOM files loaded from folder, shape: ", g.shape)\n')
                    f.write(f'print("DICOM Header Info: ", dicom_info)\n\n')
                    
                    # 添加数据旋转代码
                    if rotation_option == 1:  # 顺时针90度
                        f.write(f'# Apply clockwise 90 degree rotation\n')
                        f.write(f'print("Applying clockwise 90 degree rotation...")\n')
                        f.write(f'g = np.rot90(g, k=-1, axes=(1, 2))  # k=-1 for clockwise rotation\n')
                        f.write(f'print("After rotation, shape: ", g.shape)\n\n')
                    elif rotation_option == 2:  # 逆时针90度
                        f.write(f'# Apply counter-clockwise 90 degree rotation\n')
                        f.write(f'print("Applying counter-clockwise 90 degree rotation...")\n')
                        f.write(f'g = np.rot90(g, k=1, axes=(1, 2))  # k=1 for counter-clockwise rotation\n')
                        f.write(f'print("After rotation, shape: ", g.shape)\n\n')
                    
                    # 添加数据预处理代码
                    if apply_preprocessing:
                        f.write(f'# Apply data preprocessing: normalization\n')
                        f.write(f'print("Applying data normalization...")\n')
                        f.write(f'print(f"Before normalization - dtype: {{g.dtype}}, min: {{np.min(g):.4f}}, max: {{np.max(g):.4f}}, mean: {{np.mean(g):.4f}}")\n')
                        f.write(f'g = g / np.max(g)  # Normalize by maximum value\n')
                        f.write(f'print(f"After normalization - min: {{np.min(g):.4f}}, max: {{np.max(g):.4f}}, mean: {{np.mean(g):.4f}}")\n')
                        f.write(f'g = np.ascontiguousarray(g, dtype=np.float32)  # Convert to C-contiguous float32 array\n')
                        f.write('print(f"After dtype conversion - dtype: {g.dtype}, C_CONTIGUOUS: {g.flags[\'C_CONTIGUOUS\']}")\n\n')
                    
                    # 从DICOM header中读取参数
                    f.write(f'# Extract CT geometry parameters from DICOM header\n')
                    
                    # 如果旋转了90度，需要交换行列数
                    if rotation_option in [1, 2]:  # 如果进行了90度旋转
                        f.write(f'# After 90 degree rotation, rows and columns are swapped\n')
                        f.write(f'numRows = g.shape[2]  # Use actual shape after rotation\n')
                        f.write(f'numCols = g.shape[1]  # Use actual shape after rotation\n')
                        f.write(f'# Note: Original DICOM had Rows={{dicom_info["Rows"]}}, Columns={{dicom_info["Columns"]}}\n')
                    else:
                        f.write(f'numRows = dicom_info["Rows"]\n')
                        f.write(f'numCols = dicom_info["Columns"]\n')
                    
                    f.write(f'pixelSize = dicom_info["HorizontalPixelSize"]  # 使用水平像素大小\n')
                    f.write(f'sdd = dicom_info["DistanceSourceToDetector"]\n')
                    f.write(f'sod = dicom_info["DistanceSourceToPatient"]\n')
                    f.write(f'numAngles = g.shape[0]  # 投影数量(dcm文件数量)即为角度数量\n')
                    f.write(f'centerRow = 0.5*(numRows-1)\n')
                    f.write(f'centerCol = 0.5*(numCols-1)\n')
                    f.write(f'print(f"Parameters from DICOM: numRows={{numRows}}, numCols={{numCols}}, pixelSize={{pixelSize:.6f}}, sod={{sod}}, sdd={{sdd}}, numAngles={{numAngles}}")\n\n')
                    
                    # 用DICOM参数设置CT几何
                    f.write(f'# Set CT geometry with DICOM parameters\n')
                    f.write(f'leapct.set_conebeam(numAngles, numRows, numCols, pixelSize, pixelSize, centerRow, centerCol, leapct.setAngleArray(numAngles, 360.0), sod, sdd)\n')
                    f.write(f'leapct.set_default_volume()\n\n')
                
                # 写入标定代码
                f.write('# Initialize ball phantom calibration object\n')
                f.write(f'segmentation_threshold = {segmentation_threshold}\n')
                f.write(f'min_size = {min_size}\n')
                f.write(f'max_size = {max_size}\n')
                f.write(f'print(f"Segmentation threshold: {{segmentation_threshold:.2f}} (max of g: {{np.max(g):.2f}})")\n')
                f.write(f'print(f"Min size: {{min_size}}, Max size: {{max_size}}")\n')
                f.write(f'cal = ball_phantom_calibration(leapct, {T_z}, g, min_size=min_size, max_size=max_size, segmentation_threshold=segmentation_threshold)\n\n')
                
                f.write('# Get initial parameter estimate\n')
                f.write('x = cal.initial_guess(g)\n')
                f.write('print("Initial CT geometry parameters: ", x)\n')
                f.write('print("Initial cost function value: ", cal.cost(x))\n\n')
                
                f.write('# Show calibration results\n')
                f.write('cal.do_plot(x)\n\n')
                
                f.write('# Perform optimization\n')
                f.write('res = cal.optimize(x, True)\n')
                f.write('print("Optimized CT geometry parameters: ", res.x)\n')
                f.write('print("Optimized cost function value: ", cal.cost(res.x))\n')
                f.write('cal.do_plot(res.x)\n\n')
                
                # 添加保存参数到文件的代码
                f.write('# Save calibration results\n')
                f.write('import json\n')
                f.write('import datetime\n\n')
                f.write('# Get optimized parameters\n')
                f.write('optimized_params = res.x\n')
                f.write('print("[centerRow, centerCol, sod, odd, psi, theta, phi, r, z_0, phase]")\n')
                f.write('print("Guess of CT geometry parameters: ", optimized_params)\n')
                f.write('print(f"优化后的损失: {cal.cost(optimized_params):.6f}")\n')
                f.write('print(f"探测器水平中心: {(optimized_params[0]):.6f}")\n')
                f.write('print(f"探测器垂直中心: {(optimized_params[1]):.6f}")\n')
                f.write('print(f"探测器sdd: {(optimized_params[2] + optimized_params[3]):.6f}")\n')
                f.write('print(f"探测器sod: {optimized_params[2]:.6f}")\n')
                f.write('print(f"探测器水平方向偏移量: {(optimized_params[1] - (numRows - 1) / 2.0):.6f}")\n')
                f.write('print(f"探测器垂直方向偏移量: {(optimized_params[0] - (numCols - 1) / 2.0):.6f}")\n')
                f.write('print(f"探测器面内旋转角: {optimized_params[5]:.6f}")\n')
                f.write('print(f"探测器水平旋转角: {optimized_params[4]:.6f}")\n')
                f.write('print(f"探测器垂直旋转角: {optimized_params[6]:.6f}")\n\n')
                
                f.write('# Prepare calibration results dictionary\n')
                f.write('calibration_results = {\n')
                f.write('    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),\n')
                f.write('    "raw_parameters": {\n')
                f.write('        "centerRow": float(optimized_params[0]),\n')
                f.write('        "centerCol": float(optimized_params[1]),\n')
                f.write('        "sod": float(optimized_params[2]),\n')
                f.write('        "odd": float(optimized_params[3]),\n')
                f.write('        "psi": float(optimized_params[4]),\n')
                f.write('        "theta": float(optimized_params[5]),\n')
                f.write('        "phi": float(optimized_params[6]),\n')
                f.write('        "r": float(optimized_params[7]),\n')
                f.write('        "z_0": float(optimized_params[8]),\n')
                f.write('        "phase": float(optimized_params[9]) if len(optimized_params) > 9 else 0.0\n')
                f.write('    },\n')
                f.write('    "derived_parameters": {\n')
                f.write('        "detector_horizontal_center": float(optimized_params[2] + optimized_params[3]),\n')
                f.write('        "detector_vertical_center": float(optimized_params[2]),\n')
                f.write('        "detector_horizontal_offset": float(optimized_params[1] - (numRows - 1) / 2.0),\n')
                f.write('        "detector_vertical_offset": float(optimized_params[0] - (numCols - 1) / 2.0),\n')
                f.write('        "detector_in_plane_rotation_angle": float(optimized_params[5]),\n')
                f.write('        "detector_horizontal_rotation_angle": float(optimized_params[4]),\n')
                f.write('        "detector_vertical_rotation_angle": float(optimized_params[6])\n')
                f.write('    },\n')
                f.write('    "optimization_info": {\n')
                f.write('        "final_cost": float(cal.cost(optimized_params)),\n')
                f.write('        "initial_cost": float(cal.cost(x)),\n')
                f.write('        "success": bool(res.success),\n')
                f.write('        "message": str(res.message)\n')
                f.write('    },\n')
                f.write('    "geometry_info": {\n')
                f.write('        "numRows": int(numRows),\n')
                f.write('        "numCols": int(numCols),\n')
                f.write('        "numAngles": int(numAngles),\n')
                f.write('        "pixelSize": float(pixelSize),\n')
                f.write('        "sod": float(sod),\n')
                f.write('        "sdd": float(sdd)\n')
                f.write('    },\n')
                f.write('    "segmentation_parameters": {\n')
                f.write('        "segmentation_threshold": float(segmentation_threshold),\n')
                f.write('        "min_size": int(min_size),\n')
                f.write('        "max_size": int(max_size)\n')
                f.write('    }\n')
                f.write('}\n\n')
                
                f.write('# Save to JSON file\n')
                f.write('json_filename = "calibration_results_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"\n')
                f.write('with open(json_filename, "w", encoding="utf-8") as json_file:\n')
                f.write('    json.dump(calibration_results, json_file, indent=4, ensure_ascii=False)\n')
                f.write('print(f"\\n标定结果已保存到: {json_filename}")\n\n')
                
                f.write('# Also save to TXT file for easy reading\n')
                f.write('txt_filename = "calibration_results_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".txt"\n')
                f.write('with open(txt_filename, "w", encoding="utf-8") as txt_file:\n')
                f.write('    txt_file.write("=" * 80 + "\\n")\n')
                f.write('    txt_file.write("CT几何标定结果\\n")\n')
                f.write('    txt_file.write("=" * 80 + "\\n")\n')
                f.write('    txt_file.write(f"标定时间: {calibration_results[\'timestamp\']}\\n\\n")\n')
                f.write('    txt_file.write("-" * 80 + "\\n")\n')
                f.write('    txt_file.write("原始优化参数\\n")\n')
                f.write('    txt_file.write("-" * 80 + "\\n")\n')
                f.write('    txt_file.write("[centerRow, centerCol, sod, odd, psi, theta, phi, r, z_0, phase]\\n")\n')
                f.write('    txt_file.write(f"{list(optimized_params)}\\n\\n")\n')
                f.write('    for key, value in calibration_results["raw_parameters"].items():\n')
                f.write('        txt_file.write(f"{key:20s}: {value:.6f}\\n")\n')
                f.write('    txt_file.write("\\n" + "-" * 80 + "\\n")\n')
                f.write('    txt_file.write("派生参数\\n")\n')
                f.write('    txt_file.write("-" * 80 + "\\n")\n')
                f.write('    txt_file.write(f"探测器水平中心      : {calibration_results[\'derived_parameters\'][\'detector_horizontal_center\']:.6f}\\n")\n')
                f.write('    txt_file.write(f"探测器垂直中心      : {calibration_results[\'derived_parameters\'][\'detector_vertical_center\']:.6f}\\n")\n')
                f.write('    txt_file.write(f"探测器水平方向偏移量: {calibration_results[\'derived_parameters\'][\'detector_horizontal_offset\']:.6f}\\n")\n')
                f.write('    txt_file.write(f"探测器垂直方向偏移量: {calibration_results[\'derived_parameters\'][\'detector_vertical_offset\']:.6f}\\n")\n')
                f.write('    txt_file.write(f"探测器面内旋转角    : {calibration_results[\'derived_parameters\'][\'detector_in_plane_rotation_angle\']:.6f}\\n")\n')
                f.write('    txt_file.write(f"探测器水平旋转角    : {calibration_results[\'derived_parameters\'][\'detector_horizontal_rotation_angle\']:.6f}\\n")\n')
                f.write('    txt_file.write(f"探测器垂直旋转角    : {calibration_results[\'derived_parameters\'][\'detector_vertical_rotation_angle\']:.6f}\\n")\n')
                f.write('    txt_file.write("\\n" + "-" * 80 + "\\n")\n')
                f.write('    txt_file.write("优化信息\\n")\n')
                f.write('    txt_file.write("-" * 80 + "\\n")\n')
                f.write('    txt_file.write(f"初始损失值: {calibration_results[\'optimization_info\'][\'initial_cost\']:.6f}\\n")\n')
                f.write('    txt_file.write(f"优化后损失: {calibration_results[\'optimization_info\'][\'final_cost\']:.6f}\\n")\n')
                f.write('    txt_file.write(f"优化成功  : {calibration_results[\'optimization_info\'][\'success\']}\\n")\n')
                f.write('    txt_file.write(f"优化信息  : {calibration_results[\'optimization_info\'][\'message\']}\\n")\n')
                f.write('    txt_file.write("\\n" + "-" * 80 + "\\n")\n')
                f.write('    txt_file.write("几何信息\\n")\n')
                f.write('    txt_file.write("-" * 80 + "\\n")\n')
                f.write('    for key, value in calibration_results["geometry_info"].items():\n')
                f.write('        txt_file.write(f"{key:20s}: {value}\\n")\n')
                f.write('    txt_file.write("\\n" + "-" * 80 + "\\n")\n')
                f.write('    txt_file.write("分割参数\\n")\n')
                f.write('    txt_file.write("-" * 80 + "\\n")\n')
                f.write('    txt_file.write(f"分割阈值            : {calibration_results[\'segmentation_parameters\'][\'segmentation_threshold\']:.2f}\\n")\n')
                f.write('    txt_file.write(f"最小球体尺寸        : {calibration_results[\'segmentation_parameters\'][\'min_size\']}\\n")\n')
                f.write('    txt_file.write(f"最大球体尺寸        : {calibration_results[\'segmentation_parameters\'][\'max_size\']}\\n")\n')
                f.write('    txt_file.write("=" * 80 + "\\n")\n')
                f.write('print(f"标定结果已保存到: {txt_filename}\\n")\n')
            
            # Display confirmation dialog (using English to avoid encoding issues)
            reply = QtWidgets.QMessageBox.question(
                self, 
                'Confirm', 
                'Ball phantom calibration will be launched in a new window.\nContinue?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes
            )
            
            if reply == QtWidgets.QMessageBox.Yes:
                # Use Python interpreter to run the temporary script
                subprocess.Popen([sys.executable, script_path])
                QtWidgets.QMessageBox.information(self, "Ball Phantom Calibration", "Calibration program launched. Please check the results in the new window.")
            else:
                # Delete the temporary file
                os.unlink(script_path)
                
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Error running calibration: {str(e)}")
    
    # 优化功能已经集成到run_calibration方法生成的脚本中
