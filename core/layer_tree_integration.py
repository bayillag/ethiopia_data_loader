# -*- coding: utf-8 -*-
"""
Layer Tree Integration for Sudan Data Loader.

Adds custom context menu items and layer grouping for Sudan layers.
"""

from qgis.PyQt.QtWidgets import QAction, QMenu
from qgis.PyQt.QtCore import QObject
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsLayerTreeGroup,
    QgsLayerTreeLayer, QgsMessageLog, Qgis
)
from qgis.gui import QgsLayerTreeViewMenuProvider


class SudanLayerTreeMenuProvider(QgsLayerTreeViewMenuProvider):
    """Custom menu provider for Sudan layers in the layer tree."""

    def __init__(self, iface, view):
        """
        Initialize the menu provider.

        :param iface: QGIS interface instance
        :param view: Layer tree view
        """
        super().__init__()
        self.iface = iface
        self.view = view

    def createContextMenu(self):
        """Create context menu for layer tree."""
        menu = QMenu()

        # Get selected nodes
        selected_nodes = self.view.selectedNodes()

        if not selected_nodes:
            return menu

        # Check if any selected layer is a Sudan layer
        sudan_layers = []
        for node in selected_nodes:
            if isinstance(node, QgsLayerTreeLayer):
                layer = node.layer()
                if isinstance(layer, QgsVectorLayer) and 'sudan' in layer.name().lower():
                    sudan_layers.append(layer)

        if sudan_layers:
            # Add Sudan-specific actions
            menu.addSection('Sudan Data Loader')

            # Zoom to extent
            zoom_action = QAction('Zoom to Sudan Extent', menu)
            zoom_action.triggered.connect(lambda: self._zoom_to_layer(sudan_layers[0]))
            menu.addAction(zoom_action)

            # Show statistics
            stats_action = QAction('Show Statistics...', menu)
            stats_action.triggered.connect(lambda: self._show_statistics(sudan_layers[0]))
            menu.addAction(stats_action)

            # Quick labels submenu
            labels_menu = QMenu('Quick Labels', menu)

            label_en = QAction('English Names', labels_menu)
            label_en.triggered.connect(lambda: self._apply_labels(sudan_layers[0], 'english'))
            labels_menu.addAction(label_en)

            label_ar = QAction('Arabic Names', labels_menu)
            label_ar.triggered.connect(lambda: self._apply_labels(sudan_layers[0], 'arabic'))
            labels_menu.addAction(label_ar)

            label_pcode = QAction('P-Codes', labels_menu)
            label_pcode.triggered.connect(lambda: self._apply_labels(sudan_layers[0], 'pcode'))
            labels_menu.addAction(label_pcode)

            label_remove = QAction('Remove Labels', labels_menu)
            label_remove.triggered.connect(lambda: self._remove_labels(sudan_layers[0]))
            labels_menu.addAction(label_remove)

            menu.addMenu(labels_menu)

            menu.addSeparator()

            # Export options
            export_action = QAction('Export Selected Features...', menu)
            export_action.triggered.connect(lambda: self._export_layer(sudan_layers[0]))
            menu.addAction(export_action)

            # Generate report
            report_action = QAction('Generate Report...', menu)
            report_action.triggered.connect(lambda: self._generate_report(sudan_layers[0]))
            menu.addAction(report_action)

            menu.addSeparator()

        return menu

    def _zoom_to_layer(self, layer):
        """Zoom to layer extent."""
        self.iface.mapCanvas().setExtent(layer.extent())
        self.iface.mapCanvas().refresh()

    def _show_statistics(self, layer):
        """Show statistics for layer."""
        QgsMessageLog.logMessage(
            f"Requested statistics for: {layer.name()}",
            "Sudan Data Loader",
            Qgis.Info
        )
        # This should trigger the statistics panel
        self.iface.messageBar().pushInfo(
            'Statistics',
            f'Open Statistics Panel to view details for {layer.name()}'
        )

    def _apply_labels(self, layer, label_type):
        """Apply labels to layer."""
        from ..core.labeling_utils import LabelingUtils

        # Determine layer type and apply appropriate labels
        name = layer.name().lower()
        if 'admin 1' in name or 'states' in name:
            LabelingUtils.apply_state_labels(label_type, layer)
        elif 'admin 2' in name or 'localities' in name:
            LabelingUtils.apply_locality_labels(label_type, layer)
        else:
            LabelingUtils.apply_generic_labels(layer, label_type)

        layer.triggerRepaint()

    def _remove_labels(self, layer):
        """Remove labels from layer."""
        layer.setLabelsEnabled(False)
        layer.triggerRepaint()

    def _export_layer(self, layer):
        """Export layer features."""
        QgsMessageLog.logMessage(
            f"Requested export for: {layer.name()}",
            "Sudan Data Loader",
            Qgis.Info
        )
        self.iface.messageBar().pushInfo(
            'Export',
            f'Use Sudan Data Loader > Export Features for {layer.name()}'
        )

    def _generate_report(self, layer):
        """Generate report for layer."""
        QgsMessageLog.logMessage(
            f"Requested report for: {layer.name()}",
            "Sudan Data Loader",
            Qgis.Info
        )
        self.iface.messageBar().pushInfo(
            'Report',
            f'Use Sudan Data Loader > Generate Report for {layer.name()}'
        )


class LayerTreeIntegration(QObject):
    """Integration manager for layer tree customization."""

    def __init__(self, iface):
        """
        Initialize layer tree integration.

        :param iface: QGIS interface instance
        """
        super().__init__()
        self.iface = iface
        self.menu_provider = None
        self.original_provider = None

    def setup(self):
        """Set up layer tree integration."""
        view = self.iface.layerTreeView()

        # Store original provider
        self.original_provider = view.menuProvider()

        # Install custom provider
        self.menu_provider = SudanLayerTreeMenuProvider(self.iface, view)
        view.setMenuProvider(self.menu_provider)

        QgsMessageLog.logMessage(
            "Layer tree integration installed",
            "Sudan Data Loader",
            Qgis.Info
        )

    def teardown(self):
        """Remove layer tree integration."""
        if self.original_provider:
            self.iface.layerTreeView().setMenuProvider(self.original_provider)

    def create_sudan_group(self, group_name='Sudan Data'):
        """
        Create a layer group for Sudan data.

        :param group_name: Name for the group
        :returns: QgsLayerTreeGroup
        """
        root = QgsProject.instance().layerTreeRoot()

        # Check if group already exists
        existing = root.findGroup(group_name)
        if existing:
            return existing

        # Create new group
        group = root.insertGroup(0, group_name)
        return group

    def move_sudan_layers_to_group(self, group=None):
        """
        Move all Sudan layers to a group.

        :param group: Target group (creates 'Sudan Data' if None)
        """
        if group is None:
            group = self.create_sudan_group()

        root = QgsProject.instance().layerTreeRoot()

        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and 'sudan' in layer.name().lower():
                # Find layer node
                node = root.findLayer(layer.id())
                if node and node.parent() != group:
                    # Clone and move to group
                    clone = node.clone()
                    group.addChildNode(clone)
                    node.parent().removeChildNode(node)

    def organize_layers_by_type(self):
        """Organize Sudan layers into subgroups by type."""
        sudan_group = self.create_sudan_group()

        # Create subgroups
        subgroups = {
            'Boundaries': ['admin 0', 'admin 1', 'admin 2', 'country', 'states', 'localities'],
            'Infrastructure': ['lines', 'roads', 'railways'],
            'Points': ['points', 'facilities', 'settlements'],
            'External Data': ['hdx', 'acled', 'osm', 'firms', 'sentinel', 'worldbank', 'iom']
        }

        created_groups = {}
        for group_name in subgroups.keys():
            existing = sudan_group.findGroup(group_name)
            if existing:
                created_groups[group_name] = existing
            else:
                created_groups[group_name] = sudan_group.addGroup(group_name)

        # Move layers to appropriate subgroups
        root = QgsProject.instance().layerTreeRoot()

        for layer in QgsProject.instance().mapLayers().values():
            name_lower = layer.name().lower()
            if 'sudan' not in name_lower:
                continue

            target_group = None
            for group_name, keywords in subgroups.items():
                if any(kw in name_lower for kw in keywords):
                    target_group = created_groups[group_name]
                    break

            if target_group:
                node = root.findLayer(layer.id())
                if node and node.parent() != target_group:
                    clone = node.clone()
                    target_group.addChildNode(clone)
                    if node.parent():
                        node.parent().removeChildNode(node)
