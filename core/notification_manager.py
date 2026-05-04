# -*- coding: utf-8 -*-
"""
Notification Manager for Sudan Data Loader.

Provides toast-style notifications and message bar integration.
"""

from datetime import datetime
from collections import deque

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsOpacityEffect, QApplication
)
from qgis.PyQt.QtCore import (
    QObject, pyqtSignal, QTimer, Qt, QPropertyAnimation,
    QPoint, QEasingCurve
)
from qgis.PyQt.QtGui import QColor
from qgis.core import Qgis, QgsMessageLog
from qgis.gui import QgsMessageBar


class NotificationWidget(QFrame):
    """A toast-style notification widget."""

    closed = pyqtSignal()

    def __init__(self, message, level='info', duration=5000, parent=None):
        """
        Initialize notification widget.

        :param message: Notification message
        :param level: Notification level (info, success, warning, error)
        :param duration: Display duration in ms (0 for persistent)
        :param parent: Parent widget
        """
        super().__init__(parent)
        self.duration = duration
        self.level = level

        self.setup_ui(message)
        self.setup_style()

        if duration > 0:
            QTimer.singleShot(duration, self.fade_out)

    def setup_ui(self, message):
        """Set up the widget UI."""
        self.setFixedWidth(350)
        self.setMaximumHeight(100)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # Icon based on level
        icons = {
            'info': 'i',
            'success': '+',
            'warning': '!',
            'error': 'x'
        }
        icon_label = QLabel(icons.get(self.level, 'i'))
        icon_label.setFixedSize(24, 24)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 12px;
                font-weight: bold;
                font-size: 14px;
            }}
        """)
        layout.addWidget(icon_label)

        # Message
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("background: transparent;")
        layout.addWidget(message_label, 1)

        # Close button
        close_btn = QPushButton('x')
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 10px;
            }
        """)
        close_btn.clicked.connect(self.fade_out)
        layout.addWidget(close_btn)

    def setup_style(self):
        """Set up notification style based on level."""
        colors = {
            'info': ('#3498db', '#2980b9'),
            'success': ('#27ae60', '#219a52'),
            'warning': ('#f39c12', '#d68910'),
            'error': ('#e74c3c', '#c0392b')
        }

        bg_color, border_color = colors.get(self.level, colors['info'])

        self.setStyleSheet(f"""
            NotificationWidget {{
                background-color: {bg_color};
                color: white;
                border: 2px solid {border_color};
                border-radius: 8px;
            }}
            QLabel {{
                color: white;
            }}
        """)

    def fade_out(self):
        """Fade out and close the notification."""
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)

        self.animation = QPropertyAnimation(self.effect, b"opacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(1)
        self.animation.setEndValue(0)
        self.animation.setEasingCurve(QEasingCurve.OutQuad)
        self.animation.finished.connect(self._on_fade_complete)
        self.animation.start()

    def _on_fade_complete(self):
        """Handle fade out completion."""
        self.closed.emit()
        self.deleteLater()


class NotificationManager(QObject):
    """Manager for plugin notifications."""

    # Signals
    notification_added = pyqtSignal(str, str)  # message, level
    notification_cleared = pyqtSignal()

    # Maximum notifications to keep in history
    MAX_HISTORY = 50

    def __init__(self, iface=None):
        """
        Initialize the notification manager.

        :param iface: QGIS interface instance
        """
        super().__init__()
        self.iface = iface
        self.notifications = []  # Active notification widgets
        self.history = deque(maxlen=self.MAX_HISTORY)
        self.container = None
        self.position = 'top-right'  # top-right, top-left, bottom-right, bottom-left

    def set_container(self, parent_widget):
        """
        Set the container widget for notifications.

        :param parent_widget: Parent widget for notification container
        """
        self.container = QWidget(parent_widget)
        self.container.setFixedWidth(370)
        self.container.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.container.setAttribute(Qt.WA_TranslucentBackground, True)

        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(10, 10, 10, 10)
        self.container_layout.setSpacing(10)
        self.container_layout.addStretch()

        self._update_container_position()

    def _update_container_position(self):
        """Update container position based on settings."""
        if not self.container or not self.container.parent():
            return

        parent = self.container.parent()
        parent_rect = parent.rect()

        if self.position == 'top-right':
            x = parent_rect.width() - self.container.width() - 10
            y = 10
        elif self.position == 'top-left':
            x = 10
            y = 10
        elif self.position == 'bottom-right':
            x = parent_rect.width() - self.container.width() - 10
            y = parent_rect.height() - self.container.height() - 10
        else:  # bottom-left
            x = 10
            y = parent_rect.height() - self.container.height() - 10

        self.container.move(x, y)
        self.container.raise_()

    def notify(self, message, level='info', duration=5000, log=True):
        """
        Show a notification.

        :param message: Notification message
        :param level: Level (info, success, warning, error)
        :param duration: Display duration in ms (0 for persistent)
        :param log: Also log to QGIS message log
        """
        # Add to history
        self.history.append({
            'message': message,
            'level': level,
            'timestamp': datetime.now()
        })

        # Log to QGIS if requested
        if log:
            qgis_levels = {
                'info': Qgis.Info,
                'success': Qgis.Success,
                'warning': Qgis.Warning,
                'error': Qgis.Critical
            }
            QgsMessageLog.logMessage(
                message,
                'Sudan Data Loader',
                qgis_levels.get(level, Qgis.Info)
            )

        # Show toast notification if container is set
        if self.container:
            notification = NotificationWidget(message, level, duration, self.container)
            notification.closed.connect(lambda: self._remove_notification(notification))

            # Insert at the beginning (top)
            self.container_layout.insertWidget(0, notification)
            self.notifications.append(notification)

            # Animate in
            notification.show()
            self._update_container_position()

        # Also show in QGIS message bar for important messages
        if self.iface and level in ('warning', 'error'):
            bar_levels = {
                'warning': Qgis.Warning,
                'error': Qgis.Critical
            }
            self.iface.messageBar().pushMessage(
                'Sudan Data Loader',
                message,
                bar_levels.get(level, Qgis.Info),
                duration // 1000 if duration > 0 else 0
            )

        self.notification_added.emit(message, level)

    def info(self, message, duration=5000):
        """Show an info notification."""
        self.notify(message, 'info', duration)

    def success(self, message, duration=5000):
        """Show a success notification."""
        self.notify(message, 'success', duration)

    def warning(self, message, duration=7000):
        """Show a warning notification."""
        self.notify(message, 'warning', duration)

    def error(self, message, duration=0):
        """Show an error notification (persistent by default)."""
        self.notify(message, 'error', duration)

    def _remove_notification(self, notification):
        """Remove a notification from the active list."""
        if notification in self.notifications:
            self.notifications.remove(notification)
        self._update_container_position()

    def clear_all(self):
        """Clear all active notifications."""
        for notification in self.notifications[:]:
            notification.fade_out()
        self.notification_cleared.emit()

    def get_history(self):
        """Get notification history."""
        return list(self.history)

    def clear_history(self):
        """Clear notification history."""
        self.history.clear()

    def set_position(self, position):
        """
        Set notification position.

        :param position: Position string (top-right, top-left, bottom-right, bottom-left)
        """
        self.position = position
        self._update_container_position()


# Global notification manager instance
_notification_manager = None


def get_notification_manager(iface=None):
    """Get the global notification manager instance."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager(iface)
    elif iface and not _notification_manager.iface:
        _notification_manager.iface = iface
    return _notification_manager
