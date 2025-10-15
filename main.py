import os
# Fix for OpenMP library conflict
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import sys
from PyQt5 import QtWidgets
import numpy as np
from View.View import *



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # 启动时不自动加载任何文件，让用户通过界面选择
    viewer = CTViewer4()  # 不传递参数，使用菜单导入文件

    # 如果需要测试，可以取消下方注释并指定文件路径
    # raw 示例
    # viewer = CTViewer4("E:/xu/CT/468_384_1355_0.124558.raw",
    #                   shape=(1355, 384, 468),
    #                   spacing=(0.124558, 0.124558, 0.124558),
    #                   dtype=np.uint16)

    # nii/mhd 示例
    # viewer = CTViewer4("example_ct.nii.gz")

    viewer.resize(1200, 900)
    viewer.show()
    sys.exit(app.exec_())
