#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
排队工具2专用排队管理窗口模块 - 去除上车相关功能
"""

import os
import subprocess
import platform
from ctypes import wintypes
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QTableWidget, QTableWidgetItem,
                             QHeaderView, QSplitter, QMessageBox, QDialog, 
                             QGroupBox, QTabWidget, QFrame, QStatusBar)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont, QColor, QClipboard
from PyQt6.QtWidgets import QApplication

# 导入plyer通知库
try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False


from models import QueueItem
from queue_manager.manager_queue2 import QueueManager
from gui.insert_queue_dialog import InsertQueueDialog
from gui.manual_add_queue_dialog import ManualAddQueueDialog
from gui.log_widget_simple import LogDisplayWidget
from config import Constants
from utils import RandomSelectionAnimationThread, show_copy_notification, gui_logger


class Queue2ManagerWindow(QMainWindow):
    """默认样式"""
      # 信号定义
    danmaku_queue_signal = pyqtSignal(str)  # 排队弹幕信号
    def __init__(self, parent=None, queue_manager=None):
        """
        初始化排队管理窗口        
        Args:
            parent: 父窗口
            queue_manager: 外部队列管理器实例，如果为None则创建新实例
        """
        super().__init__(parent)
        self.setWindowTitle("子轩专属排队管理系统 - 排队工具2")
        self.setGeometry(200, 200, 1200, 800)
        
        # 设置窗口属性，确保在任务栏中独立显示
        from PyQt6.QtCore import Qt
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        
        # 设置窗口图标
        from config import Constants
        icon_path = Constants.get_icon_path(128)
        if icon_path:
            from PyQt6.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path))
        
        # 设置样式，与主窗口保持一致
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 15px;
                background-color: white;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #495057;
                background-color: white;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #45a049);
                border: none;
                color: white;
                padding: 10px 20px;
                text-align: center;
                font-size: 14px;
                font-weight: bold;
                margin: 4px 2px;
                border-radius: 6px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #45a049, stop:1 #3d8b40);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3d8b40, stop:1 #2e7031);
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #adb5bd;
            }
            QLineEdit {
                border: 2px solid #ced4da;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #4CAF50;
            }
            QTextEdit {
                border: 2px solid #ced4da;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
                background-color: white;
            }
            QLabel {
                font-size: 14px;
            }
            QTableWidget {
                border: 2px solid #dee2e6;
                border-radius: 6px;
                background-color: white;
                gridline-color: #e9ecef;
                selection-background-color: #e3f2fd;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #bbdefb;
                color: #1976d2;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f1f3f4, stop:1 #e8eaed);
                border: 1px solid #d0d7de;
                padding: 8px;
                font-weight: bold;
                font-size: 13px;
            }
            QTabWidget::pane {
                border: 2px solid #dee2e6;
                border-radius: 6px;
                background-color: white;
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 2px solid #dee2e6;
                padding: 8px 16px;
                margin-right: 2px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
            }
            QTabBar::tab:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e9ecef, stop:1 #dee2e6);
            }
        """)
        
        # 使用传入的队列管理器或创建新实例
        if queue_manager is not None:
            self.queue_manager = queue_manager
            gui_logger.debug("排队窗口初始化", "使用外部传入的队列管理器")
        else:
            self.queue_manager = QueueManager()  # 不传递参数，让它从配置中读取
            gui_logger.debug("排队窗口初始化", "创建新的队列管理器实例")
        # 子窗口
        self.name_list_editor = None        # 日志组件
        self.log_widget = LogDisplayWidget()
        
        # 持久化中奖用户显示
        self.persistent_winners_text = None
        
        # 文件监控相关
        self.name_list_file_mtime = 0
        self.file_monitor_timer = QTimer()
        self.file_monitor_timer.timeout.connect(self.check_name_list_file_changes)
        self.file_monitor_timer.start(3000)  # 每3秒检查一次文件变化
        
        # 随机选择相关
        self.animation_thread = None
        self.random_selected_rows = []
        self.final_highlighted_rows = []  # 新增：记录最终高亮的行
        self.is_animating = False  # 新增：动画状态标志
        
        # 插队名单设置 - 默认为None表示使用排队队列名单
        self.cutline_custom_namelist = None
        self.cutline_use_custom_namelist = False
        
        # 初始化UI
        self.init_ui()
        
        # 加载数据
        self.load_data()
        
        # 初始化文件修改时间
        self.update_name_list_file_mtime()

    def update_name_list_file_mtime(self):
        """更新名单文件的修改时间"""
        try:
            name_list_file = self.queue_manager.get_name_list_file()
            if name_list_file and os.path.exists(name_list_file):
                self.name_list_file_mtime = os.path.getmtime(name_list_file)
        except Exception as e:
            gui_logger.warning("获取名单文件修改时间失败", str(e))

    def check_name_list_file_changes(self):
        """检查名单文件是否有变化，如果有则自动重新加载"""
        try:
            name_list_file = self.queue_manager.get_name_list_file()
            if not name_list_file or not os.path.exists(name_list_file):
                return
            
            current_mtime = os.path.getmtime(name_list_file)
            if current_mtime > self.name_list_file_mtime:
                gui_logger.info("检测到名单文件变化", name_list_file)
                gui_logger.debug("文件修改时间检查", f"{current_mtime} > {self.name_list_file_mtime}")
                
                # 自动重新加载名单（保留队列）
                success = self.queue_manager.reload_name_list_preserve_queues()
                if success:
                    self.refresh_ui()
                    self.log_widget.log_system_event("检测到名单文件变化，已自动重新加载")
                    gui_logger.operation_complete("自动重新加载名单", "成功")
                else:
                    gui_logger.warning("自动重新加载名单失败")
                
                # 更新文件修改时间
                self.name_list_file_mtime = current_mtime
                
        except Exception as e:
            gui_logger.error("检查名单文件变化时出错", str(e))

    def refresh_ui(self):
        """直接刷新UI界面"""
        self.update_queue_table()
        self.update_cutline_table()
        self.update_button_states()
        self.update_status_bar()
        
        # 重新应用高亮效果
        self.reapply_all_highlights()
        
    
    def init_ui(self):
        """初始化用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 顶部控制按钮区域
        control_group = QGroupBox("排队控制")
        control_layout = QHBoxLayout()
        
        # 开始/停止按钮
        self.start_queue_btn = QPushButton("开始排队")
        self.start_queue_btn.clicked.connect(self.start_queue)
        control_layout.addWidget(self.start_queue_btn)
        
        self.stop_queue_btn = QPushButton("停止排队")
        self.stop_queue_btn.clicked.connect(self.stop_queue)
        self.stop_queue_btn.setEnabled(False)
        control_layout.addWidget(self.stop_queue_btn)
        
        # 插队控制按钮
        self.start_cutline_btn = QPushButton("开始插队")
        self.start_cutline_btn.clicked.connect(self.start_cutline)
        control_layout.addWidget(self.start_cutline_btn)
        
        self.stop_cutline_btn = QPushButton("停止插队")
        self.stop_cutline_btn.clicked.connect(self.stop_cutline)
        self.stop_cutline_btn.setEnabled(False)
        control_layout.addWidget(self.stop_cutline_btn)
        
        # 插队名单设置按钮
        self.cutline_namelist_btn = QPushButton("插队名单设置")
        self.cutline_namelist_btn.clicked.connect(self.show_cutline_namelist_dialog)
        control_layout.addWidget(self.cutline_namelist_btn)
        
        # 重新排队按钮
        self.requeue_btn = QPushButton("重新排队")
        self.requeue_btn.clicked.connect(self.requeue)
        control_layout.addWidget(self.requeue_btn)
        
        # 名单操作按钮
        self.reload_btn = QPushButton("重新加载名单")
        self.reload_btn.clicked.connect(self.reload_name_list)
        control_layout.addWidget(self.reload_btn)
        
        self.refresh_config_btn = QPushButton("刷新配置")
        self.refresh_config_btn.clicked.connect(self.refresh_config)
        control_layout.addWidget(self.refresh_config_btn)
        
        self.edit_name_list_btn = QPushButton("编辑名单")
        self.edit_name_list_btn.clicked.connect(self.show_name_list_editor)
        control_layout.addWidget(self.edit_name_list_btn)
        
        control_layout.addStretch()
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # 主要内容区域 - 使用标签页
        self.tab_widget = QTabWidget()
        
        # 排队管理标签页
        queue_tab = self.create_queue_tab()
        self.tab_widget.addTab(queue_tab, "排队管理")
        
        # 日志监控标签页
        log_tab = self.create_log_tab()
        self.tab_widget.addTab(log_tab, "日志监控")
        
        main_layout.addWidget(self.tab_widget)
        central_widget.setLayout(main_layout)          # 创建状态栏
        self.create_status_bar()
        
    
    def create_queue_tab(self):
        """创建排队管理标签页"""
        tab_widget = QWidget()
        layout = QVBoxLayout()
        
        # 创建主水平分割器
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 排队队列区域（左侧）
        queue_widget = self.create_queue_widget()
        main_splitter.addWidget(queue_widget)
        
        # 插队队列区域（右侧）
        cutline_widget = self.create_cutline_widget()
        main_splitter.addWidget(cutline_widget)
        
        # 设置主分割器比例（排队:插队 = 60:40）
        main_splitter.setSizes([600, 400])
        
        layout.addWidget(main_splitter)
        tab_widget.setLayout(layout)
        return tab_widget
    
    def create_log_tab(self):
        """创建日志监控标签页"""
        tab_widget = QWidget()
        layout = QVBoxLayout()
        
        # 添加日志组件
        layout.addWidget(self.log_widget)
        
        tab_widget.setLayout(layout)
        return tab_widget
    
    def create_queue_widget(self) -> QWidget:
        """创建排队队列组件"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 标题区域
        title_layout = QHBoxLayout()
        title_label = QLabel("排队队列")
        title_layout.addWidget(title_label)
        
        # 抽奖显示区域 - 单人抽奖布局
        lottery_layout = QHBoxLayout()
        
        # 抽奖结果显示（只显示一个框）
        self.lottery_display_user1 = QLabel("等待抽奖")
        self.lottery_display_user1.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                padding: 8px 15px;
                font-size: 14px;
                font-weight: normal;
                color: #495057;
                min-width: 200px;
                max-width: 300px;
                min-height: 35px;
            }
        """)
        self.lottery_display_user1.setWordWrap(True)
        self.lottery_display_user1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lottery_layout.addWidget(self.lottery_display_user1)

        # 随机按钮
        self.random_select_btn = QPushButton("随机")
        self.random_select_btn.clicked.connect(self.start_random_selection)
        self.random_select_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
                font-size: 12px;
                min-width: 60px;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
            QPushButton:pressed {
                background-color: #7d3c98;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #ffffff;
            }
        """)
        lottery_layout.addWidget(self.random_select_btn)
        
        title_layout.addLayout(lottery_layout)
        title_layout.addStretch()
          # 队列统计
        self.queue_stats_label = QLabel("共 0 人在排队")
        title_layout.addWidget(self.queue_stats_label)
        
        layout.addLayout(title_layout)        # 表格
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(4)
        self.queue_table.setHorizontalHeaderLabels(["序号", "名字", "完成", "取消"])
        # 设置表格属性
        self.setup_table(self.queue_table)
        layout.addWidget(self.queue_table)
        
        widget.setLayout(layout)
        return widget
    
    def create_cutline_widget(self) -> QWidget:
        """创建插队队列组件"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 标题区域
        title_layout = QHBoxLayout()
        title_label = QLabel("插队队列")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        # 插队统计
        self.cutline_stats_label = QLabel("共 0 人在插队")
        title_layout.addWidget(self.cutline_stats_label)
        
        layout.addLayout(title_layout)
        # 表格
        self.cutline_table = QTableWidget()
        self.cutline_table.setColumnCount(4)
        self.cutline_table.setHorizontalHeaderLabels(["序号", "名字", "完成", "取消"])
        # 设置表格属性
        self.setup_table(self.cutline_table)
        layout.addWidget(self.cutline_table)
        
        widget.setLayout(layout)
        return widget
    
    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 状态标签
        self.status_label = QLabel("正在初始化...")
        self.status_bar.addWidget(self.status_label)
        
        # 分隔符
        self.status_bar.addPermanentWidget(QLabel("|"))
        
        # 队列状态
        self.queue_status_label = QLabel("排队: 未开始")
        self.status_bar.addPermanentWidget(self.queue_status_label)        # 分隔符
        self.status_bar.addPermanentWidget(QLabel("|"))
        
        # 统计信息
        self.stats_status_label = QLabel("统计: 加载中...")
        self.status_bar.addPermanentWidget(self.stats_status_label)
    

    def setup_table(self, table: QTableWidget):
        """设置表格属性"""
        header = table.horizontalHeader()
        
        # 所有4列表格都使用相同的布局：序号、名字、完成、取消
        if table.columnCount() == 4:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # 序号列
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)           # 名字列
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)             # 完成按钮列
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)             # 取消按钮列
            
            # 设置按钮列的固定宽度
            table.setColumnWidth(2, 80)  # 完成按钮列
            table.setColumnWidth(3, 80)  # 取消按钮列
        
        # 设置行高
        table.verticalHeader().setDefaultSectionSize(40)
          # 禁用编辑
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # 设置选择行为 - 禁用选择以避免滚轮时意外选中
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # 交替行颜色
        table.setAlternatingRowColors(True)
          # 设置表格样式，修复选中时文字看不清的问题
        table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
                alternate-background-color: #f5f5f5;
            }
            QTableWidget::item {
                padding: 6px;
                border: none;
                color: #333333;
            }
            QTableWidget::item:hover {
                background-color: #e3f2fd;
                color: #333333;
            }
            QTableWidget::item:selected {
                background-color: #3daee9;
                color: white;
            }
            QTableWidget::item:selected:hover {
                background-color: #2196f3;
                color: white;
            }
            QTableWidget QScrollBar:vertical {
                background: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            QTableWidget QScrollBar::handle:vertical {
                background: #c0c0c0;
                border-radius: 6px;
                min-height: 20px;
            }            
            QTableWidget QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
        """)
        
        # 为表格中的按钮设置样式
        button_style = """
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                min-width: 50px;
                max-width: 70px;
                color: #495057;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
        """
        
        # 添加双击事件处理
        table.itemDoubleClicked.connect(self.on_table_item_double_clicked)
    
    def load_data(self):
        """加载数据"""
        # 尝试加载保存的状态
        if not self.queue_manager.load_state():
            # 如果没有保存的状态，检查是否有名单文件路径配置
            current_file = self.queue_manager.get_name_list_file()
            if current_file and current_file.strip():
                gui_logger.operation_start("加载配置的名单文件", current_file)
                self.queue_manager.load_name_list()
            else:
                gui_logger.warning("未配置名单文件路径，跳过名单加载")        # 直接更新界面，不使用回调
        self.refresh_ui()
          # 显示状态信息
        status = self.queue_manager.get_queue_status()        
        self.update_status(f"名单: {status['total_names']} 项, "
                          f"排队: {status['queue_count']} 人, "
                          f"上车: {status['boarding_count']} 人")
        
        # 记录系统启动日志
        self.log_widget.log_system_event("排队管理系统启动")
    
    def start_queue(self):
        """开始排队"""
        self.queue_manager.start_queue()
        self.refresh_ui()
        self.log_widget.log_system_event("开始排队服务")
    
    def stop_queue(self):
        """停止排队"""
        self.queue_manager.stop_queue()
        self.refresh_ui()
        self.log_widget.log_system_event("停止排队服务")
    
    def start_cutline(self):
        """开始插队"""
        self.queue_manager.start_cutline()
        self.update_button_states()
        self.log_widget.log_system_event("开始插队服务")
    
    def stop_cutline(self):
        """停止插队"""
        self.queue_manager.stop_cutline()
        self.update_button_states()
        self.log_widget.log_system_event("停止插队服务")
    
    def requeue(self):
        """重新排队 - 清空排队队列和插队队列重新开始"""
        reply = QMessageBox.question(
            self, "确认", "确定要清空排队队列和插队队列重新开始吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No        
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 重置所有名单项目的队列标志
            for item in self.queue_manager.name_list:
                item.in_queue = False
                item.is_cutline = False
                
            # 清空排队队列
            self.queue_manager.queue_list.clear()
            self.queue_manager.user_queued.clear()
            
            # 清空插队队列
            self.queue_manager.cutline_list.clear()
            self.queue_manager.user_cutline.clear()
            
            # 清除所有随机选择的字体效果，重新开始
            self.clear_all_highlights()
            
            # 重置随机选择相关的状态
            self.animation_highlighted_rows = []
            self.random_selected_rows = []
            self.final_highlighted_rows = []
            self.is_animating = False
            
            # 重置随机按钮状态
            self.reset_random_button()
            
            # 清除抽奖结果显示
            self.reset_lottery_display()
            
            # 直接更新界面（包括插队表格）
            self.update_queue_table()
            self.update_cutline_table()
            self.update_button_states()
            self.log_widget.log_system_event("清空排队队列和插队队列，重新开始，已清除所有字体效果")
    
    def reload_name_list(self):
        """重新加载名单 - 自动执行，返回成功状态"""
        try:
            # 首先调用主窗口的路径同步方法
            if hasattr(self.parent(), 'sync_file_paths'):
                self.parent().sync_file_paths()
            
            # 检查是否有名单编辑器，并获取其当前文件路径
            current_manager_file = self.queue_manager.get_name_list_file()
            gui_logger.debug("重新加载前检查", f"排队管理器当前文件路径: {current_manager_file}")
            
            if hasattr(self.parent(), 'name_list_editor') and self.parent().name_list_editor:
                editor_file = self.parent().name_list_editor.name_list_file
                gui_logger.debug("名单编辑器文件路径", editor_file)
                
                if editor_file != current_manager_file:
                    # 更新队列管理器的文件路径
                    old_path = self.queue_manager.get_name_list_file()
                    self.queue_manager.set_name_list_file(editor_file)
                    new_path = self.queue_manager.get_name_list_file()
                    gui_logger.info("文件路径更新", f"{old_path} -> {new_path}")
                else:
                    gui_logger.debug("文件路径检查", f"路径一致，无需更新: {editor_file}")
            else:
                gui_logger.warning("未找到名单编辑器或编辑器未初始化")
            
            # 使用保留队列的重新加载方法
            success = self.queue_manager.reload_name_list_preserve_queues()
            
            # 更新文件修改时间
            self.update_name_list_file_mtime()
            
            # 直接刷新UI
            self.refresh_ui()
            
            if success:
                gui_logger.operation_complete("名单重新加载", "成功，队列已保留")
                self.log_widget.log_system_event("重新加载名单成功，队列已保留")
                return True
            else:
                gui_logger.error("名单重新加载失败")
                self.log_widget.log_system_event("重新加载名单失败")
                return False
                
        except Exception as e:
            gui_logger.error("重新加载名单时发生异常", str(e))
            self.log_widget.log_system_event(f"重新加载名单异常: {str(e)}")
            return False

    def show_name_list_editor(self):
        """显示名单编辑器"""
        try:
            from gui.name_list_editor import NameListEditor
            
            if self.name_list_editor is None:
                self.name_list_editor = NameListEditor(self)
                self.name_list_editor.name_list_changed.connect(self.on_name_list_changed)
            
            self.name_list_editor.show()
            self.name_list_editor.raise_()
            self.name_list_editor.activateWindow()
        except ImportError:
            QMessageBox.information(self, "提示", "名单编辑器功能尚未实现")
    
    def show_cutline_namelist_dialog(self):
        """显示插队名单设置对话框"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QRadioButton, QButtonGroup, QLabel, QFileDialog
        
        class CutlineNamelistDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle("插队名单设置")
                self.setFixedSize(400, 200)
                self.setModal(True)
                
                layout = QVBoxLayout()
                
                # 说明文字
                info_label = QLabel("选择插队功能使用的名单：")
                info_label.setFont(QFont("", 10))
                layout.addWidget(info_label)
                
                # 单选按钮组
                self.button_group = QButtonGroup()
                
                # 使用排队名单选项
                self.use_queue_radio = QRadioButton("使用排队队列名单")
                self.button_group.addButton(self.use_queue_radio, 0)
                layout.addWidget(self.use_queue_radio)
                
                # 使用自定义名单选项
                self.use_custom_radio = QRadioButton("使用自定义名单")
                self.button_group.addButton(self.use_custom_radio, 1)
                layout.addWidget(self.use_custom_radio)
                
                # 自定义名单文件选择
                file_layout = QHBoxLayout()
                self.file_label = QLabel("未选择文件")
                self.file_button = QPushButton("选择CSV文件")
                self.file_button.clicked.connect(self.select_file)
                file_layout.addWidget(self.file_label)
                file_layout.addWidget(self.file_button)
                layout.addLayout(file_layout)
                
                # 按钮
                button_layout = QHBoxLayout()
                ok_button = QPushButton("确定")
                cancel_button = QPushButton("取消")
                ok_button.clicked.connect(self.accept)
                cancel_button.clicked.connect(self.reject)
                button_layout.addWidget(ok_button)
                button_layout.addWidget(cancel_button)
                layout.addLayout(button_layout)
                
                self.setLayout(layout)
                
                # 初始化状态
                self.custom_file_path = None
                self.use_queue_radio.setChecked(True)
                self.update_ui_state()
                
                # 连接信号
                self.use_queue_radio.toggled.connect(self.update_ui_state)
                
            def update_ui_state(self):
                """更新UI状态"""
                is_custom = self.use_custom_radio.isChecked()
                self.file_label.setEnabled(is_custom)
                self.file_button.setEnabled(is_custom)
                
            def select_file(self):
                """选择CSV文件"""
                file_path, _ = QFileDialog.getOpenFileName(
                    self, "选择CSV名单文件", "", "CSV文件 (*.csv)")
                if file_path:
                    self.custom_file_path = file_path
                    import os
                    self.file_label.setText(os.path.basename(file_path))
        
        # 创建并显示对话框
        dialog = CutlineNamelistDialog(self)
        
        # 设置当前状态
        if self.cutline_use_custom_namelist:
            dialog.use_custom_radio.setChecked(True)
            if self.cutline_custom_namelist:
                import os
                dialog.file_label.setText(os.path.basename(self.cutline_custom_namelist))
                dialog.custom_file_path = self.cutline_custom_namelist
        else:
            dialog.use_queue_radio.setChecked(True)
            
        dialog.update_ui_state()
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 保存设置
            if dialog.use_custom_radio.isChecked():
                if dialog.custom_file_path:
                    self.cutline_use_custom_namelist = True
                    self.cutline_custom_namelist = dialog.custom_file_path
                    # 设置到队列管理器
                    self.queue_manager.set_cutline_namelist(dialog.custom_file_path, True)
                    self.log_widget.log_system_event(f"插队名单设置为: {dialog.custom_file_path}")
                else:
                    QMessageBox.warning(self, "警告", "请选择自定义名单文件！")
            else:
                self.cutline_use_custom_namelist = False
                self.cutline_custom_namelist = None
                # 设置到队列管理器
                self.queue_manager.set_cutline_namelist(None, False)
                self.log_widget.log_system_event("插队名单设置为: 使用排队队列名单")
    
    def on_name_list_changed(self):
        """名单变更处理 - 自动重载，只有失败时才提示"""
        try:
            success = self.reload_name_list()
            if success:
                gui_logger.info("名单已自动重载")
            else:
                # 只有重载失败时才显示提示
                QMessageBox.warning(
                    self, "重载失败", "名单自动重载失败，请手动检查名单文件",
                    QMessageBox.StandardButton.Ok
                )
        except Exception as e:
            # 发生异常时提示用户
            QMessageBox.critical(
                self, "重载错误", f"名单重载时发生错误：{str(e)}",
                QMessageBox.StandardButton.Ok
            )

    def update_queue_table(self):
        """更新排队队列表格"""
        queue_list = self.queue_manager.queue_list
        self.queue_table.setRowCount(len(queue_list))
        
        for row, item in enumerate(queue_list):
            # 序号列
            index_text = "插队" if item.is_cutline else str(item.index)
            index_item = QTableWidgetItem(index_text)
            if item.is_cutline:
                index_item.setForeground(QColor("orange"))
                font = QFont()
                font.setBold(True)
                index_item.setFont(font)
            self.queue_table.setItem(row, 0, index_item)
            
            # 名字列
            name_item = QTableWidgetItem(item.name)
            if item.is_cutline:
                name_item.setForeground(QColor("orange"))
                font = QFont()
                font.setBold(True)
                name_item.setFont(font)
            self.queue_table.setItem(row, 1, name_item)
              # 完成按钮
            complete_btn = QPushButton("完成")
            complete_btn.setProperty("table_row", row)
            complete_btn.setProperty("table_type", "queue")
            complete_btn.setProperty("action_type", "complete")
            complete_btn.clicked.connect(self.handle_table_button_click)
            complete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #d4edda;
                    border: 1px solid #c3e6cb;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 12px;
                    min-width: 50px;
                    max-width: 70px;
                    color: #155724;
                }
                QPushButton:hover {
                    background-color: #c3e6cb;
                    border-color: #b8dabc;
                }
                QPushButton:pressed {
                    background-color: #b8dabc;
                }
            """)
            self.queue_table.setCellWidget(row, 2, complete_btn)
            
            # 取消按钮
            cancel_btn = QPushButton("取消")
            cancel_btn.setProperty("table_row", row)
            cancel_btn.setProperty("table_type", "queue")
            cancel_btn.setProperty("action_type", "cancel")
            cancel_btn.clicked.connect(self.handle_table_button_click)
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 12px;
                    min-width: 50px;
                    max-width: 70px;
                    color: #721c24;
                }
                QPushButton:hover {
                    background-color: #f5c6cb;
                    border-color: #f1b0b7;
                }
                QPushButton:pressed {
                    background-color: #f1b0b7;
                }
            """)
            self.queue_table.setCellWidget(row, 3, cancel_btn)
          # 更新统计        
        self.queue_stats_label.setText(f"共 {len(queue_list)} 人在排队")
        
        # 重新应用随机选择的高亮（如果有的话）
        if not getattr(self, 'is_animating', False):
            # 在表格更新后立即重新应用高亮
            QTimer.singleShot(10, self.reapply_all_highlights)
    
    def update_cutline_table(self):
        """更新插队队列表格"""
        cutline_list = self.queue_manager.cutline_list
        self.cutline_table.setRowCount(len(cutline_list))
        
        for row, item in enumerate(cutline_list):
            # 序号列 - 插队显示为"插队"
            index_item = QTableWidgetItem("插队")
            index_item.setForeground(QColor("orange"))
            font = QFont()
            font.setBold(True)
            index_item.setFont(font)
            self.cutline_table.setItem(row, 0, index_item)
            
            # 名字列
            name_item = QTableWidgetItem(item.name)
            name_item.setForeground(QColor("orange"))
            font = QFont()
            font.setBold(True)
            name_item.setFont(font)
            self.cutline_table.setItem(row, 1, name_item)
            
            # 完成按钮
            complete_btn = QPushButton("完成")
            complete_btn.setProperty("table_row", row)
            complete_btn.setProperty("table_type", "cutline")
            complete_btn.setProperty("action_type", "complete")
            complete_btn.clicked.connect(self.handle_table_button_click)
            complete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #d4edda;
                    border: 1px solid #c3e6cb;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 12px;
                    min-width: 50px;
                    max-width: 70px;
                    color: #155724;
                }
                QPushButton:hover {
                    background-color: #c3e6cb;
                    border-color: #b8dabc;
                }
                QPushButton:pressed {
                    background-color: #b8dabc;
                }
            """)
            self.cutline_table.setCellWidget(row, 2, complete_btn)
            
            # 取消按钮
            cancel_btn = QPushButton("取消")
            cancel_btn.setProperty("table_row", row)
            cancel_btn.setProperty("table_type", "cutline")
            cancel_btn.setProperty("action_type", "cancel")
            cancel_btn.clicked.connect(self.handle_table_button_click)
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 12px;
                    min-width: 50px;
                    max-width: 70px;
                    color: #721c24;
                }
                QPushButton:hover {
                    background-color: #f5c6cb;
                    border-color: #f1b0b7;
                }
                QPushButton:pressed {
                    background-color: #f1b0b7;
                }
            """)
            self.cutline_table.setCellWidget(row, 3, cancel_btn)
        
        # 更新统计
        self.cutline_stats_label.setText(f"共 {len(cutline_list)} 人在插队")
    
    def handle_table_button_click(self):
        """统一处理表格按钮点击"""
        sender = self.sender()
        if not sender:
            gui_logger.warning("按钮点击事件：未找到发送者")
            return
        
        row = sender.property("table_row")
        table_type = sender.property("table_type")
        action_type = sender.property("action_type")
        
        gui_logger.debug("按钮点击事件", f"行={row}, 表格={table_type}, 操作={action_type}")
        
        if row is None or table_type is None:
            gui_logger.warning("按钮点击事件：缺少必要属性", f"行={row}, 表格={table_type}")
            return
        
        try:
            if table_type == "queue":
                if action_type == "cancel":
                    gui_logger.info("执行排队取消操作", f"行={row}")
                    self.cancel_queue_item(row)
                else:  # 默认为完成操作
                    gui_logger.info("执行排队完成操作", f"行={row}")
                    self.complete_queue_item(row)
            elif table_type == "cutline":
                if action_type == "cancel":
                    gui_logger.info("执行插队取消操作", f"行={row}")
                    self.cancel_cutline_item(row)
                else:  # 默认为完成操作
                    gui_logger.info("执行插队完成操作", f"行={row}")
                    self.complete_cutline_item(row)
        except Exception as e:
            gui_logger.error("处理表格按钮点击时出错", str(e))
    
    def update_button_states(self):
        """更新按钮状态"""
        is_running = self.queue_manager.queue_started
        self.start_queue_btn.setEnabled(not is_running)
        self.stop_queue_btn.setEnabled(is_running)
        
        # 更新插队按钮状态
        is_cutline = self.queue_manager.cutline_started
        self.start_cutline_btn.setEnabled(not is_cutline)
        self.stop_cutline_btn.setEnabled(is_cutline)
          # 更新状态栏
        status_text = "运行中" if is_running else "已停止"
        cutline_text = "运行中" if is_cutline else "已停止"
        self.queue_status_label.setText(f"排队: {status_text} | 插队: {cutline_text}")
    
    def update_status(self, message: str):
        """更新状态显示"""
        self.status_label.setText(message)
        gui_logger.debug("状态更新", message)    
    def update_status_bar(self):
        """更新状态栏信息"""
        try:
            status = self.queue_manager.get_queue_status()
            stats_text = f"名单: {status['total_names']} | 排队: {status['queue_count']}"
            self.stats_status_label.setText(stats_text)
        except Exception as e:
            self.stats_status_label.setText(f"统计: 错误 - {e}")
    
    def complete_queue_item(self, index: int):
        """完成排队项目"""
        if 0 <= index < len(self.queue_manager.queue_list):
            item = self.queue_manager.queue_list[index]
            success = self.queue_manager.complete_queue_item(index)
            if success:
                self.refresh_ui()  # 直接刷新UI
                self.log_widget.log_queue_complete(item.name, "排队队列")
    
    def cancel_queue_item(self, index: int):
        """取消排队项目（不扣除次数）"""
        if 0 <= index < len(self.queue_manager.queue_list):
            item = self.queue_manager.queue_list[index]
            success = self.queue_manager.cancel_queue_item(index)
            if success:
                self.refresh_ui()  # 直接刷新UI
                self.log_widget.log_system_event(f"{item.name} 取消排队（未扣除次数）")
    
    def complete_cutline_item(self, index: int):
        """完成插队项目"""
        gui_logger.debug("完成插队项目", f"索引={index}, 插队列表长度={len(self.queue_manager.cutline_list)}")
        
        if 0 <= index < len(self.queue_manager.cutline_list):
            item = self.queue_manager.cutline_list[index]
            gui_logger.info("准备完成插队", f"用户={item.name}, 索引={index}")
            
            success = self.queue_manager.complete_cutline_item(item.name)
            if success:
                gui_logger.operation_complete("插队完成", f"用户={item.name}")
                self.refresh_ui()  # 直接刷新UI
                self.log_widget.log_queue_complete(item.name, "插队队列")
            else:
                gui_logger.error("插队完成失败", f"用户={item.name}")
        else:
            gui_logger.error("插队索引越界", f"索引={index}, 插队列表长度={len(self.queue_manager.cutline_list)}")
    
    def cancel_cutline_item(self, index: int):
        """取消插队项目（不扣除次数）"""
        gui_logger.debug("取消插队项目", f"索引={index}, 插队列表长度={len(self.queue_manager.cutline_list)}")
        
        if 0 <= index < len(self.queue_manager.cutline_list):
            item = self.queue_manager.cutline_list[index]
            gui_logger.info("准备取消插队", f"用户={item.name}, 索引={index}")
            
            success = self.queue_manager.delete_cutline_item(item.name)
            if success:
                gui_logger.operation_complete("插队取消", f"用户={item.name}")
                self.refresh_ui()  # 直接刷新UI
                self.log_widget.log_system_event(f"{item.name} 取消插队（未扣除次数）")
            else:
                gui_logger.error("插队取消失败", f"用户={item.name}")
        else:
            gui_logger.error("插队索引越界", f"索引={index}, 插队列表长度={len(self.queue_manager.cutline_list)}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止文件监控定时器
        if hasattr(self, 'file_monitor_timer'):
            self.file_monitor_timer.stop()
        super().closeEvent(event)

    def refresh_config(self):
        """刷新配置并重新加载名单文件"""
        try:
            gui_logger.operation_start("刷新配置")
            
            # 手动刷新队列管理器的配置
            success = self.queue_manager.refresh_name_list_from_config()
            
            # 直接刷新UI
            self.refresh_ui()
            
            if success:
                QMessageBox.information(self, "成功", "配置已刷新，名单文件已重新加载")
                self.log_widget.log_system_event("配置刷新成功，名单文件已重新加载")
            else:
                QMessageBox.warning(self, "警告", "配置刷新成功，但名单文件加载失败")
                self.log_widget.log_system_event("配置刷新成功，但名单文件加载失败")
                
        except Exception as e:
            error_msg = f"刷新配置失败: {str(e)}"
            gui_logger.error("刷新配置错误", error_msg)
            QMessageBox.critical(self, "错误", error_msg)            
            self.log_widget.log_system_event(f"配置刷新失败: {str(e)}")

    def process_danmaku_queue(self, username: str):
        """
        处理弹幕排队请求
        
        Args:
            username (str): 用户名
        """
        try:
            # 使用队列管理器的process_queue_request方法处理排队请求
            # 这个方法会检查queue_started状态
            success = self.queue_manager.process_queue_request(username)
            
            if success:
                # 直接刷新UI
                self.refresh_ui()
                
                # 记录成功日志
                self.log_widget.log_queue_success(username, "弹幕排队", Constants.NORMAL_COST)
            else:
                # 可能的失败原因：排队服务未开启、用户已在队列中、名单中找不到或次数不足
                if not self.queue_manager.queue_started:
                    self.log_widget.log_queue_failed(username, "排队服务未开启")
                elif username in self.queue_manager.user_queued:
                    self.log_widget.log_queue_failed(username, "已在队列中")
                else:
                    self.log_widget.log_queue_failed(username, "名单中找不到或次数不足")
            
        except Exception as e:
            self.log_widget.log_queue_failed(username, f"系统错误: {str(e)}")
    
    def process_danmaku_cutline(self, username: str):
        """
        处理弹幕插队请求
        
        Args:
            username (str): 用户名
        """
        try:
            # 调用队列管理器的插队处理函数
            success = self.queue_manager.process_cutline_request(username)
            
            if success:
                # 直接刷新UI
                self.refresh_ui()
                
                # 记录成功日志 - 插队消耗指定次数
                from config import Constants
                self.log_widget.log_queue_success(username, "弹幕插队", Constants.CUTLINE_COST)
            else:
                # 可能的失败原因：插队服务未开启、用户已在插队队列中、名单中找不到或次数不足
                if not self.queue_manager.cutline_started:
                    self.log_widget.log_queue_failed(username, "插队服务未开启")
                elif username in self.queue_manager.user_cutline:
                    self.log_widget.log_queue_failed(username, "已在插队队列")
                else:
                    self.log_widget.log_queue_failed(username, "名单中找不到或次数不足")
                
        except Exception as e:
            self.log_widget.log_queue_failed(username, f"系统错误: {str(e)}")
    
    def handle_danmaku_message(self, message_data):
        """
        处理弹幕消息 - 兼容主窗口调用
        
        Args:
            message_data (dict): 弹幕消息数据
        """
        try:
            message_type = message_data.get('type', '')
            username = message_data.get('username', '')
            message_content = message_data.get('message', '')
            
            # 处理排队弹幕
            if '排队' in message_content:
                self.process_danmaku_queue(username)
            # 处理插队弹幕
            elif '插队' in message_content:
                self.process_danmaku_cutline(username)
            # 注意：排队工具2不处理上车弹幕
                
        except Exception as e:
            gui_logger.error("处理弹幕消息失败", str(e))
    
    def on_table_item_double_clicked(self, item):
        """处理表格项目双击事件"""
        if not item:
            return
        
        # 获取当前行和列
        row = item.row()
        column = item.column()
          # 只有点击名字列（第1列，索引为1）时才复制
        if column != 1:
            return
        
        # 获取用户名
        username = item.text()
        if not username:
            return
        
        # 判断是哪个表格
        table = item.tableWidget()
        table_type = "排队队列" if table == self.queue_table else "上车队列"
        
        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        clipboard.setText(username)
        
        # 显示Windows通知
        show_copy_notification(f"'{username}' 已复制到剪贴板")
        
        # 记录日志
        self.log_widget.log_system_event(f"已复制{table_type}用户名: {username}")
    
    def clear_table_selections(self):
        """清除所有表格的选择，避免滚轮操作时意外选中"""
        try:
            if hasattr(self, 'queue_table'):
                self.queue_table.clearSelection()
            if hasattr(self, 'boarding_table'):
                self.boarding_table.clearSelection()
        except Exception as e:
            gui_logger.error("清除表格选择时出错", str(e))

    def wheelEvent(self, event):
        """重写滚轮事件，滚动后清除选择"""
        super().wheelEvent(event)
        # 延迟清除选择，避免影响滚动
        QTimer.singleShot(100, self.clear_table_selections)

    # ==================== 随机选择功能 ====================
    
    def start_random_selection(self):
        """开始随机选择抽奖动画"""
        # 执行队列管理器的随机选择
        selected_indices, selected_names = self.queue_manager.random_select(1)
        if not selected_indices:
            QMessageBox.warning(self, "警告", "排队队列中至少需要1个人才能进行随机选择")
            return

        # 如果已经在动画中，直接返回
        if self.is_animating:
            return

        # 设置动画状态
        self.is_animating = True

        # 禁用随机按钮，防止重复点击
        self.random_select_btn.setEnabled(False)
        self.random_select_btn.setText("抽奖中...")

        # 重置选中的行
        self.random_selected_rows = []
        self.final_highlighted_rows = []

        # 启动抽奖动画线程（只用于展示动画，不执行实际抽奖）
        from utils.lottery_animation_single import SingleRandomSelectionAnimationThread
        self.animation_thread = SingleRandomSelectionAnimationThread(
            self.queue_manager.queue_list, 
            self.queue_manager.recent_winners
        )
        self.animation_thread.update_display.connect(self.update_lottery_display)
        def on_animation_done(_, __):
            self.on_lottery_finished(selected_indices, selected_names)
        self.animation_thread.animation_finished.connect(on_animation_done)
        self.animation_thread.start()
    
    def update_lottery_display(self, user1_name, user2_name, char):
        """更新抽奖显示文本"""
        try:
            # 只更新单个抽奖框显示
            display_text = f"{char} {user1_name}"
            # 如果文本过长，截断显示
            if len(display_text) > 20:
                display_text = f"{char} {user1_name[:12]}..."
            self.lottery_display_user1.setText(display_text)
            self.lottery_display_user1.setStyleSheet("""
                QLabel {
                    background-color: #fff3cd;
                    border: 2px solid #ffeaa7;
                    border-radius: 6px;
                    padding: 8px 15px;
                    font-size: 14px;
                    font-weight: normal;
                    color: #856404;
                    min-width: 200px;
                    max-width: 300px;
                    min-height: 35px;
                }
            """)
        except Exception as e:
            gui_logger.error("更新抽奖显示时出错", str(e))
    
    def on_lottery_finished(self, final_indices, final_names):
        """抽奖完成回调"""
        try:
            # 停止动画状态
            self.is_animating = False
            
            # 显示最终选中结果 - 只显示一个用户
            user_text = f"🏆 {final_names[0]}" if final_names else "🏆 无人中奖"
            if len(user_text) > 20:
                user_text = f"🏆 {final_names[0][:12]}..."
                
            self.lottery_display_user1.setText(user_text)
            self.lottery_display_user1.setStyleSheet("""
                QLabel {
                    background-color: #d4edda;
                    border: 2px solid #c3e6cb;
                    border-radius: 6px;
                    padding: 8px 15px;
                    font-size: 14px;
                    font-weight: bold;
                    color: #155724;
                    min-width: 200px;
                    max-width: 300px;
                    min-height: 35px;
                }
            """)
            
            # 记录日志
            if final_names:
                log_text = f"随机选择结果: {final_names[0]}"
                self.log_widget.log_system_event(log_text)
                gui_logger.debug("抽奖日志", log_text)
            
            # 移动到顶部并显示结果
            self.move_selected_to_top(final_indices)
            
            # 应用最终高亮效果
            self.apply_final_highlights()
            
            # 重置按钮，但保持抽奖结果显示
            self.reset_random_button()
            
            
        except Exception as e:
            gui_logger.error("移动和显示结果时出错", str(e))
            self.reset_random_button()

    def reset_lottery_display(self):
        """重置抽奖显示区域"""
        self.lottery_display_user1.setText("等待抽奖")
        self.lottery_display_user1.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                padding: 8px 15px;
                font-size: 14px;
                font-weight: normal;
                color: #495057;
                min-width: 200px;
                max-width: 300px;
                min-height: 35px;
            }
        """)
    
    def apply_final_highlights(self):
        """对移动到顶部的项目应用持续高亮效果"""
        try:
            # 高亮第一行（移动到顶部的随机选中项目）
            if self.queue_table.rowCount() > 0:
                self.highlight_table_row(0, "final")
                # 记录高亮的行，用于后续维护
                self.final_highlighted_rows = [0]
            else:
                self.final_highlighted_rows = []
            
            gui_logger.debug("已对置顶项目应用持续高亮效果")
            
        except Exception as e:
            gui_logger.error("应用最终高亮时出错", str(e))
    
    def move_selected_to_top(self, selected_indices):
        """将选中的项目移到队列顶部"""
        queue_list = self.queue_manager.queue_list
        if not queue_list or not selected_indices:
            return

        # 按倒序移动，避免索引混乱
        selected_indices.sort(reverse=True)
        selected_items = []

        # 从原位置移除选中的项目
        for index in selected_indices:
            if 0 <= index < len(queue_list):
                selected_items.append(queue_list.pop(index))

        # 将选中的项目插入到队列顶部（保持原有顺序）
        selected_items.reverse()  # 恢复正序
        for i, item in enumerate(selected_items):
            queue_list.insert(i, item)

        # 保存状态
        self.queue_manager.save_state()

        gui_logger.info("移动项目到队列顶部", f"已移动 {len(selected_items)} 个项目")
        
        # 确保选中的项目在可视范围内
        self.ensure_rows_visible(selected_indices)
        
        # 刷新队列表格
        self.update_queue_table()
        

    def ensure_rows_visible(self, selected_indices):
        """确保选中的行在可视范围内"""
        for index in selected_indices:
            if 0 <= index < self.queue_table.rowCount():
                self.queue_table.scrollToItem(self.queue_table.item(index, 0))

    def highlight_table_row(self, row, effect_type="normal"):
        """设置表格行的效果，只用于置顶项目的高亮"""
        try:
            # 设置文字单元格的效果
            for col in range(self.queue_table.columnCount() - 2):  # 排除按钮列
                item = self.queue_table.item(row, col)
                if item:
                    # 清除背景色
                    item.setBackground(QColor())
                    
                    if effect_type == "final":
                        # 置顶后的持续效果：只改变颜色，不加粗
                        font = QFont()
                        font.setBold(False)  # 不加粗
                        font.setPointSize(9)  # 使用正常字体大小
                        item.setFont(font)
                        item.setForeground(QColor(0, 100, 200))  # 蓝色文字
                        
                    else:
                        # 正常状态：恢复默认
                        font = QFont()
                        font.setBold(False)
                        font.setPointSize(9)
                        item.setFont(font)
                        item.setForeground(QColor(0, 0, 0))  # 黑色文字
            
        except Exception as e:
            gui_logger.error("设置行效果时出错", f"行 {row}: {str(e)}")
    
    def clear_all_highlights(self):
        """清除所有效果"""
        try:
            for row in range(self.queue_table.rowCount()):
                self.highlight_table_row(row, "normal")
        except Exception as e:
            gui_logger.error("清除所有效果时出错", str(e))
        
        self.random_selected_rows = []
        self.final_highlighted_rows = []
    
    def reset_random_button(self):
        """重置随机按钮状态"""
        self.random_select_btn.setEnabled(True)
        self.random_select_btn.setText("随机")
        self.is_animating = False
        
        # 停止动画线程
        if self.animation_thread and self.animation_thread.isRunning():
            self.animation_thread.stop()
            self.animation_thread.wait()
            self.animation_thread = None
    
    def reapply_final_highlights(self):
        """重新应用最终效果"""
        try:
            for row in self.final_highlighted_rows:
                if row < self.queue_table.rowCount():
                    self.highlight_table_row(row, "final")
        except Exception as e:
            gui_logger.error("重新应用最终效果时出错", str(e))
    
    def reapply_all_highlights(self):
        """重新应用所有效果"""
        # 重新应用最终效果
        for row in getattr(self, 'final_highlighted_rows', []):
            if row < self.queue_table.rowCount():
                self.highlight_table_row(row, "final")
        
        # 强制刷新表格视图
        self.queue_table.viewport().update()
