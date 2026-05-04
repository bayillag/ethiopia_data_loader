# -*- coding: utf-8 -*-
"""
Advanced Search Panel for Ethiopia Data Loader.

Provides faceted search, fuzzy matching, and search history.
"""

from datetime import datetime
from collections import deque

from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QGroupBox, QComboBox, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QCheckBox,
    QTabWidget, QFormLayout, QMessageBox, QMenu
)
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsExpression,
    QgsFeatureRequest
)

# Try to import fuzzy matching library
try:
    from difflib import SequenceMatcher
    HAS_FUZZY = True
except ImportError:
    HAS_FUZZY = False


class AdvancedSearchPanel(QDockWidget):
    """Advanced search panel with faceted search and fuzzy matching."""

    # Maximum search history entries
    MAX_HISTORY = 20

    def __init__(self, iface, settings_manager=None, parent=None):
        """
        Initialize the advanced search panel.

        :param iface: QGIS interface instance
        :param settings_manager: Settings manager instance
        :param parent: Parent widget
        """
        super().__init__('Advanced Search', parent)
        self.iface = iface
        self.settings_manager = settings_manager
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.search_history = deque(maxlen=self.MAX_HISTORY)
        self.saved_searches = []
        self.current_results = []

        self._load_history()
        self.setup_ui()

    def setup_ui(self):
        """Set up the panel UI."""
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Tab widget for search modes
        tabs = QTabWidget()
        tabs.addTab(self._create_quick_search_tab(), 'Quick Search')
        tabs.addTab(self._create_faceted_tab(), 'Faceted Search')
        tabs.addTab(self._create_history_tab(), 'History')
        layout.addWidget(tabs)

        self.setWidget(main_widget)

    def _create_quick_search_tab(self):
        """Create the quick search tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Search input
        search_group = QGroupBox('Search')
        search_layout = QVBoxLayout(search_group)

        # Text input with history dropdown
        input_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Enter search term (English or Arabic)')
        self.search_input.returnPressed.connect(self._perform_quick_search)
        input_layout.addWidget(self.search_input)

        self.history_btn = QPushButton('v')
        self.history_btn.setFixedWidth(30)
        self.history_btn.clicked.connect(self._show_history_menu)
        input_layout.addWidget(self.history_btn)

        search_layout.addLayout(input_layout)

        # Search options
        options_layout = QHBoxLayout()

        self.fuzzy_check = QCheckBox('Fuzzy matching')
        self.fuzzy_check.setChecked(True)
        self.fuzzy_check.setToolTip('Allow approximate matches for transliteration variations')
        options_layout.addWidget(self.fuzzy_check)

        self.case_check = QCheckBox('Case sensitive')
        options_layout.addWidget(self.case_check)

        options_layout.addStretch()

        search_layout.addLayout(options_layout)

        # Search button
        btn_layout = QHBoxLayout()

        search_btn = QPushButton('Search')
        search_btn.clicked.connect(self._perform_quick_search)
        btn_layout.addWidget(search_btn)

        clear_btn = QPushButton('Clear')
        clear_btn.clicked.connect(self._clear_search)
        btn_layout.addWidget(clear_btn)

        search_layout.addLayout(btn_layout)

        layout.addWidget(search_group)

        # Results
        results_group = QGroupBox('Results')
        results_layout = QVBoxLayout(results_group)

        self.results_label = QLabel('Enter a search term')
        self.results_label.setStyleSheet('color: gray;')
        results_layout.addWidget(self.results_label)

        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self._zoom_to_result)
        self.results_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self._show_result_menu)
        results_layout.addWidget(self.results_list)

        # Result actions
        result_btn_layout = QHBoxLayout()

        zoom_btn = QPushButton('Zoom to Selected')
        zoom_btn.clicked.connect(self._zoom_to_selected)
        result_btn_layout.addWidget(zoom_btn)

        select_btn = QPushButton('Select All Results')
        select_btn.clicked.connect(self._select_all_results)
        result_btn_layout.addWidget(select_btn)

        results_layout.addLayout(result_btn_layout)

        layout.addWidget(results_group)

        return widget

    def _create_faceted_tab(self):
        """Create the faceted search tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Facet filters
        facets_group = QGroupBox('Filters')
        facets_layout = QFormLayout(facets_group)

        # Layer type filter
        self.layer_type_combo = QComboBox()
        self.layer_type_combo.addItem('All Layers', None)
        self.layer_type_combo.addItem('States (Admin 1)', 'admin1')
        self.layer_type_combo.addItem('Localities (Admin 2)', 'admin2')
        self.layer_type_combo.addItem('Points', 'points')
        facets_layout.addRow('Layer Type:', self.layer_type_combo)

        # State filter
        self.state_combo = QComboBox()
        self.state_combo.addItem('All States', None)
        states = [
            'Blue Nile', 'Central Darfur', 'East Darfur', 'Gedaref',
            'Gezira', 'Kassala', 'Khartoum', 'North Darfur',
            'North Kordofan', 'Northern', 'Red Sea', 'River Nile',
            'Sennar', 'South Darfur', 'South Kordofan', 'West Darfur',
            'West Kordofan', 'White Nile'
        ]
        for state in states:
            self.state_combo.addItem(state, state)
        facets_layout.addRow('State:', self.state_combo)

        # Field to search
        self.field_combo = QComboBox()
        self.field_combo.addItem('All Fields', None)
        self.field_combo.addItem('English Name', 'en')
        self.field_combo.addItem('Arabic Name', 'ar')
        self.field_combo.addItem('P-Code', 'pcode')
        facets_layout.addRow('Field:', self.field_combo)

        layout.addWidget(facets_group)

        # Search input
        search_layout = QHBoxLayout()

        self.faceted_input = QLineEdit()
        self.faceted_input.setPlaceholderText('Search term')
        self.faceted_input.returnPressed.connect(self._perform_faceted_search)
        search_layout.addWidget(self.faceted_input)

        search_btn = QPushButton('Search')
        search_btn.clicked.connect(self._perform_faceted_search)
        search_layout.addWidget(search_btn)

        layout.addLayout(search_layout)

        # Faceted results
        self.faceted_results = QListWidget()
        self.faceted_results.itemDoubleClicked.connect(self._zoom_to_faceted_result)
        layout.addWidget(self.faceted_results)

        # Save search button
        save_btn = QPushButton('Save This Search')
        save_btn.clicked.connect(self._save_current_search)
        layout.addWidget(save_btn)

        return widget

    def _create_history_tab(self):
        """Create the search history tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Recent searches
        recent_group = QGroupBox('Recent Searches')
        recent_layout = QVBoxLayout(recent_group)

        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self._replay_search)
        recent_layout.addWidget(self.history_list)

        history_btn_layout = QHBoxLayout()

        clear_history_btn = QPushButton('Clear History')
        clear_history_btn.clicked.connect(self._clear_history)
        history_btn_layout.addWidget(clear_history_btn)

        recent_layout.addLayout(history_btn_layout)

        layout.addWidget(recent_group)

        # Saved searches
        saved_group = QGroupBox('Saved Searches')
        saved_layout = QVBoxLayout(saved_group)

        self.saved_list = QListWidget()
        self.saved_list.itemDoubleClicked.connect(self._replay_saved_search)
        saved_layout.addWidget(self.saved_list)

        saved_btn_layout = QHBoxLayout()

        delete_saved_btn = QPushButton('Delete Selected')
        delete_saved_btn.clicked.connect(self._delete_saved_search)
        saved_btn_layout.addWidget(delete_saved_btn)

        saved_layout.addLayout(saved_btn_layout)

        layout.addWidget(saved_group)

        self._refresh_history_list()

        return widget

    def _perform_quick_search(self):
        """Perform quick search across all Sudan layers."""
        query = self.search_input.text().strip()
        if not query:
            return

        self.results_list.clear()
        self.current_results = []
        use_fuzzy = self.fuzzy_check.isChecked()
        case_sensitive = self.case_check.isChecked()

        # Add to history
        self._add_to_history(query)

        # Search all Sudan layers
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and 'sudan' in layer.name().lower():
                results = self._search_layer(layer, query, use_fuzzy, case_sensitive)
                self.current_results.extend(results)

        # Display results
        self.results_label.setText(f'Found {len(self.current_results)} results')

        for result in self.current_results:
            item = QListWidgetItem(
                f"{result['name']} ({result['layer']})"
            )
            item.setData(Qt.UserRole, result)

            # Color by match quality
            if result.get('exact_match'):
                item.setForeground(QColor('#27ae60'))
            elif result.get('fuzzy_score', 0) > 0.8:
                item.setForeground(QColor('#3498db'))
            else:
                item.setForeground(QColor('#7f8c8d'))

            self.results_list.addItem(item)

    def _search_layer(self, layer, query, use_fuzzy=True, case_sensitive=False):
        """
        Search a layer for matching features.

        :param layer: QgsVectorLayer to search
        :param query: Search query
        :param use_fuzzy: Enable fuzzy matching
        :param case_sensitive: Case sensitive search
        :returns: List of result dictionaries
        """
        results = []

        # Find searchable fields
        fields = layer.fields()
        searchable_fields = []
        for field in fields:
            name = field.name()
            if any(term in name.lower() for term in ['name', 'en', 'ar', 'pcode']):
                searchable_fields.append(name)

        if not searchable_fields:
            searchable_fields = [fields[0].name()] if fields else []

        search_query = query if case_sensitive else query.lower()

        for feature in layer.getFeatures():
            for field_name in searchable_fields:
                value = feature[field_name]
                if value is None:
                    continue

                value_str = str(value)
                compare_value = value_str if case_sensitive else value_str.lower()

                # Exact match
                if search_query in compare_value:
                    results.append({
                        'name': value_str,
                        'field': field_name,
                        'layer': layer.name(),
                        'layer_id': layer.id(),
                        'feature_id': feature.id(),
                        'geometry': feature.geometry(),
                        'exact_match': True,
                        'fuzzy_score': 1.0
                    })
                    break

                # Fuzzy match
                elif use_fuzzy and HAS_FUZZY:
                    ratio = SequenceMatcher(None, search_query, compare_value).ratio()
                    if ratio > 0.6:
                        results.append({
                            'name': value_str,
                            'field': field_name,
                            'layer': layer.name(),
                            'layer_id': layer.id(),
                            'feature_id': feature.id(),
                            'geometry': feature.geometry(),
                            'exact_match': False,
                            'fuzzy_score': ratio
                        })
                        break

        # Sort by match quality
        results.sort(key=lambda x: (-x.get('exact_match', False), -x.get('fuzzy_score', 0)))

        return results

    def _perform_faceted_search(self):
        """Perform faceted search with filters."""
        query = self.faceted_input.text().strip()
        layer_type = self.layer_type_combo.currentData()
        state_filter = self.state_combo.currentData()
        field_filter = self.field_combo.currentData()

        self.faceted_results.clear()

        # Build layer filter
        results = []

        for layer in QgsProject.instance().mapLayers().values():
            if not isinstance(layer, QgsVectorLayer):
                continue

            name = layer.name().lower()
            if 'sudan' not in name:
                continue

            # Apply layer type filter
            if layer_type:
                if layer_type == 'admin1' and 'admin 1' not in name and 'states' not in name:
                    continue
                elif layer_type == 'admin2' and 'admin 2' not in name and 'localities' not in name:
                    continue
                elif layer_type == 'points' and 'points' not in name:
                    continue

            # Determine search fields
            search_fields = []
            fields = layer.fields()

            if field_filter == 'en':
                search_fields = [f.name() for f in fields if 'en' in f.name().lower()]
            elif field_filter == 'ar':
                search_fields = [f.name() for f in fields if 'ar' in f.name().lower()]
            elif field_filter == 'pcode':
                search_fields = [f.name() for f in fields if 'pcode' in f.name().lower()]
            else:
                search_fields = [f.name() for f in fields]

            # Search
            for feature in layer.getFeatures():
                # Apply state filter
                if state_filter:
                    state_value = None
                    for fname in ['ADM1_EN', 'admin1Name_en', 'state']:
                        if fname in [f.name() for f in fields]:
                            state_value = feature[fname]
                            break
                    if state_value and state_filter.lower() not in str(state_value).lower():
                        continue

                # Search in fields
                for field_name in search_fields:
                    value = feature[field_name]
                    if value and query.lower() in str(value).lower():
                        results.append({
                            'name': str(value),
                            'layer': layer.name(),
                            'layer_id': layer.id(),
                            'feature_id': feature.id(),
                            'geometry': feature.geometry()
                        })
                        break

        # Display results
        for result in results:
            item = QListWidgetItem(f"{result['name']} ({result['layer']})")
            item.setData(Qt.UserRole, result)
            self.faceted_results.addItem(item)

    def _zoom_to_result(self, item):
        """Zoom to a search result."""
        result = item.data(Qt.UserRole)
        if result and result.get('geometry'):
            self.iface.mapCanvas().setExtent(result['geometry'].boundingBox())
            self.iface.mapCanvas().refresh()

            # Highlight feature
            layer = QgsProject.instance().mapLayer(result['layer_id'])
            if layer:
                layer.selectByIds([result['feature_id']])

    def _zoom_to_faceted_result(self, item):
        """Zoom to faceted search result."""
        self._zoom_to_result(item)

    def _zoom_to_selected(self):
        """Zoom to selected result in list."""
        current = self.results_list.currentItem()
        if current:
            self._zoom_to_result(current)

    def _select_all_results(self):
        """Select all search result features on the map."""
        # Group results by layer
        by_layer = {}
        for result in self.current_results:
            layer_id = result.get('layer_id')
            if layer_id not in by_layer:
                by_layer[layer_id] = []
            by_layer[layer_id].append(result['feature_id'])

        # Select features in each layer
        for layer_id, feature_ids in by_layer.items():
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer:
                layer.selectByIds(feature_ids)

    def _clear_search(self):
        """Clear search input and results."""
        self.search_input.clear()
        self.results_list.clear()
        self.current_results = []
        self.results_label.setText('Enter a search term')

        # Clear selections
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                layer.removeSelection()

    def _show_history_menu(self):
        """Show search history dropdown menu."""
        menu = QMenu(self)

        for entry in list(self.search_history)[:10]:
            action = menu.addAction(entry['query'])
            action.triggered.connect(lambda checked, q=entry['query']: self._set_search(q))

        menu.exec_(self.history_btn.mapToGlobal(self.history_btn.rect().bottomLeft()))

    def _set_search(self, query):
        """Set search input to a query."""
        self.search_input.setText(query)
        self._perform_quick_search()

    def _show_result_menu(self, pos):
        """Show context menu for search results."""
        item = self.results_list.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)

        zoom_action = menu.addAction('Zoom to Feature')
        zoom_action.triggered.connect(lambda: self._zoom_to_result(item))

        select_action = menu.addAction('Select Feature')
        select_action.triggered.connect(lambda: self._select_result(item))

        menu.exec_(self.results_list.mapToGlobal(pos))

    def _select_result(self, item):
        """Select a result feature."""
        result = item.data(Qt.UserRole)
        layer = QgsProject.instance().mapLayer(result['layer_id'])
        if layer:
            layer.selectByIds([result['feature_id']])

    def _add_to_history(self, query):
        """Add query to search history."""
        entry = {
            'query': query,
            'timestamp': datetime.now().isoformat()
        }
        self.search_history.appendleft(entry)
        self._save_history()
        self._refresh_history_list()

    def _refresh_history_list(self):
        """Refresh the history list widget."""
        self.history_list.clear()
        for entry in self.search_history:
            timestamp = entry['timestamp'][:19].replace('T', ' ')
            item = QListWidgetItem(f"{entry['query']} ({timestamp})")
            item.setData(Qt.UserRole, entry)
            self.history_list.addItem(item)

    def _clear_history(self):
        """Clear search history."""
        self.search_history.clear()
        self._save_history()
        self._refresh_history_list()

    def _replay_search(self, item):
        """Replay a search from history."""
        entry = item.data(Qt.UserRole)
        self.search_input.setText(entry['query'])
        self._perform_quick_search()

    def _replay_saved_search(self, item):
        """Replay a saved search."""
        search = item.data(Qt.UserRole)
        if search:
            self.search_input.setText(search.get('query', ''))
            self._perform_quick_search()

    def _save_current_search(self):
        """Save the current faceted search."""
        query = self.faceted_input.text().strip()
        if not query:
            QMessageBox.warning(self, 'Empty Search', 'Please enter a search term first.')
            return

        saved = {
            'query': query,
            'layer_type': self.layer_type_combo.currentData(),
            'state': self.state_combo.currentData(),
            'field': self.field_combo.currentData(),
            'timestamp': datetime.now().isoformat()
        }

        self.saved_searches.append(saved)
        self._save_history()

        # Add to saved list
        item = QListWidgetItem(f"{query} ({saved['timestamp'][:10]})")
        item.setData(Qt.UserRole, saved)
        self.saved_list.addItem(item)

        QMessageBox.information(self, 'Saved', 'Search saved successfully.')

    def _delete_saved_search(self):
        """Delete selected saved search."""
        current = self.saved_list.currentItem()
        if current:
            row = self.saved_list.row(current)
            self.saved_list.takeItem(row)
            if row < len(self.saved_searches):
                del self.saved_searches[row]
            self._save_history()

    def _load_history(self):
        """Load search history from settings."""
        if self.settings_manager:
            history_data = self.settings_manager.get('search_history', [])
            if isinstance(history_data, list):
                for entry in history_data[:self.MAX_HISTORY]:
                    if isinstance(entry, dict) and 'query' in entry:
                        self.search_history.append(entry)

            saved_data = self.settings_manager.get('saved_searches', [])
            if isinstance(saved_data, list):
                self.saved_searches = saved_data

    def _save_history(self):
        """Save search history to settings."""
        if self.settings_manager:
            self.settings_manager.set('search_history', list(self.search_history))
            self.settings_manager.set('saved_searches', self.saved_searches)
