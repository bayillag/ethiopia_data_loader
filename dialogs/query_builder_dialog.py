# -*- coding: utf-8 -*-
"""
Query Builder Dialog for Ethiopia Data Loader.

Visual query builder for filtering features.
"""

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLineEdit, QPushButton, QGroupBox,
    QLabel, QDialogButtonBox, QListWidget, QListWidgetItem,
    QMessageBox, QTextEdit
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject, QgsVectorLayer, QgsExpression


class QueryBuilderDialog(QDialog):
    """Visual query builder dialog."""

    OPERATORS = {
        'Text': [
            ('=', 'equals'),
            ('!=', 'not equals'),
            ('LIKE', 'contains'),
            ('ILIKE', 'contains (case insensitive)'),
            ('IS NULL', 'is empty'),
            ('IS NOT NULL', 'is not empty'),
        ],
        'Number': [
            ('=', 'equals'),
            ('!=', 'not equals'),
            ('<', 'less than'),
            ('<=', 'less than or equal'),
            ('>', 'greater than'),
            ('>=', 'greater than or equal'),
            ('IS NULL', 'is empty'),
            ('IS NOT NULL', 'is not empty'),
        ]
    }

    def __init__(self, parent=None):
        """
        Initialize the query builder dialog.

        :param parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle('Sudan Data Query Builder')
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.current_layer = None
        self.setup_ui()
        self.populate_layers()

    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Layer selection
        layer_group = QGroupBox('Select Layer')
        layer_layout = QFormLayout(layer_group)

        self.layer_combo = QComboBox()
        self.layer_combo.currentIndexChanged.connect(self.on_layer_changed)
        layer_layout.addRow('Layer:', self.layer_combo)

        layout.addWidget(layer_group)

        # Query builder
        query_group = QGroupBox('Build Query')
        query_layout = QVBoxLayout(query_group)

        # Field selection row
        field_row = QHBoxLayout()

        self.field_combo = QComboBox()
        self.field_combo.setMinimumWidth(150)
        self.field_combo.currentIndexChanged.connect(self.on_field_changed)
        field_row.addWidget(QLabel('Field:'))
        field_row.addWidget(self.field_combo)

        self.operator_combo = QComboBox()
        self.operator_combo.setMinimumWidth(150)
        field_row.addWidget(QLabel('Operator:'))
        field_row.addWidget(self.operator_combo)

        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText('Enter value...')
        field_row.addWidget(QLabel('Value:'))
        field_row.addWidget(self.value_edit)

        query_layout.addLayout(field_row)

        # Sample values button
        sample_btn = QPushButton('Show Sample Values')
        sample_btn.clicked.connect(self.show_sample_values)
        query_layout.addWidget(sample_btn)

        # Add condition button
        add_btn = QPushButton('Add Condition')
        add_btn.clicked.connect(self.add_condition)
        query_layout.addWidget(add_btn)

        # Conditions list
        query_layout.addWidget(QLabel('Conditions:'))
        self.conditions_list = QListWidget()
        query_layout.addWidget(self.conditions_list)

        # Condition controls
        condition_btns = QHBoxLayout()
        remove_btn = QPushButton('Remove Selected')
        remove_btn.clicked.connect(self.remove_condition)
        condition_btns.addWidget(remove_btn)

        clear_btn = QPushButton('Clear All')
        clear_btn.clicked.connect(self.clear_conditions)
        condition_btns.addWidget(clear_btn)

        query_layout.addLayout(condition_btns)

        # Combine operator
        combine_row = QHBoxLayout()
        combine_row.addWidget(QLabel('Combine conditions with:'))
        self.combine_combo = QComboBox()
        self.combine_combo.addItems(['AND', 'OR'])
        combine_row.addWidget(self.combine_combo)
        combine_row.addStretch()
        query_layout.addLayout(combine_row)

        # Expression preview
        query_layout.addWidget(QLabel('Expression:'))
        self.expression_edit = QTextEdit()
        self.expression_edit.setMaximumHeight(60)
        self.expression_edit.setReadOnly(True)
        query_layout.addWidget(self.expression_edit)

        layout.addWidget(query_group)

        # Action buttons
        action_layout = QHBoxLayout()

        select_btn = QPushButton('Select Features')
        select_btn.clicked.connect(self.select_features)
        action_layout.addWidget(select_btn)

        zoom_btn = QPushButton('Zoom to Results')
        zoom_btn.clicked.connect(self.zoom_to_results)
        action_layout.addWidget(zoom_btn)

        filter_btn = QPushButton('Filter Layer')
        filter_btn.clicked.connect(self.filter_layer)
        action_layout.addWidget(filter_btn)

        clear_filter_btn = QPushButton('Clear Filter')
        clear_filter_btn.clicked.connect(self.clear_filter)
        action_layout.addWidget(clear_filter_btn)

        layout.addLayout(action_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def populate_layers(self):
        """Populate the layer combo with Sudan layers."""
        self.layer_combo.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                if 'Sudan' in layer.name() or 'sudan' in layer.name().lower():
                    self.layer_combo.addItem(layer.name(), layer.id())

    def on_layer_changed(self, index):
        """Handle layer selection change."""
        layer_id = self.layer_combo.currentData()
        if layer_id:
            self.current_layer = QgsProject.instance().mapLayer(layer_id)
            self.populate_fields()
        else:
            self.current_layer = None
            self.field_combo.clear()

    def populate_fields(self):
        """Populate field combo with layer fields."""
        self.field_combo.clear()
        if self.current_layer:
            for field in self.current_layer.fields():
                self.field_combo.addItem(field.name(), field.typeName())

    def on_field_changed(self, index):
        """Handle field selection change."""
        self.operator_combo.clear()
        field_type = self.field_combo.currentData()

        if field_type in ['Integer', 'Real', 'Integer64', 'Double']:
            operators = self.OPERATORS['Number']
        else:
            operators = self.OPERATORS['Text']

        for op, desc in operators:
            self.operator_combo.addItem(f'{op} ({desc})', op)

    def show_sample_values(self):
        """Show sample values for the selected field."""
        if not self.current_layer:
            return

        field_name = self.field_combo.currentText()
        if not field_name:
            return

        # Get unique values (limit to 100)
        values = set()
        for feature in self.current_layer.getFeatures():
            val = feature[field_name]
            if val is not None:
                values.add(str(val))
            if len(values) >= 100:
                break

        sorted_values = sorted(values)[:50]  # Show max 50

        QMessageBox.information(
            self, 'Sample Values',
            f'Sample values for "{field_name}":\n\n' + '\n'.join(sorted_values)
        )

    def add_condition(self):
        """Add a query condition."""
        field = self.field_combo.currentText()
        operator = self.operator_combo.currentData()
        value = self.value_edit.text()

        if not field:
            return

        # Build condition string
        if operator in ['IS NULL', 'IS NOT NULL']:
            condition = f'"{field}" {operator}'
        elif operator in ['LIKE', 'ILIKE']:
            condition = f'"{field}" {operator} \'%{value}%\''
        elif self.field_combo.currentData() in ['Integer', 'Real', 'Integer64', 'Double']:
            condition = f'"{field}" {operator} {value}'
        else:
            condition = f'"{field}" {operator} \'{value}\''

        self.conditions_list.addItem(condition)
        self.update_expression()
        self.value_edit.clear()

    def remove_condition(self):
        """Remove selected condition."""
        current_row = self.conditions_list.currentRow()
        if current_row >= 0:
            self.conditions_list.takeItem(current_row)
            self.update_expression()

    def clear_conditions(self):
        """Clear all conditions."""
        self.conditions_list.clear()
        self.update_expression()

    def update_expression(self):
        """Update the expression preview."""
        conditions = []
        for i in range(self.conditions_list.count()):
            conditions.append(self.conditions_list.item(i).text())

        combine_op = f' {self.combine_combo.currentText()} '
        expression = combine_op.join(conditions)
        self.expression_edit.setText(expression)

    def get_expression(self):
        """Get the built expression string."""
        return self.expression_edit.toPlainText()

    def select_features(self):
        """Select features matching the query."""
        if not self.current_layer:
            return

        expression = self.get_expression()
        if not expression:
            QMessageBox.warning(self, 'No Query', 'Please add at least one condition.')
            return

        # Validate expression
        exp = QgsExpression(expression)
        if exp.hasParserError():
            QMessageBox.critical(
                self, 'Expression Error',
                f'Invalid expression:\n{exp.parserErrorString()}'
            )
            return

        # Select features
        self.current_layer.selectByExpression(expression)
        count = self.current_layer.selectedFeatureCount()

        QMessageBox.information(
            self, 'Selection Complete',
            f'Selected {count} features.'
        )

    def zoom_to_results(self):
        """Zoom to selected features."""
        if not self.current_layer:
            return

        if self.current_layer.selectedFeatureCount() > 0:
            from qgis.utils import iface
            iface.mapCanvas().zoomToSelected(self.current_layer)
        else:
            QMessageBox.warning(
                self, 'No Selection',
                'No features selected. Run a query first.'
            )

    def filter_layer(self):
        """Apply filter to the layer."""
        if not self.current_layer:
            return

        expression = self.get_expression()
        if expression:
            self.current_layer.setSubsetString(expression)
            QMessageBox.information(
                self, 'Filter Applied',
                'Layer filter has been applied.'
            )

    def clear_filter(self):
        """Clear the layer filter."""
        if self.current_layer:
            self.current_layer.setSubsetString('')
            QMessageBox.information(
                self, 'Filter Cleared',
                'Layer filter has been removed.'
            )
