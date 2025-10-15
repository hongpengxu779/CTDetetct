"""
View.py - 兼容性导出文件
为了保持向后兼容，从新的模块化结构中重新导出所有类

新的模块结构：
- View/viewers/ - 各种查看器组件
  - zoomable_viewer.py - ZoomableLabelViewer, SimpleZoomViewer
  - slice_viewer.py - SliceViewer
  - volume_viewer.py - VolumeViewer
  
- View/ctviewer/ - CTViewer4主窗口及其功能模块
  - main.py - CTViewer4主类
  - ui_components.py - UI组件（样式、菜单等）
  - window_level.py - 窗宽窗位控制
  - data_loader.py - 数据加载
  - filter_operations.py - 滤波操作
  - ct_operations.py - CT重建操作
  - ai_operations.py - AI分割操作
"""

# 从新的模块结构中导入所有类
from .viewers import (
    ZoomableLabelViewer,
    SimpleZoomViewer,
    SliceViewer,
    VolumeViewer
)

from .ctviewer import CTViewer4

# 导出所有类，保持向后兼容
__all__ = [
    'ZoomableLabelViewer',
    'SimpleZoomViewer',
    'SliceViewer',
    'VolumeViewer',
    'CTViewer4'
]
