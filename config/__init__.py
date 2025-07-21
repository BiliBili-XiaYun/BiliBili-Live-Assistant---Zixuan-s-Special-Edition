#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块 - 管理程序配置和常量
"""

import os
import json
from typing import Dict, Any, Optional

def get_name_list_file() -> str:
    """
    获取名单文件路径
    从配置文件中读取name_list_file字段
    如果未设置，则返回默认路径
    """
    config_file = "config.json"
    if not os.path.exists(config_file):
        # 如果配置文件不存在，返回默认路径
        return os.path.join(os.getcwd(), "name_list.json")
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    name_list_file = config.get("queue.name_list_file", "")
    if not name_list_file:
        # 如果未设置，使用默认路径
        return os.path.join(os.getcwd(), "name_list.json")
    return name_list_file

class Config:
    """配置管理类"""
    
    # 静态文件路径常量（不会变化的）
    COOKIES_FILE = "bilibili_cookies.json"
    QUEUE_STATE_FILE = "queue_state.json"
    DEDUCTION_LOG_FILE = "次数扣除日志.txt"
    
    @property
    def NAME_LIST_FILE(self) -> str:
        """
        动态获取名单文件路径
        每次访问都从当前配置中读取最新路径
        """
        config_path = self.get("queue.name_list_file", "")
        if config_path and config_path.strip():
            return os.path.abspath(config_path.strip())
        else:
            # 如果配置中没有路径，返回默认路径
            return os.path.join(os.getcwd(), "名单.csv")
    
    # 默认配置
    DEFAULT_CONFIG = {
        "window": {
            "main_window_size": [800, 600],
            "main_window_position": [100, 100],
            "queue_window_size": [1000, 700],
            "queue_window_position": [200, 200],
            "login_dialog_size": [350, 500]
        },
        "danmaku": {
            "reconnect_interval": 5,  # 重连间隔（秒）
            "max_reconnect_attempts": 10,  # 最大重连次数
            "message_buffer_size": 1000,  # 消息缓冲区大小
            "debug_mode": False  # 调试模式
        },        
        "queue": {
            "auto_save_interval": 30,  # 自动保存间隔（秒）
            "cutline_cost": 2,  # 插队消耗次数
            "normal_cost": 1,  # 正常排队消耗次数
            "enable_auto_backup": True,  # 启用自动备份
            "name_list_file": ""  # 名单文件路径（绝对路径，为空则跳过加载）
        },
        "ui": {
            "theme": "default",  # 主题
            "language": "zh_CN",  # 语言
            "auto_scroll": True,  # 自动滚动
            "show_timestamps": True,  # 显示时间戳
            "font_size": 9  # 字体大小
        }
    }
    
    def __init__(self, config_file: str = "config.json"):
        """
        初始化配置管理器
        
        Args:
            config_file (str): 配置文件路径
        """
        self.config_file = config_file
        self._config = self.DEFAULT_CONFIG.copy()
        self.load_config()
    
    def load_config(self) -> None:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self._merge_config(self._config, saved_config)
                from utils import get_main_logger

                logger = get_main_logger()
                logger.operation_complete("配置加载", f"从 {self.config_file} 加载")
            else:
                print("配置文件不存在，使用默认配置")
                self.save_config()  # 创建默认配置文件
        except Exception as e:
            print(f"加载配置文件失败: {str(e)}，使用默认配置")
    
    def get_file_modification_time(self) -> float:
        """获取配置文件修改时间"""
        try:
            if os.path.exists(self.config_file):
                return os.path.getmtime(self.config_file)
        except:
            pass
        return 0.0
    
    def is_config_file_modified(self, last_mtime: float) -> bool:
        """检查配置文件是否被修改"""
        current_mtime = self.get_file_modification_time()
        return current_mtime > last_mtime
    
    def reload_if_modified(self, last_mtime: float) -> float:
        """如果配置文件被修改则重新加载，返回新的修改时间"""
        if self.is_config_file_modified(last_mtime):
            from utils import get_main_logger

            logger = get_main_logger()
            logger.info("检测到配置文件被修改，重新加载配置")
            self.reload_config_from_file()
            return self.get_file_modification_time()
        return last_mtime
    
    def save_config(self) -> None:
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
            print(f"配置已保存到 {self.config_file}")
        except Exception as e:
            print(f"保存配置文件失败: {str(e)}")
    
    def reload_config_from_file(self) -> None:
        """重新从文件加载配置，用于同步外部配置变更"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    # 重置为默认配置后再合并
                    self._config = self.DEFAULT_CONFIG.copy()
                    self._merge_config(self._config, saved_config)
                from utils import get_main_logger

                logger = get_main_logger()
                logger.operation_complete("配置重新加载", f"从 {self.config_file} 重新加载")
            else:
                print("配置文件不存在，保持当前配置")
        except Exception as e:
            print(f"重新加载配置文件失败: {str(e)}，保持当前配置")
    
    def _merge_config(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """
        递归合并配置字典
        
        Args:
            base (dict): 基础配置
            update (dict): 更新配置
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key_path (str): 配置键路径，用点分隔，如 "window.main_window_size"
            default (Any): 默认值
            
        Returns:
            Any: 配置值
        """
        keys = key_path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key_path (str): 配置键路径
            value (Any): 配置值
        """
        keys = key_path.split('.')
        config = self._config
        
        # 创建嵌套字典路径
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # 设置最终值
        config[keys[-1]] = value
    
    def get_window_config(self, window_name: str) -> Dict[str, Any]:
        """
        获取窗口配置
        
        Args:
            window_name (str): 窗口名称
            
        Returns:
            dict: 窗口配置
        """
        return self.get(f"window.{window_name}", {})
    
    def set_window_config(self, window_name: str, config: Dict[str, Any]) -> None:
        """
        设置窗口配置
        
        Args:
            window_name (str): 窗口名称
            config (dict): 窗口配置
        """
        for key, value in config.items():
            self.set(f"window.{window_name}.{key}", value)


# 全局配置实例
app_config = Config()


# 常量定义
class Constants:
    """程序常量"""
    
    # 应用程序信息 - 现在从 version_info.py 获取
    # 保留这些常量是为了向后兼容，但推荐使用 version_info 模块
    @property
    def APP_NAME(self):
        from version_info import APP_NAME
        return APP_NAME
    
    @property 
    def APP_VERSION(self):
        from version_info import APP_VERSION
        return APP_VERSION
    
    @property
    def APP_ORGANIZATION(self):
        from version_info import ORGANIZATION_NAME
        return ORGANIZATION_NAME
    
    # 静态文件路径常量（不会变化的）
    COOKIES_FILE = "bilibili_cookies.json"
    QUEUE_STATE_FILE = "queue_state.json"
    DEDUCTION_LOG_FILE = "次数扣除日志.txt"    # 图标文件路径（ICO格式，兼容性更好）
    ICON_64 = "resource/icon/app_icon_64.ico"
    ICON_128 = "resource/icon/app_icon_128.ico"
    ICON_256 = "resource/icon/app_icon_256.ico"
    ICON_512 = "resource/icon/app_icon_512.ico"
    ICON_ICO = "resource/icon/app_icon.ico"  # 通用ICO格式图标
    
    # 网络相关
    BILIBILI_LOGIN_QR_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
    BILIBILI_LOGIN_POLL_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
    BILIBILI_NAV_URL = "https://api.bilibili.com/x/web-interface/nav"
    
    # HTTP头信息
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Referer': 'https://www.bilibili.com/',
        'Origin': 'https://www.bilibili.com',
        'Accept': 'application/json, text/plain, */*',
    }
    
    # 消息类型
    MESSAGE_TYPE_DANMAKU = 'danmaku'
    MESSAGE_TYPE_GIFT = 'gift'
    MESSAGE_TYPE_GUARD = 'guard'
    MESSAGE_TYPE_SUPER_CHAT = 'super_chat'
      # 队列相关
    QUEUE_KEYWORD = '排队'
    BOARDING_KEYWORD = '上车'  # 上车关键词
    CUTLINE_KEYWORD = '插队'  # 插队关键词
    CUTLINE_COST = 2  # 插队消耗次数
    NORMAL_COST = 1   # 正常排队消耗次数
    
    # 舰长等级映射
    GUARD_LEVEL_NAMES = {
        1: '总督',
        2: '提督', 
        3: '舰长'
    }
    
    # 消息颜色
    COLOR_DANMAKU = '#000000'
    COLOR_GIFT = '#ff6600'
    COLOR_GUARD = '#9900ff'
    COLOR_SUPER_CHAT = '#ff0000'
    
    # 二维码状态码
    QR_CODE_SUCCESS = 0        # 扫码成功
    QR_CODE_EXPIRED = 86038    # 二维码过期
    QR_CODE_SCANNED = 86090    # 已扫码待确认
    QR_CODE_NOT_SCANNED = 86101  # 未扫码
    
    # 测试模式关键词
    TEST_MODE_KEYWORDS = ['test', 'testing', '测试', '本地测试']
    
    # 支持的括号字符
    SUPPORTED_BRACKETS = ['(', '（']
    
    # 文件编码
    FILE_ENCODING = 'utf-8'
    
    # 超时设置（秒）
    HTTP_TIMEOUT = 10
    LOGIN_POLL_INTERVAL = 2
    MONITOR_STOP_TIMEOUT = 5
      # UI相关
    QR_CODE_SIZE = (280, 280)
    LOGIN_DIALOG_SIZE = (350, 500)
    INSERT_QUEUE_DIALOG_SIZE = (300, 400)
    MAIN_WINDOW_SIZE = (800, 600)
    QUEUE_WINDOW_SIZE = (1000, 700)
    
    @staticmethod
    def get_name_list_file() -> str:
        """
        动态获取名单文件路径
        每次调用都从当前配置中读取最新路径
        """
        config_path = app_config.get("queue.name_list_file", "")
        if config_path and config_path.strip():
            return os.path.abspath(config_path.strip())
        else:            # 如果配置中没有路径，返回默认路径
            return os.path.join(os.getcwd(), "名单.csv")
    
    @staticmethod
    def get_icon_path(size=128):
        """
        获取程序图标路径（所有图标均为ICO格式）
        
        Args:
            size: 图标尺寸，支持64, 128, 256, 512，或'default'使用通用图标
            
        Returns:
            str: 图标文件的绝对路径，如果文件不存在则返回None
        """
        # 如果请求默认图标或者没有指定尺寸
        if size == 'default' or size not in [64, 128, 256, 512]:
            icon_path = os.path.join(os.getcwd(), Constants.ICON_ICO)
            if os.path.exists(icon_path):
                return icon_path
                
        # 根据尺寸选择对应的ICO文件
        icon_mapping = {
            64: Constants.ICON_64,
            128: Constants.ICON_128,
            256: Constants.ICON_256,
            512: Constants.ICON_512
        }
        
        if size in icon_mapping:
            icon_path = os.path.join(os.getcwd(), icon_mapping[size])
            if os.path.exists(icon_path):
                return icon_path
        
        # 如果指定尺寸的图标不存在，回退到通用图标
        fallback_path = os.path.join(os.getcwd(), Constants.ICON_ICO)
        if os.path.exists(fallback_path):
            return fallback_path
            
        return None


# 创建动态名单文件路径的便捷函数
def get_current_name_list_file() -> str:
    """
    获取当前名单文件路径的便捷函数
    可以替代 Constants.NAME_LIST_FILE 的使用
    """
    return Constants.get_name_list_file()


