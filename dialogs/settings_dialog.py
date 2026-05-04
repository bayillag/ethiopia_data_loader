# -*- coding: utf-8 -*-
"""
Settings Dialog for Ethiopia Data Loader.

Provides a configuration dialog for plugin settings.
"""

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QCheckBox, QComboBox, QPushButton,
    QGroupBox, QListWidget, QListWidgetItem, QLabel,
    QDialogButtonBox, QTabWidget, QWidget, QMessageBox
)
from qgis.PyQt.QtCore import Qt


class SettingsDialog(QDialog):
    """Settings dialog for Sudan Data Loader plugin."""

    def __init__(self, settings_manager, parent=None):
        """
        Initialize the settings dialog.

        :param settings_manager: SettingsManager instance
        :param parent: Parent widget
        """
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle('Sudan Data Loader - Settings')
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # General tab
        self.general_tab = QWidget()
        self.setup_general_tab()
        self.tab_widget.addTab(self.general_tab, 'General')

        # Layers tab
        self.layers_tab = QWidget()
        self.setup_layers_tab()
        self.tab_widget.addTab(self.layers_tab, 'Layers')

        # Appearance tab
        self.appearance_tab = QWidget()
        self.setup_appearance_tab()
        self.tab_widget.addTab(self.appearance_tab, 'Appearance')

        # API Keys tab
        self.api_keys_tab = QWidget()
        self.setup_api_keys_tab()
        self.tab_widget.addTab(self.api_keys_tab, 'API Keys')

        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.restore_defaults)
        layout.addWidget(button_box)

    def setup_general_tab(self):
        """Set up the General settings tab."""
        layout = QVBoxLayout(self.general_tab)

        # Server settings group
        server_group = QGroupBox('Server Settings')
        server_layout = QFormLayout(server_group)

        self.server_url_edit = QLineEdit()
        self.server_url_edit.setPlaceholderText('Enter custom server URL...')
        server_layout.addRow('Server URL:', self.server_url_edit)

        self.auto_update_check = QCheckBox('Check for updates on startup')
        server_layout.addRow('', self.auto_update_check)

        layout.addWidget(server_group)

        # Labels settings group
        labels_group = QGroupBox('Labels')
        labels_layout = QFormLayout(labels_group)

        self.label_language_combo = QComboBox()
        self.label_language_combo.addItem('English', 'english')
        self.label_language_combo.addItem('Arabic', 'arabic')
        self.label_language_combo.addItem('Both', 'both')
        labels_layout.addRow('Label Language:', self.label_language_combo)

        layout.addWidget(labels_group)

        layout.addStretch()

    def setup_layers_tab(self):
        """Set up the Layers settings tab."""
        layout = QVBoxLayout(self.layers_tab)

        # Default layers group
        layers_group = QGroupBox('Default Layers')
        layers_layout = QVBoxLayout(layers_group)

        self.layer_checkboxes = {}
        layer_options = [
            ('admin0', 'Admin 0 - Country Boundary'),
            ('admin1', 'Admin 1 - States'),
            ('admin2', 'Admin 2 - Localities'),
            ('admin_lines', 'Administrative Lines'),
            ('admin_points', 'Administrative Points'),
        ]

        for layer_id, label in layer_options:
            checkbox = QCheckBox(label)
            self.layer_checkboxes[layer_id] = checkbox
            layers_layout.addWidget(checkbox)

        layout.addWidget(layers_group)

        # Remember selection option
        self.remember_selection_check = QCheckBox('Remember last layer selection')
        layout.addWidget(self.remember_selection_check)

        layout.addStretch()

    def setup_appearance_tab(self):
        """Set up the Appearance settings tab."""
        layout = QVBoxLayout(self.appearance_tab)

        # Style preset group
        style_group = QGroupBox('Style Preset')
        style_layout = QFormLayout(style_group)

        self.style_preset_combo = QComboBox()
        self.style_preset_combo.addItem('Default', 'default')
        self.style_preset_combo.addItem('Satellite-Friendly', 'satellite')
        self.style_preset_combo.addItem('Grayscale', 'grayscale')
        self.style_preset_combo.addItem('Humanitarian', 'humanitarian')
        style_layout.addRow('Default Style:', self.style_preset_combo)

        layout.addWidget(style_group)

        # Panels group
        panels_group = QGroupBox('Dock Panels')
        panels_layout = QVBoxLayout(panels_group)

        self.panel_checkboxes = {}
        panel_options = [
            ('data_info', 'Show Data Info Panel on startup'),
            ('search', 'Show Search Panel on startup'),
            ('bookmarks', 'Show Bookmarks Panel on startup'),
            ('statistics', 'Show Statistics Panel on startup'),
        ]

        for panel_id, label in panel_options:
            checkbox = QCheckBox(label)
            self.panel_checkboxes[panel_id] = checkbox
            panels_layout.addWidget(checkbox)

        layout.addWidget(panels_group)

        layout.addStretch()

    def setup_api_keys_tab(self):
        """Set up the API Keys settings tab."""
        layout = QVBoxLayout(self.api_keys_tab)

        # ACLED API group
        acled_group = QGroupBox('ACLED (Armed Conflict Location & Event Data)')
        acled_layout = QVBoxLayout(acled_group)

        # Info label
        info_label = QLabel(
            'ACLED provides conflict event data. Create a free myACLED account at:\n'
            '<a href="https://acleddata.com/">https://acleddata.com/</a>\n\n'
            'Use your myACLED account email and password below.'
        )
        info_label.setOpenExternalLinks(True)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        acled_layout.addWidget(info_label)

        # Email field
        form_layout = QFormLayout()

        self.acled_email_edit = QLineEdit()
        self.acled_email_edit.setPlaceholderText('Your myACLED account email...')
        form_layout.addRow('Email:', self.acled_email_edit)

        # Password field (ACLED uses account password for OAuth)
        self.acled_api_key_edit = QLineEdit()
        self.acled_api_key_edit.setPlaceholderText('Your myACLED account password...')
        self.acled_api_key_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow('Password:', self.acled_api_key_edit)

        acled_layout.addLayout(form_layout)

        # Show/Hide password checkbox
        self.show_api_key_check = QCheckBox('Show password')
        self.show_api_key_check.toggled.connect(self._toggle_api_key_visibility)
        acled_layout.addWidget(self.show_api_key_check)

        # Status label
        self.acled_status_label = QLabel('')
        self.acled_status_label.setStyleSheet("font-style: italic;")
        acled_layout.addWidget(self.acled_status_label)

        layout.addWidget(acled_group)

        # Note about API access
        note_group = QGroupBox('Note')
        note_layout = QVBoxLayout(note_group)
        note_label = QLabel(
            'ACLED requires a free account for API access.\n'
            '1. Go to acleddata.com and create an account\n'
            '2. Enter your account email and password above\n'
            '3. Your credentials are stored locally and used for OAuth authentication'
        )
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #666;")
        note_layout.addWidget(note_label)
        layout.addWidget(note_group)

        layout.addStretch()

    def _toggle_api_key_visibility(self, show):
        """Toggle API key visibility."""
        if show:
            self.acled_api_key_edit.setEchoMode(QLineEdit.Normal)
        else:
            self.acled_api_key_edit.setEchoMode(QLineEdit.Password)

    def load_settings(self):
        """Load settings into the dialog."""
        # General tab
        self.server_url_edit.setText(self.settings_manager.get_server_url())
        self.auto_update_check.setChecked(self.settings_manager.get_auto_update_check())

        # Label language
        language = self.settings_manager.get_label_language()
        index = self.label_language_combo.findData(language)
        if index >= 0:
            self.label_language_combo.setCurrentIndex(index)

        # Layers tab
        default_layers = self.settings_manager.get_default_layers()
        for layer_id, checkbox in self.layer_checkboxes.items():
            checkbox.setChecked(layer_id in default_layers)

        self.remember_selection_check.setChecked(
            self.settings_manager.get_remember_layer_selection()
        )

        # Appearance tab
        preset = self.settings_manager.get_style_preset()
        index = self.style_preset_combo.findData(preset)
        if index >= 0:
            self.style_preset_combo.setCurrentIndex(index)

        # Panel visibility
        for panel_id, checkbox in self.panel_checkboxes.items():
            checkbox.setChecked(self.settings_manager.get_panel_visibility(panel_id))

        # API Keys tab
        self.acled_email_edit.setText(self.settings_manager.get_acled_email() or '')
        self.acled_api_key_edit.setText(self.settings_manager.get_acled_api_key() or '')
        self._update_acled_status()

    def _update_acled_status(self):
        """Update ACLED credentials status label."""
        if self.settings_manager.has_acled_credentials():
            self.acled_status_label.setText('Status: Credentials configured')
            self.acled_status_label.setStyleSheet("color: #27ae60; font-style: italic;")
        else:
            self.acled_status_label.setText('Status: No credentials configured')
            self.acled_status_label.setStyleSheet("color: #e67e22; font-style: italic;")

    def save_settings(self):
        """Save settings from the dialog."""
        # General tab
        self.settings_manager.set_server_url(self.server_url_edit.text())
        self.settings_manager.set_auto_update_check(self.auto_update_check.isChecked())
        self.settings_manager.set_label_language(
            self.label_language_combo.currentData()
        )

        # Layers tab
        selected_layers = [
            layer_id for layer_id, checkbox in self.layer_checkboxes.items()
            if checkbox.isChecked()
        ]
        self.settings_manager.set_default_layers(selected_layers)
        self.settings_manager.set_remember_layer_selection(
            self.remember_selection_check.isChecked()
        )

        # Appearance tab
        self.settings_manager.set_style_preset(
            self.style_preset_combo.currentData()
        )

        # Panel visibility
        for panel_id, checkbox in self.panel_checkboxes.items():
            self.settings_manager.set_panel_visibility(panel_id, checkbox.isChecked())

        # API Keys tab
        self.settings_manager.set_acled_email(self.acled_email_edit.text().strip())
        self.settings_manager.set_acled_api_key(self.acled_api_key_edit.text().strip())

    def restore_defaults(self):
        """Restore default settings."""
        reply = QMessageBox.question(
            self, 'Restore Defaults',
            'Are you sure you want to restore all settings to their default values?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.settings_manager.reset_to_defaults()
            self.load_settings()

    def accept(self):
        """Handle dialog acceptance."""
        self.save_settings()
        super().accept()
