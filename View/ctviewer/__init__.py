"""
CTViewer4 模块化组件
将主要的CT查看器功能按模块拆分

模块结构：
- main.py - CTViewer4主类
- ui_components.py - UI组件（样式、菜单等）
- window_level.py - 窗宽窗位控制
- data_loader.py - 数据加载
- filter_operations.py - 滤波操作
- ct_operations.py - CT重建操作
- ai_operations.py - AI分割操作
"""

from .main import CTViewer4

__all__ = ['CTViewer4']

