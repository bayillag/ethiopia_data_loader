# -*- coding: utf-8 -*-
"""
Layer Selection Dialog for Ethiopia Data Loader.

Allows users to choose which layers to load.
"""

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QCheckBox,
    QPushButton, QGroupBox, QLabel, QDialogButtonBox
)
from qgis.PyQt.QtCore import Qt


class LayerSelectionDialog(QDialog):
    """Dialog for selecting which Sudan layers to load."""

    # Layer definitions
    LAYERS = [
        {
            'id': 'admin0',
            'name': 'Admin 0 - Country Boundary',
            'description': 'Sudan country outline',
            'default': True
        },
        {
            'id': 'admin1',
            'name': 'Admin 1 - States',
            'description': '18 States of Sudan',
            'default': True
        },
        {
            'id': 'admin2',
            'name': 'Admin 2 - Localities',
            'description': 'Locality-level divisions',
            'default': True
        },
        {
            'id': 'admin_lines',
            'name': 'Administrative Lines',
            'description': 'Boundary lines',
            'default': False
        },
        {
            'id': 'admin_points',
            'name': 'Administrative Points',
            'description': 'Capital and admin centers',
            'default': False
        },
    ]

    def __init__(self, settings_manager=None, parent=None):
        """
        Initialize the layer selection dialog.

        :param settings_manager: SettingsManager instance (optional)
        :param parent: Parent widget
        """
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle('Select Layers to Load')
        self.setMinimumWidth(400)
        self.setup_ui()
        self.load_selection()

    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Header
        header_label = QLabel('Select which Sudan data layers to load:')
        header_label.setStyleSheet('font-weight: bold; margin-bottom: 10px;')
        layout.addWidget(header_label)

        # Layers group
        layers_group = QGroupBox('Available Layers')
        layers_layout = QVBoxLayout(layers_group)

        self.checkboxes = {}
        for layer in self.LAYERS:
            checkbox = QCheckBox(layer['name'])
            checkbox.setToolTip(layer['description'])
            checkbox.setChecked(layer['default'])
            self.checkboxes[layer['id']] = checkbox
            layers_layout.addWidget(checkbox)

        layout.addWidget(layers_group)

        # Quick selection buttons
        button_layout = QHBoxLayout()

        select_all_btn = QPushButton('Select All')
        select_all_btn.clicked.connect(self.select_all)
        button_layout.addWidget(select_all_btn)

        select_none_btn = QPushButton('Select None')
        select_none_btn.clicked.connect(self.select_none)
        button_layout.addWidget(select_none_btn)

        select_defaults_btn = QPushButton('Defaults')
        select_defaults_btn.clicked.connect(self.select_defaults)
        button_layout.addWidget(select_defaults_btn)

        layout.addLayout(button_layout)

        # Remember selection checkbox
        self.remember_check = QCheckBox('Remember my selection')
        if self.settings_manager:
            self.remember_check.setChecked(
                self.settings_manager.get_remember_layer_selection()
            )
        layout.addWidget(self.remember_check)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_selection(self):
        """Load previously saved selection if available."""
        if not self.settings_manager:
            return

        if self.settings_manager.get_remember_layer_selection():
            last_selection = self.settings_manager.get_last_layer_selection()
            if last_selection:
                for layer_id, checkbox in self.checkboxes.items():
                    checkbox.setChecked(layer_id in last_selection)

    def select_all(self):
        """Select all layers."""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)

    def select_none(self):
        """Deselect all layers."""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)

    def select_defaults(self):
        """Reset to default selection."""
        for layer in self.LAYERS:
            self.checkboxes[layer['id']].setChecked(layer['default'])

    def get_selected_layers(self):
        """
        Get the list of selected layer IDs.

        :returns: List of selected layer IDs
        """
        return [
            layer_id for layer_id, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        ]

    def accept(self):
        """Handle dialog acceptance."""
        if self.settings_manager:
            # Save remember preference
            self.settings_manager.set_remember_layer_selection(
                self.remember_check.isChecked()
            )

            # Save selection if remember is enabled
            if self.remember_check.isChecked():
                self.settings_manager.set_last_layer_selection(
                    self.get_selected_layers()
                )

        super().accept()
