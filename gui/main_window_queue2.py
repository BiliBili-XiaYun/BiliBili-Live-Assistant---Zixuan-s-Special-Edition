#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口模块 - B站弹幕监控主界面 (排队工具2专用版)
直接复制原版代码，只去除上车相关功能
"""

import os
import platform
import threading
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QTextEdit, QLineEdit, 
                             QMessageBox, QDialog, QFrame, QGroupBox, QApplication,
                             QTableWidget, QTableWidgetItem)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor

# 导入通知相关模块
try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    # gui_logger 在后面导入，这里先不使用

from bilibili import DanmakuMonitorThread, LoginManager
from gui.login_dialog import LoginDialog
from gui.queue_window_queue2 import Queue2ManagerWindow
from gui.name_list_editor import NameListEditor
from queue_manager.manager_queue2 import QueueManager
from utils import extract_room_id, is_test_mode_input, gui_logger
from config import Constants, app_config

# 现在可以使用gui_logger了
if not PLYER_AVAILABLE:
    gui_logger.warning("plyer库未安装，将使用备用通知方式")


class MainWindowQueue2(QMainWindow):
    """B站弹幕监控主窗口 - 排队工具2专用版本"""
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        # 登录管理器
        self.login_manager = LoginManager()
        
        # 队列管理器 - 独立于排队窗口，用于处理舰长礼物等事件
        self.queue_manager = QueueManager()
        
        # 监控线程
        self.monitor_thread = None
        # 子窗口
        self.queue_window = None
        self.name_list_editor = None
        # 测试模式相关
        self.is_test_mode = False
        
        # 新舰长数据
        self.new_guard_data = []
        self.guard_csv_path = None
        self.last_guard_file_mtime = 0
        
        # 初始化UI
        self.init_ui()
        
        # 自动填入房号13355
        self.room_input.setText("13355")        
        # 加载保存的登录信息
        self.load_saved_login()
    
    def init_ui(self):
        """初始化用户界面"""
        # 直接从 version_info 导入应用名称，避免使用 property
        from version_info import APP_NAME
        self.setWindowTitle(f"{APP_NAME} - 排队工具2 (bilibili-api)")
        self.setGeometry(100, 100, *Constants.MAIN_WINDOW_SIZE)
        
        # 设置窗口图标
        icon_path = Constants.get_icon_path(128)
        if icon_path:
            from PyQt6.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path))
        
        # 设置样式
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
        """)
        
        # 中央组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 顶部控制区域
        control_group = QGroupBox("用户控制")
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)
        
        # 登录按钮
        self.login_btn = QPushButton("🔑 登录B站")
        self.login_btn.clicked.connect(self.show_login_dialog)
        self.login_btn.setMinimumHeight(40)
        control_layout.addWidget(self.login_btn)
        
        # 用户信息显示
        self.user_label = QLabel("📱 未登录")
        self.user_label.setStyleSheet("color: #666; font-weight: bold;")
        control_layout.addWidget(self.user_label)
        
        control_layout.addStretch()
        
        # 名单编辑按钮
        self.name_list_btn = QPushButton("📝 名单编辑")
        self.name_list_btn.clicked.connect(self.show_name_list_editor)
        self.name_list_btn.setStyleSheet("background-color: #2196F3;")
        self.name_list_btn.setMinimumHeight(40)
        control_layout.addWidget(self.name_list_btn)
        
        # 排队按钮 - 标记为排队工具2
        self.queue_btn = QPushButton("🎯 排队工具2")
        self.queue_btn.clicked.connect(self.show_queue_window)
        self.queue_btn.setStyleSheet("background-color: #FF5722;")  # 使用不同颜色区分
        self.queue_btn.setMinimumHeight(40)
        control_layout.addWidget(self.queue_btn)
        
        # 设置按钮
        self.settings_btn = QPushButton("⚙️ 设置")
        self.settings_btn.clicked.connect(self.show_settings_dialog)
        self.settings_btn.setStyleSheet("background-color: #9C27B0;")
        self.settings_btn.setMinimumHeight(40)
        control_layout.addWidget(self.settings_btn)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # 直播间连接区域
        room_group = QGroupBox("直播间连接")
        room_layout = QVBoxLayout()
        
        # 输入行
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("📺 直播间地址/房间号:"))
        
        self.room_input = QLineEdit()
        self.room_input.setPlaceholderText("输入直播间URL或房间号，如：https://live.bilibili.com/12345 或 12345")
        self.room_input.setMinimumHeight(35)
        input_layout.addWidget(self.room_input)
        
        room_layout.addLayout(input_layout)
        
        # 按钮行
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.connect_btn = QPushButton("🔗 连接")
        self.connect_btn.clicked.connect(self.connect_to_room)
        self.connect_btn.setMinimumHeight(40)
        self.connect_btn.setMinimumWidth(100)
        button_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QPushButton("❌ 断开")
        self.disconnect_btn.clicked.connect(self.disconnect_from_room)
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.setStyleSheet("background-color: #f44336;")
        self.disconnect_btn.setMinimumHeight(40)
        self.disconnect_btn.setMinimumWidth(100)
        button_layout.addWidget(self.disconnect_btn)
        
        room_layout.addLayout(button_layout)
        room_group.setLayout(room_layout)
        layout.addWidget(room_group)
        
        # 状态显示
        status_group = QGroupBox("连接状态")
        status_layout = QVBoxLayout()
        self.status_label = QLabel("📡 请登录并输入直播间地址")
        self.status_label.setStyleSheet("color: #666; font-size: 14px; padding: 10px;")
        status_layout.addWidget(self.status_label)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        # 弹幕显示区域
        danmaku_group = QGroupBox("弹幕监控")
        danmaku_layout = QVBoxLayout()
        
        # 创建水平分割器，实现7:3布局
        from PyQt6.QtWidgets import QSplitter, QTableWidget, QTableWidgetItem
        from PyQt6.QtCore import QTimer
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 弹幕显示区域（左侧，70%）
        self.danmaku_display = QTextEdit()
        self.danmaku_display.setReadOnly(True)
        self.danmaku_display.setPlaceholderText("💬 弹幕消息将在这里显示...")
        self.danmaku_display.setMinimumHeight(300)
        splitter.addWidget(self.danmaku_display)
        
        # 新舰长显示区域（右侧，30%）
        new_guard_widget = self.create_new_guard_widget()
        splitter.addWidget(new_guard_widget)
        
        # 设置分割器比例 (弹幕:新舰长 = 70:30)
        splitter.setSizes([700, 300])
        
        danmaku_layout.addWidget(splitter)
        danmaku_group.setLayout(danmaku_layout)
        layout.addWidget(danmaku_group)
        
        central_widget.setLayout(layout)
    
    def show_login_dialog(self):
        """显示登录对话框"""
        dialog = LoginDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:            
            self.update_user_info()
    
    def show_queue_window(self):
        """显示排队管理窗口"""
        # 使用排队工具2专用窗口
        if self.queue_window is None:
            # 传递主窗口的队列管理器给排队窗口，但不设置父窗口以便独立显示在任务栏
            self.queue_window = Queue2ManagerWindow(None, self.queue_manager)
            # 新创建的排队窗口，需要从配置同步路径
            self.sync_file_path_from_config()
        
        self.queue_window.show()
        self.queue_window.raise_()
        self.queue_window.activateWindow()

    def show_settings_dialog(self):
        """显示设置对话框"""
        from gui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self.on_settings_changed)
        dialog.exec()
    
    def on_settings_changed(self):
        """处理设置变更"""
        gui_logger.info("设置已更新，正在应用变更...")
        # 这里可以根据需要重新加载配置或更新UI
        # 例如更新文件监控间隔等

    def show_name_list_editor(self):
        """显示名单编辑器"""
        if self.name_list_editor is None:
            # 直接从配置文件读取当前路径
            from config import app_config
            current_file = app_config.get("queue.name_list_file", "")
            if current_file:
                gui_logger.debug("从配置文件获取文件路径", current_file)
            else:
                gui_logger.warning("配置文件中未设置名单路径")
            
            self.name_list_editor = NameListEditor(self, current_file)
            
        # 只连接名单变更信号
        try:
            # 先断开可能存在的连接
            self.name_list_editor.name_list_changed.disconnect()
        except:
            pass
        # 重新连接信号
        self.name_list_editor.name_list_changed.connect(self.on_name_list_changed)
        gui_logger.debug("已连接名单编辑器信号")
        
        self.name_list_editor.show()
        self.name_list_editor.raise_()
        self.name_list_editor.activateWindow()
    def load_saved_login(self):
        """加载保存的登录信息"""
        self.update_user_info()
        
        # 如果已经登录，自动连接到房号13355
        if self.login_manager.is_logged_in():
            gui_logger.info("检测到已登录状态，自动连接到房号13355")
            # 使用QTimer延迟连接，确保UI完全加载
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(500, self.auto_connect_to_room)
    
    def update_user_info(self):
        """更新用户信息显示"""
        if self.login_manager.is_logged_in():
            user_info = self.login_manager.get_user_info()
            if user_info:
                self.user_label.setText(f"✅ 已登录: {user_info}")
                self.user_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
                self.login_btn.setText("🔑 重新登录")
        else:
            self.user_label.setText("❌ 未登录")
            self.user_label.setStyleSheet("color: #f44336; font-weight: bold;")
            self.login_btn.setText("🔑 登录B站")
    
    def connect_to_room(self):
        """连接到直播间"""
        room_input = self.room_input.text().strip()
        if not room_input:
            QMessageBox.warning(self, "错误", 
                              "请输入直播间地址或房间号，或输入 'test' 进入测试模式")
            return
        
        # 检查是否为测试模式
        if is_test_mode_input(room_input):
            self.start_test_mode()
            return
        
        try:
            room_id = extract_room_id(room_input)
            gui_logger.debug("提取到房间ID", str(room_id))
        except ValueError as e:
            QMessageBox.warning(self, "错误", str(e))
            return
        
        # 断开之前的连接
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.disconnect_from_room()
        
        # 获取登录cookies
        cookies = self.login_manager.get_cookies()
        
        # 创建新的监控线程
        self.monitor_thread = DanmakuMonitorThread(room_id, cookies)
        self.monitor_thread.message_received.connect(self.on_message_received)
        self.monitor_thread.status_changed.connect(self.on_status_changed)
        self.monitor_thread.error_occurred.connect(self.on_error_occurred)
        
        # 启动监控
        gui_logger.operation_start("启动弹幕监控线程")
        self.monitor_thread.start()
        
        # 更新UI状态
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.room_input.setEnabled(False)
        
        self.is_test_mode = False
    
    def start_test_mode(self):
        """启动测试模式"""
        self.is_test_mode = True
        self.status_label.setText("测试模式 - 可手动发送测试弹幕")
        self.danmaku_display.append(
            "[测试模式] 已进入测试模式，您可以在排队管理窗口中测试功能"
        )
        
        # 更新UI状态
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.room_input.setEnabled(False)
        
        gui_logger.info("已进入测试模式")
    
    def disconnect_from_room(self):
        """断开直播间连接"""
        if self.monitor_thread and self.monitor_thread.isRunning():
            gui_logger.operation_start("断开直播间连接")
            self.monitor_thread.stop_monitoring()
            self.monitor_thread.quit()
            self.monitor_thread.wait(Constants.MONITOR_STOP_TIMEOUT * 1000)  # 等待最多5秒
            
            if self.monitor_thread.isRunning():
                gui_logger.warning("强制终止监控线程")
                self.monitor_thread.terminate()
                self.monitor_thread.wait()
        
        # 重置UI状态
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.room_input.setEnabled(True)
        self.status_label.setText("已断开连接")
        self.is_test_mode = False
    
    def on_message_received(self, message_info: dict):
        """
        处理接收到的消息 - 去除上车相关逻辑
        
        Args:
            message_info (dict): 消息信息字典
        """
        try:
            message_type = message_info.get('type', 'unknown')
            timestamp = message_info.get('timestamp', '')
            username = message_info.get('username', '未知用户')            
            # 检查是否为排队弹幕（关键词匹配）
            if (message_type == Constants.MESSAGE_TYPE_DANMAKU and 
                Constants.QUEUE_KEYWORD in message_info.get('message', '')):
                if self.queue_window:
                    self.queue_window.process_danmaku_queue(username)
            
            # 检查是否为插队弹幕（关键词匹配）
            elif (message_type == Constants.MESSAGE_TYPE_DANMAKU and 
                  Constants.CUTLINE_KEYWORD in message_info.get('message', '')):
                if self.queue_window:
                    self.queue_window.process_danmaku_cutline(username)
            
            # 注意：这里移除了上车弹幕的处理逻辑
            # 删除了以下代码：
            # elif (message_type == Constants.MESSAGE_TYPE_DANMAKU and 
            #       Constants.BOARDING_KEYWORD in message_info.get('message', '')):
            #     if self.queue_window:
            #         self.queue_window.process_danmaku_boarding(username)
            
            # 处理舰长礼物事件
            elif message_type == Constants.MESSAGE_TYPE_GUARD:
                guard_level = message_info.get('guard_level', 0)
                guard_months = message_info.get('num', 1)  # 购买的月份数量
                if guard_level > 0:
                    # 使用主窗口的队列管理器处理舰长礼物，传递月份数量
                    success = self.queue_manager.process_guard_gift(username, guard_level, guard_months)
                    if success:
                        # 刷新主窗口的新舰长显示
                        self.refresh_new_guard_data()
                        
                        # 如果排队窗口打开，触发其文件检查和UI刷新
                        if self.queue_window:
                            # 更新排队窗口的文件修改时间，这样它会在下次检查时发现变化
                            self.queue_window.update_name_list_file_mtime()
                            # 直接触发文件检查，确保立即刷新
                            from PyQt6.QtCore import QTimer
                            QTimer.singleShot(500, self.queue_window.check_name_list_file_changes)
                        
                        # 在弹幕显示中添加特殊标记
                        guard_name = Constants.GUARD_LEVEL_NAMES.get(guard_level, f"等级{guard_level}")
                        guard_rewards = app_config.get("gift_monitor.guard_rewards", {})
                        reward_count = guard_rewards.get(guard_name, 0)
                        total_reward = reward_count * guard_months  # 总奖励次数 = 单次奖励 × 月份数
                        
                        month_text = f"{guard_months}个月" if guard_months > 1 else ""
                        special_msg = f"🎖️ <font color='#FFD700'><b>{username} 开通了{guard_months}个月{guard_name}，已自动获得 {total_reward} 次排队机会！</b></font>"
                        self.danmaku_display.append(special_msg)
            
            # 格式化并显示消息
            formatted_msg = self.format_message(message_info)
            if formatted_msg:
                self.danmaku_display.append(formatted_msg)
                
                # 自动滚动到底部
                scrollbar = self.danmaku_display.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
            
        except Exception as e:
            gui_logger.error("处理消息异常", str(e))
    
    def format_message(self, message_info: dict) -> str:
        """
        格式化消息显示
        
        Args:
            message_info (dict): 消息信息
            
        Returns:
            str: 格式化后的消息字符串
        """
        message_type = message_info.get('type', 'unknown')
        timestamp = message_info.get('timestamp', '')
        username = message_info.get('username', '未知用户')
        
        if message_type == Constants.MESSAGE_TYPE_DANMAKU:
            message = message_info.get('message', '')
            color = message_info.get('color', Constants.COLOR_DANMAKU)
            return f"[{timestamp}] <font color='{color}'>{username}: {message}</font>"
            
        elif message_type == Constants.MESSAGE_TYPE_GIFT:
            gift_name = message_info.get('gift_name', '未知礼物')
            num = message_info.get('num', 1)
            return f"[{timestamp}] <font color='{Constants.COLOR_GIFT}'>[礼物] {username} 送出 {gift_name} x{num}</font>"
            
        elif message_type == Constants.MESSAGE_TYPE_GUARD:
            guard_level = message_info.get('guard_level', 0)
            guard_months = message_info.get('num', 1)  # 购买月份数
            guard_name = Constants.GUARD_LEVEL_NAMES.get(guard_level, f'舰长Lv{guard_level}')
            month_text = f"{guard_months}个月" if guard_months > 1 else ""
            return f"[{timestamp}] <font color='{Constants.COLOR_GUARD}'>[舰长] {username} 购买了 {month_text}{guard_name}</font>"
            
        elif message_type == Constants.MESSAGE_TYPE_SUPER_CHAT:
            message = message_info.get('message', '')
            price = message_info.get('price', 0)
            return f"[{timestamp}] <font color='{Constants.COLOR_SUPER_CHAT}'>[醒目留言] {username} (¥{price}): {message}</font>"
        
        return ""
    
    def on_status_changed(self, status: str):
        """状态变化处理"""
        self.status_label.setText(status)
        gui_logger.debug("状态更新", status)
    
    def on_error_occurred(self, error: str):
        """错误处理"""
        self.status_label.setText(f"错误: {error}")
        gui_logger.error("发生错误", error)
        QMessageBox.critical(self, "错误", error)
        
        # 重置UI状态        
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.room_input.setEnabled(True)
        self.is_test_mode = False
    
    def on_name_list_changed(self):
        """名单变更处理 - 自动重载，只有失败时才提示"""
        # 如果排队窗口存在，自动重新加载名单
        if self.queue_window:
            try:
                success = self.queue_window.reload_name_list()
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
    
    def sync_file_path_from_config(self):
        """从配置文件同步文件路径到排队管理器"""
        if self.queue_window:
            # 让排队管理器从配置重新加载路径和数据
            success = self.queue_window.queue_manager.refresh_name_list_from_config()
            
            # 刷新排队窗口UI
            self.queue_window.refresh_ui()
            
            if success:
                gui_logger.operation_complete("从配置文件同步文件路径并重新加载名单", "成功")
            else:                
                gui_logger.warning("配置文件同步成功，但名单加载失败")
    
    def closeEvent(self, event):
        """关闭事件处理"""
        # 断开监控连接
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.disconnect_from_room()
        
        # 保存队列管理器状态
        if hasattr(self, 'queue_manager'):
            self.queue_manager.save_state()
            gui_logger.info("主窗口关闭: 已保存队列管理器状态")
        
        # 关闭子窗口
        if self.queue_window:
            self.queue_window.close()
        
        event.accept()

    def auto_connect_to_room(self):
        """自动连接到房号13355"""
        try:
            # 检查房间号是否已经填入
            if self.room_input.text().strip() == "13355":
                # 直接调用连接方法
                self.connect_to_room()
                gui_logger.operation_complete("自动连接到房号13355", "成功")
            else:
                # 确保房间号为13355
                self.room_input.setText("13355")
                # 调用连接方法
                self.connect_to_room()
                gui_logger.operation_complete("自动设置房号13355并连接", "成功")
        except Exception as e:
            gui_logger.error("自动连接到房号13355失败", str(e))
    
    def create_new_guard_widget(self):
        """创建新舰长显示组件"""
        from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget
        from PyQt6.QtCore import QTimer
        from PyQt6.QtGui import QFont
        
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 标题区域
        title_layout = QHBoxLayout()
        title_label = QLabel("今日新舰长")
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        # 刷新按钮
        self.refresh_guard_btn = QPushButton("刷新")
        self.refresh_guard_btn.clicked.connect(self.refresh_new_guard_data)
        self.refresh_guard_btn.setMaximumWidth(80)
        self.refresh_guard_btn.setMaximumHeight(25)
        title_layout.addWidget(self.refresh_guard_btn)
        
        layout.addLayout(title_layout)
        # 统计信息
        self.new_guard_stats_label = QLabel("加载中...")
        self.new_guard_stats_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.new_guard_stats_label)
        
        # 新舰长列表
        self.new_guard_table = QTableWidget()
        self.new_guard_table.setColumnCount(1)
        self.new_guard_table.setHorizontalHeaderLabels(["新舰长名单"])        # 设置表格属性
        header = self.new_guard_table.horizontalHeader()
        header.setStretchLastSection(True)
        self.new_guard_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.new_guard_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.new_guard_table.setAlternatingRowColors(True)
        self.new_guard_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.new_guard_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # 设置表格样式，修复选中时文字看不清的问题
        self.new_guard_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
                alternate-background-color: #f5f5f5;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 8px;
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
        
        # 连接双击事件
        self.new_guard_table.itemDoubleClicked.connect(self.on_new_guard_item_double_clicked)
        
        layout.addWidget(self.new_guard_table)
        
        # 文件信息显示
        self.guard_file_label = QLabel("文件: 未找到")
        self.guard_file_label.setWordWrap(True)
        self.guard_file_label.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(self.guard_file_label)
        
        widget.setLayout(layout)
        
        # 初始化文件监控定时器
        self.guard_file_timer = QTimer()
        self.guard_file_timer.timeout.connect(self.check_guard_file_update)
        self.guard_file_timer.start(5000)  # 每5秒检查一次文件更新        
        # 初始加载数据
        self.refresh_new_guard_data()
        
        return widget
    
    def find_latest_guard_csv(self):
        """查找最新的新舰长CSV文件"""
        import glob
        
        try:
            # 查找上级目录中的日期格式CSV文件
            current_dir = os.path.dirname(os.path.abspath(__file__))  # gui目录
            project_dir = os.path.dirname(current_dir)  # 项目根目录
            parent_dir = os.path.dirname(project_dir)  # 上级目录
            
            # 尝试多种文件名模式
            patterns = [
                os.path.join(parent_dir, "*-新舰长.csv"),
                os.path.join(parent_dir, "20??-??-??-新舰长.csv"),
                os.path.join(parent_dir, "20??-??-??*.csv"),
            ]
            
            csv_files = []
            for pattern in patterns:
                csv_files.extend(glob.glob(pattern))
            
            if csv_files:
                # 去重并按文件修改时间排序，返回最新的
                csv_files = list(set(csv_files))
                latest_file = max(csv_files, key=os.path.getmtime)
                return latest_file
            
            return None
            
        except Exception as e:
            gui_logger.error("查找新舰长CSV文件失败", str(e))
            return None
    
    def load_new_guard_data(self):
        """加载新舰长数据（不解析，直接显示原始内容）"""
        try:
            csv_path = self.find_latest_guard_csv()
            if not csv_path or not os.path.exists(csv_path):
                self.new_guard_data = []
                self.guard_csv_path = None
                return False
            
            self.guard_csv_path = csv_path
            self.new_guard_data = []
            
            # 读取CSV文件，直接显示原始内容
            import csv
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for i, row in enumerate(reader):
                    if i == 0 and row and row[0] == "用户名":
                        continue  # 跳过标题行
                    if row and row[0].strip():
                        original_text = row[0].strip()
                        if original_text:  # 确保内容不为空
                            self.new_guard_data.append(original_text)
            
            return True
            
        except Exception as e:
            print(f"加载新舰长数据失败: {e}")
            self.new_guard_data = []
            return False
    
    def update_new_guard_table(self):
        """更新新舰长表格显示"""
        try:
            if not hasattr(self, 'new_guard_table'):
                return
                
            self.new_guard_table.setRowCount(len(self.new_guard_data))
            
            for i, guard_text in enumerate(self.new_guard_data):
                # 直接显示原始文本，不设置颜色
                from PyQt6.QtWidgets import QTableWidgetItem
                
                item = QTableWidgetItem(guard_text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                self.new_guard_table.setItem(i, 0, item)
            
            # 更新统计信息
            total_count = len(self.new_guard_data)
            level_counts = {"总督": 0, "提督": 0, "舰长": 0}
            
            for guard_text in self.new_guard_data:
                if "总督" in guard_text:
                    level_counts["总督"] += 1
                elif "提督" in guard_text:
                    level_counts["提督"] += 1
                else:
                    level_counts["舰长"] += 1
            
            stats_text = f"共 {total_count} 人"
            if total_count > 0:
                details = []
                for level, count in level_counts.items():
                    if count > 0:
                        details.append(f"{level}: {count}")
                if details:
                    stats_text += f" ({', '.join(details)})"
            
            self.new_guard_stats_label.setText(stats_text)
            
            # 更新文件路径显示
            if self.guard_csv_path:
                filename = os.path.basename(self.guard_csv_path)
                self.guard_file_label.setText(f"文件: {filename}")
            else:                
                self.guard_file_label.setText("文件: 未找到")
                
        except Exception as e:
            print(f"更新新舰长表格失败: {e}")
    
    def refresh_new_guard_data(self):
        """刷新新舰长数据"""
        try:
            if self.load_new_guard_data():
                self.update_new_guard_table()
                self.last_guard_file_mtime = os.path.getmtime(self.guard_csv_path) if self.guard_csv_path else 0
                gui_logger.operation_complete("新舰长数据刷新", "成功")
            else:
                print("主窗口: 新舰长数据刷新失败")
        except Exception as e:
            print(f"主窗口: 刷新新舰长数据失败: {e}")
    
    def check_guard_file_update(self):
        """检查新舰长文件是否有更新"""
        try:
            current_file = self.find_latest_guard_csv()
            
            # 检查是否有新文件或文件是否更新
            if current_file and current_file != self.guard_csv_path:
                gui_logger.info("检测到新的舰长文件", current_file)
                self.refresh_new_guard_data()
            elif current_file and os.path.exists(current_file):
                current_mtime = os.path.getmtime(current_file)
                if current_mtime > self.last_guard_file_mtime:
                    gui_logger.info("检测到舰长文件更新", current_file)
                    self.refresh_new_guard_data()
                    
        except Exception as e:
            print(f"主窗口: 检查舰长文件更新失败: {e}")

    def on_new_guard_item_double_clicked(self, item):
        """处理新舰长列表双击事件"""
        if item:
            text = item.text()
            # 复制到剪贴板
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            
            # 显示通知
            self.show_copy_notification(text)
            gui_logger.info("已复制新舰长", text)
    
    def show_copy_notification(self, text):
        """显示复制通知"""
        try:
            def show_notification():
                # 获取ICO格式图标路径（用于通知）
                from config import Constants
                icon_path = Constants.get_icon_path(256)  # 使用256px ICO图标
                
                notification.notify(
                    title="子轩专属排队工具",
                    message=text,
                    app_name="子轩专属排队工具",
                    app_icon=icon_path if icon_path else "",  # 如果图标不存在则不设置
                    timeout=2,  # 3秒后消失
                    ticker="复制通知",
                    toast=True  # 在Windows上使用Toast通知
                )
            
            # 在后台线程中显示通知，避免阻塞UI
            thread = threading.Thread(target=show_notification, daemon=True)
            thread.start()
        except Exception as e:
            print(f"通知显示失败: {e}")
            # 备用方案：控制台输出
            print(f"复制成功: {text}")
