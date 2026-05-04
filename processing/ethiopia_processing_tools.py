# -*- coding: utf-8 -*-
"""
Sudan Processing Tools for Ethiopia Data Loader.

Provides simplified processing tools with presets for Ethiopia data.
"""

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QDoubleSpinBox, QPushButton, QGroupBox,
    QLabel, QDialogButtonBox, QCheckBox, QLineEdit,
    QFileDialog, QMessageBox, QProgressDialog
)
from qgis.PyQt.QtCore import Qt
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsProcessingFeedback,
    QgsVectorFileWriter, QgsCoordinateTransformContext,
    QgsProcessingUtils
)
import processing


class EthiopiaProcessingTools:
    """Processing tools for Ethiopia data operations."""

    def __init__(self, iface):
        """
        Initialize the processing tools.

        :param iface: QGIS interface instance
        """
        self.iface = iface

    def clip_by_state(self, input_layer, state_name):
        """
        Clip a layer by a Ethiopia state boundary.

        :param input_layer: Layer to clip
        :param state_name: Name of the state to clip to
        :returns: Clipped layer or None
        """
        # Find the states layer
        states_layer = None
        for layer in QgsProject.instance().mapLayers().values():
            if 'Admin 1' in layer.name() or 'States' in layer.name():
                states_layer = layer
                break

        if not states_layer:
            QMessageBox.warning(
                self.iface.mainWindow(),
                'Layer Not Found',
                'Could not find the States layer. Please load Ethiopia Admin 1 first.'
            )
            return None

        # Find the state feature
        state_feature = None
        for feature in states_layer.getFeatures():
            for field_name in ['ADM1_EN', 'admin1Name_en', 'name', 'NAME']:
                if field_name in [f.name() for f in states_layer.fields()]:
                    if feature[field_name] == state_name:
                        state_feature = feature
                        break
            if state_feature:
                break

        if not state_feature:
            QMessageBox.warning(
                self.iface.mainWindow(),
                'State Not Found',
                f'Could not find state: {state_name}'
            )
            return None

        # Run clip
        try:
            result = processing.run('native:clip', {
                'INPUT': input_layer,
                'OVERLAY': QgsProcessingUtils.mapLayerFromString(
                    f'{states_layer.source()}|subset="ADM1_EN" = \'{state_name}\''
                ),
                'OUTPUT': 'memory:'
            })
            return result['OUTPUT']
        except Exception as e:
            QMessageBox.critical(
                self.iface.mainWindow(),
                'Processing Error',
                f'Clip operation failed:\n{str(e)}'
            )
            return None

    def buffer_features(self, layer, distance_km, segments=16):
        """
        Create buffer around features.

        :param layer: Input layer
        :param distance_km: Buffer distance in kilometers
        :param segments: Number of segments for circular buffers
        :returns: Buffered layer or None
        """
        # Convert km to degrees (approximate for Sudan's latitude)
        distance_deg = distance_km / 111  # 1 degree ≈ 111 km

        try:
            result = processing.run('native:buffer', {
                'INPUT': layer,
                'DISTANCE': distance_deg,
                'SEGMENTS': segments,
                'END_CAP_STYLE': 0,  # Round
                'JOIN_STYLE': 0,  # Round
                'MITER_LIMIT': 2,
                'DISSOLVE': False,
                'OUTPUT': 'memory:'
            })
            return result['OUTPUT']
        except Exception as e:
            QMessageBox.critical(
                self.iface.mainWindow(),
                'Processing Error',
                f'Buffer operation failed:\n{str(e)}'
            )
            return None

    def dissolve_features(self, layer, field=None):
        """
        Dissolve features, optionally by field.

        :param layer: Input layer
        :param field: Field to dissolve by (optional)
        :returns: Dissolved layer or None
        """
        try:
            params = {
                'INPUT': layer,
                'OUTPUT': 'memory:'
            }
            if field:
                params['FIELD'] = [field]

            result = processing.run('native:dissolve', params)
            return result['OUTPUT']
        except Exception as e:
            QMessageBox.critical(
                self.iface.mainWindow(),
                'Processing Error',
                f'Dissolve operation failed:\n{str(e)}'
            )
            return None

    def intersection(self, layer1, layer2):
        """
        Calculate intersection of two layers.

        :param layer1: First input layer
        :param layer2: Second input layer
        :returns: Intersection layer or None
        """
        try:
            result = processing.run('native:intersection', {
                'INPUT': layer1,
                'OVERLAY': layer2,
                'OUTPUT': 'memory:'
            })
            return result['OUTPUT']
        except Exception as e:
            QMessageBox.critical(
                self.iface.mainWindow(),
                'Processing Error',
                f'Intersection operation failed:\n{str(e)}'
            )
            return None

    def centroid(self, layer):
        """
        Calculate centroids of polygon features.

        :param layer: Input polygon layer
        :returns: Point layer with centroids or None
        """
        try:
            result = processing.run('native:centroids', {
                'INPUT': layer,
                'ALL_PARTS': False,
                'OUTPUT': 'memory:'
            })
            return result['OUTPUT']
        except Exception as e:
            QMessageBox.critical(
                self.iface.mainWindow(),
                'Processing Error',
                f'Centroid operation failed:\n{str(e)}'
            )
            return None


class ProcessingDialog(QDialog):
    """Dialog for Sudan processing tools."""

    def __init__(self, iface, parent=None):
        """
        Initialize the processing dialog.

        :param iface: QGIS interface instance
        :param parent: Parent widget
        """
        super().__init__(parent)
        self.iface = iface
        self.processing_tools = SudanProcessingTools(iface)
        self.setWindowTitle('Sudan Processing Tools')
        self.setMinimumWidth(450)
        self.setup_ui()
        self.populate_layers()

    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Tool selection
        tool_group = QGroupBox('Select Tool')
        tool_layout = QFormLayout(tool_group)

        self.tool_combo = QComboBox()
        self.tool_combo.addItems([
            'Clip by State',
            'Buffer',
            'Dissolve',
            'Intersection',
            'Calculate Centroids'
        ])
        self.tool_combo.currentIndexChanged.connect(self.on_tool_changed)
        tool_layout.addRow('Tool:', self.tool_combo)

        layout.addWidget(tool_group)

        # Input parameters
        params_group = QGroupBox('Parameters')
        self.params_layout = QFormLayout(params_group)

        # Input layer
        self.input_combo = QComboBox()
        self.params_layout.addRow('Input Layer:', self.input_combo)

        # State selector (for clip)
        self.state_combo = QComboBox()
        self.state_combo.addItems([
            'Khartoum', 'Northern', 'River Nile', 'Red Sea', 'Kassala',
            'Gedaref', 'Sennar', 'Blue Nile', 'White Nile', 'Gezira',
            'North Kordofan', 'South Kordofan', 'West Kordofan',
            'North Darfur', 'West Darfur', 'Central Darfur', 'South Darfur', 'East Darfur'
        ])
        self.state_label = QLabel('Clip to State:')
        self.params_layout.addRow(self.state_label, self.state_combo)

        # Buffer distance
        self.buffer_spin = QDoubleSpinBox()
        self.buffer_spin.setRange(0.1, 1000)
        self.buffer_spin.setValue(10)
        self.buffer_spin.setSuffix(' km')
        self.buffer_label = QLabel('Buffer Distance:')
        self.params_layout.addRow(self.buffer_label, self.buffer_spin)

        # Dissolve field
        self.dissolve_combo = QComboBox()
        self.dissolve_label = QLabel('Dissolve by Field:')
        self.params_layout.addRow(self.dissolve_label, self.dissolve_combo)

        # Overlay layer (for intersection)
        self.overlay_combo = QComboBox()
        self.overlay_label = QLabel('Overlay Layer:')
        self.params_layout.addRow(self.overlay_label, self.overlay_combo)

        layout.addWidget(params_group)

        # Output options
        output_group = QGroupBox('Output')
        output_layout = QVBoxLayout(output_group)

        self.add_to_map_check = QCheckBox('Add result to map')
        self.add_to_map_check.setChecked(True)
        output_layout.addWidget(self.add_to_map_check)

        layout.addWidget(output_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.button(QDialogButtonBox.Ok).setText('Run')
        button_box.accepted.connect(self.run_tool)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Initial visibility
        self.on_tool_changed(0)

    def populate_layers(self):
        """Populate layer combos with available layers."""
        self.input_combo.clear()
        self.overlay_combo.clear()

        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                self.input_combo.addItem(layer.name(), layer.id())
                self.overlay_combo.addItem(layer.name(), layer.id())

    def on_tool_changed(self, index):
        """Handle tool selection change."""
        tool = self.tool_combo.currentText()

        # Hide all optional parameters first
        self.state_label.setVisible(False)
        self.state_combo.setVisible(False)
        self.buffer_label.setVisible(False)
        self.buffer_spin.setVisible(False)
        self.dissolve_label.setVisible(False)
        self.dissolve_combo.setVisible(False)
        self.overlay_label.setVisible(False)
        self.overlay_combo.setVisible(False)

        # Show relevant parameters
        if tool == 'Clip by State':
            self.state_label.setVisible(True)
            self.state_combo.setVisible(True)
        elif tool == 'Buffer':
            self.buffer_label.setVisible(True)
            self.buffer_spin.setVisible(True)
        elif tool == 'Dissolve':
            self.dissolve_label.setVisible(True)
            self.dissolve_combo.setVisible(True)
            self.update_dissolve_fields()
        elif tool == 'Intersection':
            self.overlay_label.setVisible(True)
            self.overlay_combo.setVisible(True)

    def update_dissolve_fields(self):
        """Update dissolve field combo based on selected layer."""
        self.dissolve_combo.clear()
        self.dissolve_combo.addItem('(No field - dissolve all)', None)

        layer_id = self.input_combo.currentData()
        if layer_id:
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer:
                for field in layer.fields():
                    self.dissolve_combo.addItem(field.name(), field.name())

    def get_input_layer(self):
        """Get the selected input layer."""
        layer_id = self.input_combo.currentData()
        if layer_id:
            return QgsProject.instance().mapLayer(layer_id)
        return None

    def run_tool(self):
        """Run the selected processing tool."""
        tool = self.tool_combo.currentText()
        input_layer = self.get_input_layer()

        if not input_layer:
            QMessageBox.warning(self, 'No Layer', 'Please select an input layer.')
            return

        result_layer = None

        try:
            if tool == 'Clip by State':
                state = self.state_combo.currentText()
                result_layer = self.processing_tools.clip_by_state(input_layer, state)

            elif tool == 'Buffer':
                distance = self.buffer_spin.value()
                result_layer = self.processing_tools.buffer_features(input_layer, distance)

            elif tool == 'Dissolve':
                field = self.dissolve_combo.currentData()
                result_layer = self.processing_tools.dissolve_features(input_layer, field)

            elif tool == 'Intersection':
                overlay_id = self.overlay_combo.currentData()
                overlay_layer = QgsProject.instance().mapLayer(overlay_id)
                if overlay_layer:
                    result_layer = self.processing_tools.intersection(input_layer, overlay_layer)

            elif tool == 'Calculate Centroids':
                result_layer = self.processing_tools.centroid(input_layer)

            if result_layer and self.add_to_map_check.isChecked():
                result_layer.setName(f'{input_layer.name()} - {tool}')
                QgsProject.instance().addMapLayer(result_layer)
                QMessageBox.information(
                    self, 'Success',
                    f'Processing complete. Result added as:\n{result_layer.name()}'
                )
                self.accept()

        except Exception as e:
            QMessageBox.critical(
                self, 'Error',
                f'Processing failed:\n{str(e)}'
            )
