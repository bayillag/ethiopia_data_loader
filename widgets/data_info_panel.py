# -*- coding: utf-8 -*-
"""
Data Info Panel for Ethiopia Data Loader.

Dock widget showing data version, feature counts, CRS, and extent.
"""

from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QFormLayout,
    QLabel, QGroupBox, QPushButton, QTreeWidget, QTreeWidgetItem
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject, QgsVectorLayer


class DataInfoPanel(QDockWidget):
    """Dock widget displaying Ethiopia data information."""

    def __init__(self, parent=None):
        """
        Initialize the data info panel.

        :param parent: Parent widget
        """
        super().__init__('Ethiopia Data Info', parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setup_ui()

    def setup_ui(self):
        """Set up the panel UI."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Version info group
        version_group = QGroupBox('Data Version')
        version_layout = QFormLayout(version_group)

        self.version_label = QLabel('Not loaded')
        version_layout.addRow('Version:', self.version_label)

        self.last_update_label = QLabel('N/A')
        version_layout.addRow('Last Update:', self.last_update_label)

        self.source_label = QLabel('N/A')
        version_layout.addRow('Source:', self.source_label)

        layout.addWidget(version_group)

        # Layers info
        layers_group = QGroupBox('Loaded Layers')
        layers_layout = QVBoxLayout(layers_group)

        self.layers_tree = QTreeWidget()
        self.layers_tree.setHeaderLabels(['Layer', 'Features', 'Type'])
        self.layers_tree.setRootIsDecorated(False)
        layers_layout.addWidget(self.layers_tree)

        layout.addWidget(layers_group)

        # Extent info group
        extent_group = QGroupBox('Data Extent')
        extent_layout = QFormLayout(extent_group)

        self.crs_label = QLabel('N/A')
        extent_layout.addRow('CRS:', self.crs_label)

        self.xmin_label = QLabel('N/A')
        extent_layout.addRow('X Min:', self.xmin_label)

        self.xmax_label = QLabel('N/A')
        extent_layout.addRow('X Max:', self.xmax_label)

        self.ymin_label = QLabel('N/A')
        extent_layout.addRow('Y Min:', self.ymin_label)

        self.ymax_label = QLabel('N/A')
        extent_layout.addRow('Y Max:', self.ymax_label)

        layout.addWidget(extent_group)

        # Refresh button
        refresh_btn = QPushButton('Refresh Info')
        refresh_btn.clicked.connect(self.refresh_info)
        layout.addWidget(refresh_btn)

        layout.addStretch()

        self.setWidget(widget)

    def refresh_info(self):
        """Refresh the displayed information."""
        self.layers_tree.clear()

        # Find Sudan layers
        sudan_layers = []
        combined_extent = None

        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                name_lower = layer.name().lower()
                if 'sudan' in name_lower:
                    sudan_layers.append(layer)

                    # Add to tree
                    geom_type = ['Point', 'Line', 'Polygon', 'Unknown'][layer.geometryType()]
                    item = QTreeWidgetItem([
                        layer.name(),
                        str(layer.featureCount()),
                        geom_type
                    ])
                    self.layers_tree.addTopLevelItem(item)

                    # Update combined extent
                    if combined_extent is None:
                        combined_extent = layer.extent()
                    else:
                        combined_extent.combineExtentWith(layer.extent())

        # Update extent info
        if combined_extent:
            self.xmin_label.setText(f'{combined_extent.xMinimum():.4f}')
            self.xmax_label.setText(f'{combined_extent.xMaximum():.4f}')
            self.ymin_label.setText(f'{combined_extent.yMinimum():.4f}')
            self.ymax_label.setText(f'{combined_extent.yMaximum():.4f}')

        # Update CRS from first layer
        if sudan_layers:
            self.crs_label.setText(sudan_layers[0].crs().authid())
        else:
            self.crs_label.setText('No layers loaded')
            self.xmin_label.setText('N/A')
            self.xmax_label.setText('N/A')
            self.ymin_label.setText('N/A')
            self.ymax_label.setText('N/A')

        # Resize columns
        self.layers_tree.resizeColumnToContents(0)
        self.layers_tree.resizeColumnToContents(1)

    def set_version_info(self, version, last_update=None, source=None):
        """
        Set the version information.

        :param version: Version string
        :param last_update: Last update date string
        :param source: Data source string
        """
        self.version_label.setText(version or 'Unknown')
        self.last_update_label.setText(last_update or 'N/A')
        self.source_label.setText(source or 'N/A')
