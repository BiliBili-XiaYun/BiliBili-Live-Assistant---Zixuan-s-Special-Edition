#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
名单编辑器模块 - 提供名单的可视化编辑界面
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QInputDialog, QLabel, QFileDialog,
                             QLineEdit, QComboBox, QSpinBox, QSplitter,
                             QWidget, QTextEdit)
from PyQt6.QtCore import Qt, pyqtSignal
import csv
import os
import re
from typing import List, Dict, Optional

from models import QueueItem
from config import Constants, app_config
from utils import parse_name_count, format_name_count, gui_logger

class NameListEditor(QDialog):
    """名单编辑器对话框"""
      # 信号定义
    name_list_changed = pyqtSignal()  # 名单变更信号
    
    def __init__(self, parent=None, name_list_file: str = None):
        """
        初始化名单编辑器
        
        Args:
            parent: 父窗口
            name_list_file: 名单文件路径
        """
        super().__init__(parent)
        self.setWindowTitle("名单编辑器")
        self.setModal(True)
        self.resize(800, 600)
          # 设置窗口图标
        icon_path = Constants.get_icon_path(128)
        if icon_path:
            from PyQt6.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path))
        
        # 文件路径处理，优先使用配置中的路径
        if name_list_file:
            self.name_list_file = os.path.abspath(name_list_file)
            gui_logger.debug("名单编辑器初始化", f"使用传入的文件路径: {self.name_list_file}")
        else:
            # 从配置中读取路径
            config_path = app_config.get("queue.name_list_file", "")
            if config_path and config_path.strip():
                self.name_list_file = os.path.abspath(config_path.strip())
                gui_logger.debug("名单编辑器初始化", f"从配置中读取文件路径: {self.name_list_file}")
            else:                # 如果配置中也没有，使用默认路径但不自动加载
                self.name_list_file = ""
                gui_logger.warning("配置中未设置文件路径，不自动加载")
        
        gui_logger.debug("名单编辑器初始化完成", f"当前文件路径: {self.name_list_file}")
        
        # 名单数据
        self.name_list: List[QueueItem] = []
        
        # 修改状态追踪
        self.is_modified = False
        
        # 初始化UI
        self.init_ui()
          # 加载名单
        self.load_name_list()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout()
        
        # 顶部信息栏
        info_layout = QHBoxLayout()
        abs_path = os.path.abspath(self.name_list_file)
        self.file_label = QLabel(f"当前文件: {abs_path}")
        info_layout.addWidget(self.file_label)
        
        info_layout.addStretch()
        
        # 统计信息
        self.stats_label = QLabel("统计: 0 项")
        info_layout.addWidget(self.stats_label)
        
        layout.addLayout(info_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：名单表格
        table_widget = self.create_table_widget()
        splitter.addWidget(table_widget)
        
        # 右侧：编辑面板
        edit_widget = self.create_edit_widget()
        splitter.addWidget(edit_widget)
        
        # 设置分割器比例
        splitter.setSizes([500, 300])
        layout.addWidget(splitter)
          # 底部按钮栏
        button_layout = QHBoxLayout()
        
        # 文件操作按钮
        self.load_file_btn = QPushButton("加载文件")
        self.load_file_btn.clicked.connect(self.open_file)
        button_layout.addWidget(self.load_file_btn)
        
        # 保存按钮 - 保存到当前路径
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_current)
        button_layout.addWidget(self.save_btn)
        
        # 另存为按钮
        self.save_as_btn = QPushButton("另存为")
        self.save_as_btn.clicked.connect(self.save_as)
        button_layout.addWidget(self.save_as_btn)
        
        self.refresh_config_btn = QPushButton("刷新配置")
        self.refresh_config_btn.clicked.connect(self.refresh_config)
        button_layout.addWidget(self.refresh_config_btn)
        
        button_layout.addStretch()
        
        # 对话框按钮
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept_with_save)
        button_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject_with_check)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def create_table_widget(self) -> QWidget:
        """创建表格组件"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 表格标题和工具栏
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("名单列表"))
        
        header_layout.addStretch()
        
        # 表格操作按钮
        self.add_btn = QPushButton("添加")
        self.add_btn.clicked.connect(self.add_item)
        header_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.clicked.connect(self.edit_item)
        self.edit_btn.setEnabled(False)
        header_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self.delete_item)
        self.delete_btn.setEnabled(False)
        header_layout.addWidget(self.delete_btn)
        
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_all)
        header_layout.addWidget(self.clear_btn)
        
        layout.addLayout(header_layout)
        
        # 名单表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["序号", "名字", "次数"])
        
        # 设置表格属性
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # 序号列
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)           # 名字列
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # 次数列
          # 设置行高
        self.table.verticalHeader().setDefaultSectionSize(30)
        
        # 选择整行
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
          # 设置表格样式，修复选中时文字看不清的问题
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
                alternate-background-color: #f5f5f5;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
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
        
        # 连接选择变化信号
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.table.itemDoubleClicked.connect(self.edit_item)
        
        layout.addWidget(self.table)
        widget.setLayout(layout)
        return widget
    
    def create_edit_widget(self) -> QWidget:
        """创建编辑面板"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("编辑面板"))
        
        # 名字输入
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("名字:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入名字")
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # 次数输入
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("次数:"))
        self.count_spinbox = QSpinBox()
        self.count_spinbox.setMinimum(1)
        self.count_spinbox.setMaximum(9999)
        self.count_spinbox.setValue(1)
        count_layout.addWidget(self.count_spinbox)
        layout.addLayout(count_layout)
        
        # 操作按钮
        edit_button_layout = QHBoxLayout()
        
        self.add_edit_btn = QPushButton("添加项目")
        self.add_edit_btn.clicked.connect(self.add_from_edit_panel)
        edit_button_layout.addWidget(self.add_edit_btn)
        
        self.update_edit_btn = QPushButton("更新项目")
        self.update_edit_btn.clicked.connect(self.update_from_edit_panel)
        self.update_edit_btn.setEnabled(False)
        edit_button_layout.addWidget(self.update_edit_btn)
        
        layout.addLayout(edit_button_layout)
        
        # 分隔线
        layout.addWidget(QLabel("─" * 30))
        
        # 批量操作区域
        layout.addWidget(QLabel("批量操作"))
        
        # 批量输入文本框
        self.batch_text = QTextEdit()
        self.batch_text.setPlaceholderText(
            "批量输入格式：\n"
            "名字1\n"
            "名字2(次数\n"
            "名字3(10\n"
            "\n"
            "或者粘贴CSV内容"
        )
        self.batch_text.setMaximumHeight(150)
        layout.addWidget(self.batch_text)
        
        # 批量操作按钮
        batch_button_layout = QHBoxLayout()
        
        self.parse_batch_btn = QPushButton("解析并预览")
        self.parse_batch_btn.clicked.connect(self.parse_batch_input)
        batch_button_layout.addWidget(self.parse_batch_btn)
        
        self.apply_batch_btn = QPushButton("应用批量输入")
        self.apply_batch_btn.clicked.connect(self.apply_batch_input)
        batch_button_layout.addWidget(self.apply_batch_btn)
        
        layout.addLayout(batch_button_layout)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def load_name_list(self):
        """加载名单"""
        try:
            # 如果名单文件路径为空，跳过加载
            if not self.name_list_file or not self.name_list_file.strip():
                gui_logger.warning("名单文件路径为空，跳过加载")
                self.name_list = []
                self.update_table()
                self.update_stats()
                return
            
            # 确保使用绝对路径
            abs_file_path = os.path.abspath(self.name_list_file)
            
            if os.path.exists(abs_file_path):
                with open(abs_file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    self.name_list = []
                    
                    for row_index, row in enumerate(reader, 1):
                        if not row or not row[0].strip():
                            continue
                        
                        name_with_count = row[0].strip()
                        if not name_with_count:
                            continue
                        
                        # 解析名字和次数
                        name, count = parse_name_count(name_with_count)
                        
                        if name:
                            item = QueueItem(name=name, count=count, index=row_index)
                            self.name_list.append(item)
                            
                gui_logger.operation_complete("加载名单文件", f"成功加载 {len(self.name_list)} 项")
            else:
                gui_logger.error("名单文件不存在", abs_file_path)
                self.name_list = []
            
            self.update_table()
            self.update_stats()
            
            # 加载完成后清除修改标志，表示当前状态与文件同步
            self.is_modified = False
            
        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"加载名单文件失败：{str(e)}")
            gui_logger.error("加载失败详细信息", str(e))
            gui_logger.debug("原始文件路径", str(self.name_list_file))
            gui_logger.debug("绝对文件路径", os.path.abspath(self.name_list_file))
            self.name_list = []
            self.update_table()
            self.update_stats()
    
    def save_name_list(self):
        """保存名单（内部方法，不显示弹窗）"""
        try:
            # 确保使用绝对路径
            abs_file_path = os.path.abspath(self.name_list_file)
            
            # 确保目录存在
            dir_path = os.path.dirname(abs_file_path)
            if dir_path:  # 只有当目录路径不为空时才创建
                os.makedirs(dir_path, exist_ok=True)
            
            with open(abs_file_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                
                for item in self.name_list:
                    name_str = format_name_count(item.name, item.count)
                    writer.writerow([name_str])
            
            # 保存文件路径到配置中
            app_config.set("queue.name_list_file", abs_file_path)
            app_config.save_config()
            
            self.name_list_changed.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存名单文件失败：{str(e)}\n文件路径: {self.name_list_file}")
            gui_logger.error("保存失败详细信息", str(e))
            gui_logger.debug("原始文件路径", str(self.name_list_file))
            gui_logger.debug("绝对文件路径", os.path.abspath(self.name_list_file))
            gui_logger.debug("当前工作目录", os.getcwd())
    
    def save_as(self):
        """另存为"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "另存为", "", "CSV文件 (*.csv);;所有文件 (*)"
        )
        
        if file_path:            # 确保使用绝对路径
            abs_file_path = os.path.abspath(file_path)
            old_file = self.name_list_file
            self.name_list_file = abs_file_path
            self.save_name_list()
            
            # 保存到配置中
            app_config.set("queue.name_list_file", abs_file_path)
            app_config.save_config()
              # 更新显示的文件路径
            self.file_label.setText(f"当前文件: {abs_file_path}")
            self.is_modified = False  # 清除修改标志
            
            gui_logger.operation_complete("另存为", f"保存到配置: {abs_file_path}")
    
    def open_file(self):
        """打开文件"""        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开名单文件", "", "CSV文件 (*.csv);;所有文件 (*)"
        )
        
        if file_path:            # 确保使用绝对路径
            abs_file_path = os.path.abspath(file_path)
            self.name_list_file = abs_file_path
            
            # 保存到配置中
            app_config.set("queue.name_list_file", abs_file_path)
            app_config.save_config()
            
            self.file_label.setText(f"当前文件: {abs_file_path}")
            self.load_name_list()
            gui_logger.operation_complete("打开文件", f"保存到配置: {abs_file_path}")
    
    def new_name_list(self):
        """新建名单"""
        reply = QMessageBox.question(
            self, "确认", "新建名单将清空当前内容，是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.name_list = []
            self.is_modified = True
            self.update_table()
            self.update_stats()
            self.clear_edit_panel()
    
    def update_table(self):
        """更新表格显示"""
        self.table.setRowCount(len(self.name_list))
        
        for row, item in enumerate(self.name_list):
            # 序号
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            
            # 名字
            self.table.setItem(row, 1, QTableWidgetItem(item.name))
            
            # 次数
            self.table.setItem(row, 2, QTableWidgetItem(str(item.count)))
    
    def update_stats(self):
        """更新统计信息"""
        total_items = len(self.name_list)
        total_count = sum(item.count for item in self.name_list)
        unique_names = len(set(item.name for item in self.name_list))
        
        stats_text = f"统计: {total_items} 项, {unique_names} 个不同名字, 总计 {total_count} 次"
        self.stats_label.setText(stats_text)
    
    def on_selection_changed(self):
        """选择变化处理"""
        selected_rows = self.get_selected_rows()
        has_selection = len(selected_rows) > 0
        
        self.edit_btn.setEnabled(has_selection and len(selected_rows) == 1)
        self.delete_btn.setEnabled(has_selection)
        
        # 如果选择了单个项目，在编辑面板中显示
        if len(selected_rows) == 1:
            item = self.name_list[selected_rows[0]]
            self.name_edit.setText(item.name)
            self.count_spinbox.setValue(item.count)
            self.update_edit_btn.setEnabled(True)
            self.add_edit_btn.setText("添加项目")
        else:
            self.clear_edit_panel()
    
    def get_selected_rows(self) -> List[int]:
        """获取选中的行"""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return []
        
        rows = list(set(item.row() for item in selected_items))
        return sorted(rows)
    
    def clear_edit_panel(self):
        """清空编辑面板"""
        self.name_edit.clear()
        self.count_spinbox.setValue(1)
        self.update_edit_btn.setEnabled(False)
        self.add_edit_btn.setText("添加项目")
    
    def add_item(self):
        """添加项目"""
        dialog = AddEditItemDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, count = dialog.get_result()
            if name:
                item = QueueItem(name=name, count=count, index=len(self.name_list) + 1)
                self.name_list.append(item)
                self.is_modified = True
                self.update_table()
                self.update_stats()
    
    def edit_item(self):
        """编辑项目"""
        selected_rows = self.get_selected_rows()
        if len(selected_rows) != 1:
            return
        
        row = selected_rows[0]
        item = self.name_list[row]
        
        dialog = AddEditItemDialog(self, item.name, item.count)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, count = dialog.get_result()
            if name:
                item.name = name
                item.count = count
                self.is_modified = True
                self.update_table()
                self.update_stats()
                self.on_selection_changed()  # 更新编辑面板
    
    def delete_item(self):
        """删除项目"""
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            return
        
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除选中的 {len(selected_rows)} 个项目吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No        
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 从后往前删除，避免索引变化
            for row in reversed(selected_rows):
                del self.name_list[row]
            
            self.is_modified = True
            self.update_table()
            self.update_stats()
            self.clear_edit_panel()
    
    def clear_all(self):
        """清空所有项目"""
        if not self.name_list:
            return
        
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空所有项目吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.name_list = []
            self.is_modified = True
            self.update_table()
            self.update_stats()
            self.clear_edit_panel()
    
    def add_from_edit_panel(self):
        """从编辑面板添加项目"""
        name = self.name_edit.text().strip()
        count = self.count_spinbox.value()
        
        if not name:
            QMessageBox.warning(self, "输入错误", "请输入名字")
            return
        
        item = QueueItem(name=name, count=count, index=len(self.name_list) + 1)
        self.name_list.append(item)
        self.is_modified = True
        self.update_table()
        self.update_stats()
        self.clear_edit_panel()
    
    def update_from_edit_panel(self):
        """从编辑面板更新项目"""
        selected_rows = self.get_selected_rows()
        if len(selected_rows) != 1:
            return
        
        row = selected_rows[0]
        name = self.name_edit.text().strip()
        count = self.count_spinbox.value()
        
        if not name:
            QMessageBox.warning(self, "输入错误", "请输入名字")
            return
        
        item = self.name_list[row]
        item.name = name
        item.count = count
        
        self.is_modified = True
        self.update_table()
        self.update_stats()
    
    def parse_batch_input(self):
        """解析批量输入"""
        text = self.batch_text.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "提示", "请输入批量数据")
            return
        
        try:
            lines = text.split('\n')
            parsed_items = []
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                name, count = parse_name_count(line)
                if name:
                    parsed_items.append(f"{name} (次数: {count})")
            
            if parsed_items:
                preview_text = "解析结果预览：\n" + "\n".join(parsed_items)
                QMessageBox.information(self, "解析结果", preview_text)
            else:
                QMessageBox.warning(self, "解析失败", "没有解析到有效的数据")
                
        except Exception as e:
            QMessageBox.critical(self, "解析错误", f"解析批量输入时出错：{str(e)}")
    
    def apply_batch_input(self):
        """应用批量输入"""
        text = self.batch_text.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "提示", "请输入批量数据")
            return
        
        try:
            lines = text.split('\n')
            new_items = []
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                name, count = parse_name_count(line)
                if name:
                    item = QueueItem(name=name, count=count, index=len(self.name_list) + len(new_items) + 1)
                    new_items.append(item)
            
            if new_items:
                reply = QMessageBox.question(
                    self, "确认添加", f"确定要添加 {len(new_items)} 个项目吗？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.name_list.extend(new_items)
                    self.is_modified = True
                    self.update_table()
                    self.update_stats()
                    self.batch_text.clear()
                    QMessageBox.information(self, "添加成功", f"成功添加 {len(new_items)} 个项目")
            else:
                QMessageBox.warning(self, "添加失败", "没有解析到有效的数据")
                
        except Exception as e:
            QMessageBox.critical(self, "添加错误", f"应用批量输入时出错：{str(e)}")
    
    def refresh_config(self):
        """刷新配置并重新加载名单文件"""
        try:
            gui_logger.operation_start("刷新配置")
            
            # 重新加载配置文件
            app_config.reload_config_from_file()
            
            # 获取新的名单文件路径
            new_path = app_config.get("queue.name_list_file", "")
            if new_path and new_path.strip():
                new_abs_path = os.path.abspath(new_path.strip())
                
                if new_abs_path != self.name_list_file:
                    gui_logger.info("检测到文件路径变更", f"{self.name_list_file} -> {new_abs_path}")
                    self.name_list_file = new_abs_path
                    
                    # 更新文件标签
                    self.file_label.setText(f"当前文件: {new_abs_path}")
                
                # 重新加载名单文件
                self.load_name_list()
                
                QMessageBox.information(self, "成功", "配置已刷新，名单文件已重新加载")
                gui_logger.operation_complete("配置刷新", "成功")
            else:
                QMessageBox.warning(self, "警告", "配置中未设置名单文件路径")
                gui_logger.warning("配置中未设置名单文件路径")
                
        except Exception as e:
            error_msg = f"刷新配置失败: {str(e)}"
            gui_logger.error("配置刷新错误", error_msg)
            QMessageBox.critical(self, "错误", error_msg)

    def save_current(self):
        """保存到当前文件路径"""
        if not self.name_list_file:
            # 如果没有当前文件路径，提示用户选择
            QMessageBox.information(self, "提示", "当前没有文件路径，将使用另存为功能")
            self.save_as()
            return
        
        try:
            # 确保使用绝对路径
            abs_file_path = os.path.abspath(self.name_list_file)
            
            # 确保目录存在，如果不存在则自动创建
            dir_path = os.path.dirname(abs_file_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                gui_logger.info("自动创建目录", dir_path)
            
            # 保存文件
            with open(abs_file_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                
                for item in self.name_list:
                    name_str = format_name_count(item.name, item.count)
                    writer.writerow([name_str])
            
            # 保存文件路径到配置中
            app_config.set("queue.name_list_file", abs_file_path)
            app_config.save_config()
            
            gui_logger.operation_complete("保存文件", abs_file_path)
            self.name_list_changed.emit()
            self.is_modified = False  # 清除修改标志
            
            # 不显示弹窗，只在状态栏或控制台显示
            # QMessageBox.information(self, "保存成功", f"名单已保存")
            
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存名单文件失败：{str(e)}\n文件路径: {self.name_list_file}")
            gui_logger.error("保存失败详细信息", str(e))

    def accept_with_save(self):
        """点击确定按钮时保存并关闭"""
        try:
            if self.is_modified and self.name_list:  # 只有修改过且有数据才保存
                if self.name_list_file:
                    # 有文件路径，直接保存
                    self.save_current()
                    gui_logger.operation_complete("确定时自动保存", "完成")
                else:
                    # 没有文件路径，使用默认路径
                    default_path = os.path.join(os.getcwd(), "名单.csv")
                    self.name_list_file = default_path
                    self.save_current()
                    gui_logger.operation_complete("确定时自动保存", f"保存到默认路径: {default_path}")
            else:
                gui_logger.debug("确定时无需保存（未修改或无数据）")
        except Exception as e:
            gui_logger.error("确定时自动保存失败", str(e))
            # 即使保存失败也继续关闭对话框
        
        # 调用原始的accept方法
        super().accept()

    def reject_with_check(self):
        """点击取消按钮时检查是否有未保存的修改"""
        if self.is_modified:
            reply = QMessageBox.question(
                self, "未保存的修改", 
                "您有未保存的修改，是否要保存？\n\n是：保存并关闭\n否：不保存直接关闭\n取消：返回编辑",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 保存并关闭
                try:
                    if self.name_list_file:
                        self.save_current()
                    else:
                        # 没有文件路径，使用默认路径
                        default_path = os.path.join(os.getcwd(), "名单.csv")
                        self.name_list_file = default_path
                        self.save_current()
                    super().reject()
                except Exception as e:
                    QMessageBox.critical(self, "保存失败", f"保存失败：{str(e)}")
                    return
            elif reply == QMessageBox.StandardButton.No:
                # 不保存直接关闭
                super().reject()
            # 如果选择取消，什么都不做，返回编辑
        else:
            # 没有修改，直接关闭
            super().reject()

    def closeEvent(self, event):
        """窗口关闭事件 - 只有修改过才自动保存"""
        gui_logger.debug("关闭事件触发", f"is_modified={self.is_modified}, name_list长度={len(self.name_list)}")
        try:
            if self.is_modified and self.name_list:  # 只有修改过且有数据才保存
                gui_logger.info("检测到修改，进行自动保存")
                if self.name_list_file:
                    # 有文件路径，直接保存
                    self.save_current()
                    gui_logger.operation_complete("关闭时自动保存", "完成")
                else:
                    # 没有文件路径，使用默认路径
                    default_path = os.path.join(os.getcwd(), "名单.csv")
                    self.name_list_file = default_path
                    self.save_current()
                    gui_logger.operation_complete("关闭时自动保存", f"保存到默认路径: {default_path}")
            else:
                gui_logger.debug("关闭时无需保存（未修改或无数据）")
        except Exception as e:
            gui_logger.error("关闭时自动保存失败", str(e))
        
        # 调用父类的关闭事件
        super().closeEvent(event)

class AddEditItemDialog(QDialog):
    """添加/编辑项目对话框"""
    
    def __init__(self, parent=None, name: str = "", count: int = 1):
        """
        初始化对话框
        
        Args:
            parent: 父窗口
            name: 初始名字
            count: 初始次数
        """
        super().__init__(parent)
        self.setWindowTitle("添加/编辑项目")
        self.setModal(True)
        self.resize(300, 150)
        
        layout = QVBoxLayout()
        
        # 名字输入
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("名字:"))
        self.name_edit = QLineEdit(name)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # 次数输入
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("次数:"))
        self.count_spinbox = QSpinBox()
        self.count_spinbox.setMinimum(1)
        self.count_spinbox.setMaximum(9999)
        self.count_spinbox.setValue(count)
        count_layout.addWidget(self.count_spinbox)
        layout.addLayout(count_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # 设置焦点
        self.name_edit.setFocus()
        self.name_edit.selectAll()
    
    def get_result(self) -> tuple:
        """
        获取结果
        
        Returns:
            tuple: (名字, 次数)
        """
        return self.name_edit.text().strip(), self.count_spinbox.value()
    
    def closeEvent(self, event):
        """关闭事件处理 - 通知主窗口同步配置"""
        # 如果有父窗口且父窗口有同步方法，调用同步
        if self.parent() and hasattr(self.parent(), 'sync_file_path_from_config'):
            self.parent().sync_file_path_from_config()
            gui_logger.debug("关闭时触发主窗口同步配置")
        event.accept()
