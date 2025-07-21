#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志记录工具模块 - 处理排队日志记录
"""

import os
from datetime import datetime
from typing import List


def get_constants():
    """获取常量"""
    from config import Constants
    return Constants


class QueueLogger:
    """排队日志记录器"""
    
    def __init__(self, log_file: str = None):
        """
        初始化日志记录器
        
        Args:
            log_file: 日志文件路径
        """
        if log_file is None:
            Constants = get_constants()
            log_file = Constants.DEDUCTION_LOG_FILE
        self.log_file = log_file
        self.ensure_log_file()
    
    def ensure_log_file(self):
        """确保日志文件存在"""
        try:
            if not os.path.exists(self.log_file):
                # 创建日志文件
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    f.write(f"# B站弹幕排队系统日志 - 创建于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("# 格式: [时间] 操作类型 - 用户名 - 详细信息\n\n")
        except Exception as e:
            print(f"创建日志文件失败: {e}")
    
    def log_queue_success(self, username: str, queue_type: str = "正常排队", cost: int = 1):
        """
        记录排队成功日志
        
        Args:
            username: 用户名
            queue_type: 排队类型
            cost: 消耗次数
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] 排队成功 - {username} - {queue_type} (消耗次数: {cost})\n"
        self._write_log(log_entry)
    
    def log_queue_failed(self, username: str, reason: str):
        """
        记录排队失败日志
        
        Args:
            username: 用户名
            reason: 失败原因
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] 排队失败 - {username} - {reason}\n"
        self._write_log(log_entry)
    
    def log_queue_complete(self, username: str, queue_type: str = "排队"):
        """
        记录完成排队日志
        
        Args:
            username: 用户名
            queue_type: 队列类型
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] 完成排队 - {username} - {queue_type}\n"
        self._write_log(log_entry)
    
    def log_system_event(self, event: str):
        """
        记录系统事件日志
        
        Args:
            event: 事件描述
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] 系统事件 - {event}\n"
        self._write_log(log_entry)
    
    def log_guard_gift(self, username: str, guard_level: str, reward_count: int, is_new_user: bool = False):
        """
        记录舰长礼物日志
        
        Args:
            username: 用户名
            guard_level: 舰长等级
            reward_count: 奖励次数
            is_new_user: 是否为新用户
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        user_type = "新用户" if is_new_user else "现有用户"
        log_entry = f"[{timestamp}] 舰长礼物 - {username} - {user_type}开通{guard_level}，获得{reward_count}次机会\n"
        self._write_log(log_entry)
    
    def _write_log(self, log_entry: str):
        """
        写入日志到文件
        
        Args:
            log_entry: 日志条目
        """
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"写入日志失败: {e}")
    
    def get_recent_logs(self, max_lines: int = 1000) -> List[str]:
        """
        获取最近的日志
        
        Args:
            max_lines: 最大行数
            
        Returns:
            List[str]: 日志行列表
        """
        try:
            if not os.path.exists(self.log_file):
                return []
            
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 过滤掉注释行
                lines = [line for line in lines if not line.startswith('#')]
                return lines[-max_lines:]
        except Exception as e:
            print(f"读取日志失败: {e}")
            return []
