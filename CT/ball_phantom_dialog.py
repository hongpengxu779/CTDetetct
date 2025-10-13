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
        self.sod_input.setRange(10.0, 1000.0)
        self.sod_input.setValue(255.8)
        self.sod_input.setDecimals(2)
        param_layout.addWidget(self.sod_input, row, 1)
        
        param_layout.addWidget(QtWidgets.QLabel("源到探测器距离 (SDD):"), row, 2)
        self.sdd_input = QtWidgets.QDoubleSpinBox()
        self.sdd_input.setRange(10.0, 1000.0)
        self.sdd_input.setValue(345.1)
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
        
    def browse_projection_file(self):
        """浏览选择投影数据文件"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 
            "选择投影数据文件",
            "",
            "所有文件 (*)"
        )
        
        if file_path:
            self.projection_file_path.setText(file_path)
    
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
                T_z = self.Tz_input.value()
                
                # 写入标定脚本
                f.write('# -*- coding: utf-8 -*-\n')  # 添加编码声明
                f.write('from leap_preprocessing_algorithms import *\n')
                f.write('from leapctype import *\n')
                f.write('import matplotlib\n')
                f.write('matplotlib.use("TKAGG")\n')
                f.write('import numpy as np\n\n')
                
                f.write('# Set nominal geometry\n')
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
                
                if self.use_simulated_data.isChecked():
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
                    projection_file = self.projection_file_path.text()
                    if not projection_file:
                        QtWidgets.QMessageBox.warning(self, "警告", "请选择投影数据文件")
                        os.unlink(script_path)  # 删除临时文件
                        return
                    
                    f.write(f'# Load actual projection data\n')
                    f.write(f'import numpy as np\n')
                    f.write(f'g = np.load("{projection_file}")\n')
                    f.write(f'print("Projection data loaded, shape: ", g.shape)\n\n')
                
                # 写入标定代码
                f.write('# Initialize ball phantom calibration object\n')
                f.write(f'cal = ball_phantom_calibration(leapct, {T_z}, g, segmentation_threshold=np.max(g)/3.0)\n\n')
                
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
                f.write('cal.do_plot(res.x)\n')
            
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
