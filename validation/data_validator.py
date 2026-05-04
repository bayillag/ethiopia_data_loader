# -*- coding: utf-8 -*-
"""
Data Validator for Ethiopia Data Loader.

Validates Ethiopia administrative data for geometry and attribute completeness.
"""

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QPushButton, QGroupBox, QLabel,
    QDialogButtonBox, QTextEdit, QProgressDialog,
    QTreeWidget, QTreeWidgetItem, QMessageBox
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsGeometry,
    QgsFeatureRequest
)


class DataValidator:
    """Validates Ethiopia data layers."""

    # Required fields for each layer type
    REQUIRED_FIELDS = {
        'admin0': ['ADM0_EN', 'ADM0_PCODE'],
        'admin1': ['ADM1_EN', 'ADM1_AR', 'ADM1_PCODE', 'ADM0_PCODE'],
        'admin2': ['ADM2_EN', 'ADM2_AR', 'ADM2_PCODE', 'ADM1_PCODE'],
    }

    def __init__(self):
        """Initialize the validator."""
        self.issues = []

    def validate_layer(self, layer):
        """
        Run all validations on a layer.

        :param layer: QgsVectorLayer to validate
        :returns: List of validation issues
        """
        self.issues = []

        if not layer or not layer.isValid():
            self.issues.append({
                'type': 'error',
                'category': 'Layer',
                'message': 'Layer is invalid or not loaded'
            })
            return self.issues

        # Run validations
        self._validate_geometry(layer)
        self._validate_topology(layer)
        self._validate_attributes(layer)
        self._validate_crs(layer)

        return self.issues

    def _validate_geometry(self, layer):
        """Validate geometry validity."""
        invalid_count = 0
        null_count = 0

        for feature in layer.getFeatures():
            geom = feature.geometry()

            if geom.isNull() or geom.isEmpty():
                null_count += 1
                continue

            if not geom.isGeosValid():
                invalid_count += 1
                self.issues.append({
                    'type': 'error',
                    'category': 'Geometry',
                    'message': f'Feature {feature.id()} has invalid geometry',
                    'feature_id': feature.id()
                })

        if null_count > 0:
            self.issues.append({
                'type': 'warning',
                'category': 'Geometry',
                'message': f'{null_count} features have null/empty geometry'
            })

        if invalid_count == 0 and null_count == 0:
            self.issues.append({
                'type': 'info',
                'category': 'Geometry',
                'message': 'All geometries are valid'
            })

    def _validate_topology(self, layer):
        """Validate topology (overlaps, gaps)."""
        if layer.geometryType() != 2:  # Only for polygons
            return

        # Check for self-intersections
        self_intersect_count = 0

        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom.isNull():
                continue

            # Check if geometry has self-intersections
            if not geom.isSimple():
                self_intersect_count += 1
                self.issues.append({
                    'type': 'warning',
                    'category': 'Topology',
                    'message': f'Feature {feature.id()} has self-intersection',
                    'feature_id': feature.id()
                })

        if self_intersect_count == 0:
            self.issues.append({
                'type': 'info',
                'category': 'Topology',
                'message': 'No self-intersections found'
            })

    def _validate_attributes(self, layer):
        """Validate attribute completeness."""
        # Determine layer type based on name
        layer_type = None
        name_lower = layer.name().lower()

        if 'admin 0' in name_lower or 'country' in name_lower:
            layer_type = 'admin0'
        elif 'admin 1' in name_lower or 'state' in name_lower:
            layer_type = 'admin1'
        elif 'admin 2' in name_lower or 'local' in name_lower:
            layer_type = 'admin2'

        if not layer_type:
            return

        required = self.REQUIRED_FIELDS.get(layer_type, [])
        field_names = [f.name() for f in layer.fields()]

        # Check for missing required fields
        missing_fields = [f for f in required if f not in field_names]
        if missing_fields:
            self.issues.append({
                'type': 'warning',
                'category': 'Attributes',
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            })

        # Check for NULL values in required fields
        for field in required:
            if field not in field_names:
                continue

            null_count = 0
            for feature in layer.getFeatures():
                value = feature[field]
                if value is None or (isinstance(value, str) and value.strip() == ''):
                    null_count += 1

            if null_count > 0:
                self.issues.append({
                    'type': 'warning',
                    'category': 'Attributes',
                    'message': f'Field "{field}" has {null_count} NULL/empty values'
                })

        if not missing_fields:
            self.issues.append({
                'type': 'info',
                'category': 'Attributes',
                'message': 'All required fields present'
            })

    def _validate_crs(self, layer):
        """Validate coordinate reference system."""
        crs = layer.crs()

        if not crs.isValid():
            self.issues.append({
                'type': 'error',
                'category': 'CRS',
                'message': 'Layer has invalid CRS'
            })
            return

        # Check if it's a geographic CRS (expected for Sudan data)
        if crs.isGeographic():
            self.issues.append({
                'type': 'info',
                'category': 'CRS',
                'message': f'CRS: {crs.authid()} (Geographic - OK)'
            })
        else:
            self.issues.append({
                'type': 'info',
                'category': 'CRS',
                'message': f'CRS: {crs.authid()} (Projected)'
            })

    def get_summary(self):
        """Get a summary of validation results."""
        errors = sum(1 for i in self.issues if i['type'] == 'error')
        warnings = sum(1 for i in self.issues if i['type'] == 'warning')
        info = sum(1 for i in self.issues if i['type'] == 'info')

        return {
            'errors': errors,
            'warnings': warnings,
            'info': info,
            'total': len(self.issues)
        }


class ValidationDialog(QDialog):
    """Dialog for data validation."""

    def __init__(self, iface, parent=None):
        """
        Initialize the validation dialog.

        :param iface: QGIS interface instance
        :param parent: Parent widget
        """
        super().__init__(parent)
        self.iface = iface
        self.validator = DataValidator()
        self.setWindowTitle('Sudan Data Validator')
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.setup_ui()
        self.populate_layers()

    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Layer selection
        layer_group = QGroupBox('Select Layer to Validate')
        layer_layout = QHBoxLayout(layer_group)

        self.layer_combo = QComboBox()
        layer_layout.addWidget(self.layer_combo)

        validate_btn = QPushButton('Validate')
        validate_btn.clicked.connect(self.run_validation)
        layer_layout.addWidget(validate_btn)

        validate_all_btn = QPushButton('Validate All Sudan Layers')
        validate_all_btn.clicked.connect(self.validate_all)
        layer_layout.addWidget(validate_all_btn)

        layout.addWidget(layer_group)

        # Results summary
        summary_group = QGroupBox('Summary')
        summary_layout = QHBoxLayout(summary_group)

        self.errors_label = QLabel('Errors: 0')
        self.errors_label.setStyleSheet('color: red; font-weight: bold;')
        summary_layout.addWidget(self.errors_label)

        self.warnings_label = QLabel('Warnings: 0')
        self.warnings_label.setStyleSheet('color: orange; font-weight: bold;')
        summary_layout.addWidget(self.warnings_label)

        self.info_label = QLabel('Info: 0')
        self.info_label.setStyleSheet('color: green;')
        summary_layout.addWidget(self.info_label)

        summary_layout.addStretch()
        layout.addWidget(summary_group)

        # Results tree
        results_group = QGroupBox('Validation Results')
        results_layout = QVBoxLayout(results_group)

        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(['Type', 'Category', 'Message'])
        self.results_tree.setColumnWidth(0, 80)
        self.results_tree.setColumnWidth(1, 100)
        self.results_tree.itemDoubleClicked.connect(self.on_result_double_clicked)
        results_layout.addWidget(self.results_tree)

        layout.addWidget(results_group)

        # Buttons
        button_layout = QHBoxLayout()

        zoom_btn = QPushButton('Zoom to Selected Issue')
        zoom_btn.clicked.connect(self.zoom_to_issue)
        button_layout.addWidget(zoom_btn)

        export_btn = QPushButton('Export Report')
        export_btn.clicked.connect(self.export_report)
        button_layout.addWidget(export_btn)

        button_layout.addStretch()

        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def populate_layers(self):
        """Populate the layer combo."""
        self.layer_combo.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                if 'sudan' in layer.name().lower():
                    self.layer_combo.addItem(layer.name(), layer.id())

    def get_selected_layer(self):
        """Get the selected layer."""
        layer_id = self.layer_combo.currentData()
        if layer_id:
            return QgsProject.instance().mapLayer(layer_id)
        return None

    def run_validation(self):
        """Run validation on selected layer."""
        layer = self.get_selected_layer()
        if not layer:
            QMessageBox.warning(self, 'No Layer', 'Please select a layer to validate.')
            return

        # Show progress
        progress = QProgressDialog('Validating...', None, 0, 0, self)
        progress.setWindowTitle('Validation Progress')
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        # Run validation
        issues = self.validator.validate_layer(layer)
        progress.close()

        # Display results
        self.display_results(issues, layer.name())

    def validate_all(self):
        """Validate all Sudan layers."""
        self.results_tree.clear()
        all_issues = []

        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and 'sudan' in layer.name().lower():
                issues = self.validator.validate_layer(layer)
                for issue in issues:
                    issue['layer'] = layer.name()
                all_issues.extend(issues)

        self.display_results(all_issues)

    def display_results(self, issues, layer_name=None):
        """Display validation results in the tree."""
        self.results_tree.clear()

        # Update summary
        summary = self.validator.get_summary()
        self.errors_label.setText(f'Errors: {summary["errors"]}')
        self.warnings_label.setText(f'Warnings: {summary["warnings"]}')
        self.info_label.setText(f'Info: {summary["info"]}')

        # Add items to tree
        for issue in issues:
            item = QTreeWidgetItem([
                issue['type'].upper(),
                issue['category'],
                issue['message']
            ])

            # Set colors
            if issue['type'] == 'error':
                item.setForeground(0, QColor('red'))
            elif issue['type'] == 'warning':
                item.setForeground(0, QColor('orange'))
            else:
                item.setForeground(0, QColor('green'))

            item.setData(0, Qt.UserRole, issue)
            self.results_tree.addTopLevelItem(item)

    def on_result_double_clicked(self, item, column):
        """Handle double-click on result item."""
        self.zoom_to_issue()

    def zoom_to_issue(self):
        """Zoom to the feature with the issue."""
        current_item = self.results_tree.currentItem()
        if not current_item:
            return

        issue = current_item.data(0, Qt.UserRole)
        if not issue or 'feature_id' not in issue:
            return

        layer = self.get_selected_layer()
        if not layer:
            return

        feature_id = issue['feature_id']
        feature = layer.getFeature(feature_id)

        if feature.hasGeometry():
            extent = feature.geometry().boundingBox()
            extent.scale(1.5)
            self.iface.mapCanvas().setExtent(extent)
            self.iface.mapCanvas().refresh()

            # Select the feature
            layer.selectByIds([feature_id])

    def export_report(self):
        """Export validation report."""
        from qgis.PyQt.QtWidgets import QFileDialog
        import os

        file_path, _ = QFileDialog.getSaveFileName(
            self, 'Export Validation Report',
            os.path.expanduser('~/validation_report.txt'),
            'Text Files (*.txt)'
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('Sudan Data Validation Report\n')
                f.write('=' * 50 + '\n\n')

                summary = self.validator.get_summary()
                f.write(f'Summary:\n')
                f.write(f'  Errors: {summary["errors"]}\n')
                f.write(f'  Warnings: {summary["warnings"]}\n')
                f.write(f'  Info: {summary["info"]}\n\n')

                f.write('Details:\n')
                f.write('-' * 50 + '\n')

                for i in range(self.results_tree.topLevelItemCount()):
                    item = self.results_tree.topLevelItem(i)
                    f.write(f'[{item.text(0)}] {item.text(1)}: {item.text(2)}\n')

            QMessageBox.information(
                self, 'Export Complete',
                f'Report saved to:\n{file_path}'
            )
        except Exception as e:
            QMessageBox.critical(
                self, 'Export Error',
                f'Failed to export report:\n{str(e)}'
            )
