# -*- coding: utf-8 -*-
"""
Theme Manager for Ethiopia Data Loader.

Provides dark mode support and adaptive theming based on QGIS settings.
"""

from qgis.PyQt.QtWidgets import QApplication
from qgis.PyQt.QtGui import QPalette, QColor
from qgis.PyQt.QtCore import QObject, pyqtSignal, QSettings
from qgis.core import QgsSettings


class ThemeManager(QObject):
    """Manager for plugin theming and dark mode support."""

    # Theme changed signal
    theme_changed = pyqtSignal(str)  # theme name

    # Color schemes
    THEMES = {
        'light': {
            'background': '#ffffff',
            'surface': '#f5f5f5',
            'primary': '#3498db',
            'primary_dark': '#2980b9',
            'secondary': '#2ecc71',
            'accent': '#9b59b6',
            'text': '#2c3e50',
            'text_secondary': '#7f8c8d',
            'border': '#bdc3c7',
            'error': '#e74c3c',
            'warning': '#f39c12',
            'success': '#27ae60',
            'info': '#3498db'
        },
        'dark': {
            'background': '#1e1e1e',
            'surface': '#2d2d2d',
            'primary': '#3498db',
            'primary_dark': '#2980b9',
            'secondary': '#2ecc71',
            'accent': '#9b59b6',
            'text': '#ecf0f1',
            'text_secondary': '#95a5a6',
            'border': '#4a4a4a',
            'error': '#e74c3c',
            'warning': '#f39c12',
            'success': '#27ae60',
            'info': '#3498db'
        },
        'high_contrast': {
            'background': '#000000',
            'surface': '#1a1a1a',
            'primary': '#00ff00',
            'primary_dark': '#00cc00',
            'secondary': '#ffff00',
            'accent': '#ff00ff',
            'text': '#ffffff',
            'text_secondary': '#cccccc',
            'border': '#ffffff',
            'error': '#ff0000',
            'warning': '#ffff00',
            'success': '#00ff00',
            'info': '#00ffff'
        }
    }

    def __init__(self):
        """Initialize the theme manager."""
        super().__init__()
        self.current_theme = 'light'
        self.auto_detect = True
        self._load_settings()

    def _load_settings(self):
        """Load theme settings."""
        settings = QgsSettings()
        self.current_theme = settings.value('SudanDataLoader/theme', 'light')
        self.auto_detect = settings.value('SudanDataLoader/theme_auto_detect', True, type=bool)

        if self.auto_detect:
            self.current_theme = self.detect_qgis_theme()

    def _save_settings(self):
        """Save theme settings."""
        settings = QgsSettings()
        settings.setValue('SudanDataLoader/theme', self.current_theme)
        settings.setValue('SudanDataLoader/theme_auto_detect', self.auto_detect)

    def detect_qgis_theme(self):
        """
        Detect whether QGIS is using a dark theme.

        :returns: 'dark' or 'light'
        """
        # Check application palette
        app = QApplication.instance()
        if app:
            palette = app.palette()
            bg_color = palette.color(QPalette.Window)
            # If background luminance is low, it's dark theme
            luminance = (0.299 * bg_color.red() +
                         0.587 * bg_color.green() +
                         0.114 * bg_color.blue())
            if luminance < 128:
                return 'dark'

        # Also check QGIS settings
        settings = QgsSettings()
        ui_theme = settings.value('qgis/UITheme', '')
        if ui_theme and 'dark' in ui_theme.lower():
            return 'dark'

        return 'light'

    def get_current_theme(self):
        """Get the current theme name."""
        if self.auto_detect:
            return self.detect_qgis_theme()
        return self.current_theme

    def set_theme(self, theme_name):
        """
        Set the current theme.

        :param theme_name: Theme name ('light', 'dark', 'high_contrast')
        """
        if theme_name in self.THEMES:
            self.current_theme = theme_name
            self.auto_detect = False
            self._save_settings()
            self.theme_changed.emit(theme_name)

    def set_auto_detect(self, enabled):
        """
        Enable or disable automatic theme detection.

        :param enabled: True to enable auto-detection
        """
        self.auto_detect = enabled
        self._save_settings()
        if enabled:
            new_theme = self.detect_qgis_theme()
            if new_theme != self.current_theme:
                self.current_theme = new_theme
                self.theme_changed.emit(new_theme)

    def get_color(self, color_name):
        """
        Get a color from the current theme.

        :param color_name: Color name (e.g., 'primary', 'background')
        :returns: Color hex string
        """
        theme = self.THEMES.get(self.get_current_theme(), self.THEMES['light'])
        return theme.get(color_name, '#000000')

    def get_colors(self):
        """
        Get all colors for the current theme.

        :returns: Dictionary of color names to hex values
        """
        return self.THEMES.get(self.get_current_theme(), self.THEMES['light']).copy()

    def is_dark_mode(self):
        """Check if currently using dark mode."""
        return self.get_current_theme() in ('dark', 'high_contrast')

    def get_stylesheet(self, widget_type='general'):
        """
        Get a stylesheet for the current theme.

        :param widget_type: Type of widget ('general', 'panel', 'button', 'input')
        :returns: CSS stylesheet string
        """
        colors = self.get_colors()

        stylesheets = {
            'general': f"""
                QWidget {{
                    background-color: {colors['background']};
                    color: {colors['text']};
                }}
                QGroupBox {{
                    border: 1px solid {colors['border']};
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                    font-weight: bold;
                }}
                QGroupBox::title {{
                    color: {colors['text']};
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }}
            """,
            'panel': f"""
                QDockWidget {{
                    background-color: {colors['background']};
                    color: {colors['text']};
                }}
                QDockWidget::title {{
                    background-color: {colors['surface']};
                    padding: 5px;
                }}
            """,
            'button': f"""
                QPushButton {{
                    background-color: {colors['primary']};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {colors['primary_dark']};
                }}
                QPushButton:pressed {{
                    background-color: {colors['primary_dark']};
                }}
                QPushButton:disabled {{
                    background-color: {colors['border']};
                    color: {colors['text_secondary']};
                }}
            """,
            'input': f"""
                QLineEdit, QTextEdit, QPlainTextEdit {{
                    background-color: {colors['surface']};
                    color: {colors['text']};
                    border: 1px solid {colors['border']};
                    border-radius: 4px;
                    padding: 5px;
                }}
                QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                    border-color: {colors['primary']};
                }}
                QComboBox {{
                    background-color: {colors['surface']};
                    color: {colors['text']};
                    border: 1px solid {colors['border']};
                    border-radius: 4px;
                    padding: 5px;
                }}
            """,
            'table': f"""
                QTableWidget {{
                    background-color: {colors['background']};
                    color: {colors['text']};
                    gridline-color: {colors['border']};
                    border: 1px solid {colors['border']};
                }}
                QTableWidget::item {{
                    padding: 5px;
                }}
                QTableWidget::item:selected {{
                    background-color: {colors['primary']};
                    color: white;
                }}
                QHeaderView::section {{
                    background-color: {colors['surface']};
                    color: {colors['text']};
                    padding: 5px;
                    border: 1px solid {colors['border']};
                }}
            """,
            'list': f"""
                QListWidget {{
                    background-color: {colors['background']};
                    color: {colors['text']};
                    border: 1px solid {colors['border']};
                }}
                QListWidget::item {{
                    padding: 5px;
                }}
                QListWidget::item:selected {{
                    background-color: {colors['primary']};
                    color: white;
                }}
                QListWidget::item:hover {{
                    background-color: {colors['surface']};
                }}
            """
        }

        return stylesheets.get(widget_type, stylesheets['general'])

    def get_icon_color(self):
        """Get appropriate icon color for current theme."""
        if self.is_dark_mode():
            return '#ffffff'
        return '#2c3e50'

    def apply_to_widget(self, widget, widget_type='general'):
        """
        Apply theme stylesheet to a widget.

        :param widget: Qt widget
        :param widget_type: Type of styling to apply
        """
        widget.setStyleSheet(self.get_stylesheet(widget_type))


# Global theme manager instance
_theme_manager = None


def get_theme_manager():
    """Get the global theme manager instance."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager
