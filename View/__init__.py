"""
View 模块初始化
"""

# 导入查看器组件
from .viewers import (
    ZoomableLabelViewer,
    SimpleZoomViewer,
    SliceViewer,
    VolumeViewer
)

# 导入主窗口
from .ctviewer import CTViewer4

__all__ = [
    'ZoomableLabelViewer',
    'SimpleZoomViewer',
    'SliceViewer',
    'VolumeViewer',
    'CTViewer4'
]
