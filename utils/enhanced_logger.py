#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强日志系统 - 统一的日志记录和管理
"""

import os
import logging
import gzip
from datetime import datetime
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler


class EnhancedLogger:
    """增强的日志记录器，支持多级别和文件轮转"""
    
    def __init__(self, name: str = "QueueSystem", log_dir: Optional[str] = None):
        """
        初始化增强日志记录器
        
        Args:
            name: 日志器名称
            log_dir: 日志目录，如果为None则使用默认目录
        """
        self.name = name
        # 使用默认路径避免循环导入
        default_log_file = "次数扣除日志.txt"
        self.log_dir = log_dir or os.path.dirname(os.path.abspath(default_log_file))
        self.ensure_log_directory()
        
        # 创建主日志器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self.setup_handlers()
    
    def ensure_log_directory(self):
        """确保日志目录存在"""
        try:
            Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"创建日志目录失败 {self.log_dir}: {e}")
    
    def setup_handlers(self):
        """设置日志处理器"""
        # 文件处理器 - 详细日志（10MB轮转）
        file_handler = RotatingFileHandler(
            filename=os.path.join(self.log_dir, "system.log"),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # 控制台处理器 - 重要信息
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        # 业务日志处理器 - 用户操作记录（保持原有格式兼容）
        business_log_file = "次数扣除日志.txt"  # 使用硬编码避免循环导入
        business_handler = RotatingFileHandler(
            filename=business_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        business_handler.setLevel(logging.INFO)
        business_formatter = logging.Formatter('%(message)s')
        business_handler.setFormatter(business_formatter)
        
        # 添加处理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # 创建业务日志器
        self.business_logger = logging.getLogger(f"{self.name}.business")
        self.business_logger.setLevel(logging.INFO)
        self.business_logger.addHandler(business_handler)
        self.business_logger.propagate = False  # 不传播到父日志器
    
    def debug(self, message: str, extra_info: str = ""):
        """记录调试信息"""
        full_message = f"{message} {extra_info}".strip()
        self.logger.debug(full_message)
    
    def info(self, message: str, extra_info: str = ""):
        """记录信息"""
        full_message = f"{message} {extra_info}".strip()
        self.logger.info(full_message)
    
    def warning(self, message: str, extra_info: str = ""):
        """记录警告"""
        full_message = f"{message} {extra_info}".strip()
        self.logger.warning(full_message)
    
    def error(self, message: str, extra_info: str = "", exc_info: bool = False):
        """记录错误"""
        full_message = f"{message} {extra_info}".strip()
        self.logger.error(full_message, exc_info=exc_info)
    
    def operation_start(self, operation: str, details: str = ""):
        """记录操作开始"""
        message = f"正在进行 {operation}..."
        if details:
            message += f" ({details})"
        self.info(message)
    
    def operation_complete(self, operation: str, details: str = ""):
        """记录操作完成"""
        message = f"{operation} 完成"
        if details:
            message += f" - {details}"
        self.info(message)
    
    def operation_failed(self, operation: str, error: str, details: str = ""):
        """记录操作失败"""
        message = f"{operation} 失败: {error}"
        if details:
            message += f" ({details})"
        self.error(message)
    
    # 业务日志方法（保持原有格式）
    def log_queue_success(self, username: str, queue_type: str = "正常排队", cost: int = 1):
        """记录排队成功"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"[{timestamp}] 排队成功 - {username} - {queue_type} (消耗次数: {cost})"
        self.business_logger.info(message)
        self.debug(f"用户排队成功", f"用户={username}, 类型={queue_type}, 消耗={cost}")
    
    def log_queue_failed(self, username: str, reason: str):
        """记录排队失败"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"[{timestamp}] 排队失败 - {username} - {reason}"
        self.business_logger.info(message)
        self.debug(f"用户排队失败", f"用户={username}, 原因={reason}")
    
    def log_queue_complete(self, username: str, queue_type: str = "排队"):
        """记录完成排队"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"[{timestamp}] 完成排队 - {username} - {queue_type}"
        self.business_logger.info(message)
        self.debug(f"用户完成排队", f"用户={username}, 类型={queue_type}")
    
    def log_system_event(self, event: str):
        """记录系统事件"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"[{timestamp}] 系统事件 - {event}"
        self.business_logger.info(message)
        self.debug(f"系统事件", event)
    
    def log_guard_gift(self, username: str, guard_level: str, reward_count: int, is_new_user: bool = False):
        """记录舰长礼物"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        user_type = "新用户" if is_new_user else "现有用户"
        message = f"[{timestamp}] 舰长礼物 - {username} - {user_type}开通{guard_level}，获得{reward_count}次机会"
        self.business_logger.info(message)
        self.debug(f"舰长礼物", f"用户={username}, 等级={guard_level}, 奖励={reward_count}, 新用户={is_new_user}")
    
    def get_recent_logs(self, max_lines: int = 1000) -> list:
        """获取最近的业务日志"""
        try:
            business_log_file = "次数扣除日志.txt"  # 使用硬编码避免循环导入

            if not os.path.exists(business_log_file):
                return []
            
            with open(business_log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 过滤掉注释行
                lines = [line for line in lines if not line.startswith('#')]
                return lines[-max_lines:]
        except Exception as e:
            self.error(f"读取业务日志失败", str(e))
            return []


# 全局日志器实例
main_logger = EnhancedLogger("MainSystem")
queue_logger = EnhancedLogger("QueueManager")
gui_logger = EnhancedLogger("GUI")
bilibili_logger = EnhancedLogger("Bilibili")
