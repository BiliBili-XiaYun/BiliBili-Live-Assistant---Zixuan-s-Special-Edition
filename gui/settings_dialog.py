#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置对话框模块 - 程序全局设置
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QGroupBox, QMessageBox, 
                             QTabWidget, QWidget, QCheckBox, QSpinBox,
                             QLineEdit, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from config import app_config
from utils import gui_logger


class SettingsDialog(QDialog):
    """设置对话框"""
    
    # 信号定义
    settings_changed = pyqtSignal()  # 设置变更信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("程序设置")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        
        # 设置窗口图标
        from config import Constants
        icon_path = Constants.get_icon_path(128)
        if icon_path:
            from PyQt6.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path))
        
        self.init_ui()
        self.load_current_settings()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout()
        
        # 创建选项卡容器
        self.tab_widget = QTabWidget()
        
        # 日志设置选项卡
        self.create_logging_tab()
        
        # 通用设置选项卡
        self.create_general_tab()
        
        # 高级设置选项卡
        self.create_advanced_tab()
        
        layout.addWidget(self.tab_widget)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.apply_btn = QPushButton("应用")
        self.apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.apply_btn)
        
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept_settings)
        button_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def create_logging_tab(self):
        """创建日志设置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 日志级别设置
        log_level_group = QGroupBox("日志级别设置")
        log_level_layout = QVBoxLayout()
        
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("日志级别:"))
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
        self.log_level_combo.setToolTip(
            "DEBUG: 显示所有调试信息\n"
            "INFO: 显示一般信息和重要事件\n" 
            "WARNING: 仅显示警告和错误\n"
            "ERROR: 仅显示错误信息\n"
            "CRITICAL: 仅显示严重错误"
        )
        level_layout.addWidget(self.log_level_combo)
        level_layout.addStretch()
        
        log_level_layout.addLayout(level_layout)
        
        # 日志文件设置
        file_layout = QHBoxLayout()
        self.enable_file_logging = QCheckBox("启用文件日志")
        self.enable_file_logging.setChecked(True)
        self.enable_file_logging.setToolTip("将日志保存到文件中")
        file_layout.addWidget(self.enable_file_logging)
        file_layout.addStretch()
        
        log_level_layout.addLayout(file_layout)
        
        # 日志文件大小限制
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("日志文件大小限制(MB):"))
        
        self.log_file_size = QSpinBox()
        self.log_file_size.setRange(1, 100)
        self.log_file_size.setValue(10)
        self.log_file_size.setToolTip("单个日志文件的最大大小，超过后会自动轮转")
        size_layout.addWidget(self.log_file_size)
        size_layout.addStretch()
        
        log_level_layout.addLayout(size_layout)
        
        log_level_group.setLayout(log_level_layout)
        layout.addWidget(log_level_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "日志设置")
    
    def create_general_tab(self):
        """创建通用设置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 界面设置
        ui_group = QGroupBox("界面设置")
        ui_layout = QVBoxLayout()
        
        # 启动时自动连接
        self.auto_connect = QCheckBox("启动时自动连接直播间")
        self.auto_connect.setToolTip("程序启动后自动连接到配置的直播间")
        ui_layout.addWidget(self.auto_connect)
        
        # 最小化到系统托盘
        self.minimize_to_tray = QCheckBox("最小化到系统托盘")
        self.minimize_to_tray.setToolTip("点击最小化按钮时隐藏到系统托盘而不是任务栏")
        ui_layout.addWidget(self.minimize_to_tray)
        
        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)
        
        # 通知设置
        notification_group = QGroupBox("通知设置")
        notification_layout = QVBoxLayout()
        
        self.enable_notifications = QCheckBox("启用桌面通知")
        self.enable_notifications.setToolTip("重要事件发生时显示桌面通知")
        notification_layout.addWidget(self.enable_notifications)
        
        notification_group.setLayout(notification_layout)
        layout.addWidget(notification_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "通用设置")
    
    def create_advanced_tab(self):
        """创建高级设置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 性能设置
        performance_group = QGroupBox("性能设置")
        performance_layout = QVBoxLayout()
        
        # 文件监控间隔
        monitor_layout = QHBoxLayout()
        monitor_layout.addWidget(QLabel("文件监控间隔(秒):"))
        
        self.file_monitor_interval = QSpinBox()
        self.file_monitor_interval.setRange(1, 60)
        self.file_monitor_interval.setValue(5)
        self.file_monitor_interval.setToolTip("检查名单文件变化的时间间隔")
        monitor_layout.addWidget(self.file_monitor_interval)
        monitor_layout.addStretch()
        
        performance_layout.addLayout(monitor_layout)
        
        performance_group.setLayout(performance_layout)
        layout.addWidget(performance_group)
        
        # 调试设置
        debug_group = QGroupBox("调试设置")
        debug_layout = QVBoxLayout()
        
        self.enable_debug_mode = QCheckBox("启用调试模式")
        self.enable_debug_mode.setToolTip("启用额外的调试信息输出")
        debug_layout.addWidget(self.enable_debug_mode)
        
        debug_group.setLayout(debug_layout)
        layout.addWidget(debug_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "高级设置")
    
    def load_current_settings(self):
        """加载当前设置"""
        try:
            # 日志设置
            current_log_level = app_config.get("logging.level", "INFO")
            index = self.log_level_combo.findText(current_log_level)
            if index >= 0:
                self.log_level_combo.setCurrentIndex(index)
            
            self.enable_file_logging.setChecked(app_config.get("logging.enable_file", True))
            self.log_file_size.setValue(app_config.get("logging.max_file_size_mb", 10))
            
            # 通用设置
            self.auto_connect.setChecked(app_config.get("general.auto_connect", True))
            self.minimize_to_tray.setChecked(app_config.get("general.minimize_to_tray", False))
            self.enable_notifications.setChecked(app_config.get("general.enable_notifications", True))
            
            # 高级设置
            self.file_monitor_interval.setValue(app_config.get("advanced.file_monitor_interval", 5))
            self.enable_debug_mode.setChecked(app_config.get("advanced.debug_mode", False))
            
        except Exception as e:
            gui_logger.error("加载设置失败", str(e))
    
    def apply_settings(self):
        """应用设置"""
        try:
            # 保存日志设置
            app_config.set("logging.level", self.log_level_combo.currentText())
            app_config.set("logging.enable_file", self.enable_file_logging.isChecked())
            app_config.set("logging.max_file_size_mb", self.log_file_size.value())
            
            # 保存通用设置
            app_config.set("general.auto_connect", self.auto_connect.isChecked())
            app_config.set("general.minimize_to_tray", self.minimize_to_tray.isChecked())
            app_config.set("general.enable_notifications", self.enable_notifications.isChecked())
            
            # 保存高级设置
            app_config.set("advanced.file_monitor_interval", self.file_monitor_interval.value())
            app_config.set("advanced.debug_mode", self.enable_debug_mode.isChecked())
            
            # 应用日志级别设置
            self.apply_log_level_change()
            
            # 发出设置变更信号
            self.settings_changed.emit()
            
            QMessageBox.information(self, "成功", "设置已应用")
            gui_logger.info("用户设置已应用")
            
        except Exception as e:
            gui_logger.error("应用设置失败", str(e))
            QMessageBox.critical(self, "错误", f"应用设置失败: {str(e)}")
    
    def apply_log_level_change(self):
        """应用日志级别变更"""
        try:
            from utils import main_logger, queue_logger, gui_logger, bilibili_logger
            
            new_level = self.log_level_combo.currentText()
            
            # 更新所有日志器的级别
            loggers = [
                ("MainSystem", main_logger),
                ("QueueManager", queue_logger), 
                ("GUI", gui_logger),
                ("Bilibili", bilibili_logger)
            ]
            
            for logger_name, logger in loggers:
                logger.set_log_level(new_level)
                # 只在第一个日志器中记录变更，避免重复输出
                if logger_name == "MainSystem":
                    gui_logger.info(f"全局日志级别已更新为: {new_level}")
                    break
            
        except Exception as e:
            gui_logger.error("更新日志级别失败", str(e))
    
    def accept_settings(self):
        """确定并关闭"""
        self.apply_settings()
        self.accept()
    
    def reset_to_defaults(self):
        """重置为默认设置"""
        reply = QMessageBox.question(
            self, "确认重置", 
            "确定要重置所有设置为默认值吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 重置为默认值
            self.log_level_combo.setCurrentText("INFO")
            self.enable_file_logging.setChecked(True)
            self.log_file_size.setValue(10)
            self.auto_connect.setChecked(True)
            self.minimize_to_tray.setChecked(False)
            self.enable_notifications.setChecked(True)
            self.file_monitor_interval.setValue(5)
            self.enable_debug_mode.setChecked(False)
            
            gui_logger.info("设置已重置为默认值")
