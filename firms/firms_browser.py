# -*- coding: utf-8 -*-
"""
NASA FIRMS Browser Dialog for Ethiopia Data Loader.

Provides a UI for browsing and downloading NASA fire/hotspot data for Ethiopia.
"""

import os
from datetime import datetime

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QGroupBox, QLabel, QComboBox, QPushButton, QSpinBox,
    QProgressBar, QMessageBox, QFormLayout, QSlider,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsVectorLayer, QgsProject, QgsMarkerSymbol,
    QgsCategorizedSymbolRenderer, QgsRendererCategory
)

from .firms_client import FIRMSClient


class FIRMSBrowserDialog(QDialog):
    """Dialog for browsing NASA FIRMS fire data for Sudan."""

    def __init__(self, iface, settings_manager=None, parent=None):
        """
        Initialize the FIRMS browser dialog.

        :param iface: QGIS interface instance
        :param settings_manager: Settings manager (optional)
        :param parent: Parent widget
        """
        super().__init__(parent)
        self.iface = iface
        self.settings_manager = settings_manager
        self.client = FIRMSClient()
        self.current_fires = []
        self.pending_layers = []

        self.setWindowTitle('NASA FIRMS Fire Data - Sudan')
        self.setMinimumSize(700, 600)

        self._load_api_key()
        self.setup_ui()
        self.connect_signals()

    def _load_api_key(self):
        """Load API key from settings if available."""
        if self.settings_manager:
            api_key = self.settings_manager.get('firms_api_key', '')
            if api_key:
                self.client.set_api_key(api_key)

    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel('NASA FIRMS - Fire Information for Resource Management')
        header.setStyleSheet('font-size: 16px; font-weight: bold; padding: 10px;')
        layout.addWidget(header)

        # API key status/input
        api_group = QGroupBox('API Configuration')
        api_layout = QFormLayout(api_group)

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText('Optional: Enter NASA FIRMS API key for extended data')
        self.api_key_input.setEchoMode(QLineEdit.Password)
        if self.client.has_api_key():
            self.api_key_input.setText('********')
        api_layout.addRow('API Key:', self.api_key_input)

        api_info = QLabel(
            'Get a free API key at: firms.modaps.eosdis.nasa.gov/api/area\n'
            'Without API key, limited data is available.'
        )
        api_info.setStyleSheet('color: gray; font-style: italic;')
        api_layout.addRow('', api_info)

        layout.addWidget(api_group)

        # Data source selection
        source_group = QGroupBox('Data Source')
        source_layout = QFormLayout(source_group)

        self.source_combo = QComboBox()
        for source in self.client.get_data_sources():
            info = self.client.get_data_source_info(source)
            self.source_combo.addItem(f"{info['name']} ({info['resolution']})", source)
        source_layout.addRow('Satellite:', self.source_combo)

        layout.addWidget(source_group)

        # Time range
        time_group = QGroupBox('Time Range')
        time_layout = QFormLayout(time_group)

        self.time_combo = QComboBox()
        for time_key in self.client.get_time_ranges():
            info = self.client.get_time_range_info(time_key)
            self.time_combo.addItem(info['label'], time_key)
        time_layout.addRow('Period:', self.time_combo)

        layout.addWidget(time_group)

        # Confidence filter
        conf_group = QGroupBox('Confidence Filter')
        conf_layout = QHBoxLayout(conf_group)

        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(0, 100)
        self.conf_slider.setValue(0)
        self.conf_slider.valueChanged.connect(self._update_conf_label)
        conf_layout.addWidget(self.conf_slider)

        self.conf_label = QLabel('0% (All fires)')
        conf_layout.addWidget(self.conf_label)

        layout.addWidget(conf_group)

        # Fetch button
        btn_layout = QHBoxLayout()

        self.fetch_btn = QPushButton('Fetch Fire Data')
        self.fetch_btn.clicked.connect(self._fetch_data)
        btn_layout.addWidget(self.fetch_btn)

        self.add_to_map_btn = QPushButton('Fetch && Add to Map')
        self.add_to_map_btn.clicked.connect(lambda: self._fetch_data(add_to_map=True))
        btn_layout.addWidget(self.add_to_map_btn)

        layout.addLayout(btn_layout)

        # Statistics
        stats_group = QGroupBox('Fire Statistics')
        stats_layout = QFormLayout(stats_group)

        self.stats_labels = {}
        for stat_name in ['Total Fires', 'High Confidence', 'Nominal Confidence',
                          'Low Confidence', 'Date Range', 'Avg Fire Power']:
            label = QLabel('N/A')
            stats_layout.addRow(f'{stat_name}:', label)
            self.stats_labels[stat_name] = label

        layout.addWidget(stats_group)

        # Fire data table
        data_group = QGroupBox('Fire Detections')
        data_layout = QVBoxLayout(data_group)

        self.fire_table = QTableWidget()
        self.fire_table.setColumnCount(6)
        self.fire_table.setHorizontalHeaderLabels([
            'Date', 'Time', 'Lat', 'Lon', 'Confidence', 'FRP'
        ])
        self.fire_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.fire_table.setAlternatingRowColors(True)
        data_layout.addWidget(self.fire_table)

        layout.addWidget(data_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel('Ready')
        self.status_label.setStyleSheet('color: gray;')
        layout.addWidget(self.status_label)

        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.accept)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)

    def connect_signals(self):
        """Connect client signals."""
        self.client.data_loaded.connect(self._on_data_loaded)
        self.client.error_occurred.connect(self._on_error)
        self.client.progress_update.connect(self._on_progress)

    def _update_conf_label(self, value):
        """Update confidence label."""
        if value == 0:
            self.conf_label.setText('0% (All fires)')
        elif value < 30:
            self.conf_label.setText(f'{value}% (Low+)')
        elif value < 80:
            self.conf_label.setText(f'{value}% (Nominal+)')
        else:
            self.conf_label.setText(f'{value}% (High only)')

    def _fetch_data(self, add_to_map=False):
        """Fetch fire data."""
        # Update API key if changed
        api_key = self.api_key_input.text()
        if api_key and api_key != '********':
            self.client.set_api_key(api_key)
            if self.settings_manager:
                self.settings_manager.set('firms_api_key', api_key)

        source = self.source_combo.currentData()
        time_range = self.time_combo.currentData()
        min_confidence = self.conf_slider.value()

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText('Fetching fire data...')

        self.current_fires = self.client.fetch_fire_data(
            source=source,
            time_range=time_range,
            min_confidence=min_confidence
        )

        if self.current_fires and add_to_map:
            self._prepare_layer()

        self.progress_bar.setVisible(False)

    def _on_data_loaded(self, fires):
        """Handle data loaded signal."""
        self.current_fires = fires
        self._update_table()
        self._update_statistics()

        self.status_label.setText(f'Loaded {len(fires)} fire detections')

    def _on_error(self, error):
        """Handle error signal."""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f'Error: {error}')
        QMessageBox.warning(self, 'Error', error)

    def _on_progress(self, message):
        """Handle progress update."""
        self.status_label.setText(message)

    def _update_table(self):
        """Update fire data table."""
        self.fire_table.setRowCount(len(self.current_fires))

        for row, fire in enumerate(self.current_fires):
            self.fire_table.setItem(row, 0, QTableWidgetItem(fire.get('acq_date', '')))
            self.fire_table.setItem(row, 1, QTableWidgetItem(fire.get('acq_time', '')))
            self.fire_table.setItem(row, 2, QTableWidgetItem(f"{fire.get('latitude', 0):.4f}"))
            self.fire_table.setItem(row, 3, QTableWidgetItem(f"{fire.get('longitude', 0):.4f}"))

            # Confidence with color
            conf = fire.get('confidence', 0)
            conf_item = QTableWidgetItem(str(conf))
            if conf >= 80:
                conf_item.setForeground(QColor('#e74c3c'))
            elif conf >= 30:
                conf_item.setForeground(QColor('#e67e22'))
            else:
                conf_item.setForeground(QColor('#f1c40f'))
            self.fire_table.setItem(row, 4, conf_item)

            self.fire_table.setItem(row, 5, QTableWidgetItem(f"{fire.get('frp', 0):.1f}"))

    def _update_statistics(self):
        """Update statistics display."""
        stats = self.client.get_statistics(self.current_fires)

        if stats:
            self.stats_labels['Total Fires'].setText(str(stats.get('total_fires', 0)))

            by_conf = stats.get('by_confidence', {})
            self.stats_labels['High Confidence'].setText(str(by_conf.get('high', 0)))
            self.stats_labels['Nominal Confidence'].setText(str(by_conf.get('nominal', 0)))
            self.stats_labels['Low Confidence'].setText(str(by_conf.get('low', 0)))

            date_range = stats.get('date_range', {})
            self.stats_labels['Date Range'].setText(
                f"{date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}"
            )

            self.stats_labels['Avg Fire Power'].setText(f"{stats.get('avg_frp', 0):.1f} MW")
        else:
            for label in self.stats_labels.values():
                label.setText('N/A')

    def _prepare_layer(self):
        """Prepare layer for adding to map."""
        if not self.current_fires:
            return

        geojson = self.client.fires_to_geojson(self.current_fires)
        filepath = self.client.save_geojson(geojson)

        source = self.source_combo.currentText()
        time_range = self.time_combo.currentText()

        self.pending_layers.append({
            'file_path': filepath,
            'layer_name': f"FIRMS Fires - {source} ({time_range})",
            'fire_count': len(self.current_fires)
        })

    def get_pending_layers(self):
        """Get pending layers to add."""
        return self.pending_layers

    def add_layer_to_map(self, file_path, layer_name, fire_count):
        """
        Add fire layer to map.

        :returns: Tuple of (success, layer_name or error)
        """
        try:
            layer = QgsVectorLayer(file_path, layer_name, 'ogr')

            if not layer.isValid():
                return False, f"Failed to load layer: {file_path}"

            # Apply categorized styling by confidence
            self._style_fire_layer(layer)

            QgsProject.instance().addMapLayer(layer)
            return True, layer_name

        except Exception as e:
            return False, str(e)

    def _style_fire_layer(self, layer):
        """Apply fire-appropriate styling to layer."""
        categories = []

        # High confidence - red
        high_symbol = QgsMarkerSymbol.createSimple({
            'name': 'circle',
            'color': '#e74c3c',
            'size': '4',
            'outline_color': '#c0392b',
            'outline_width': '0.5'
        })
        categories.append(QgsRendererCategory('high', high_symbol, 'High Confidence'))

        # Nominal confidence - orange
        nom_symbol = QgsMarkerSymbol.createSimple({
            'name': 'circle',
            'color': '#e67e22',
            'size': '3',
            'outline_color': '#d35400',
            'outline_width': '0.5'
        })
        categories.append(QgsRendererCategory('nominal', nom_symbol, 'Nominal Confidence'))

        # Low confidence - yellow
        low_symbol = QgsMarkerSymbol.createSimple({
            'name': 'circle',
            'color': '#f1c40f',
            'size': '2.5',
            'outline_color': '#f39c12',
            'outline_width': '0.5'
        })
        categories.append(QgsRendererCategory('low', low_symbol, 'Low Confidence'))

        renderer = QgsCategorizedSymbolRenderer('confidence_level', categories)
        layer.setRenderer(renderer)
        layer.triggerRepaint()
