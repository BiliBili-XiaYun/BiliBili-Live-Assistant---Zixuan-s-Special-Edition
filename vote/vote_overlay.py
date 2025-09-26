#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""投票悬浮窗 (半透明置顶，可拖拽，ESC关闭)"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from .vote_manager import VoteManager
from utils import gui_logger

class VoteOverlayWindow(QWidget):
    voteEnded = pyqtSignal()              # 投票结束（自动/手动）
    visibilityChanged = pyqtSignal(bool)  # 窗口显隐变化
    """更易读的投票悬浮窗

    改进内容:
    - 半透明圆角深色背景 (rgba)
    - 更大的字体 (标题/选项动态缩放)
    - 选项数字突出，颜色对比增强
    - 可根据选项数量自动调整字号，保证信息完整显示
    """
    def __init__(self, vote_manager: VoteManager):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.vote_manager = vote_manager
        self.drag_pos = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle("投票进行中")
        self.base_width = 560
        self.base_height = 460
        self.resize(self.base_width, self.base_height)
        # 使用自绘背景 + RGBA，不再依赖整体 windowOpacity，避免文字发灰
        self.setWindowOpacity(1.0)
        self._build_ui()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(1000)

    def _build_ui(self):
        self.setStyleSheet("""
        QWidget { background-color: rgba(20,20,20,180); border:2px solid rgba(255,255,255,40); border-radius:18px; }
        QLabel { color: #f5f5f5; }
        QPushButton { background: rgba(255,255,255,70); color:#111; font-weight:bold; padding:8px 16px; border:1px solid rgba(255,255,255,120); border-radius:8px; }
        QPushButton:hover { background: rgba(255,255,255,110); }
        QPushButton:pressed { background: rgba(255,255,255,150); }
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(24,20,24,16)
        layout.setSpacing(12)

        self.title_label = QLabel("投票标题")
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.title_label)

        self.options_label = QLabel("")
        self.options_label.setTextFormat(Qt.TextFormat.RichText)
        self.options_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.options_label.setWordWrap(True)
        layout.addWidget(self.options_label, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.end_btn = QPushButton("结束投票")
        self.end_btn.clicked.connect(self._manual_end)
        btn_layout.addWidget(self.end_btn)
        self.close_btn = QPushButton("关闭窗口 (ESC)")
        self.close_btn.clicked.connect(self.hide)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event):
        self.visibilityChanged.emit(True)
        super().showEvent(event)

    def hideEvent(self, event):
        self.visibilityChanged.emit(False)
        super().hideEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            diff = event.globalPosition().toPoint() - self.drag_pos
            self.move(self.pos() + diff)
            self.drag_pos = event.globalPosition().toPoint()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        super().mouseReleaseEvent(event)

    def refresh(self):
        progress = self.vote_manager.get_progress()
        if not progress.get("running"):
            # 若存在已结束结果也展示最终统计
            if self.vote_manager.current_result:
                self._show_final_result()
            else:
                self.title_label.setText("(投票未进行)")
                self.options_label.setText("")
            self.end_btn.setEnabled(False)
            return
        self.title_label.setText(progress.get("title", "投票"))
        # 运行中确保结束按钮可用
        if not self.end_btn.isEnabled():
            self.end_btn.setEnabled(True)

        options = progress.get("options", [])
        count_map = progress.get("counts", {})
        n = len(options)
        # 动态字号策略
        if n <= 5:
            opt_size = 26
        elif n <= 8:
            opt_size = 24
        elif n <= 10:
            opt_size = 22
        else:
            opt_size = 20

        base_line_parts = []
        for idx, opt in enumerate(options, start=1):
            count = count_map.get(idx, 0)
            base_line_parts.append(
                f"<div style='margin:2px 0;font-size:{opt_size}px;line-height:{opt_size+6}px;'>"
                f"<span style='color:#FFD54F;font-weight:600'>{idx}.</span> "
                f"<span style='color:#FFFFFF;font-weight:500'>{opt}</span> "
                f"<span style='color:#66BB6A;font-weight:600'>({count}票)</span>"
                f"</div>"
            )

        if progress.get("auto_end"):
            remain = int(progress["auto_end"] - __import__('time').time())
            if remain < 0:
                remain = 0
            base_line_parts.append(
                f"<div style='margin-top:6px;font-size:{max(16,opt_size-6)}px;color:#90CAF9;'>⏳ 剩余: {remain}s</div>"
            )

        self.options_label.setText("".join(base_line_parts))

        # 自动结束检测
        if self.vote_manager.tick_auto_end():
            gui_logger.info("投票自动结束")
            self._show_final_result()
            self.voteEnded.emit()

    def _show_final_result(self):
        res = self.vote_manager.current_result
        if not res:
            return
        # 排序
        sorted_items = sorted(res.counts.items(), key=lambda x: (-x[1], x[0]))
        total = sum(res.counts.values())
        self.title_label.setText(f"投票结束 · 总票数 {total}")
        lines = []
        n = len(res.config.options)
        if n <= 5:
            opt_size = 26
        elif n <= 8:
            opt_size = 24
        elif n <= 10:
            opt_size = 22
        else:
            opt_size = 20
        # 找出最高票（可能并列）
        top_vote = sorted_items[0][1] if sorted_items else 0
        for rank, (idx, cnt) in enumerate(sorted_items, start=1):
            name = res.config.options[idx-1]
            pct = f"{(cnt/total*100):.1f}%" if total > 0 else "0.0%"
            highlight = cnt == top_vote and top_vote > 0
            bg = "background:rgba(255,215,64,0.18);border:1px solid rgba(255,215,64,0.5);" if highlight else ""
            tag = "<span style='color:#FFC107;font-weight:600'>★</span> " if highlight else ""
            lines.append(
                f"<div style='margin:2px 0;padding:2px 6px;border-radius:8px;{bg}font-size:{opt_size}px;line-height:{opt_size+6}px;'>"
                f"<span style='color:#FFD54F;font-weight:600'>{rank}.</span> "
                f"{tag}<span style='color:#FFFFFF;font-weight:500'>{name}</span> "
                f"<span style='color:#66BB6A;font-weight:600'>({cnt}票 {pct})</span>"
                f"</div>"
            )
        self.options_label.setText("".join(lines) + "<div style='margin-top:8px;font-size:20px;color:#EF5350;font-weight:700'>投票已结束</div>")
        self.end_btn.setEnabled(False)

    def _manual_end(self):
        if not self.vote_manager.is_running:
            return
        res = self.vote_manager.end_vote()
        if res:
            self._show_final_result()
            gui_logger.info("手动结束投票")
            self.end_btn.setEnabled(False)
            self.voteEnded.emit()
