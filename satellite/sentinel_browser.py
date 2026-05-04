# -*- coding: utf-8 -*-
"""
Sentinel Hub Browser Dialog for Ethiopia Data Loader.

Provides a UI for browsing and downloading Sentinel-2 satellite imagery for Ethiopia.
"""

import os
from datetime import datetime, timedelta

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QGroupBox, QLabel, QComboBox, QPushButton, QSpinBox,
    QProgressBar, QMessageBox, QListWidget, QListWidgetItem,
    QFormLayout, QDateEdit, QSlider, QCheckBox, QSplitter
)
from qgis.PyQt.QtCore import Qt, QDate
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsRasterLayer, QgsProject, QgsCoordinateReferenceSystem

from .sentinel_client import SentinelClient


class SentinelBrowserDialog(QDialog):
    """Dialog for browsing and downloading Sentinel-2 imagery for Ethiopia."""

    def __init__(self, iface, settings_manager, parent=None):
        """
        Initialize the Sentinel browser dialog.

        :param iface: QGIS interface instance
        :param settings_manager: Settings manager for credentials
        :param parent: Parent widget
        """
        super().__init__(parent)
        self.iface = iface
        self.settings_manager = settings_manager
        self.client = SentinelClient()
        self.scenes = []
        self.pending_layers = []

        self.setWindowTitle('Sentinel-2 Satellite Imagery - Ethiopia')
        self.setMinimumSize(900, 700)

        self._load_credentials()
        self.setup_ui()
        self.connect_signals()

    def _load_credentials(self):
        """Load Sentinel Hub credentials from settings."""
        client_id = self.settings_manager.get('sentinel_client_id', '')
        client_secret = self.settings_manager.get('sentinel_client_secret', '')
        if client_id and client_secret:
            self.client.set_credentials(client_id, client_secret)

    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Header with status
        header_layout = QHBoxLayout()
        header = QLabel('Sentinel Hub Satellite Imagery')
        header.setStyleSheet('font-size: 16px; font-weight: bold;')
        header_layout.addWidget(header)

        self.auth_status = QLabel()
        self._update_auth_status()
        header_layout.addWidget(self.auth_status)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Credentials warning if needed
        if not self.client.has_credentials():
            cred_warning = QLabel(
                'Sentinel Hub credentials not configured. '
                'Please enter your Client ID and Secret in Settings > API Keys tab.\n'
                'Get free credentials at: https://www.sentinel-hub.com/'
            )
            cred_warning.setWordWrap(True)
            cred_warning.setStyleSheet('color: orange; padding: 10px; background: #fff3cd; border-radius: 5px;')
            layout.addWidget(cred_warning)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._create_search_tab(), 'Search Scenes')
        tabs.addTab(self._create_download_tab(), 'Download Image')
        tabs.addTab(self._create_presets_tab(), 'Visualization Presets')
        layout.addWidget(tabs)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel('Ready')
        self.status_label.setStyleSheet('color: gray;')
        layout.addWidget(self.status_label)

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.auth_btn = QPushButton('Test Authentication')
        self.auth_btn.clicked.connect(self._test_auth)
        btn_layout.addWidget(self.auth_btn)

        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _create_search_tab(self):
        """Create the scene search tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Search parameters
        params_group = QGroupBox('Search Parameters')
        params_layout = QFormLayout(params_group)

        # State selection
        self.search_state_combo = QComboBox()
        self.search_state_combo.addItem('All of Sudan', None)
        for state in sorted(self.client.get_states()):
            self.search_state_combo.addItem(state, state)
        params_layout.addRow('State:', self.search_state_combo)

        # Date range
        date_layout = QHBoxLayout()

        self.search_start_date = QDateEdit()
        self.search_start_date.setCalendarPopup(True)
        self.search_start_date.setDate(QDate.currentDate().addDays(-30))
        date_layout.addWidget(QLabel('From:'))
        date_layout.addWidget(self.search_start_date)

        self.search_end_date = QDateEdit()
        self.search_end_date.setCalendarPopup(True)
        self.search_end_date.setDate(QDate.currentDate())
        date_layout.addWidget(QLabel('To:'))
        date_layout.addWidget(self.search_end_date)

        params_layout.addRow('Date Range:', date_layout)

        # Cloud cover
        cloud_layout = QHBoxLayout()
        self.cloud_slider = QSlider(Qt.Horizontal)
        self.cloud_slider.setRange(0, 100)
        self.cloud_slider.setValue(30)
        self.cloud_slider.valueChanged.connect(self._update_cloud_label)
        cloud_layout.addWidget(self.cloud_slider)

        self.cloud_label = QLabel('30%')
        cloud_layout.addWidget(self.cloud_label)

        params_layout.addRow('Max Cloud Cover:', cloud_layout)

        # Result limit
        self.result_limit = QSpinBox()
        self.result_limit.setRange(1, 100)
        self.result_limit.setValue(20)
        params_layout.addRow('Max Results:', self.result_limit)

        layout.addWidget(params_group)

        # Search button
        search_btn = QPushButton('Search Scenes')
        search_btn.clicked.connect(self._search_scenes)
        layout.addWidget(search_btn)

        # Results
        results_group = QGroupBox('Search Results')
        results_layout = QVBoxLayout(results_group)

        self.scenes_list = QListWidget()
        self.scenes_list.currentItemChanged.connect(self._on_scene_selected)
        results_layout.addWidget(self.scenes_list)

        # Scene info
        self.scene_info_label = QLabel('Select a scene to see details')
        self.scene_info_label.setWordWrap(True)
        results_layout.addWidget(self.scene_info_label)

        layout.addWidget(results_group)

        return widget

    def _create_download_tab(self):
        """Create the download tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Area selection
        area_group = QGroupBox('Area Selection')
        area_layout = QFormLayout(area_group)

        self.download_state_combo = QComboBox()
        self.download_state_combo.addItem('All of Sudan', None)
        for state in sorted(self.client.get_states()):
            self.download_state_combo.addItem(state, state)
        area_layout.addRow('State:', self.download_state_combo)

        # Custom bbox option
        self.use_canvas_extent = QCheckBox('Use current map canvas extent')
        area_layout.addRow('', self.use_canvas_extent)

        layout.addWidget(area_group)

        # Date selection
        date_group = QGroupBox('Date Range')
        date_layout = QFormLayout(date_group)

        date_range_layout = QHBoxLayout()

        self.download_start_date = QDateEdit()
        self.download_start_date.setCalendarPopup(True)
        self.download_start_date.setDate(QDate.currentDate().addDays(-30))
        date_range_layout.addWidget(QLabel('From:'))
        date_range_layout.addWidget(self.download_start_date)

        self.download_end_date = QDateEdit()
        self.download_end_date.setCalendarPopup(True)
        self.download_end_date.setDate(QDate.currentDate())
        date_range_layout.addWidget(QLabel('To:'))
        date_range_layout.addWidget(self.download_end_date)

        date_layout.addRow('Date Range:', date_range_layout)

        layout.addWidget(date_group)

        # Visualization
        vis_group = QGroupBox('Visualization')
        vis_layout = QFormLayout(vis_group)

        self.preset_combo = QComboBox()
        for preset in self.client.get_presets():
            info = self.client.get_preset_info(preset)
            self.preset_combo.addItem(preset, preset)
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        vis_layout.addRow('Preset:', self.preset_combo)

        self.preset_desc_label = QLabel()
        self.preset_desc_label.setWordWrap(True)
        self.preset_desc_label.setStyleSheet('color: gray;')
        vis_layout.addRow('', self.preset_desc_label)

        self._on_preset_changed(self.preset_combo.currentText())

        layout.addWidget(vis_group)

        # Output options
        output_group = QGroupBox('Output Options')
        output_layout = QFormLayout(output_group)

        size_layout = QHBoxLayout()
        self.output_width = QSpinBox()
        self.output_width.setRange(256, 4096)
        self.output_width.setValue(1024)
        size_layout.addWidget(QLabel('Width:'))
        size_layout.addWidget(self.output_width)

        self.output_height = QSpinBox()
        self.output_height.setRange(256, 4096)
        self.output_height.setValue(1024)
        size_layout.addWidget(QLabel('Height:'))
        size_layout.addWidget(self.output_height)

        output_layout.addRow('Size (px):', size_layout)

        layout.addWidget(output_group)

        # Download button
        btn_layout = QHBoxLayout()

        download_btn = QPushButton('Download Image')
        download_btn.clicked.connect(self._download_image)
        btn_layout.addWidget(download_btn)

        download_add_btn = QPushButton('Download && Add to Map')
        download_add_btn.clicked.connect(lambda: self._download_image(add_to_map=True))
        btn_layout.addWidget(download_add_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

        return widget

    def _create_presets_tab(self):
        """Create the presets info tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info_label = QLabel(
            'Sentinel-2 provides multispectral imagery that can be visualized in different ways '
            'to highlight various features on the ground. Select a preset to learn more.'
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Preset list with descriptions
        presets_group = QGroupBox('Available Visualization Presets')
        presets_layout = QVBoxLayout(presets_group)

        for preset_name, preset_info in self.client.VISUALIZATION_PRESETS.items():
            preset_widget = QWidget()
            preset_layout = QVBoxLayout(preset_widget)

            name_label = QLabel(f"<b>{preset_name}</b>")
            preset_layout.addWidget(name_label)

            desc_label = QLabel(preset_info.get('description', ''))
            desc_label.setStyleSheet('color: gray; margin-left: 10px;')
            preset_layout.addWidget(desc_label)

            presets_layout.addWidget(preset_widget)

        presets_layout.addStretch()
        layout.addWidget(presets_group)

        # Help info
        help_group = QGroupBox('Getting Started')
        help_layout = QVBoxLayout(help_group)

        help_text = QLabel(
            '1. Create a free Sentinel Hub account at sentinel-hub.com\n'
            '2. Create an OAuth client in your dashboard\n'
            '3. Enter the Client ID and Secret in Settings > API Keys\n'
            '4. Search for scenes or download imagery directly\n\n'
            'Note: Free accounts have limited processing units per month.'
        )
        help_text.setWordWrap(True)
        help_layout.addWidget(help_text)

        layout.addWidget(help_group)

        return widget

    def connect_signals(self):
        """Connect client signals."""
        self.client.auth_complete.connect(self._on_auth_complete)
        self.client.search_complete.connect(self._on_search_complete)
        self.client.download_complete.connect(self._on_download_complete)
        self.client.error_occurred.connect(self._on_error)
        self.client.progress_update.connect(self._on_progress)

    def _update_auth_status(self):
        """Update authentication status indicator."""
        if self.client.has_credentials():
            if self.client.access_token:
                self.auth_status.setText('Authenticated')
                self.auth_status.setStyleSheet('color: green; font-weight: bold;')
            else:
                self.auth_status.setText('Credentials configured')
                self.auth_status.setStyleSheet('color: orange;')
        else:
            self.auth_status.setText('No credentials')
            self.auth_status.setStyleSheet('color: red;')

    def _update_cloud_label(self, value):
        """Update cloud cover label."""
        self.cloud_label.setText(f'{value}%')

    def _on_preset_changed(self, preset_name):
        """Handle preset selection change."""
        info = self.client.get_preset_info(preset_name)
        self.preset_desc_label.setText(info.get('description', ''))

    def _test_auth(self):
        """Test authentication."""
        if not self.client.has_credentials():
            QMessageBox.warning(
                self, 'No Credentials',
                'Please configure Sentinel Hub credentials in Settings > API Keys.'
            )
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText('Testing authentication...')

        success = self.client.authenticate()
        self._update_auth_status()

        self.progress_bar.setVisible(False)
        if success:
            self.status_label.setText('Authentication successful')
            QMessageBox.information(self, 'Success', 'Authentication successful!')
        else:
            self.status_label.setText('Authentication failed')

    def _search_scenes(self):
        """Search for Sentinel-2 scenes."""
        if not self.client.has_credentials():
            QMessageBox.warning(
                self, 'No Credentials',
                'Please configure Sentinel Hub credentials in Settings > API Keys.'
            )
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.scenes_list.clear()

        state = self.search_state_combo.currentData()
        start_date = self.search_start_date.date().toString('yyyy-MM-dd')
        end_date = self.search_end_date.date().toString('yyyy-MM-dd')
        max_cloud = self.cloud_slider.value()
        limit = self.result_limit.value()

        self.scenes = self.client.search_scenes(
            state=state,
            start_date=start_date,
            end_date=end_date,
            max_cloud_cover=max_cloud,
            limit=limit
        )

        self.progress_bar.setVisible(False)

    def _on_search_complete(self, scenes):
        """Handle search completion."""
        self.scenes_list.clear()
        for scene in scenes:
            date_str = scene.get('datetime', '')[:10]
            cloud = scene.get('cloud_cover', 0)
            item = QListWidgetItem(f"{date_str} - Cloud: {cloud:.1f}%")
            item.setData(Qt.UserRole, scene)
            self.scenes_list.addItem(item)

        self.status_label.setText(f'Found {len(scenes)} scenes')

    def _on_scene_selected(self, current, previous):
        """Handle scene selection."""
        if current:
            scene = current.data(Qt.UserRole)
            self.scene_info_label.setText(
                f"<b>Scene ID:</b> {scene.get('id', 'N/A')}<br>"
                f"<b>Date:</b> {scene.get('datetime', 'N/A')}<br>"
                f"<b>Cloud Cover:</b> {scene.get('cloud_cover', 0):.1f}%<br>"
                f"<b>Bounding Box:</b> {scene.get('bbox', [])}"
            )

    def _download_image(self, add_to_map=False):
        """Download satellite image."""
        if not self.client.has_credentials():
            QMessageBox.warning(
                self, 'No Credentials',
                'Please configure Sentinel Hub credentials in Settings > API Keys.'
            )
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        # Determine bbox
        if self.use_canvas_extent.isChecked():
            extent = self.iface.mapCanvas().extent()
            bbox = [extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()]
        else:
            state = self.download_state_combo.currentData()
            if state:
                bbox = self.client.get_bbox_for_state(state)
            else:
                bbox = self.client.SUDAN_BBOX

        start_date = self.download_start_date.date().toString('yyyy-MM-dd')
        end_date = self.download_end_date.date().toString('yyyy-MM-dd')
        preset = self.preset_combo.currentData()
        width = self.output_width.value()
        height = self.output_height.value()

        filepath = self.client.download_image(
            bbox=bbox,
            start_date=start_date,
            end_date=end_date,
            preset=preset,
            width=width,
            height=height
        )

        self.progress_bar.setVisible(False)

        if filepath and add_to_map:
            self.pending_layers.append({
                'file_path': filepath,
                'preset': preset,
                'start_date': start_date,
                'end_date': end_date
            })

    def _on_auth_complete(self, success):
        """Handle authentication completion."""
        self._update_auth_status()

    def _on_download_complete(self, filepath):
        """Handle download completion."""
        self.status_label.setText(f'Download complete: {os.path.basename(filepath)}')

    def _on_error(self, error):
        """Handle errors."""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f'Error: {error}')
        QMessageBox.warning(self, 'Error', error)

    def _on_progress(self, message):
        """Handle progress updates."""
        self.status_label.setText(message)

    def get_pending_layers(self):
        """Get pending layers to add."""
        return self.pending_layers

    def add_layer_to_map(self, file_path, preset, start_date, end_date):
        """
        Add downloaded image to map.

        :returns: Tuple of (success, layer_name or error)
        """
        try:
            layer_name = f"Sentinel-2 {preset} ({start_date} to {end_date})"
            layer = QgsRasterLayer(file_path, layer_name)

            if not layer.isValid():
                return False, f"Failed to load raster: {file_path}"

            # Set CRS
            layer.setCrs(QgsCoordinateReferenceSystem('EPSG:4326'))

            QgsProject.instance().addMapLayer(layer)
            return True, layer_name

        except Exception as e:
            return False, str(e)
