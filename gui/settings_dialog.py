#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置对话框模块 - 程序全局设置
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QGroupBox, QMessageBox, 
                             QTabWidget, QWidget, QCheckBox, QSpinBox,
                             QLineEdit, QFileDialog, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from config import app_config
from utils import gui_logger

try:
    from utils.kokoro_tts import last_import_error as _kokoro_last_import_error
except Exception:
    def _kokoro_last_import_error():
        return None

last_import_error = _kokoro_last_import_error


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
        # TTS设置选项卡
        self.create_tts_tab()
        
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

        # 关键词设置
        keywords_group = QGroupBox("关键词设置")
        kw_layout = QVBoxLayout()
        from PyQt6.QtWidgets import QFormLayout
        form = QFormLayout()
        self.queue_keyword_edit = QLineEdit()
        self.boarding_keyword_edit = QLineEdit()
        self.cutline_keyword_edit = QLineEdit()
        form.addRow(QLabel("排队关键词:"), self.queue_keyword_edit)
        form.addRow(QLabel("上车关键词:"), self.boarding_keyword_edit)
        form.addRow(QLabel("插队关键词:"), self.cutline_keyword_edit)
        kw_layout.addLayout(form)
        tips = QLabel("提示: 修改后点击底部‘应用’保存，重载配置会自动生效；默认分别为 ‘排队’、‘刑具排队’、‘我要插队’。")
        tips.setWordWrap(True)
        kw_layout.addWidget(tips)
        keywords_group.setLayout(kw_layout)
        layout.addWidget(keywords_group)
        
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

    def create_tts_tab(self):
        from PyQt6.QtWidgets import QFormLayout, QSlider, QScrollArea
        # 使用可滚动容器，避免控件过多时被挤压
        content = QWidget()
        layout = QVBoxLayout(content)

        # 开关与基础参数
        base_group = QGroupBox("基础设置")
        base_layout = QVBoxLayout()
        self.tts_enable = QCheckBox("启用TTS播报")
        base_layout.addWidget(self.tts_enable)

        # 引擎/语速/音量
        form = QFormLayout()
        self.tts_engine_combo = QComboBox()
        self.tts_engine_combo.addItem("Kokoro 离线 (kokoro)", userData="kokoro")
        self.tts_engine_combo.addItem("Edge 在线 (edge-tts)", userData="edge-tts")
        self.tts_engine_combo.addItem("本地 (pyttsx3)", userData="pyttsx3")
        form.addRow(QLabel("引擎:"), self.tts_engine_combo)
        self.tts_rate = QSpinBox(); self.tts_rate.setRange(80, 300); self.tts_rate.setSingleStep(10)
        from PyQt6.QtWidgets import QDoubleSpinBox as _QDB
        self.tts_volume = _QDB(); self.tts_volume.setRange(0.0, 1.0); self.tts_volume.setSingleStep(0.1)
        form.addRow(QLabel("语速:"), self.tts_rate)
        form.addRow(QLabel("音量:"), self.tts_volume)
        # 已移除 Kokoro 专用参数

        # 语音选择 + 刷新
        self.tts_voice_combo = QComboBox()
        try:
            self.tts_voice_combo.addItem("请点击‘刷新语音列表’加载可用语音", userData="")
        except Exception:
            pass
        form.addRow(QLabel("语音:"), self.tts_voice_combo)
        self.tts_refresh_voices_btn = QPushButton("刷新语音列表")
        form.addRow(QLabel(""), self.tts_refresh_voices_btn)
        # 试听按钮（由主窗口接线触发试听）
        self.tts_preview_btn = QPushButton("试听当前设置")
        form.addRow(QLabel(""), self.tts_preview_btn)

        # 已移除 Piper 相关参数
        base_layout.addLayout(form)
        base_group.setLayout(base_layout)
        layout.addWidget(base_group)

        # 事件开关
        event_group = QGroupBox("事件播报开关")
        ev_layout = QVBoxLayout()
        self.tts_enable_danmaku = QCheckBox("弹幕")
        self.tts_enable_gift = QCheckBox("礼物")
        self.tts_enable_guard = QCheckBox("上舰")
        self.tts_enable_sc = QCheckBox("醒目留言")
        for w in [self.tts_enable_danmaku, self.tts_enable_gift, self.tts_enable_guard,
                  self.tts_enable_sc]:
            ev_layout.addWidget(w)
        event_group.setLayout(ev_layout)
        layout.addWidget(event_group)

        # 模板设置
        tpl_group = QGroupBox("自定义模板")
        tpl_layout = QFormLayout()
        self.tpl_gift = QLineEdit()
        self.tpl_guard = QLineEdit()
        self.tpl_sc = QLineEdit()
        self.tpl_danmaku = QLineEdit()
        tpl_layout.addRow("礼物:", self.tpl_gift)
        tpl_layout.addRow("上舰:", self.tpl_guard)
        tpl_layout.addRow("醒目留言:", self.tpl_sc)
        tpl_layout.addRow("弹幕:", self.tpl_danmaku)
        help_label = QLabel("可用占位符: {username}, {message}, {giftname}, {time}, {guardname}")
        help_label.setWordWrap(True)
        tpl_group.setLayout(tpl_layout)
        layout.addWidget(tpl_group)
        layout.addWidget(help_label)

        layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        self.tab_widget.addTab(scroll, "TTS设置")

    # 由主窗口注入可用语音列表
    def populate_tts_voices(self, voices: dict[str, str], current_id: str = ""):
        try:
            self.tts_voice_combo.clear()
            # voices: id -> name
            for vid, name in voices.items():
                self.tts_voice_combo.addItem(name or vid, userData=vid)
            # 选择当前
            if current_id:
                idx = self.tts_voice_combo.findData(current_id)
                if idx >= 0:
                    self.tts_voice_combo.setCurrentIndex(idx)
        except Exception:
            pass
    
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
            # 关键词
            self.queue_keyword_edit.setText(app_config.get("keywords.queue", "排队"))
            self.boarding_keyword_edit.setText(app_config.get("keywords.boarding", "刑具排队"))
            self.cutline_keyword_edit.setText(app_config.get("keywords.cutline", "我要插队"))
            
            # 高级设置
            self.file_monitor_interval.setValue(app_config.get("advanced.file_monitor_interval", 5))
            self.enable_debug_mode.setChecked(app_config.get("advanced.debug_mode", False))

            # TTS设置
            t = app_config.get("tts", {}) or {}
            self.tts_enable.setChecked(t.get("enable", False))
            # 引擎
            eng = t.get("engine", "kokoro")
            idx = self.tts_engine_combo.findData(eng)
            if idx >= 0:
                self.tts_engine_combo.setCurrentIndex(idx)
            self.tts_rate.setValue(int(t.get("rate", 180)))
            self.tts_volume.setValue(float(t.get("volume", 1.0)))
            # 无 Kokoro 参数
            # 语音列表需要运行期获取，由主窗口注入或延迟填充，这里只设置占位
            self._pending_voice_id = t.get("voice_id", "")
            self.tts_enable_danmaku.setChecked(bool(t.get("enable_danmaku", False)))
            self.tts_enable_gift.setChecked(bool(t.get("enable_gift", True)))
            self.tts_enable_guard.setChecked(bool(t.get("enable_guard", True)))
            self.tts_enable_sc.setChecked(bool(t.get("enable_super_chat", True)))
            tpl = t.get("templates", {}) or {}
            self.tpl_gift.setText(tpl.get("gift", ""))
            self.tpl_guard.setText(tpl.get("guard", ""))
            self.tpl_sc.setText(tpl.get("super_chat", ""))
            self.tpl_danmaku.setText(tpl.get("danmaku", ""))
            
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
            # 保存 TTS 设置
            t = app_config.get("tts", {}) or {}
            t.update({
                "enable": self.tts_enable.isChecked(),
                "engine": self.tts_engine_combo.currentData() or "kokoro",
                "rate": self.tts_rate.value(),
                "volume": float(self.tts_volume.value()),
                "voice_id": self.tts_voice_combo.currentData() or self.tts_voice_combo.currentText(),
                "enable_danmaku": self.tts_enable_danmaku.isChecked(),
                "enable_gift": self.tts_enable_gift.isChecked(),
                "enable_guard": self.tts_enable_guard.isChecked(),
                "enable_super_chat": self.tts_enable_sc.isChecked(),
                "templates": {
                    "gift": self.tpl_gift.text(),
                    "guard": self.tpl_guard.text(),
                    "super_chat": self.tpl_sc.text(),
                    "danmaku": self.tpl_danmaku.text(),
                }
            })
            app_config.set("tts", t)
            # 保存关键词设置
            app_config.set("keywords.queue", self.queue_keyword_edit.text().strip() or "排队")
            app_config.set("keywords.boarding", self.boarding_keyword_edit.text().strip() or "刑具排队")
            app_config.set("keywords.cutline", self.cutline_keyword_edit.text().strip() or "我要插队")
            # 立即落盘
            app_config.save_config()
            # 并同步至运行时常量（无需重启）
            try:
                from config import Constants as _C
                _C.QUEUE_KEYWORD = app_config.get("keywords.queue", _C.QUEUE_KEYWORD)
                _C.BOARDING_KEYWORD = app_config.get("keywords.boarding", _C.BOARDING_KEYWORD)
                _C.CUTLINE_KEYWORD = app_config.get("keywords.cutline", _C.CUTLINE_KEYWORD)
            except Exception:
                pass
            
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
