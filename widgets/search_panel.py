# -*- coding: utf-8 -*-
"""
Search Panel for Ethiopia Data Loader.

Searchable dock widget with autocomplete for finding admin areas.
"""

from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QComboBox, QLabel, QGroupBox, QCheckBox
)
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.core import QgsProject, QgsVectorLayer, QgsFeatureRequest


class SearchPanel(QDockWidget):
    """Dock widget for searching Ethiopia administrative areas."""

    # Common field names to search
    SEARCH_FIELDS = [
        'ADM1_EN', 'ADM1_AR', 'ADM1_PCODE',  # State level
        'ADM2_EN', 'ADM2_AR', 'ADM2_PCODE',  # Locality level
        'admin1Name_en', 'admin1Name_ar', 'admin1Pcode',
        'admin2Name_en', 'admin2Name_ar', 'admin2Pcode',
        'name', 'NAME', 'Name',
        'name_en', 'name_ar',
    ]

    def __init__(self, iface, parent=None):
        """
        Initialize the search panel.

        :param iface: QGIS interface instance
        :param parent: Parent widget
        """
        super().__init__('Ethiopia Search', parent)
        self.iface = iface
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        self.setup_ui()

    def setup_ui(self):
        """Set up the panel UI."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Search input
        search_group = QGroupBox('Search')
        search_layout = QVBoxLayout(search_group)

        # Search box
        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('Search states, localities...')
        self.search_edit.textChanged.connect(self.on_search_text_changed)
        self.search_edit.returnPressed.connect(self.perform_search)
        search_row.addWidget(self.search_edit)

        self.search_btn = QPushButton('Search')
        self.search_btn.clicked.connect(self.perform_search)
        search_row.addWidget(self.search_btn)

        search_layout.addLayout(search_row)

        # Search options
        options_row = QHBoxLayout()

        self.search_english_check = QCheckBox('English')
        self.search_english_check.setChecked(True)
        options_row.addWidget(self.search_english_check)

        self.search_arabic_check = QCheckBox('Arabic')
        self.search_arabic_check.setChecked(True)
        options_row.addWidget(self.search_arabic_check)

        self.search_pcode_check = QCheckBox('P-Codes')
        self.search_pcode_check.setChecked(True)
        options_row.addWidget(self.search_pcode_check)

        options_row.addStretch()
        search_layout.addLayout(options_row)

        layout.addWidget(search_group)

        # Results list
        results_group = QGroupBox('Results')
        results_layout = QVBoxLayout(results_group)

        self.results_label = QLabel('Enter a search term above')
        results_layout.addWidget(self.results_label)

        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.zoom_to_result)
        results_layout.addWidget(self.results_list)

        # Result actions
        action_row = QHBoxLayout()

        zoom_btn = QPushButton('Zoom to Selected')
        zoom_btn.clicked.connect(self.zoom_to_selected)
        action_row.addWidget(zoom_btn)

        select_btn = QPushButton('Select Feature')
        select_btn.clicked.connect(self.select_feature)
        action_row.addWidget(select_btn)

        results_layout.addLayout(action_row)

        layout.addWidget(results_group)

        layout.addStretch()

        self.setWidget(widget)

    def on_search_text_changed(self, text):
        """Handle search text changes with debouncing."""
        # Debounce the search
        self.search_timer.stop()
        if len(text) >= 2:
            self.search_timer.start(300)  # 300ms delay

    def perform_search(self):
        """Perform the search operation."""
        search_text = self.search_edit.text().strip()
        if len(search_text) < 2:
            self.results_list.clear()
            self.results_label.setText('Enter at least 2 characters')
            return

        self.results_list.clear()
        results = []

        # Determine which field types to search
        search_en = self.search_english_check.isChecked()
        search_ar = self.search_arabic_check.isChecked()
        search_pcode = self.search_pcode_check.isChecked()

        # Search through Sudan layers
        for layer in QgsProject.instance().mapLayers().values():
            if not isinstance(layer, QgsVectorLayer):
                continue

            name_lower = layer.name().lower()
            if 'sudan' not in name_lower:
                continue

            # Get searchable fields for this layer
            field_names = [f.name() for f in layer.fields()]
            search_fields = []

            for field in field_names:
                field_lower = field.lower()
                if search_en and ('_en' in field_lower or 'name' in field_lower):
                    search_fields.append(field)
                elif search_ar and '_ar' in field_lower:
                    search_fields.append(field)
                elif search_pcode and 'pcode' in field_lower:
                    search_fields.append(field)

            if not search_fields:
                # Fallback to common fields
                for f in self.SEARCH_FIELDS:
                    if f in field_names:
                        search_fields.append(f)

            # Search features
            for feature in layer.getFeatures():
                for field in search_fields:
                    value = feature[field]
                    if value and search_text.lower() in str(value).lower():
                        results.append({
                            'layer': layer,
                            'feature_id': feature.id(),
                            'field': field,
                            'value': str(value),
                            'layer_name': layer.name()
                        })
                        break  # Only add once per feature

        # Display results
        for result in results[:100]:  # Limit to 100 results
            item = QListWidgetItem(
                f"{result['value']} ({result['layer_name']})"
            )
            item.setData(Qt.UserRole, result)
            self.results_list.addItem(item)

        self.results_label.setText(f'Found {len(results)} results')

    def get_selected_result(self):
        """Get the currently selected search result."""
        current_item = self.results_list.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        return None

    def zoom_to_result(self, item):
        """Zoom to a search result."""
        result = item.data(Qt.UserRole)
        if result:
            layer = result['layer']
            feature_id = result['feature_id']

            # Get the feature
            feature = layer.getFeature(feature_id)
            if feature.hasGeometry():
                # Zoom to feature extent
                extent = feature.geometry().boundingBox()
                extent.scale(1.5)  # Add some padding
                self.iface.mapCanvas().setExtent(extent)
                self.iface.mapCanvas().refresh()

    def zoom_to_selected(self):
        """Zoom to the selected result."""
        current_item = self.results_list.currentItem()
        if current_item:
            self.zoom_to_result(current_item)

    def select_feature(self):
        """Select the feature from the search result."""
        result = self.get_selected_result()
        if result:
            layer = result['layer']
            feature_id = result['feature_id']

            # Select the feature
            layer.selectByIds([feature_id])
            self.iface.setActiveLayer(layer)
