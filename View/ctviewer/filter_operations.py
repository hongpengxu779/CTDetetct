"""
滤波操作功能
负责各种图像滤波处理
"""

from PyQt5 import QtWidgets, QtCore
from Traditional.Filter.filter_op import Filter_op


class FilterOperations:
    """滤波操作类，作为Mixin使用"""
    
    def apply_anisotropic_filter(self):
        """应用各向异性平滑滤波"""
        if not hasattr(self, 'array') or self.array is None:
            QtWidgets.QMessageBox.warning(self, "警告", "请先加载数据")
            return
            
        try:
            # 创建滤波器对象
            filter_op = Filter_op()
            
            # 创建进度对话框
            progress = QtWidgets.QProgressDialog("应用各向异性平滑滤波...", "取消", 0, 0, self)
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.show()
            QtWidgets.QApplication.processEvents()
              
            # 调用滤波函数
            filtered_array = filter_op.apply_anisotropic_filter(
                self.array, 
                spacing=self.spacing
            )
            
            # 关闭进度对话框
            progress.close()
            
            if filtered_array is not None:
                # 更新当前数组
                self.array = filtered_array
                
                # 显示成功消息
                QtWidgets.QMessageBox.information(self, "成功", "滤波处理完成，正在更新视图...")
                QtWidgets.QApplication.processEvents()
                
                # 更新视图
                self.update_viewers()
                
                # 通知用户完成
                QtWidgets.QMessageBox.information(self, "成功", "视图已更新")
            else:
                QtWidgets.QMessageBox.warning(self, "警告", "滤波处理未返回结果")
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"应用滤波时出错：{str(e)}")
    
    def apply_curvature_flow_filter(self):
        """应用曲率流去噪滤波"""
        if not hasattr(self, 'array') or self.array is None:
            QtWidgets.QMessageBox.warning(self, "警告", "请先加载数据")
            return
            
        try:
            # 弹出参数设置对话框
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("曲率流去噪参数")
            
            form_layout = QtWidgets.QFormLayout(dialog)
            
            iterations_input = QtWidgets.QSpinBox()
            iterations_input.setRange(1, 100)
            iterations_input.setValue(10)
            form_layout.addRow("迭代次数:", iterations_input)
            
            time_step_input = QtWidgets.QDoubleSpinBox()
            time_step_input.setRange(0.001, 0.1)
            time_step_input.setSingleStep(0.005)
            time_step_input.setDecimals(4)
            time_step_input.setValue(0.0625)
            form_layout.addRow("时间步长:", time_step_input)
            
            button_box = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
            )
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            form_layout.addRow(button_box)
            
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                # 创建滤波器对象
                filter_op = Filter_op()
                
                # 获取参数
                num_iterations = iterations_input.value()
                time_step = time_step_input.value()
                
                # 创建进度对话框
                progress = QtWidgets.QProgressDialog(
                    f"应用曲率流去噪...\n迭代次数: {num_iterations}, 时间步长: {time_step}", 
                    "取消", 0, 0, self
                )
                progress.setWindowModality(QtCore.Qt.WindowModal)
                progress.show()
                QtWidgets.QApplication.processEvents()
                
                # 调用滤波函数
                filtered_array = filter_op.apply_curvature_flow_filter(
                    self.array, 
                    num_iterations=num_iterations,
                    time_step=time_step,
                    spacing=self.spacing
                )
                
                # 关闭进度对话框
                progress.close()
                
                if filtered_array is not None:
                    # 更新当前数组
                    self.array = filtered_array
                    
                    # 显示成功消息
                    QtWidgets.QMessageBox.information(self, "成功", "曲率流去噪完成，正在更新视图...")
                    QtWidgets.QApplication.processEvents()
                    
                    # 更新视图
                    self.update_viewers()
                    
                    # 通知用户完成
                    QtWidgets.QMessageBox.information(self, "成功", "视图已更新")
                else:
                    QtWidgets.QMessageBox.warning(self, "警告", "滤波处理未返回结果")
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"应用曲率流去噪时出错：{str(e)}")

