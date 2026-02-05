"""
CT重建操作功能
负责各种CT重建相关的操作
"""

from PyQt5 import QtWidgets
# NOTE: 多球标定不再需要，移除相关依赖
# from CT.ball_phantom_dialog import BallPhantomCalibrationDialog
from CT.helical_ct_dialog import HelicalCTReconstructionDialog
from CT.circle_ct_dialog import CircleCTReconstructionDialog


class CTOperations:
    """CT重建操作类，作为Mixin使用"""

    # NOTE: 多球标定不再需要，移除该功能入口
    # def run_ball_phantom_calibration(self):
    #     """运行多球标定程序"""
    #     try:
    #         dialog = BallPhantomCalibrationDialog(self)
    #         dialog.exec_()
    #     except Exception as e:
    #         QtWidgets.QMessageBox.critical(self, "错误", f"运行多球标定程序时出错：{str(e)}")

    def run_helical_ct_reconstruction(self):
        """运行螺旋CT重建程序"""
        try:
            # 创建螺旋CT重建对话框
            dialog = HelicalCTReconstructionDialog(self)
            dialog.exec_()
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"运行螺旋CT重建程序时出错：{str(e)}")
    
    def run_circle_ct_reconstruction(self):
        """运行圆轨迹CT重建程序"""
        try:
            # 创建圆轨迹CT重建对话框
            dialog = CircleCTReconstructionDialog(self)
            dialog.exec_()
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"运行圆轨迹CT重建程序时出错：{str(e)}")

