#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
登录对话框模块 - 处理B站登录界面
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from bilibili import QRLoginThread, LoginManager
from models import UserInfo
from config import Constants


class LoginDialog(QDialog):
    """B站登录对话框"""
    
    def __init__(self, parent=None):
        """
        初始化登录对话框
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self.setWindowTitle("B站登录")
        self.setFixedSize(*Constants.LOGIN_DIALOG_SIZE)
        self.setModal(True)
        
        # 设置窗口图标
        icon_path = Constants.get_icon_path(128)
        if icon_path:
            from PyQt6.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path))
        
        # 登录管理器
        self.login_manager = LoginManager()
        self.login_thread = None
        self.qr_key = None
        
        # 初始化UI
        self.init_ui()
        
        # 加载已保存的登录信息
        self.load_saved_login()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout()
        
        # 状态标签
        self.status_label = QLabel("点击下方按钮获取登录二维码")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 二维码显示区域
        self.qr_label = QLabel()
        self.qr_label.setMinimumSize(*Constants.QR_CODE_SIZE)
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setStyleSheet("border: 1px solid gray; background-color: white;")
        layout.addWidget(self.qr_label)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.get_qr_btn = QPushButton("获取二维码")
        self.get_qr_btn.clicked.connect(self.get_qr_code)
        button_layout.addWidget(self.get_qr_btn)
        
        self.refresh_btn = QPushButton("刷新状态")
        self.refresh_btn.clicked.connect(self.refresh_status)
        self.refresh_btn.setEnabled(False)
        button_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(button_layout)
        
        # 用户信息显示
        self.user_info_label = QLabel("未登录")
        self.user_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.user_info_label)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setEnabled(False)
        control_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        control_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(control_layout)
        self.setLayout(layout)
    
    def get_qr_code(self):
        """获取登录二维码"""
        try:
            # 获取二维码
            pixmap, qr_key = self.login_manager.get_qr_code()
            self.qr_key = qr_key
            
            # 缩放到合适大小并显示
            scaled_pixmap = pixmap.scaled(
                *Constants.QR_CODE_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.qr_label.setPixmap(scaled_pixmap)
            
            # 开始轮询登录状态
            self.start_login_polling()
            
            # 更新UI状态
            self.status_label.setText("请使用B站APP扫描二维码登录")
            self.get_qr_btn.setEnabled(False)
            self.refresh_btn.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
    
    def start_login_polling(self):
        """开始登录状态轮询"""
        if self.login_thread and self.login_thread.isRunning():
            self.login_thread.stop()
            self.login_thread.wait()
        
        if not self.qr_key:
            return
        
        self.login_thread = QRLoginThread(self.qr_key)
        self.login_thread.update_status.connect(self.update_status)
        self.login_thread.login_success.connect(self.on_login_success)
        self.login_thread.login_failed.connect(self.on_login_failed)
        self.login_thread.start()
    
    def update_status(self, status: str):
        """更新状态显示"""
        self.status_label.setText(status)
    
    def on_login_success(self, cookies: dict):
        """登录成功处理"""
        # 保存cookies
        if self.login_manager.save_cookies(cookies):
            # 更新用户信息显示
            user_info = self.login_manager.get_user_info()
            if user_info:
                self.user_info_label.setText(f"已登录: {user_info}")
                self.status_label.setText("登录成功！")
                self.ok_btn.setEnabled(True)
            
            # 重置UI状态
            self.get_qr_btn.setEnabled(True)
            self.refresh_btn.setEnabled(False)
            
            if self.login_thread:
                self.login_thread.stop()
        else:
            QMessageBox.warning(self, "警告", "保存登录信息失败")
    
    def on_login_failed(self, error: str):
        """登录失败处理"""
        self.status_label.setText(f"登录失败: {error}")
        self.get_qr_btn.setEnabled(True)
        self.refresh_btn.setEnabled(False)
        
        if self.login_thread:
            self.login_thread.stop()
    
    def refresh_status(self):
        """刷新登录状态"""
        if self.qr_key:
            self.start_login_polling()
    
    def load_saved_login(self):
        """加载已保存的登录信息"""
        if self.login_manager.is_logged_in():
            user_info = self.login_manager.get_user_info()
            if user_info:
                self.user_info_label.setText(f"已登录: {user_info}")
                self.status_label.setText("使用保存的登录信息")
                self.ok_btn.setEnabled(True)
    
    def get_cookies(self):
        """获取当前cookies"""
        return self.login_manager.get_cookies()
    
    def get_user_info(self) -> UserInfo:
        """获取当前用户信息"""
        return self.login_manager.get_user_info()
    
    def closeEvent(self, event):
        """关闭事件处理"""
        if self.login_thread and self.login_thread.isRunning():
            self.login_thread.stop()
            self.login_thread.wait()
        event.accept()
