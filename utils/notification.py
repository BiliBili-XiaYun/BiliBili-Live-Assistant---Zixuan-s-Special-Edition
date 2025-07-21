#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知工具模块 - 处理系统通知
"""

import ctypes
import platform
import threading
from ctypes import wintypes
from PyQt6.QtCore import QTimer

try:
    from plyer import notification
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False
    notification = None


class NotificationManager:
    """系统通知管理器"""
    
    def __init__(self):
        """初始化通知管理器"""
        self.is_windows = platform.system() == "Windows"
    
    def show_notification(self, message: str, title: str = "子轩专属排队工具", timeout: int = 2):
        """
        显示系统通知
        
        Args:
            message: 通知消息
            title: 通知标题
            timeout: 超时时间（秒）
        """
        try:
            if HAS_PLYER:
                self._show_plyer_notification(message, title, timeout)
            elif self.is_windows:
                self._show_balloon_notification(message, title, timeout)
            else:
                self._show_console_notification(message, title)
        except Exception as e:
            try:
                from utils import gui_logger
                gui_logger.error("显示通知失败", str(e))
            except ImportError:
                print(f"显示通知失败: {str(e)}")
            self._show_console_notification(message, title)
    
    def _show_plyer_notification(self, message: str, title: str, timeout: int):
        """使用plyer库显示系统通知"""
        try:
            def show_notification():
                # 获取ICO格式图标路径（用于通知）
                from config import Constants
                from utils import gui_logger
                icon_path = Constants.get_icon_path(256)  # 使用256px ICO图标
                
                notification.notify(
                    title=title,
                    message=message,
                    app_name=title,
                    app_icon=icon_path if icon_path else "",  # 如果图标不存在则不设置
                    timeout=timeout,
                    ticker="复制通知",
                    toast=True  # 在Windows上使用Toast通知
                )
            
            # 在后台线程中显示通知，避免阻塞UI
            thread = threading.Thread(target=show_notification, daemon=True)
            thread.start()
            
        except Exception as e:
            raise Exception(f"plyer通知失败: {e}")
    
    def _show_balloon_notification(self, message: str, title: str, timeout: int):
        """使用Windows Shell API显示气球提示"""
        try:
            # 定义Windows API结构和常量
            class NOTIFYICONDATA(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("hWnd", wintypes.HWND),
                    ("uID", wintypes.UINT),
                    ("uFlags", wintypes.UINT),
                    ("uCallbackMessage", wintypes.UINT),
                    ("hIcon", wintypes.HICON),
                    ("szTip", wintypes.WCHAR * 128),
                    ("dwState", wintypes.DWORD),
                    ("dwStateMask", wintypes.DWORD),
                    ("szInfo", wintypes.WCHAR * 256),
                    ("uTimeout", wintypes.UINT),
                    ("szInfoTitle", wintypes.WCHAR * 64),
                    ("dwInfoFlags", wintypes.DWORD),
                    ("guidItem", ctypes.c_char * 16),
                    ("hBalloonIcon", wintypes.HICON)
                ]
            
            # Windows API常量
            NIM_ADD = 0x00000000
            NIM_DELETE = 0x00000002
            NIF_MESSAGE = 0x00000001
            NIF_ICON = 0x00000002
            NIF_TIP = 0x00000004
            NIF_INFO = 0x00000010
            NIIF_INFO = 0x00000001
            
            # 这个方法需要窗口句柄，暂时使用控制台输出
            self._show_console_notification(message, title)
            
        except Exception as e:
            raise Exception(f"Windows API气球提示失败: {e}")
    
    def _show_console_notification(self, message: str, title: str):
        """在控制台输出通知"""
        try:
            from utils import gui_logger
            gui_logger.info("通知", f"{title}: {message}")
        except ImportError:
            print(f"通知: {title}: {message}")


# 全局通知管理器实例
notification_manager = NotificationManager()


def show_notification(message: str, title: str = "子轩专属排队工具", timeout: int = 2):
    """
    显示系统通知的便捷函数
    
    Args:
        message: 通知消息
        title: 通知标题
        timeout: 超时时间（秒）
    """
    notification_manager.show_notification(message, title, timeout)


def show_copy_notification(message: str):
    """
    显示复制通知的便捷函数
    
    Args:
        message: 通知消息
    """
    show_notification(message, "复制通知", 2)
