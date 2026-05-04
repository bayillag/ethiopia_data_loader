# -*- coding: utf-8 -*-
"""
OSM Browser Dialog for Ethiopia Data Loader.

Provides a UI for browsing and downloading OpenStreetMap data for Ethiopia.
"""

import json
import os
from datetime import datetime

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QGroupBox, QLabel, QComboBox, QPushButton, QTextEdit,
    QProgressBar, QMessageBox, QListWidget, QListWidgetItem,
    QCheckBox, QSplitter, QFormLayout, QPlainTextEdit
)
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QFont, QColor
from qgis.core import (
    QgsVectorLayer, QgsProject, QgsSymbol,
    QgsCategorizedSymbolRenderer, QgsRendererCategory,
    QgsMarkerSymbol, QgsLineSymbol, QgsFillSymbol
)

from .osm_client import OSMClient


class OSMBrowserDialog(QDialog):
    """Dialog for browsing and downloading OSM data for Sudan."""

    def __init__(self, iface, parent=None):
        """
        Initialize the OSM browser dialog.

        :param iface: QGIS interface instance
        :param parent: Parent widget
        """
        super().__init__(parent)
        self.iface = iface
        self.client = OSMClient()
        self.pending_layers = []

        self.setWindowTitle('OpenStreetMap Data Browser - Sudan')
        self.setMinimumSize(800, 600)
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel('OpenStreetMap / Overpass API')
        header.setStyleSheet('font-size: 16px; font-weight: bold; padding: 10px;')
        layout.addWidget(header)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._create_poi_tab(), 'Points of Interest')
        tabs.addTab(self._create_infrastructure_tab(), 'Infrastructure')
        tabs.addTab(self._create_custom_tab(), 'Custom Query')
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
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _create_poi_tab(self):
        """Create the Points of Interest tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Splitter for category list and info
        splitter = QSplitter(Qt.Horizontal)

        # Left: Category selection
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # State filter
        state_group = QGroupBox('Location Filter')
        state_layout = QFormLayout(state_group)

        self.poi_state_combo = QComboBox()
        self.poi_state_combo.addItem('All of Sudan', None)
        for state in sorted(self.client.get_states()):
            self.poi_state_combo.addItem(state, state)
        state_layout.addRow('State:', self.poi_state_combo)

        left_layout.addWidget(state_group)

        # Category list
        cat_group = QGroupBox('POI Categories')
        cat_layout = QVBoxLayout(cat_group)

        self.poi_list = QListWidget()
        for category in self.client.get_categories():
            item = QListWidgetItem(category)
            info = self.client.get_category_info(category)
            item.setToolTip(info.get('description', ''))
            # Set color indicator
            color = info.get('color', '#95a5a6')
            item.setForeground(QColor(color))
            self.poi_list.addItem(item)

        self.poi_list.currentItemChanged.connect(self._on_poi_selected)
        cat_layout.addWidget(self.poi_list)

        left_layout.addWidget(cat_group)
        splitter.addWidget(left_widget)

        # Right: Info and actions
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Category info
        info_group = QGroupBox('Category Information')
        info_layout = QVBoxLayout(info_group)

        self.poi_info_label = QLabel('Select a category to see details')
        self.poi_info_label.setWordWrap(True)
        info_layout.addWidget(self.poi_info_label)

        right_layout.addWidget(info_group)

        # Actions
        action_group = QGroupBox('Actions')
        action_layout = QVBoxLayout(action_group)

        self.poi_download_btn = QPushButton('Download Selected Category')
        self.poi_download_btn.setEnabled(False)
        self.poi_download_btn.clicked.connect(self._download_poi)
        action_layout.addWidget(self.poi_download_btn)

        self.poi_add_to_map_btn = QPushButton('Download && Add to Map')
        self.poi_add_to_map_btn.setEnabled(False)
        self.poi_add_to_map_btn.clicked.connect(lambda: self._download_poi(add_to_map=True))
        action_layout.addWidget(self.poi_add_to_map_btn)

        right_layout.addWidget(action_group)

        # Results
        results_group = QGroupBox('Results')
        results_layout = QVBoxLayout(results_group)

        self.poi_results_label = QLabel('No data loaded')
        results_layout.addWidget(self.poi_results_label)

        right_layout.addWidget(results_group)
        right_layout.addStretch()

        splitter.addWidget(right_widget)
        splitter.setSizes([300, 400])

        layout.addWidget(splitter)
        return widget

    def _create_infrastructure_tab(self):
        """Create the Infrastructure tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left: Category selection
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # State filter
        state_group = QGroupBox('Location Filter')
        state_layout = QFormLayout(state_group)

        self.infra_state_combo = QComboBox()
        self.infra_state_combo.addItem('All of Sudan', None)
        for state in sorted(self.client.get_states()):
            self.infra_state_combo.addItem(state, state)
        state_layout.addRow('State:', self.infra_state_combo)

        left_layout.addWidget(state_group)

        # Category list
        cat_group = QGroupBox('Infrastructure Categories')
        cat_layout = QVBoxLayout(cat_group)

        self.infra_list = QListWidget()
        for category in self.client.get_infrastructure_categories():
            item = QListWidgetItem(category)
            info = self.client.get_category_info(category)
            item.setToolTip(info.get('description', ''))
            color = info.get('color', '#95a5a6')
            item.setForeground(QColor(color))
            self.infra_list.addItem(item)

        self.infra_list.currentItemChanged.connect(self._on_infra_selected)
        cat_layout.addWidget(self.infra_list)

        # Warning for large datasets
        warning_label = QLabel(
            'Note: Some infrastructure categories (e.g., All Roads, Buildings) '
            'may return very large datasets. Consider filtering by state.'
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet('color: orange; font-style: italic;')
        cat_layout.addWidget(warning_label)

        left_layout.addWidget(cat_group)
        splitter.addWidget(left_widget)

        # Right: Info and actions
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Category info
        info_group = QGroupBox('Category Information')
        info_layout = QVBoxLayout(info_group)

        self.infra_info_label = QLabel('Select a category to see details')
        self.infra_info_label.setWordWrap(True)
        info_layout.addWidget(self.infra_info_label)

        right_layout.addWidget(info_group)

        # Actions
        action_group = QGroupBox('Actions')
        action_layout = QVBoxLayout(action_group)

        self.infra_download_btn = QPushButton('Download Selected Category')
        self.infra_download_btn.setEnabled(False)
        self.infra_download_btn.clicked.connect(self._download_infrastructure)
        action_layout.addWidget(self.infra_download_btn)

        self.infra_add_to_map_btn = QPushButton('Download && Add to Map')
        self.infra_add_to_map_btn.setEnabled(False)
        self.infra_add_to_map_btn.clicked.connect(lambda: self._download_infrastructure(add_to_map=True))
        action_layout.addWidget(self.infra_add_to_map_btn)

        right_layout.addWidget(action_group)

        # Results
        results_group = QGroupBox('Results')
        results_layout = QVBoxLayout(results_group)

        self.infra_results_label = QLabel('No data loaded')
        results_layout.addWidget(self.infra_results_label)

        right_layout.addWidget(results_group)
        right_layout.addStretch()

        splitter.addWidget(right_widget)
        splitter.setSizes([300, 400])

        layout.addWidget(splitter)
        return widget

    def _create_custom_tab(self):
        """Create the Custom Query tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Instructions
        instructions = QLabel(
            'Enter a custom Overpass QL query. The query will be executed against '
            'the Overpass API and results will be converted to GeoJSON.\n\n'
            'Example query for hospitals in Khartoum:'
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Query editor
        self.query_editor = QPlainTextEdit()
        self.query_editor.setPlaceholderText('Enter Overpass QL query here...')
        font = QFont('Consolas', 10)
        self.query_editor.setFont(font)

        # Default example query
        example_query = '''[out:json][timeout:180];
area["name"="Sudan"]->.sudan;
(
  node["amenity"="hospital"](area.sudan);
  way["amenity"="hospital"](area.sudan);
);
out center body;
>;
out skel qt;'''
        self.query_editor.setPlainText(example_query)
        layout.addWidget(self.query_editor)

        # Query templates
        templates_group = QGroupBox('Query Templates')
        templates_layout = QHBoxLayout(templates_group)

        templates = [
            ('Hospitals', 'amenity=hospital'),
            ('Schools', 'amenity=school'),
            ('Roads', 'highway~"."'),
            ('Water', 'natural=water')
        ]

        for name, tag in templates:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, t=tag: self._insert_template(t))
            templates_layout.addWidget(btn)

        layout.addWidget(templates_group)

        # Execute button
        btn_layout = QHBoxLayout()

        self.custom_execute_btn = QPushButton('Execute Query')
        self.custom_execute_btn.clicked.connect(self._execute_custom_query)
        btn_layout.addWidget(self.custom_execute_btn)

        self.custom_add_btn = QPushButton('Execute && Add to Map')
        self.custom_add_btn.clicked.connect(lambda: self._execute_custom_query(add_to_map=True))
        btn_layout.addWidget(self.custom_add_btn)

        layout.addLayout(btn_layout)

        # Results
        self.custom_results_label = QLabel('No query executed')
        layout.addWidget(self.custom_results_label)

        return widget

    def connect_signals(self):
        """Connect client signals."""
        self.client.query_progress.connect(self._on_progress)
        self.client.query_complete.connect(self._on_query_complete)
        self.client.query_error.connect(self._on_query_error)

    def _on_poi_selected(self, current, previous):
        """Handle POI category selection."""
        if current:
            category = current.text()
            info = self.client.get_category_info(category)
            self.poi_info_label.setText(
                f"<b>{category}</b><br><br>"
                f"Description: {info.get('description', 'N/A')}<br>"
                f"OSM Tags: {info.get('tags', 'N/A')}"
            )
            self.poi_download_btn.setEnabled(True)
            self.poi_add_to_map_btn.setEnabled(True)
        else:
            self.poi_download_btn.setEnabled(False)
            self.poi_add_to_map_btn.setEnabled(False)

    def _on_infra_selected(self, current, previous):
        """Handle infrastructure category selection."""
        if current:
            category = current.text()
            info = self.client.get_category_info(category)
            self.infra_info_label.setText(
                f"<b>{category}</b><br><br>"
                f"Description: {info.get('description', 'N/A')}<br>"
                f"OSM Tags: {info.get('tags', 'N/A')}<br>"
                f"Geometry: {info.get('geometry', 'mixed')}"
            )
            self.infra_download_btn.setEnabled(True)
            self.infra_add_to_map_btn.setEnabled(True)
        else:
            self.infra_download_btn.setEnabled(False)
            self.infra_add_to_map_btn.setEnabled(False)

    def _on_progress(self, message):
        """Handle progress updates."""
        self.status_label.setText(message)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

    def _on_query_complete(self, geojson):
        """Handle query completion."""
        self.progress_bar.setVisible(False)
        count = len(geojson.get('features', []))
        self.status_label.setText(f'Query complete: {count} features')

    def _on_query_error(self, error):
        """Handle query errors."""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f'Error: {error}')
        QMessageBox.warning(self, 'Query Error', error)

    def _download_poi(self, add_to_map=False):
        """Download selected POI category."""
        current = self.poi_list.currentItem()
        if not current:
            return

        category = current.text()
        state = self.poi_state_combo.currentData()

        self.status_label.setText(f'Downloading {category}...')
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        # Execute query
        geojson = self.client.query_pois(category, state=state)

        if geojson:
            count = len(geojson.get('features', []))
            self.poi_results_label.setText(f'Downloaded {count} features')

            if add_to_map and count > 0:
                self._add_geojson_to_map(geojson, category, 'poi')
        else:
            self.poi_results_label.setText('Download failed')

        self.progress_bar.setVisible(False)

    def _download_infrastructure(self, add_to_map=False):
        """Download selected infrastructure category."""
        current = self.infra_list.currentItem()
        if not current:
            return

        category = current.text()
        state = self.infra_state_combo.currentData()

        self.status_label.setText(f'Downloading {category}...')
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        # Execute query
        geojson = self.client.query_infrastructure(category, state=state)

        if geojson:
            count = len(geojson.get('features', []))
            self.infra_results_label.setText(f'Downloaded {count} features')

            if add_to_map and count > 0:
                self._add_geojson_to_map(geojson, category, 'infrastructure')
        else:
            self.infra_results_label.setText('Download failed')

        self.progress_bar.setVisible(False)

    def _execute_custom_query(self, add_to_map=False):
        """Execute custom Overpass query."""
        query = self.query_editor.toPlainText().strip()
        if not query:
            QMessageBox.warning(self, 'No Query', 'Please enter an Overpass query.')
            return

        self.status_label.setText('Executing custom query...')
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        # Execute query
        geojson = self.client.query_custom(query)

        if geojson:
            count = len(geojson.get('features', []))
            self.custom_results_label.setText(f'Query returned {count} features')

            if add_to_map and count > 0:
                self._add_geojson_to_map(geojson, 'Custom OSM Query', 'custom')
        else:
            self.custom_results_label.setText('Query failed')

        self.progress_bar.setVisible(False)

    def _insert_template(self, tag):
        """Insert a query template."""
        template = f'''[out:json][timeout:180];
area["name"="Sudan"]->.sudan;
(
  node["{tag.split('=')[0] if '=' in tag else tag}"{"=" + '"' + tag.split('=')[1] + '"' if '=' in tag else '~"."'}](area.sudan);
  way["{tag.split('=')[0] if '=' in tag else tag}"{"=" + '"' + tag.split('=')[1] + '"' if '=' in tag else '~"."'}](area.sudan);
);
out center body;
>;
out skel qt;'''
        self.query_editor.setPlainText(template)

    def _add_geojson_to_map(self, geojson, layer_name, layer_type):
        """
        Add GeoJSON data as a layer to the map.

        :param geojson: GeoJSON dict
        :param layer_name: Name for the layer
        :param layer_type: Type hint for styling
        """
        # Save to temp file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"osm_{layer_name.lower().replace(' ', '_')}_{timestamp}.geojson"
        filepath = self.client.save_geojson(geojson, filename)

        # Queue for adding after dialog closes
        self.pending_layers.append({
            'file_path': filepath,
            'layer_name': f"OSM - {layer_name}",
            'layer_type': layer_type,
            'category': layer_name
        })

        self.status_label.setText(f'Layer "{layer_name}" ready to add to map')

    def get_pending_layers(self):
        """Get list of layers pending to be added."""
        return self.pending_layers

    def add_layer_to_map(self, file_path, layer_name, layer_type, category):
        """
        Actually add the layer to the map.

        :param file_path: Path to GeoJSON file
        :param layer_name: Display name for layer
        :param layer_type: Type hint for styling
        :param category: Category name for styling
        :returns: Tuple of (success, layer_name or error)
        """
        try:
            layer = QgsVectorLayer(file_path, layer_name, 'ogr')

            if not layer.isValid():
                return False, f"Failed to load {layer_name}"

            # Apply styling based on type and category
            self._style_layer(layer, layer_type, category)

            QgsProject.instance().addMapLayer(layer)
            return True, layer_name

        except Exception as e:
            return False, str(e)

    def _style_layer(self, layer, layer_type, category):
        """Apply appropriate styling to a layer."""
        geom_type = layer.geometryType()

        # Get color from category info
        info = self.client.get_category_info(category)
        color = info.get('color', '#3498db')

        if geom_type == 0:  # Point
            symbol = QgsMarkerSymbol.createSimple({
                'name': 'circle',
                'color': color,
                'size': '3',
                'outline_color': '#000000',
                'outline_width': '0.5'
            })
            layer.renderer().setSymbol(symbol)

        elif geom_type == 1:  # Line
            symbol = QgsLineSymbol.createSimple({
                'color': color,
                'width': '0.5'
            })
            layer.renderer().setSymbol(symbol)

        elif geom_type == 2:  # Polygon
            symbol = QgsFillSymbol.createSimple({
                'color': color + '40',  # Add transparency
                'outline_color': color,
                'outline_width': '0.5'
            })
            layer.renderer().setSymbol(symbol)

        layer.triggerRepaint()
