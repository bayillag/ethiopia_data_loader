# -*- coding: utf-8 -*-
"""
Export Dialog for Ethiopia Data Loader.

Dialog for exporting selected features to various formats.
"""

import os
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLineEdit, QPushButton, QGroupBox,
    QLabel, QDialogButtonBox, QCheckBox, QRadioButton,
    QButtonGroup, QFileDialog, QMessageBox, QProgressDialog
)
from qgis.PyQt.QtCore import Qt
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsVectorFileWriter,
    QgsCoordinateReferenceSystem, QgsCoordinateTransformContext
)


class ExportDialog(QDialog):
    """Dialog for exporting Sudan data features."""

    # Export format configurations
    FORMATS = {
        'GeoPackage': {
            'driver': 'GPKG',
            'extension': 'gpkg',
            'filter': 'GeoPackage (*.gpkg)',
        },
        'Shapefile': {
            'driver': 'ESRI Shapefile',
            'extension': 'shp',
            'filter': 'Shapefile (*.shp)',
        },
        'GeoJSON': {
            'driver': 'GeoJSON',
            'extension': 'geojson',
            'filter': 'GeoJSON (*.geojson)',
        },
        'KML': {
            'driver': 'KML',
            'extension': 'kml',
            'filter': 'KML (*.kml)',
        },
        'CSV': {
            'driver': 'CSV',
            'extension': 'csv',
            'filter': 'CSV (*.csv)',
        },
        'DXF': {
            'driver': 'DXF',
            'extension': 'dxf',
            'filter': 'DXF (*.dxf)',
        },
    }

    def __init__(self, settings_manager=None, parent=None):
        """
        Initialize the export dialog.

        :param settings_manager: SettingsManager instance (optional)
        :param parent: Parent widget
        """
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle('Export Sudan Data')
        self.setMinimumWidth(500)
        self.setup_ui()
        self.populate_layers()
        self.load_settings()

    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Layer selection
        layer_group = QGroupBox('Source Layer')
        layer_layout = QFormLayout(layer_group)

        self.layer_combo = QComboBox()
        self.layer_combo.currentIndexChanged.connect(self.on_layer_changed)
        layer_layout.addRow('Layer:', self.layer_combo)

        self.feature_count_label = QLabel('Features: 0')
        layer_layout.addRow('', self.feature_count_label)

        layout.addWidget(layer_group)

        # Export scope
        scope_group = QGroupBox('Export Scope')
        scope_layout = QVBoxLayout(scope_group)

        self.scope_group = QButtonGroup(self)

        self.all_features_radio = QRadioButton('All features')
        self.all_features_radio.setChecked(True)
        self.scope_group.addButton(self.all_features_radio)
        scope_layout.addWidget(self.all_features_radio)

        self.selected_radio = QRadioButton('Selected features only')
        self.scope_group.addButton(self.selected_radio)
        scope_layout.addWidget(self.selected_radio)

        self.visible_radio = QRadioButton('Visible features (current extent)')
        self.scope_group.addButton(self.visible_radio)
        scope_layout.addWidget(self.visible_radio)

        layout.addWidget(scope_group)

        # Output format
        format_group = QGroupBox('Output Format')
        format_layout = QFormLayout(format_group)

        self.format_combo = QComboBox()
        for format_name in self.FORMATS.keys():
            self.format_combo.addItem(format_name)
        self.format_combo.currentIndexChanged.connect(self.on_format_changed)
        format_layout.addRow('Format:', self.format_combo)

        layout.addWidget(format_group)

        # Output file
        output_group = QGroupBox('Output File')
        output_layout = QHBoxLayout(output_group)

        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText('Select output file...')
        output_layout.addWidget(self.output_edit)

        browse_btn = QPushButton('Browse...')
        browse_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(browse_btn)

        layout.addWidget(output_group)

        # Options
        options_group = QGroupBox('Options')
        options_layout = QVBoxLayout(options_group)

        self.add_to_map_check = QCheckBox('Add exported layer to map')
        self.add_to_map_check.setChecked(True)
        options_layout.addWidget(self.add_to_map_check)

        self.overwrite_check = QCheckBox('Overwrite if exists')
        self.overwrite_check.setChecked(True)
        options_layout.addWidget(self.overwrite_check)

        # CRS option
        crs_layout = QHBoxLayout()
        crs_layout.addWidget(QLabel('CRS:'))
        self.crs_combo = QComboBox()
        self.crs_combo.addItem('Same as source', 'source')
        self.crs_combo.addItem('WGS 84 (EPSG:4326)', 'EPSG:4326')
        self.crs_combo.addItem('Web Mercator (EPSG:3857)', 'EPSG:3857')
        crs_layout.addWidget(self.crs_combo)
        crs_layout.addStretch()
        options_layout.addLayout(crs_layout)

        layout.addWidget(options_group)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.button(QDialogButtonBox.Ok).setText('Export')
        button_box.accepted.connect(self.do_export)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def populate_layers(self):
        """Populate the layer combo with available layers."""
        self.layer_combo.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                self.layer_combo.addItem(layer.name(), layer.id())

    def on_layer_changed(self, index):
        """Handle layer selection change."""
        layer = self.get_selected_layer()
        if layer:
            total = layer.featureCount()
            selected = layer.selectedFeatureCount()
            self.feature_count_label.setText(
                f'Features: {total} total, {selected} selected'
            )

    def on_format_changed(self, index):
        """Handle format selection change."""
        # Update output file extension if path is set
        current_path = self.output_edit.text()
        if current_path:
            format_name = self.format_combo.currentText()
            config = self.FORMATS.get(format_name, {})
            new_ext = config.get('extension', '')

            base, _ = os.path.splitext(current_path)
            self.output_edit.setText(f'{base}.{new_ext}')

    def browse_output(self):
        """Open file browser for output file."""
        format_name = self.format_combo.currentText()
        config = self.FORMATS.get(format_name, {})
        file_filter = config.get('filter', 'All Files (*.*)')

        # Get starting directory
        start_dir = ''
        if self.settings_manager:
            start_dir = self.settings_manager.get_last_export_path()
        if not start_dir:
            start_dir = os.path.expanduser('~')

        file_path, _ = QFileDialog.getSaveFileName(
            self, 'Export File', start_dir, file_filter
        )

        if file_path:
            self.output_edit.setText(file_path)
            if self.settings_manager:
                self.settings_manager.set_last_export_path(
                    os.path.dirname(file_path)
                )

    def load_settings(self):
        """Load settings from settings manager."""
        if not self.settings_manager:
            return

        # Set last used format
        last_format = self.settings_manager.get_last_export_format()
        index = self.format_combo.findText(last_format)
        if index >= 0:
            self.format_combo.setCurrentIndex(index)

    def get_selected_layer(self):
        """Get the currently selected layer."""
        layer_id = self.layer_combo.currentData()
        if layer_id:
            return QgsProject.instance().mapLayer(layer_id)
        return None

    def do_export(self):
        """Perform the export operation."""
        layer = self.get_selected_layer()
        if not layer:
            QMessageBox.warning(self, 'No Layer', 'Please select a layer to export.')
            return

        output_path = self.output_edit.text()
        if not output_path:
            QMessageBox.warning(self, 'No Output', 'Please specify an output file.')
            return

        # Check if file exists
        if os.path.exists(output_path) and not self.overwrite_check.isChecked():
            reply = QMessageBox.question(
                self, 'File Exists',
                'Output file already exists. Overwrite?',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        format_name = self.format_combo.currentText()
        config = self.FORMATS.get(format_name, {})
        driver = config.get('driver', 'GPKG')

        # Determine CRS
        crs_option = self.crs_combo.currentData()
        if crs_option == 'source':
            dest_crs = layer.crs()
        else:
            dest_crs = QgsCoordinateReferenceSystem(crs_option)

        # Determine features to export
        if self.selected_radio.isChecked():
            if layer.selectedFeatureCount() == 0:
                QMessageBox.warning(
                    self, 'No Selection',
                    'No features selected. Please select features first.'
                )
                return
            features = layer.selectedFeatures()
            only_selected = True
        elif self.visible_radio.isChecked():
            from qgis.utils import iface
            extent = iface.mapCanvas().extent()
            features = layer.getFeatures(extent)
            only_selected = False
        else:
            features = None
            only_selected = False

        # Show progress
        progress = QProgressDialog('Exporting...', 'Cancel', 0, 100, self)
        progress.setWindowTitle('Export Progress')
        progress.setWindowModality(Qt.WindowModal)
        progress.setValue(0)

        try:
            # Set up writer options
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = driver
            options.fileEncoding = 'UTF-8'

            if only_selected:
                options.onlySelectedFeatures = True

            transform_context = QgsProject.instance().transformContext()

            # Write the file
            error, error_message = QgsVectorFileWriter.writeAsVectorFormatV3(
                layer,
                output_path,
                transform_context,
                options
            )

            progress.setValue(100)
            progress.close()

            if error != QgsVectorFileWriter.NoError:
                QMessageBox.critical(
                    self, 'Export Error',
                    f'Failed to export:\n{error_message}'
                )
                return

            # Add to map if requested
            if self.add_to_map_check.isChecked():
                layer_name = os.path.splitext(os.path.basename(output_path))[0]
                new_layer = QgsVectorLayer(output_path, layer_name, 'ogr')
                if new_layer.isValid():
                    QgsProject.instance().addMapLayer(new_layer)

            # Save format preference
            if self.settings_manager:
                self.settings_manager.set_last_export_format(format_name)

            QMessageBox.information(
                self, 'Export Complete',
                f'Successfully exported to:\n{output_path}'
            )
            self.accept()

        except Exception as e:
            progress.close()
            QMessageBox.critical(
                self, 'Export Error',
                f'An error occurred:\n{str(e)}'
            )
