#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志模块 - 处理排队日志记录和显示 (简洁版)
"""

import os
import time
from datetime import datetime
from typing import List, Optional
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QLabel, QComboBox, QFrame)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor

from config import Constants
from utils import QueueLogger, gui_logger, gui_logger


class LogDisplayWidget(QWidget):
    """日志显示组件 - 简洁版"""
    
    # 信号定义
    log_updated = pyqtSignal(str)
    
    def __init__(self, parent=None):
        """
        初始化日志显示组件
        
        Args:
            parent: 父组件
        """
        super().__init__(parent)
        
        # 日志记录器
        self.logger = QueueLogger()
        
        # 日志缓存
        self.log_cache: List[str] = []
        self.max_cache_size = 100000  # 设置10万条弹幕缓存上限
        
        # 自动滚动相关
        self.auto_scroll_enabled = True  # 自动滚动状态
        self.user_scrolled = False  # 用户是否手动滚动过
        
        # 统计数据
        self.stats = {
            'total_success': 0,
            'total_failed': 0,
            'total_complete': 0,
            'session_start': datetime.now()
        }
        
        # 初始化UI
        self.init_ui()
        
        # 定时更新
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_stats_display)
        self.update_timer.start(5000)  # 每5秒更新一次
        
        # 连接信号
        self.log_updated.connect(self.append_log_text)
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout()
        
        # 控制面板
        control_panel = QFrame()
        control_layout = QHBoxLayout()
        
        # 日志级别过滤
        self.level_filter = QComboBox()
        self.level_filter.addItems(["全部", "成功", "失败", "完成", "系统"])
        self.level_filter.currentTextChanged.connect(self.filter_logs)
        control_layout.addWidget(QLabel("筛选:"))
        control_layout.addWidget(self.level_filter)
        
        # 清空按钮
        self.clear_btn = QPushButton("清空日志")
        self.clear_btn.clicked.connect(self.clear_logs)
        control_layout.addWidget(self.clear_btn)
        
        # 保存按钮
        self.save_btn = QPushButton("保存日志")
        self.save_btn.clicked.connect(self.save_logs)
        control_layout.addWidget(self.save_btn)
        
        # 自动滚动开关
        self.auto_scroll_btn = QPushButton("自动滚动: 开")
        self.auto_scroll_btn.setCheckable(True)
        self.auto_scroll_btn.setChecked(True)
        self.auto_scroll_btn.clicked.connect(self.toggle_auto_scroll)
        control_layout.addWidget(self.auto_scroll_btn)
        
        control_layout.addStretch()
        control_panel.setLayout(control_layout)
        layout.addWidget(control_panel)
        
        # 日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        # 设置等宽字体
        font = QFont("Consolas", 9)
        if not font.exactMatch():
            font = QFont("Courier New", 9)
        self.log_text.setFont(font)
        
        # 安装事件过滤器来监听滚轮事件
        self.log_text.installEventFilter(self)
        
        # 连接滚动条信号
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.valueChanged.connect(self.on_scroll_value_changed)
        
        layout.addWidget(self.log_text)
        
        # 统计信息面板
        stats_panel = QFrame()
        stats_layout = QHBoxLayout()
        
        self.stats_label = QLabel("统计: 成功: 0 | 失败: 0 | 完成: 0")
        stats_layout.addWidget(self.stats_label)
        
        stats_layout.addStretch()
        
        self.session_label = QLabel("会话开始时间: --")
        stats_layout.addWidget(self.session_label)
        
        stats_panel.setLayout(stats_layout)
        layout.addWidget(stats_panel)
        
        self.setLayout(layout)
        
        # 更新会话时间显示
        self.update_session_display()
    
    def toggle_auto_scroll(self):
        """切换自动滚动状态"""
        self.auto_scroll_enabled = self.auto_scroll_btn.isChecked()
        if self.auto_scroll_enabled:
            self.auto_scroll_btn.setText("自动滚动: 开")
            # 立即滚动到底部
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.log_text.setTextCursor(cursor)
            gui_logger.debug("用户手动开启自动滚动")
        else:
            self.auto_scroll_btn.setText("自动滚动: 关")
            gui_logger.debug("用户手动关闭自动滚动")
    
    def filter_logs(self, filter_type: str):
        """
        过滤日志显示
        
        Args:
            filter_type: 过滤类型
        """
        # 简单实现：重新加载所有日志并过滤
        self.refresh_logs()
    
    def clear_logs(self):
        """清空日志显示"""
        self.log_text.clear()
        self.log_cache.clear()
        
        # 重置统计
        self.stats['total_success'] = 0
        self.stats['total_failed'] = 0
        self.stats['total_complete'] = 0
        self.update_stats_display()
    
    def save_logs(self):
        """保存当前显示的日志"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"排队日志_导出_{timestamp}.txt"
            filepath = os.path.join(os.path.dirname(Constants.DEDUCTION_LOG_FILE), filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.log_text.toPlainText())
            
            self.log_system_event(f"日志已导出到: {filepath}")
        except Exception as e:
            self.log_system_event(f"导出日志失败: {e}")
    
    def refresh_logs(self):
        """刷新日志显示"""
        try:
            # 获取最近的日志
            recent_logs = self.logger.get_recent_logs(self.max_cache_size)
            
            # 应用过滤
            filter_type = self.level_filter.currentText()
            if filter_type != "全部":
                filter_mapping = {
                    "成功": "排队成功",
                    "失败": "排队失败", 
                    "完成": "完成排队",
                    "系统": "系统事件"
                }
                filter_keyword = filter_mapping.get(filter_type)
                if filter_keyword:
                    recent_logs = [log for log in recent_logs if filter_keyword in log]
            
            # 更新显示
            self.log_text.clear()
            for log in recent_logs:
                self.log_text.append(log.strip())
            
            # 自动滚动到底部（仅当用户启用时）
            if self.auto_scroll_enabled:
                cursor = self.log_text.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.log_text.setTextCursor(cursor)
                
        except Exception as e:
            gui_logger.error("刷新日志失败", str(e))
    
    def append_log_text(self, text: str):
        """添加日志文本到显示区域"""
        # 添加到缓存
        self.log_cache.append(text)
        
        # 管理缓存大小
        self.manage_cache_size()
        
        # 添加到显示区域
        self.log_text.append(text)
        
        # 自动滚动（仅当用户启用时）
        if self.auto_scroll_enabled:
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.log_text.setTextCursor(cursor)
    
    def update_stats_display(self):
        """更新统计显示"""
        stats_text = f"统计: 成功: {self.stats['total_success']} | 失败: {self.stats['total_failed']} | 完成: {self.stats['total_complete']}"
        self.stats_label.setText(stats_text)
    
    def update_session_display(self):
        """更新会话时间显示"""
        session_time = self.stats['session_start'].strftime('%Y-%m-%d %H:%M:%S')
        self.session_label.setText(f"会话开始时间: {session_time}")
    
    # 日志记录方法
    def log_queue_success(self, username: str, queue_type: str = "正常排队", cost: int = 1):
        """记录排队成功"""
        self.logger.log_queue_success(username, queue_type, cost)
        self.stats['total_success'] += 1
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_text = f"[{timestamp}] 排队成功 - {username} - {queue_type} (消耗次数: {cost})"
        self.log_updated.emit(log_text)
    
    def log_queue_failed(self, username: str, reason: str):
        """记录排队失败"""
        self.logger.log_queue_failed(username, reason)
        self.stats['total_failed'] += 1
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_text = f"[{timestamp}] 排队失败 - {username} - {reason}"
        self.log_updated.emit(log_text)
    
    def log_queue_complete(self, username: str, queue_type: str = "排队"):
        """记录完成排队"""
        self.logger.log_queue_complete(username, queue_type)
        self.stats['total_complete'] += 1
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_text = f"[{timestamp}] 完成排队 - {username} - {queue_type}"
        self.log_updated.emit(log_text)
    
    def log_system_event(self, event: str):
        """记录系统事件"""
        self.logger.log_system_event(event)
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_text = f"[{timestamp}] 系统事件 - {event}"
        self.log_updated.emit(log_text)
    
    def log_guard_gift(self, username: str, guard_level: str, reward_count: int, is_new_user: bool = False):
        """记录舰长礼物"""
        self.logger.log_guard_gift(username, guard_level, reward_count, is_new_user)
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        user_type = "新用户" if is_new_user else "现有用户"
        log_text = f"[{timestamp}] 舰长礼物 - {username} - {user_type}开通{guard_level}，获得{reward_count}次机会"
        self.log_updated.emit(log_text)
    
    def eventFilter(self, obj, event):
        """事件过滤器，监听滚轮事件"""
        if obj == self.log_text and event.type() == event.Type.Wheel:
            # 用户使用滚轮时，暂时关闭自动滚动
            if self.auto_scroll_enabled:
                self.auto_scroll_enabled = False
                self.user_scrolled = True
                self.update_auto_scroll_button()
                gui_logger.debug("检测到滚轮操作，已关闭自动滚动")
        return super().eventFilter(obj, event)
    
    def on_scroll_value_changed(self, value):
        """滚动条值变化时的处理"""
        if self.user_scrolled:
            scrollbar = self.log_text.verticalScrollBar()
            # 检查是否滚动到底部（允许一些误差）
            if value >= scrollbar.maximum() - 5:
                # 用户滚动到底部，重新开启自动滚动
                self.auto_scroll_enabled = True
                self.user_scrolled = False
                self.update_auto_scroll_button()
                gui_logger.debug("检测到滚动到底部，已重新开启自动滚动")
    
    def update_auto_scroll_button(self):
        """更新自动滚动按钮状态"""
        if self.auto_scroll_enabled:
            self.auto_scroll_btn.setText("自动滚动: 开")
            self.auto_scroll_btn.setChecked(True)
        else:
            self.auto_scroll_btn.setText("自动滚动: 关")
            self.auto_scroll_btn.setChecked(False)
    
    def manage_cache_size(self):
        """管理缓存大小，防止内存过度使用"""
        if len(self.log_cache) > self.max_cache_size:
            # 删除最旧的20%缓存
            remove_count = int(self.max_cache_size * 0.2)
            self.log_cache = self.log_cache[remove_count:]
            
            # 同时清理显示的文本
            text = self.log_text.toPlainText()
            lines = text.split('\n')
            if len(lines) > self.max_cache_size:
                # 保留最新的80%内容
                keep_count = int(self.max_cache_size * 0.8)
                new_text = '\n'.join(lines[-keep_count:])
                self.log_text.setPlainText(new_text)
                
                # 如果启用自动滚动，滚动到底部
                if self.auto_scroll_enabled:
                    cursor = self.log_text.textCursor()
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    self.log_text.setTextCursor(cursor)
            
            gui_logger.debug("弹幕缓存已清理", f"当前缓存大小: {len(self.log_cache)}")
