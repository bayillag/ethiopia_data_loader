# -*- coding: utf-8 -*-
"""
Sketching Tools for Ethiopia Data Loader.

Provides drawing and annotation tools using memory layers.
"""

from qgis.PyQt.QtWidgets import (
    QToolBar, QAction, QMenu, QInputDialog, QColorDialog, QMessageBox
)
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtCore import Qt
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry,
    QgsPointXY, QgsWkbTypes, QgsField, QgsSymbol,
    QgsSingleSymbolRenderer, QgsMarkerSymbol, QgsLineSymbol,
    QgsFillSymbol, QgsTextAnnotation, QgsAnnotationLayer
)
from qgis.gui import (
    QgsMapToolEmitPoint, QgsMapToolCapture, QgsRubberBand
)
from qgis.PyQt.QtCore import QVariant


class PointCaptureTool(QgsMapToolEmitPoint):
    """Map tool for capturing point features."""

    def __init__(self, canvas, sketching_toolbar):
        """Initialize the point capture tool."""
        super().__init__(canvas)
        self.sketching_toolbar = sketching_toolbar
        self.canvas = canvas

    def canvasReleaseEvent(self, event):
        """Handle canvas click to add point."""
        point = self.toMapCoordinates(event.pos())
        self.sketching_toolbar.add_point_feature(point)


class LineCaptureTool(QgsMapToolCapture):
    """Map tool for capturing line features."""

    def __init__(self, canvas, sketching_toolbar):
        """Initialize the line capture tool."""
        super().__init__(canvas, sketching_toolbar.sketching_toolbar.iface.cadDockWidget(), QgsMapToolCapture.CaptureLine)
        self.sketching_toolbar = sketching_toolbar

    def cadCanvasReleaseEvent(self, event):
        """Handle canvas release event."""
        super().cadCanvasReleaseEvent(event)

        if event.button() == Qt.RightButton:
            # Finish the line
            points = self.points()
            if len(points) >= 2:
                self.sketching_toolbar.add_line_feature(points)
            self.stopCapturing()
            self.startCapturing()


class SketchingToolbar:
    """Toolbar for sketching and drawing tools."""

    SKETCHES_LAYER_NAME = 'Ethiopia Sketches'

    def __init__(self, iface):
        """
        Initialize the sketching toolbar.

        :param iface: QGIS interface instance
        """
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.sketching_toolbar = None
        self.sketches_layer = None
        self.current_tool = None
        self.rubber_band = None
        self.point_tool = None
        self.current_color = QColor(255, 0, 0)  # Default red

        # Action references (created in setup_toolbar)
        self.point_action = None
        self.line_action = None
        self.polygon_action = None
        self.color_action = None
        self.clear_action = None

    def create_sketches_layer(self, geometry_type='Point'):
        """
        Create or get the sketches memory layer.

        :param geometry_type: 'Point', 'LineString', or 'Polygon'
        :returns: QgsVectorLayer
        """
        layer_name = f'{self.SKETCHES_LAYER_NAME} ({geometry_type}s)'

        # Check if layer already exists
        existing = QgsProject.instance().mapLayersByName(layer_name)
        if existing:
            return existing[0]

        # Create new memory layer
        uri = f'{geometry_type}?crs=EPSG:4326'
        layer = QgsVectorLayer(uri, layer_name, 'memory')

        if not layer.isValid():
            return None

        # Add fields
        provider = layer.dataProvider()
        provider.addAttributes([
            QgsField('id', QVariant.Int),
            QgsField('label', QVariant.String),
            QgsField('notes', QVariant.String),
            QgsField('created', QVariant.String),
        ])
        layer.updateFields()

        # Set default style
        if geometry_type == 'Point':
            symbol = QgsMarkerSymbol.createSimple({
                'name': 'circle',
                'color': self.current_color.name(),
                'size': '4'
            })
        elif geometry_type == 'LineString':
            symbol = QgsLineSymbol.createSimple({
                'color': self.current_color.name(),
                'width': '0.5'
            })
        else:  # Polygon
            symbol = QgsFillSymbol.createSimple({
                'color': self.current_color.name(),
                'outline_color': 'black',
                'outline_width': '0.3'
            })

        layer.setRenderer(QgsSingleSymbolRenderer(symbol))

        # Add to project
        QgsProject.instance().addMapLayer(layer)

        return layer

    def setup_toolbar(self):
        """Create the sketching toolbar."""
        self.sketching_toolbar = QToolBar('Sudan Sketching')
        self.sketching_toolbar.setObjectName('SudanSketchingToolbar')

        # Point tool
        self.point_action = QAction('Add Point', self.iface.mainWindow())
        self.point_action.setCheckable(True)
        self.point_action.triggered.connect(self.activate_point_tool)
        self.sketching_toolbar.addAction(self.point_action)

        # Line tool
        self.line_action = QAction('Draw Line', self.iface.mainWindow())
        self.line_action.setCheckable(True)
        self.line_action.triggered.connect(self.activate_line_tool)
        self.sketching_toolbar.addAction(self.line_action)

        # Polygon tool
        self.polygon_action = QAction('Draw Polygon', self.iface.mainWindow())
        self.polygon_action.setCheckable(True)
        self.polygon_action.triggered.connect(self.activate_polygon_tool)
        self.sketching_toolbar.addAction(self.polygon_action)

        self.sketching_toolbar.addSeparator()

        # Color picker
        self.color_action = QAction('Color', self.iface.mainWindow())
        self.color_action.triggered.connect(self.pick_color)
        self.sketching_toolbar.addAction(self.color_action)

        # Clear sketches
        self.clear_action = QAction('Clear All', self.iface.mainWindow())
        self.clear_action.triggered.connect(self.clear_sketches)
        self.sketching_toolbar.addAction(self.clear_action)

        # Add toolbar to QGIS
        self.iface.addToolBar(self.sketching_toolbar)

        return self.sketching_toolbar

    def remove_toolbar(self):
        """Remove the sketching toolbar."""
        # Deactivate any active tool first
        self.deactivate_tools()

        if self.sketching_toolbar:
            self.iface.removeToolBar(self.sketching_toolbar)
            self.sketching_toolbar = None

        # Clear action references
        self.point_action = None
        self.line_action = None
        self.polygon_action = None
        self.color_action = None
        self.clear_action = None

    def activate_point_tool(self, checked):
        """Activate the point drawing tool."""
        if checked:
            self.deactivate_tools()
            self.point_action.setChecked(True)
            self.point_tool = PointCaptureTool(self.canvas, self)
            self.canvas.setMapTool(self.point_tool)
        else:
            self.deactivate_tools()

    def activate_line_tool(self, checked):
        """Activate the line drawing tool."""
        if checked:
            self.deactivate_tools()
            self.line_action.setChecked(True)
            # Use rubber band for line drawing
            self.start_rubber_band_capture('line')
        else:
            self.deactivate_tools()

    def activate_polygon_tool(self, checked):
        """Activate the polygon drawing tool."""
        if checked:
            self.deactivate_tools()
            self.polygon_action.setChecked(True)
            # Use rubber band for polygon drawing
            self.start_rubber_band_capture('polygon')
        else:
            self.deactivate_tools()

    def start_rubber_band_capture(self, geom_type):
        """Start capturing with rubber band."""
        if geom_type == 'line':
            self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        else:
            self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)

        self.rubber_band.setColor(self.current_color)
        self.rubber_band.setWidth(2)

    def deactivate_tools(self):
        """Deactivate all sketching tools."""
        # Only try to uncheck actions if they exist
        if self.point_action:
            self.point_action.setChecked(False)
        if self.line_action:
            self.line_action.setChecked(False)
        if self.polygon_action:
            self.polygon_action.setChecked(False)

        if self.rubber_band:
            self.canvas.scene().removeItem(self.rubber_band)
            self.rubber_band = None

        # Only unset map tool if there is one
        current_tool = self.canvas.mapTool()
        if current_tool:
            self.canvas.unsetMapTool(current_tool)

    def pick_color(self):
        """Open color picker dialog."""
        color = QColorDialog.getColor(self.current_color, self.iface.mainWindow())
        if color.isValid():
            self.current_color = color

    def add_point_feature(self, point):
        """
        Add a point feature to the sketches layer.

        :param point: QgsPointXY
        """
        layer = self.create_sketches_layer('Point')
        if not layer:
            return

        # Ask for label
        label, ok = QInputDialog.getText(
            self.iface.mainWindow(),
            'Point Label',
            'Enter label for this point (optional):'
        )

        # Create feature
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(point))
        feature['label'] = label if ok else ''

        # Add feature
        layer.startEditing()
        layer.addFeature(feature)
        layer.commitChanges()

        layer.triggerRepaint()

    def add_line_feature(self, points):
        """
        Add a line feature to the sketches layer.

        :param points: List of QgsPointXY
        """
        layer = self.create_sketches_layer('LineString')
        if not layer:
            return

        # Create feature
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPolylineXY(points))

        # Add feature
        layer.startEditing()
        layer.addFeature(feature)
        layer.commitChanges()

        layer.triggerRepaint()

    def add_polygon_feature(self, points):
        """
        Add a polygon feature to the sketches layer.

        :param points: List of QgsPointXY (ring)
        """
        layer = self.create_sketches_layer('Polygon')
        if not layer:
            return

        # Close the ring if needed
        if points[0] != points[-1]:
            points.append(points[0])

        # Create feature
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPolygonXY([points]))

        # Add feature
        layer.startEditing()
        layer.addFeature(feature)
        layer.commitChanges()

        layer.triggerRepaint()

    def clear_sketches(self):
        """Clear all sketches."""
        reply = QMessageBox.question(
            self.iface.mainWindow(),
            'Clear Sketches',
            'Are you sure you want to clear all sketches?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Remove all sketches layers
        for geom_type in ['Point', 'LineString', 'Polygon']:
            layer_name = f'{self.SKETCHES_LAYER_NAME} ({geom_type}s)'
            layers = QgsProject.instance().mapLayersByName(layer_name)
            for layer in layers:
                QgsProject.instance().removeMapLayer(layer)
