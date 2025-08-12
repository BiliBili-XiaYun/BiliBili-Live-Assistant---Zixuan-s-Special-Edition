#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
排队工具2专用插队对话框模块 - 支持独立名单导入
"""

import os
import csv
from typing import List, Optional
import re

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QCheckBox, QGroupBox, QMessageBox, QFileDialog,
                             QRadioButton, QButtonGroup, QTabWidget, QWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from models import QueueItem
from config import Constants


class InsertQueue2Dialog(QDialog):
    """排队工具2专用插队选择对话框 - 支持独立名单"""
    
    def __init__(self, default_name_list: List[QueueItem], parent=None):
        """
        初始化插队对话框
        
        Args:
            default_name_list (List[QueueItem]): 默认的排队队列名单
            parent: 父窗口
        """
        super().__init__(parent)
        self.setWindowTitle("插队 - 排队工具2")
        self.setFixedSize(700, 600)
        self.setModal(True)
        
        # 设置窗口图标
        icon_path = Constants.get_icon_path(128)
        if icon_path:
            from PyQt6.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path))
        
        self.default_name_list = default_name_list
        self.custom_name_list = []  # 独立导入的名单
        self.current_name_list = default_name_list  # 当前使用的名单
        self.selected_item = None
        self.fuzzy_search_enabled = True
        
        self.init_ui()
        self.update_name_list_display()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout()
        
        # 标题说明
        title_label = QLabel("插队功能 - 排队工具2")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        description_label = QLabel("选择要插队的用户，插队将消耗2次数，会插入到队列最前面")
        description_label.setWordWrap(True)
        layout.addWidget(description_label)
        
        # 名单选择区域
        name_source_group = QGroupBox("名单来源")
        name_source_layout = QVBoxLayout()
        
        # 名单选择选项
        self.name_source_group = QButtonGroup()
        
        self.use_default_rb = QRadioButton("使用排队队列名单")
        self.use_default_rb.setChecked(True)
        self.use_default_rb.toggled.connect(self.on_name_source_changed)
        self.name_source_group.addButton(self.use_default_rb, 0)
        name_source_layout.addWidget(self.use_default_rb)
        
        self.use_custom_rb = QRadioButton("使用独立插队名单")
        self.use_custom_rb.toggled.connect(self.on_name_source_changed)
        self.name_source_group.addButton(self.use_custom_rb, 1)
        name_source_layout.addWidget(self.use_custom_rb)
        
        # 导入名单按钮
        import_layout = QHBoxLayout()
        self.import_btn = QPushButton("📁 导入插队名单 (CSV)")
        self.import_btn.clicked.connect(self.import_custom_name_list)
        self.import_btn.setEnabled(False)
        import_layout.addWidget(self.import_btn)
        
        self.custom_name_status = QLabel("未导入独立名单")
        self.custom_name_status.setStyleSheet("color: #666;")
        import_layout.addWidget(self.custom_name_status)
        import_layout.addStretch()
        
        name_source_layout.addLayout(import_layout)
        name_source_group.setLayout(name_source_layout)
        layout.addWidget(name_source_group)
        
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
        
        self.ok_btn = QPushButton("确定插队")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setEnabled(False)
        button_layout.addWidget(self.ok_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def on_name_source_changed(self):
        """名单来源选择变化"""
        if self.use_default_rb.isChecked():
            # 使用默认名单
            self.current_name_list = self.default_name_list
            self.import_btn.setEnabled(False)
        else:
            # 使用独立名单
            if self.custom_name_list:
                self.current_name_list = self.custom_name_list
            else:
                self.current_name_list = []
            self.import_btn.setEnabled(True)
        
        self.update_name_list_display()
        self.filter_names()
    
    def import_custom_name_list(self):
        """导入独立的插队名单"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入插队名单",
            "",
            "CSV 文件 (*.csv);;所有文件 (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            custom_items = []
            with open(file_path, 'r', encoding='utf-8') as f:
                # 尝试自动检测CSV格式
                sample = f.read(1024)
                f.seek(0)
                
                # 检测分隔符
                delimiter = ','
                if sample.count('\t') > sample.count(','):
                    delimiter = '\t'
                
                reader = csv.reader(f, delimiter=delimiter)
                
                for row_idx, row in enumerate(reader, 1):
                    if not row or len(row) < 2:  # 跳过空行或格式不对的行
                        continue
                    
                    try:
                        name = row[0].strip()
                        count = int(row[1]) if row[1].strip() else 5  # 默认5次数
                        
                        if name:  # 确保名字不为空
                            item = QueueItem(
                                index=row_idx,
                                name=name,
                                count=count
                            )
                            custom_items.append(item)
                    except (ValueError, IndexError) as e:
                        continue  # 跳过格式错误的行
            
            if not custom_items:
                QMessageBox.warning(self, "导入失败", "未能从文件中读取到有效的名单数据")
                return
            
            self.custom_name_list = custom_items
            self.custom_name_status.setText(f"已导入 {len(custom_items)} 个用户")
            self.custom_name_status.setStyleSheet("color: #28a745;")
            
            # 自动切换到独立名单
            self.use_custom_rb.setChecked(True)
            self.on_name_source_changed()
            
            QMessageBox.information(
                self, 
                "导入成功", 
                f"成功导入 {len(custom_items)} 个用户到插队名单\n\n"
                f"文件: {os.path.basename(file_path)}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "导入错误", f"导入文件失败:\n{e}")
    
    def update_name_list_display(self):
        """更新名单显示信息"""
        if self.use_default_rb.isChecked():
            count = len(self.default_name_list)
            self.custom_name_status.setText(f"使用排队队列名单 ({count} 个用户)")
            self.custom_name_status.setStyleSheet("color: #007bff;")
        else:
            if self.custom_name_list:
                count = len(self.custom_name_list)
                self.custom_name_status.setText(f"使用独立名单 ({count} 个用户)")
                self.custom_name_status.setStyleSheet("color: #28a745;")
            else:
                self.custom_name_status.setText("请导入独立插队名单")
                self.custom_name_status.setStyleSheet("color: #dc3545;")
    
    def on_search_mode_changed(self):
        """搜索模式变化处理"""
        self.fuzzy_search_enabled = self.fuzzy_search_cb.isChecked()
        # 重新执行搜索
        self.filter_names()
    
    def filter_names(self):
        """根据搜索条件过滤名字"""
        search_text = self.search_input.text().strip().lower()
        self.result_list.clear()
        self.selected_item = None
        self.ok_btn.setEnabled(False)
        
        if not self.current_name_list:
            hint_item = QListWidgetItem("没有可用的名单数据")
            hint_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.result_list.addItem(hint_item)
            self.selected_info_label.setText("没有可用的名单数据")
            return
        
        matched_items = []
        
        for item in self.current_name_list:
            # 检查次数是否足够
            if item.count < 2:
                continue
            
            # 检查名字匹配
            if not search_text:
                matched_items.append(item)
            else:
                name_lower = item.name.lower()
                
                if self.fuzzy_search_enabled:
                    # 模糊搜索：包含关系
                    if search_text in name_lower:
                        matched_items.append(item)
                else:
                    # 精确搜索：开头匹配
                    if name_lower.startswith(search_text):
                        matched_items.append(item)
        
        # 显示匹配结果
        for item in matched_items:
            list_item = QListWidgetItem(f"{item.name} (序号:{item.index}, 剩余次数:{item.count})")
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.result_list.addItem(list_item)
        
        if not matched_items:
            hint_text = "没有找到匹配的名字或次数不足" if not self.fuzzy_search_enabled else "没有找到匹配的名字或次数不足（已启用模糊搜索）"
            hint_item = QListWidgetItem(hint_text)
            hint_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.result_list.addItem(hint_item)
        
        # 更新统计信息
        total_available = len([item for item in self.current_name_list if item.count >= 2])
        status_text = f"显示 {len(matched_items)} / {total_available} 个可插队项目"
        self.selected_info_label.setText(status_text)
    
    def on_item_clicked(self, item: QListWidgetItem):
        """点击项目处理"""
        queue_item = item.data(Qt.ItemDataRole.UserRole)
        if queue_item is not None:
            self.selected_item = queue_item
            self.ok_btn.setEnabled(True)
            
            # 更新选中项目信息
            source_text = "排队队列名单" if self.use_default_rb.isChecked() else "独立插队名单"
            info_text = f"已选择: {queue_item.name} (序号:{queue_item.index}, 剩余次数:{queue_item.count}) - 插队消耗2次数 [来源: {source_text}]"
            self.selected_info_label.setText(info_text)
        else:
            self.selected_item = None
            self.ok_btn.setEnabled(False)
    
    def on_item_selected(self, item: QListWidgetItem):
        """双击选择项目处理"""
        queue_item = item.data(Qt.ItemDataRole.UserRole)
        if queue_item is not None:
            self.selected_item = queue_item
            self.ok_btn.setEnabled(True)
            self.accept()
    
    def get_selected_item(self) -> Optional[QueueItem]:
        """获取选中的项目"""
        return self.selected_item
    
    def is_using_custom_list(self) -> bool:
        """是否使用独立名单"""
        return self.use_custom_rb.isChecked()
    
    def accept(self):
        """确认选择"""
        if self.selected_item is None:
            QMessageBox.warning(self, "未选择", "请先选择要插队的项目")
            return
        
        if self.selected_item.count < 2:
            QMessageBox.warning(self, "次数不足", f"{self.selected_item.name} 的剩余次数不足2次，无法插队")
            return
        
        # 如果使用独立名单，确认插队操作
        if self.is_using_custom_list():
            reply = QMessageBox.question(
                self,
                "确认插队",
                f"确定要让 '{self.selected_item.name}' 插队吗？\n\n"
                f"来源: 独立插队名单\n"
                f"消耗次数: 2次\n"
                f"剩余次数: {self.selected_item.count} → {self.selected_item.count - 2}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply != QMessageBox.StandardButton.Yes:
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
