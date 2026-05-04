# -*- coding: utf-8 -*-
"""
Statistics Panel for Ethiopia Data Loader.

Dock widget showing feature counts, area calculations, and selection statistics.
"""

from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLabel, QGroupBox, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem,
    QFileDialog, QMessageBox, QHeaderView
)
from qgis.PyQt.QtCore import Qt
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsDistanceArea,
    QgsCoordinateReferenceSystem, QgsUnitTypes
)
import csv
import os


class StatisticsPanel(QDockWidget):
    """Dock widget displaying Ethiopia data statistics."""

    def __init__(self, iface, parent=None):
        """
        Initialize the statistics panel.

        :param iface: QGIS interface instance
        :param parent: Parent widget
        """
        super().__init__('Ethiopia Statistics', parent)
        self.iface = iface
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.distance_area = QgsDistanceArea()
        self.distance_area.setSourceCrs(
            QgsCoordinateReferenceSystem('EPSG:4326'),
            QgsProject.instance().transformContext()
        )
        self.distance_area.setEllipsoid('WGS84')
        self.setup_ui()

    def setup_ui(self):
        """Set up the panel UI."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Layer selection
        layer_group = QGroupBox('Select Layer')
        layer_layout = QHBoxLayout(layer_group)

        self.layer_combo = QComboBox()
        self.layer_combo.currentIndexChanged.connect(self.on_layer_changed)
        layer_layout.addWidget(self.layer_combo)

        refresh_layers_btn = QPushButton('Refresh')
        refresh_layers_btn.clicked.connect(self.populate_layers)
        layer_layout.addWidget(refresh_layers_btn)

        layout.addWidget(layer_group)

        # Summary statistics
        summary_group = QGroupBox('Summary Statistics')
        summary_layout = QFormLayout(summary_group)

        self.feature_count_label = QLabel('0')
        summary_layout.addRow('Total Features:', self.feature_count_label)

        self.selected_count_label = QLabel('0')
        summary_layout.addRow('Selected Features:', self.selected_count_label)

        self.total_area_label = QLabel('0 km²')
        summary_layout.addRow('Total Area:', self.total_area_label)

        self.selected_area_label = QLabel('0 km²')
        summary_layout.addRow('Selected Area:', self.selected_area_label)

        self.crs_label = QLabel('N/A')
        summary_layout.addRow('CRS:', self.crs_label)

        layout.addWidget(summary_group)

        # Detailed statistics table
        detail_group = QGroupBox('Feature Details')
        detail_layout = QVBoxLayout(detail_group)

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(3)
        self.stats_table.setHorizontalHeaderLabels(['Name', 'Area (km²)', '%'])
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        self.stats_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.stats_table.setAlternatingRowColors(True)
        detail_layout.addWidget(self.stats_table)

        layout.addWidget(detail_group)

        # Action buttons
        btn_layout = QHBoxLayout()

        calc_btn = QPushButton('Calculate Statistics')
        calc_btn.clicked.connect(self.calculate_statistics)
        btn_layout.addWidget(calc_btn)

        export_btn = QPushButton('Export to CSV')
        export_btn.clicked.connect(self.export_statistics)
        btn_layout.addWidget(export_btn)

        layout.addLayout(btn_layout)

        self.setWidget(widget)

        # Initial population
        self.populate_layers()

    def populate_layers(self):
        """Populate the layer combo with Sudan layers."""
        self.layer_combo.clear()
        self.layer_combo.addItem('-- Select Layer --', None)

        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                name_lower = layer.name().lower()
                if 'sudan' in name_lower:
                    self.layer_combo.addItem(layer.name(), layer.id())

    def on_layer_changed(self, index):
        """Handle layer selection change."""
        layer = self.get_selected_layer()
        if layer:
            self.feature_count_label.setText(str(layer.featureCount()))
            self.selected_count_label.setText(str(layer.selectedFeatureCount()))
            self.crs_label.setText(layer.crs().authid())

            # Update distance area CRS
            self.distance_area.setSourceCrs(
                layer.crs(),
                QgsProject.instance().transformContext()
            )
        else:
            self.feature_count_label.setText('0')
            self.selected_count_label.setText('0')
            self.crs_label.setText('N/A')

    def get_selected_layer(self):
        """Get the currently selected layer."""
        layer_id = self.layer_combo.currentData()
        if layer_id:
            return QgsProject.instance().mapLayer(layer_id)
        return None

    def calculate_statistics(self):
        """Calculate and display statistics for the selected layer."""
        layer = self.get_selected_layer()
        if not layer:
            QMessageBox.warning(self, 'No Layer', 'Please select a layer first.')
            return

        # Check if polygon layer
        if layer.geometryType() != 2:  # 2 = Polygon
            QMessageBox.warning(
                self, 'Invalid Layer Type',
                'Area statistics require a polygon layer.'
            )
            return

        # Clear table
        self.stats_table.setRowCount(0)

        # Find name field
        name_field = None
        for field_name in ['ADM1_EN', 'ADM2_EN', 'name', 'NAME', 'Name', 'admin1Name_en', 'admin2Name_en']:
            if field_name in [f.name() for f in layer.fields()]:
                name_field = field_name
                break

        # Calculate areas
        total_area = 0
        feature_areas = []

        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom:
                # Calculate area in square kilometers
                area = self.distance_area.measureArea(geom) / 1_000_000  # Convert to km²

                name = 'Unnamed'
                if name_field:
                    name = feature[name_field] or 'Unnamed'

                feature_areas.append({
                    'name': name,
                    'area': area
                })
                total_area += area

        # Sort by area descending
        feature_areas.sort(key=lambda x: x['area'], reverse=True)

        # Populate table
        self.stats_table.setRowCount(len(feature_areas))
        for row, fa in enumerate(feature_areas):
            percentage = (fa['area'] / total_area * 100) if total_area > 0 else 0

            self.stats_table.setItem(row, 0, QTableWidgetItem(str(fa['name'])))
            self.stats_table.setItem(row, 1, QTableWidgetItem(f"{fa['area']:,.2f}"))
            self.stats_table.setItem(row, 2, QTableWidgetItem(f"{percentage:.1f}%"))

        # Update summary
        self.total_area_label.setText(f"{total_area:,.2f} km²")
        self.feature_count_label.setText(str(layer.featureCount()))
        self.selected_count_label.setText(str(layer.selectedFeatureCount()))

        # Calculate selected area
        if layer.selectedFeatureCount() > 0:
            selected_area = 0
            for feature in layer.selectedFeatures():
                geom = feature.geometry()
                if geom:
                    selected_area += self.distance_area.measureArea(geom) / 1_000_000
            self.selected_area_label.setText(f"{selected_area:,.2f} km²")
        else:
            self.selected_area_label.setText('0 km²')

    def export_statistics(self):
        """Export statistics to CSV file."""
        if self.stats_table.rowCount() == 0:
            QMessageBox.warning(
                self, 'No Data',
                'Please calculate statistics first.'
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, 'Export Statistics',
            os.path.expanduser('~/sudan_statistics.csv'),
            'CSV Files (*.csv)'
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Name', 'Area (km²)', 'Percentage'])

                for row in range(self.stats_table.rowCount()):
                    name = self.stats_table.item(row, 0).text()
                    area = self.stats_table.item(row, 1).text()
                    percentage = self.stats_table.item(row, 2).text()
                    writer.writerow([name, area, percentage])

            QMessageBox.information(
                self, 'Export Complete',
                f'Statistics exported to:\n{file_path}'
            )
        except Exception as e:
            QMessageBox.critical(
                self, 'Export Error',
                f'Failed to export:\n{str(e)}'
            )
