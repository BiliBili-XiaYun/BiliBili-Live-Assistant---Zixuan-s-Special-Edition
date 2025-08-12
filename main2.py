#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站直播弹幕监控程序 - 排队工具2专用入口文件
简化版本，专注于排队和插队功能
"""

import sys
import os

# 设置环境变量以优化启动速度
os.environ['PYTHONOPTIMIZE'] = '2'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

# 添加当前目录到Python路径，确保模块导入正常
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


def setup_environment():
    """设置运行环境"""
    # 设置工作目录
    os.chdir(current_dir)


def configure_third_party_logging():
    """配置第三方库的日志格式"""
    import logging
    
    # 配置bilibili-api库的日志格式
    bilibili_loggers = [
        'bilibili_api',
        'bilibili_api.live',
        'bilibili_api.danmaku'
    ]
    
    for logger_name in bilibili_loggers:
        logger = logging.getLogger(logger_name)
        # 清除现有处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 创建新的格式化处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # 只显示警告和错误
        formatter = logging.Formatter(
            '[%(asctime)s][%(levelname)s] Bilibili-API: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.setLevel(logging.WARNING)
        logger.propagate = False  # 阻止传播到根日志器


def main():
    """主函数 - 排队工具2专用"""
    try:
        # 设置环境
        setup_environment()
        
        # 配置第三方库日志格式
        configure_third_party_logging()
        
        # 初始化日志系统
        from utils import get_main_logger
        from version_info import get_version_string
        main_logger = get_main_logger()
        main_logger.operation_start("排队工具2启动", get_version_string())
        
        # 延迟导入PyQt6以提升启动速度
        from PyQt6.QtWidgets import QApplication
        
        # 创建QApplication实例
        app = QApplication(sys.argv)
        
        # 设置应用程序信息
        from version_info import APP_NAME, APP_VERSION, ORGANIZATION_NAME
        app.setApplicationName(f"{APP_NAME} - 排队工具2")
        app.setApplicationVersion(APP_VERSION)
        app.setOrganizationName(ORGANIZATION_NAME)
        
        # 设置应用程序图标
        from config import Constants
        icon_path = Constants.get_icon_path(128)
        if icon_path:
            from PyQt6.QtGui import QIcon
            app.setWindowIcon(QIcon(icon_path))
        
        # 创建并显示主窗口 - 使用简化的主窗口
        from gui.main_window_queue2 import MainWindowQueue2
        main_window = MainWindowQueue2()
        main_window.show()
        
        main_logger.operation_complete("排队工具2启动完成")
        
        # 运行应用程序主循环
        return app.exec()
        
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        return 0
    except Exception as e:
        print(f"程序启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
