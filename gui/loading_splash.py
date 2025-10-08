#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""应用启动时的加载界面。"""
from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPalette, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class LoadingSplashScreen(QWidget):
    """带日志输出的启动加载界面。"""

    def __init__(self) -> None:
        super().__init__(
            flags=Qt.WindowType.SplashScreen
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setObjectName("LoadingSplashScreen")

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        container = QWidget(self)
        container.setObjectName("splashContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(24, 24, 24, 24)
        container_layout.setSpacing(16)

        self.title_label = QLabel("正在启动排队工具…", container)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress_bar = QProgressBar(container)
        self.progress_bar.setRange(0, 0)  # 不确定耗时，使用不确定进度条
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(14)

        self.log_view = QTextEdit(container)
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(160)
        self.log_view.setObjectName("splashLogView")

        container_layout.addWidget(self.title_label)
        container_layout.addWidget(self.progress_bar)
        container_layout.addWidget(self.log_view)
        outer_layout.addWidget(container)

        self._apply_styles()
        self.resize(520, 320)
        self._center_on_screen()

    def _apply_styles(self) -> None:
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255, 235))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(33, 37, 41))
        self.setPalette(palette)

        self.setStyleSheet(
            """
            QWidget#splashContainer {
                background-color: rgba(255, 255, 255, 235);
                border-radius: 18px;
                border: 1px solid rgba(0, 0, 0, 40);
            }
            QTextEdit#splashLogView {
                background-color: rgba(248, 249, 250, 220);
                border: 1px solid rgba(0, 0, 0, 30);
                border-radius: 10px;
                padding: 8px;
                font-size: 12px;
                color: #212529;
            }
            QProgressBar {
                border: 1px solid rgba(0, 0, 0, 20);
                border-radius: 7px;
                background-color: rgba(255, 255, 255, 200);
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 7px;
            }
        """
        )

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geometry = screen.availableGeometry()
        x = int(geometry.center().x() - self.width() / 2)
        y = int(geometry.center().y() - self.height() / 2)
        self.move(x, y)

    def append_message(self, message: str) -> None:
        if not message:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_view.append(f"[{timestamp}] {message}")
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)
        QApplication.processEvents()

    def set_title(self, title: str) -> None:
        if title:
            self.title_label.setText(title)
            QApplication.processEvents()

    def finish(self, target: QWidget | None = None) -> None:
        self.close()
        if target is not None:
            target.raise_()
            target.activateWindow()
            QApplication.processEvents()


__all__ = ["LoadingSplashScreen"]
