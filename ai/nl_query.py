# -*- coding: utf-8 -*-
"""
Natural Language Query for Ethiopia Data Loader.

Parses natural language queries into QGIS expressions and filter operations.
"""

import re
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QComboBox, QGroupBox, QListWidget,
    QListWidgetItem, QMessageBox
)
from qgis.PyQt.QtCore import Qt
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsExpression,
    QgsFeatureRequest, QgsMessageLog, Qgis
)


class NaturalLanguageQuery:
    """Parser for natural language queries on Sudan data."""

    # Keyword mappings to fields
    FIELD_MAPPINGS = {
        # State/Admin names
        'state': ['ADM1_EN', 'admin1Name_en', 'state_name'],
        'locality': ['ADM2_EN', 'admin2Name_en', 'locality_name'],
        'name': ['ADM1_EN', 'ADM2_EN', 'name', 'NAME'],
        'arabic': ['ADM1_AR', 'ADM2_AR', 'name_ar'],
        'pcode': ['ADM1_PCODE', 'ADM2_PCODE', 'pcode'],

        # Numeric
        'population': ['population', 'pop', 'total_pop'],
        'area': ['area', 'AREA', 'Shape_Area']
    }

    # State name variations
    STATE_NAMES = {
        'khartoum': 'Khartoum',
        'darfur': ['North Darfur', 'South Darfur', 'West Darfur', 'Central Darfur', 'East Darfur'],
        'north darfur': 'North Darfur',
        'south darfur': 'South Darfur',
        'west darfur': 'West Darfur',
        'central darfur': 'Central Darfur',
        'east darfur': 'East Darfur',
        'kassala': 'Kassala',
        'gedaref': 'Gedaref',
        'gezira': 'Gezira',
        'sennar': 'Sennar',
        'blue nile': 'Blue Nile',
        'white nile': 'White Nile',
        'river nile': 'River Nile',
        'northern': 'Northern',
        'red sea': 'Red Sea',
        'north kordofan': 'North Kordofan',
        'south kordofan': 'South Kordofan',
        'west kordofan': 'West Kordofan'
    }

    # Operator mappings
    OPERATORS = {
        'greater than': '>',
        'more than': '>',
        'above': '>',
        'over': '>',
        'less than': '<',
        'fewer than': '<',
        'below': '<',
        'under': '<',
        'equal to': '=',
        'equals': '=',
        'is': '=',
        'at least': '>=',
        'at most': '<=',
        'between': 'BETWEEN'
    }

    # Query templates
    QUERY_PATTERNS = [
        # "Show all X in Y"
        (r'show\s+(?:all\s+)?(\w+)\s+in\s+(\w+(?:\s+\w+)?)', 'filter_by_location'),
        # "Find X with Y > Z"
        (r'find\s+(\w+)\s+(?:with|where)\s+(\w+)\s+(>|<|=|>=|<=)\s*(\d+)', 'filter_by_value'),
        # "X with population > Y"
        (r'(\w+)\s+(?:with|where)\s+population\s+(greater|more|less|above|below|over|under)\s+(?:than\s+)?(\d+)', 'filter_population'),
        # "Count X in Y"
        (r'count\s+(\w+)\s+in\s+(\w+(?:\s+\w+)?)', 'count_in_location'),
        # "List states/localities"
        (r'list\s+(?:all\s+)?(\w+)', 'list_features'),
        # "Zoom to X"
        (r'zoom\s+to\s+(\w+(?:\s+\w+)?)', 'zoom_to'),
        # "Select X"
        (r'select\s+(\w+(?:\s+\w+)?)', 'select_feature')
    ]

    def __init__(self):
        """Initialize the NL query parser."""
        self.query_history = []

    def parse(self, query_text):
        """
        Parse a natural language query.

        :param query_text: Natural language query string
        :returns: Dictionary with parsed query info or None
        """
        query_lower = query_text.lower().strip()

        # Add to history
        self.query_history.append(query_text)

        # Try each pattern
        for pattern, query_type in self.QUERY_PATTERNS:
            match = re.search(pattern, query_lower)
            if match:
                return self._process_match(query_type, match, query_text)

        # Try simple location filter
        for state_key, state_value in self.STATE_NAMES.items():
            if state_key in query_lower:
                return {
                    'type': 'filter_by_location',
                    'location': state_value if isinstance(state_value, str) else state_value[0],
                    'expression': self._build_location_expression(state_value),
                    'original_query': query_text
                }

        return None

    def _process_match(self, query_type, match, original):
        """Process a regex match into a query structure."""
        groups = match.groups()

        if query_type == 'filter_by_location':
            feature_type = groups[0]
            location = groups[1]

            # Normalize location
            normalized_loc = self.STATE_NAMES.get(location.lower(), location.title())

            return {
                'type': query_type,
                'feature_type': feature_type,
                'location': normalized_loc,
                'expression': self._build_location_expression(normalized_loc),
                'original_query': original
            }

        elif query_type == 'filter_by_value':
            feature_type = groups[0]
            field = groups[1]
            operator = groups[2]
            value = groups[3]

            field_name = self._get_field_name(field)

            return {
                'type': query_type,
                'feature_type': feature_type,
                'field': field_name,
                'operator': operator,
                'value': value,
                'expression': f'"{field_name}" {operator} {value}',
                'original_query': original
            }

        elif query_type == 'filter_population':
            feature_type = groups[0]
            operator_word = groups[1]
            value = groups[2]

            operator = '>' if operator_word in ['greater', 'more', 'above', 'over'] else '<'

            return {
                'type': 'filter_by_value',
                'feature_type': feature_type,
                'field': 'population',
                'operator': operator,
                'value': value,
                'expression': f'"population" {operator} {value}',
                'original_query': original
            }

        elif query_type == 'count_in_location':
            feature_type = groups[0]
            location = groups[1]
            normalized_loc = self.STATE_NAMES.get(location.lower(), location.title())

            return {
                'type': query_type,
                'feature_type': feature_type,
                'location': normalized_loc,
                'original_query': original
            }

        elif query_type == 'list_features':
            feature_type = groups[0]

            return {
                'type': query_type,
                'feature_type': feature_type,
                'original_query': original
            }

        elif query_type in ['zoom_to', 'select_feature']:
            target = groups[0]
            normalized = self.STATE_NAMES.get(target.lower(), target.title())

            return {
                'type': query_type,
                'target': normalized,
                'original_query': original
            }

        return None

    def _build_location_expression(self, location):
        """Build QGIS expression for location filter."""
        if isinstance(location, list):
            # Multiple locations (e.g., all Darfur states)
            conditions = []
            for loc in location:
                conditions.append(f'"ADM1_EN" ILIKE \'%{loc}%\'')
            return ' OR '.join(conditions)
        else:
            return f'"ADM1_EN" ILIKE \'%{location}%\' OR "ADM2_EN" ILIKE \'%{location}%\''

    def _get_field_name(self, keyword):
        """Get actual field name from keyword."""
        keyword_lower = keyword.lower()
        for key, fields in self.FIELD_MAPPINGS.items():
            if key in keyword_lower:
                return fields[0]
        return keyword

    def execute(self, parsed_query, iface):
        """
        Execute a parsed query.

        :param parsed_query: Parsed query dictionary
        :param iface: QGIS interface instance
        :returns: Tuple of (success, result_message)
        """
        if not parsed_query:
            return False, "Could not understand the query"

        query_type = parsed_query['type']

        if query_type == 'filter_by_location':
            return self._execute_filter(parsed_query, iface)

        elif query_type == 'filter_by_value':
            return self._execute_filter(parsed_query, iface)

        elif query_type == 'count_in_location':
            return self._execute_count(parsed_query, iface)

        elif query_type == 'list_features':
            return self._execute_list(parsed_query, iface)

        elif query_type == 'zoom_to':
            return self._execute_zoom(parsed_query, iface)

        elif query_type == 'select_feature':
            return self._execute_select(parsed_query, iface)

        return False, f"Unknown query type: {query_type}"

    def _execute_filter(self, query, iface):
        """Execute a filter query."""
        expression = query.get('expression')
        if not expression:
            return False, "No filter expression"

        # Find appropriate layer
        layer = self._find_sudan_layer()
        if not layer:
            return False, "No Sudan layer found"

        # Apply filter
        layer.setSubsetString(expression)
        layer.triggerRepaint()

        count = layer.featureCount()
        return True, f"Filter applied: {count} features match"

    def _execute_count(self, query, iface):
        """Execute a count query."""
        location = query.get('location')
        expression = self._build_location_expression(location)

        layer = self._find_sudan_layer(query.get('feature_type'))
        if not layer:
            return False, "No appropriate layer found"

        request = QgsFeatureRequest().setFilterExpression(expression)
        count = sum(1 for _ in layer.getFeatures(request))

        return True, f"Count in {location}: {count} features"

    def _execute_list(self, query, iface):
        """Execute a list query."""
        feature_type = query.get('feature_type')
        layer = self._find_sudan_layer(feature_type)

        if not layer:
            return False, "No appropriate layer found"

        names = []
        for feature in layer.getFeatures():
            for field in ['ADM1_EN', 'ADM2_EN', 'name', 'NAME']:
                if field in [f.name() for f in layer.fields()]:
                    name = feature[field]
                    if name:
                        names.append(str(name))
                    break

        return True, f"Found {len(names)} features:\n" + "\n".join(names[:20])

    def _execute_zoom(self, query, iface):
        """Execute a zoom query."""
        target = query.get('target')
        expression = self._build_location_expression(target)

        layer = self._find_sudan_layer()
        if not layer:
            return False, "No Sudan layer found"

        request = QgsFeatureRequest().setFilterExpression(expression)
        features = list(layer.getFeatures(request))

        if features:
            extent = features[0].geometry().boundingBox()
            for f in features[1:]:
                extent.combineExtentWith(f.geometry().boundingBox())

            iface.mapCanvas().setExtent(extent)
            iface.mapCanvas().refresh()
            return True, f"Zoomed to {target}"

        return False, f"Could not find {target}"

    def _execute_select(self, query, iface):
        """Execute a select query."""
        target = query.get('target')
        expression = self._build_location_expression(target)

        layer = self._find_sudan_layer()
        if not layer:
            return False, "No Sudan layer found"

        request = QgsFeatureRequest().setFilterExpression(expression)
        feature_ids = [f.id() for f in layer.getFeatures(request)]

        layer.selectByIds(feature_ids)
        return True, f"Selected {len(feature_ids)} features"

    def _find_sudan_layer(self, hint=None):
        """Find appropriate Sudan layer."""
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and 'sudan' in layer.name().lower():
                if hint:
                    hint_lower = hint.lower()
                    name_lower = layer.name().lower()
                    if hint_lower in name_lower:
                        return layer
                else:
                    return layer
        return None

    def get_suggestions(self, partial_query):
        """Get query suggestions based on partial input."""
        suggestions = [
            "Show all localities in Khartoum",
            "Find states with population > 1000000",
            "Count localities in Darfur",
            "List all states",
            "Zoom to North Darfur",
            "Select Kassala"
        ]

        if partial_query:
            partial_lower = partial_query.lower()
            return [s for s in suggestions if partial_lower in s.lower()]

        return suggestions


class NLQueryDialog(QDialog):
    """Dialog for natural language queries."""

    def __init__(self, iface, parent=None):
        """Initialize the NL query dialog."""
        super().__init__(parent)
        self.iface = iface
        self.parser = NaturalLanguageQuery()

        self.setWindowTitle('Natural Language Query - Sudan Data')
        self.setMinimumSize(600, 500)
        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Query input
        query_group = QGroupBox('Enter Your Query')
        query_layout = QVBoxLayout(query_group)

        input_layout = QHBoxLayout()
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText('e.g., "Show all localities in Khartoum"')
        self.query_input.returnPressed.connect(self.execute_query)
        self.query_input.textChanged.connect(self.update_suggestions)
        input_layout.addWidget(self.query_input)

        self.execute_btn = QPushButton('Execute')
        self.execute_btn.clicked.connect(self.execute_query)
        input_layout.addWidget(self.execute_btn)

        query_layout.addLayout(input_layout)
        layout.addWidget(query_group)

        # Suggestions
        suggest_group = QGroupBox('Suggestions')
        suggest_layout = QVBoxLayout(suggest_group)

        self.suggestions_list = QListWidget()
        self.suggestions_list.itemDoubleClicked.connect(self.use_suggestion)
        suggest_layout.addWidget(self.suggestions_list)

        layout.addWidget(suggest_group)

        # Results
        results_group = QGroupBox('Results')
        results_layout = QVBoxLayout(results_group)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)

        layout.addWidget(results_group)

        # Actions
        btn_layout = QHBoxLayout()

        clear_btn = QPushButton('Clear Filter')
        clear_btn.clicked.connect(self.clear_filter)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()

        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        # Initial suggestions
        self.update_suggestions()

    def update_suggestions(self):
        """Update suggestions based on current input."""
        self.suggestions_list.clear()
        partial = self.query_input.text()
        suggestions = self.parser.get_suggestions(partial)

        for suggestion in suggestions:
            self.suggestions_list.addItem(suggestion)

    def use_suggestion(self, item):
        """Use a suggestion."""
        self.query_input.setText(item.text())
        self.execute_query()

    def execute_query(self):
        """Execute the current query."""
        query_text = self.query_input.text().strip()
        if not query_text:
            return

        self.results_text.clear()
        self.results_text.append(f"Query: {query_text}\n")

        # Parse query
        parsed = self.parser.parse(query_text)

        if parsed:
            self.results_text.append(f"Parsed as: {parsed['type']}\n")
            if 'expression' in parsed:
                self.results_text.append(f"Expression: {parsed['expression']}\n")

            # Execute
            success, message = self.parser.execute(parsed, self.iface)
            self.results_text.append(f"\n{'Success' if success else 'Failed'}: {message}")
        else:
            self.results_text.append("Could not understand the query.\nTry one of the suggestions.")

    def clear_filter(self):
        """Clear any applied filters."""
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and 'sudan' in layer.name().lower():
                layer.setSubsetString('')
                layer.triggerRepaint()

        self.results_text.append("\nFilters cleared.")
