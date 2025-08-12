#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单人抽奖动画模块 - 处理单人随机选择动画逻辑
"""

import random
import time
from typing import List, Deque
from PyQt6.QtCore import QThread, pyqtSignal
from collections import deque

from models import QueueItem

class SingleRandomSelectionAnimationThread(QThread):
    """单人随机选择动画线程"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 延迟导入以避免循环导入
        from utils import get_queue_logger
        self.queue_logger = get_queue_logger()
    
    # 信号定义
    update_display = pyqtSignal(str, str, str)  # 用户1名字, 用户2名字, 滚动字符
    animation_finished = pyqtSignal(list, list)  # 最终选中的索引列表, 最终选中的名字列表
    
    def __init__(self, queue_list: List[QueueItem], recent_winners=None):
        """
        初始化单人抽奖动画线程
        
        Args:
            queue_list: 排队列表
            recent_winners: 最近中奖用户名队列
        """
        super().__init__()
        self.queue_list = queue_list
        self.running = True
        
        # 动画参数
        self.animation_duration = 3.0  # 动画持续时间（秒）
        self.initial_delay = 0.1  # 初始延迟（秒）
        self.final_delay = 0.3  # 最终延迟（秒）
        
        # 滚动字符
        self.scroll_chars = ["🎲", "🎯", "🎪", "🎨", "🎭", "🎳", "🎮", "🎸"]
        
        # 传入主逻辑的 recent_winners（用户名队列）
        self.recent_winners = recent_winners if recent_winners is not None else []
    
    def run(self):
        """执行单人抽奖动画"""
        try:
            start_time = time.time()
            
            while self.running and (time.time() - start_time) < self.animation_duration:
                # 计算当前进度
                progress = (time.time() - start_time) / self.animation_duration
                
                # 过滤掉最近中奖的用户（使用用户名）
                available_indices = [i for i, item in enumerate(self.queue_list) if item.name not in self.recent_winners]
                
                # 如果可用用户不足1个，使用所有用户
                if len(available_indices) < 1:
                    available_indices = list(range(len(self.queue_list)))
                
                # 随机选择一个用户
                if available_indices:
                    selected_index = random.choice(available_indices)
                    selected_name = self.queue_list[selected_index].name
                else:
                    selected_name = ""

                # 随机选择滚动字符
                scroll_char = random.choice(self.scroll_chars)

                # 发送更新信号（只发送一个用户，第二个用户为空）
                self.update_display.emit(selected_name, "", scroll_char)

                # 计算延迟时间（随着时间增长，速度减慢）
                delay = self.initial_delay + (self.final_delay - self.initial_delay) * progress
                self.msleep(int(delay * 1000))
            
            # 动画结束，选择最终结果
            if self.running:
                # 过滤掉最近中奖的用户
                available_indices = [i for i in range(len(self.queue_list)) if i not in self.recent_winners]

                # 如果可用用户不足1个，直接使用所有用户
                if len(available_indices) < 1:
                    available_indices = [i for i in range(len(self.queue_list)) if i not in self.recent_winners]
                    if len(available_indices) < 1:
                        available_indices = list(range(len(self.queue_list)))

                # 选择最终中奖者（只选择1个）
                if available_indices:
                    final_index = random.choice(available_indices)
                    final_indices = [final_index]
                    final_names = [self.queue_list[final_index].name]
                else:
                    final_indices = []
                    final_names = []

                # 动画线程不再维护中奖队列，由主逻辑统一管理

                # 发送完成信号
                self.animation_finished.emit(final_indices, final_names)

        except Exception as e:
            self.queue_logger.error("单人抽奖动画线程错误", str(e), exc_info=True)

    def stop(self):
        """停止动画"""
        self.running = False
