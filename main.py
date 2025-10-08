#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站直播弹幕监控程序 - 主入口文件
使用 bilibili-api 库实现
优化版本 - 提升启动速度和稳定性
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
    
    # 跳过DPI设置以避免权限问题
    # Qt6会自动处理DPI缩放


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
    """主函数 - 优化启动速度"""
    splash = None
    tts_manager = None
    try:
        # 设置环境
        setup_environment()
        
        # 配置第三方库日志格式
        configure_third_party_logging()
        
        # 初始化日志系统
        from utils import get_main_logger
        from version_info import get_version_string
        main_logger = get_main_logger()
        main_logger.operation_start("应用程序启动", get_version_string())
        
        # 延迟导入PyQt6以提升启动速度
        from PyQt6.QtWidgets import QApplication
        
        # 创建QApplication实例
        app = QApplication(sys.argv)
        
        # 设置应用程序信息
        from version_info import APP_NAME, APP_VERSION, ORGANIZATION_NAME
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)
        app.setOrganizationName(ORGANIZATION_NAME)
        
        # 设置应用程序图标
        from config import Constants, app_config
        from PyQt6.QtGui import QIcon
        icon_path = Constants.get_icon_path(128)
        if icon_path:
            app.setWindowIcon(QIcon(icon_path))
            main_logger.debug("应用程序图标设置成功", f"路径: {icon_path}")

        # 创建加载界面
        try:
            from gui.loading_splash import LoadingSplashScreen

            splash = LoadingSplashScreen()
            splash.set_title("正在启动排队工具…")
            splash.append_message("初始化应用所需组件…")
            splash.show()
            app.processEvents()
        except Exception as splash_exc:  # pragma: no cover - GUI 初始化失败时
            splash = None
            main_logger.warning("加载界面初始化失败", repr(splash_exc))

        def splash_log(message: str) -> None:
            if message:
                main_logger.debug("启动进度", message)
            if splash is not None and message:
                splash.append_message(message)
                app.processEvents()

        # 初始化并预加载 TTS
        try:
            main_logger.operation_start("初始化语音引擎")
            from utils.tts import TTSManager

            tts_manager = TTSManager(settings={"tts": app_config.get("tts", {})})
            splash_log("准备 Kokoro 语音模型…")
            preload_ok = tts_manager.preload_kokoro(status_callback=splash_log)
            if preload_ok:
                splash_log("Kokoro 语音模型预加载完成")
                main_logger.operation_complete("初始化语音引擎", "Kokoro 预加载成功")
            else:
                splash_log("Kokoro 预加载未完成，将在首次使用时加载")
                main_logger.warning("Kokoro 预加载未完成", "将按需延迟加载")
        except Exception as tts_exc:
            main_logger.warning("语音引擎初始化失败", repr(tts_exc))
            splash_log(f"语音引擎初始化失败：{tts_exc}")
            tts_manager = None
        
        # 延迟导入主窗口模块
        main_logger.operation_start("加载主窗口模块")
        splash_log("加载主窗口模块…")
        from gui.main_window import BilibiliDanmakuMonitor
        
        # 创建主窗口
        main_logger.operation_start("创建主窗口")
        splash_log("创建主窗口界面…")
        window = BilibiliDanmakuMonitor(tts_manager=tts_manager)
        window.show()
        main_logger.operation_complete("主窗口创建", "窗口已显示")
        if splash is not None:
            splash.append_message("启动完成，正在进入主界面…")
            splash.finish(window)
        
        # 运行应用程序
        main_logger.info("应用程序启动成功，进入主循环")
        sys.exit(app.exec())
        
    except ImportError as e:
        error_msg = f"导入模块失败: {str(e)}\n请确保已安装所有依赖包！"
        try:
            from utils import get_main_logger
            main_logger = get_main_logger()
            main_logger.error("导入模块失败", str(e))
        except:
            print(error_msg)  # 日志系统不可用时的后备方案
        try:
            if splash is not None:
                splash.close()
        except Exception:
            pass
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
            QMessageBox.critical(None, "启动错误", error_msg)
        except Exception:
            pass
        sys.exit(1)
        
    except Exception as e:
        error_msg = f"程序启动失败: {str(e)}"
        try:
            from utils import get_main_logger
            main_logger = get_main_logger()
            main_logger.error("程序启动失败", str(e), exc_info=True)
        except:
            print(error_msg)  # 日志系统不可用时的后备方案
        try:
            if splash is not None:
                splash.close()
        except Exception:
            pass
        try:
            import traceback
            traceback.print_exc()
            
            from PyQt6.QtWidgets import QApplication, QMessageBox
            app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
            QMessageBox.critical(None, "启动错误", error_msg + "\n\n详细信息请查看控制台输出。")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
