#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动添加对话框模块 - 处理手动添加选择界面，支持排队和上车，支持模糊检索
"""

from typing import List, Optional
import re

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QCheckBox, QGroupBox, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from models import QueueItem
from config import Constants


class ManualAddQueueDialog(QDialog):
    """手动添加对话框"""
    
    def __init__(self, name_list: List[QueueItem], parent=None):
        """
        初始化手动添加对话框
        
        Args:
            name_list (List[QueueItem]): 可选择的名单项目列表
            parent: 父窗口
        """
        super().__init__(parent)
        self.setWindowTitle("手动添加")
        self.setFixedSize(600, 550)
        self.setModal(True)
        
        # 设置窗口图标
        icon_path = Constants.get_icon_path(128)
        if icon_path:
            from PyQt6.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path))
        
        self.name_list = name_list
        self.selected_item = None
        self.fuzzy_search_enabled = True
        self.add_type = "queue"  # "queue", "cutline" 或 "boarding"
        
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout()
          # 标题说明
        title_label = QLabel("手动添加")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        description_label = QLabel("当弹幕用户名与本地存储不一致时，可手动搜索并添加到排队或上车列表")
        description_label.setWordWrap(True)
        layout.addWidget(description_label)
        
        # 添加类型选择组
        type_group = QGroupBox("添加类型")
        type_layout = QHBoxLayout()
        
        self.queue_radio = QCheckBox("排队")
        self.queue_radio.setChecked(True)
        self.queue_radio.toggled.connect(self.on_type_changed)
        type_layout.addWidget(self.queue_radio)
        
        self.cutline_radio = QCheckBox("插队")
        self.cutline_radio.setChecked(False)
        self.cutline_radio.toggled.connect(self.on_type_changed)
        type_layout.addWidget(self.cutline_radio)
        
        self.boarding_radio = QCheckBox("上车")
        self.boarding_radio.setChecked(False)
        self.boarding_radio.toggled.connect(self.on_type_changed)
        type_layout.addWidget(self.boarding_radio)
        
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # 搜索选项组
        search_group = QGroupBox("搜索选项")
        search_layout = QVBoxLayout()
          # 模糊搜索选项
        self.fuzzy_search_cb = QCheckBox("启用模糊搜索")
        self.fuzzy_search_cb.setChecked(True)
        self.fuzzy_search_cb.toggled.connect(self.on_search_mode_changed)
        search_layout.addWidget(self.fuzzy_search_cb)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
          # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入名字或部分文字进行搜索...")
        self.search_input.textChanged.connect(self.filter_names)
        layout.addWidget(QLabel("搜索名字:"))
        layout.addWidget(self.search_input)
        
        # 匹配结果列表
        self.result_list = QListWidget()
        self.result_list.itemClicked.connect(self.on_item_clicked)
        self.result_list.itemDoubleClicked.connect(self.on_item_selected)
        layout.addWidget(QLabel("匹配结果:"))
        layout.addWidget(self.result_list)
        
        # 选中项目信息
        self.selected_info_label = QLabel("请选择一个项目")
        layout.addWidget(self.selected_info_label)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.ok_btn = QPushButton("添加到排队")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setEnabled(False)
        button_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # 初始化显示所有名字
        self.filter_names("")
        
    def on_search_mode_changed(self, enabled: bool):
        """搜索模式改变处理"""
        self.fuzzy_search_enabled = enabled
        current_text = self.search_input.text()
        if current_text:
            self.filter_names(current_text)
            
        # 更新搜索框提示文字
        if enabled:
            self.search_input.setPlaceholderText("输入名字或部分文字进行搜索...")
        else:
            self.search_input.setPlaceholderText("输入完整名字进行精确搜索...")
    
    def fuzzy_match(self, search_text: str, target_name: str) -> bool:
        """
        模糊匹配算法
        
        Args:
            search_text: 搜索文本
            target_name: 目标名字
            
        Returns:
            bool: 是否匹配
        """
        search_lower = search_text.lower().strip()
        target_lower = target_name.lower()
        
        # 1. 直接包含匹配
        if search_lower in target_lower:
            return True
        
        # 2. 字符顺序匹配（不要求连续）
        search_index = 0
        for char in target_lower:
            if search_index < len(search_lower) and char == search_lower[search_index]:
                search_index += 1
                if search_index == len(search_lower):
                    return True
        
        # 3. 正则模糊匹配（容错）
        try:
            # 将搜索文本转换为模糊匹配的正则表达式
            pattern = '.*'.join(re.escape(char) for char in search_lower)
            return bool(re.search(pattern, target_lower))
        except:
            return False
    
    def filter_names(self, text: str):
        """
        过滤名字列表
        
        Args:
            text (str): 搜索文本
        """
        self.result_list.clear()
        search_text = text.strip()
        
        matched_items = []
        
        for item in self.name_list:
            # 只显示有次数的项目
            if item.count <= 0:
                continue
                
            is_match = False
            
            if not search_text:  # 空搜索显示所有
                is_match = True
            elif self.fuzzy_search_enabled:
                is_match = self.fuzzy_match(search_text, item.name)
            else:  # 精确搜索
                is_match = search_text.lower() in item.name.lower()
            
            if is_match:
                matched_items.append(item)
        
        # 按名字排序
        matched_items.sort(key=lambda x: x.name)
        
        # 添加到列表
        for item in matched_items:
            display_text = f"{item.name} (序号:{item.index}, 次数:{item.count})"
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.result_list.addItem(list_item)
          # 如果没有搜索结果，显示提示
        if self.result_list.count() == 0 and search_text:
            hint_text = "没有找到匹配的名字" if not self.fuzzy_search_enabled else "没有找到匹配的名字（已启用模糊搜索）"
            hint_item = QListWidgetItem(hint_text)
            hint_item.setFlags(Qt.ItemFlag.NoItemFlags)  # 禁用选择
            self.result_list.addItem(hint_item)
        
        # 更新统计信息
        total_available = len([item for item in self.name_list if item.count > 0])
        status_text = f"显示 {len(matched_items)} / {total_available} 个可用项目"
        self.selected_info_label.setText(status_text)
    
    def on_item_clicked(self, item: QListWidgetItem):
        """
        点击项目处理
        
        Args:
            item (QListWidgetItem): 点击的列表项
        """
        queue_item = item.data(Qt.ItemDataRole.UserRole)
        if queue_item is not None:  # 确保不是提示项
            self.selected_item = queue_item
            self.ok_btn.setEnabled(True)
            
            # 更新选中项目信息
            info_text = f"已选择: {queue_item.name} (序号:{queue_item.index}, 剩余次数:{queue_item.count})"
            self.selected_info_label.setText(info_text)
        else:
            self.selected_item = None
            self.ok_btn.setEnabled(False)
    
    def on_item_selected(self, item: QListWidgetItem):
        """
        双击选择项目处理
        
        Args:
            item (QListWidgetItem): 选中的列表项
        """
        queue_item = item.data(Qt.ItemDataRole.UserRole)
        if queue_item is not None:  # 确保不是提示项
            self.selected_item = queue_item
            self.ok_btn.setEnabled(True)
            self.accept()
    
    def get_selected_item(self) -> Optional[QueueItem]:
        """
        获取选中的项目
        
        Returns:
            Optional[QueueItem]: 选中的项目，如果没有选择则返回None
        """
        return self.selected_item
    
    def accept(self):
        """确认选择"""
        if self.selected_item is None:
            QMessageBox.warning(self, "未选择", "请先选择要添加到排队的项目")
            return
        
        if self.selected_item.count <= 0:
            QMessageBox.warning(self, "次数不足", f"{self.selected_item.name} 的剩余次数为 0，无法添加到排队")
            return
        
        super().accept()
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        # 支持回车键确认选择
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            current_item = self.result_list.currentItem()
            if current_item and current_item.data(Qt.ItemDataRole.UserRole) is not None:
                self.on_item_selected(current_item)
                return
        
        # 支持ESC键取消
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        
        super().keyPressEvent(event)
    
    def on_type_changed(self):
        """添加类型变化处理"""
        # 确保只有一个复选框被选中
        sender = self.sender()
        
        # 先清除所有选择
        if sender == self.queue_radio and self.queue_radio.isChecked():
            self.cutline_radio.setChecked(False)
            self.boarding_radio.setChecked(False)
            self.add_type = "queue"
        elif sender == self.cutline_radio and self.cutline_radio.isChecked():
            self.queue_radio.setChecked(False)
            self.boarding_radio.setChecked(False)
            self.add_type = "cutline"
        elif sender == self.boarding_radio and self.boarding_radio.isChecked():
            self.queue_radio.setChecked(False)
            self.cutline_radio.setChecked(False)
            self.add_type = "boarding"
        else:
            # 如果当前的复选框被取消选中，默认选中排队
            if not self.queue_radio.isChecked() and not self.cutline_radio.isChecked() and not self.boarding_radio.isChecked():
                self.queue_radio.setChecked(True)
                self.add_type = "queue"
        
        # 更新按钮文本
        if self.add_type == "queue":
            self.ok_btn.setText("添加到排队")
        elif self.add_type == "cutline":
            self.ok_btn.setText("添加到插队")
        elif self.add_type == "boarding":
            self.ok_btn.setText("添加到上车")
        if self.add_type == "queue":
            self.ok_btn.setText("添加到排队")
        else:
            self.ok_btn.setText("添加到上车")
