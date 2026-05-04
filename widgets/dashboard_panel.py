# -*- coding: utf-8 -*-
"""
Dashboard Panel for Ethiopia Data Loader.

Provides a main dashboard with KPI cards, mini-map, and quick actions.
"""

from datetime import datetime

from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QGroupBox, QGridLayout, QPushButton,
    QFrame, QScrollArea, QSizePolicy
)
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QFont, QColor, QPainter
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsDistanceArea,
    QgsCoordinateReferenceSystem
)


class KPICard(QFrame):
    """A card widget displaying a key performance indicator."""

    def __init__(self, title, value='--', subtitle='', color='#3498db', parent=None):
        """
        Initialize the KPI card.

        :param title: Card title
        :param value: Main value to display
        :param subtitle: Additional text below value
        :param color: Accent color
        :param parent: Parent widget
        """
        super().__init__(parent)
        self.color = color

        self.setFrameStyle(QFrame.StyledPanel)
        self.setMinimumSize(150, 100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.setup_ui(title, value, subtitle)
        self.update_style()

    def setup_ui(self, title, value, subtitle):
        """Set up the card UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)

        # Title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet('color: gray; font-size: 11px;')
        layout.addWidget(self.title_label)

        # Value
        self.value_label = QLabel(value)
        value_font = QFont()
        value_font.setPointSize(24)
        value_font.setBold(True)
        self.value_label.setFont(value_font)
        layout.addWidget(self.value_label)

        # Subtitle
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet('color: gray; font-size: 10px;')
        layout.addWidget(self.subtitle_label)

    def update_style(self):
        """Update card style."""
        self.setStyleSheet(f"""
            KPICard {{
                background-color: white;
                border: none;
                border-left: 4px solid {self.color};
                border-radius: 8px;
            }}
        """)
        self.value_label.setStyleSheet(f'color: {self.color};')

    def set_value(self, value, subtitle=''):
        """Update the displayed value."""
        self.value_label.setText(str(value))
        if subtitle:
            self.subtitle_label.setText(subtitle)

    def set_color(self, color):
        """Update the accent color."""
        self.color = color
        self.update_style()


class DashboardPanel(QDockWidget):
    """Main dashboard panel for Ethiopia Data Loader."""

    def __init__(self, iface, parent=None):
        """
        Initialize the dashboard panel.

        :param iface: QGIS interface instance
        :param parent: Parent widget
        """
        super().__init__('Ethiopia Dashboard', parent)
        self.iface = iface
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        # Initialize distance calculator
        self.distance_area = QgsDistanceArea()
        self.distance_area.setSourceCrs(
            QgsCoordinateReferenceSystem('EPSG:4326'),
            QgsProject.instance().transformContext()
        )
        self.distance_area.setEllipsoid('WGS84')

        self.setup_ui()

        # Connect to project signals for auto-refresh
        QgsProject.instance().layersAdded.connect(self.refresh_stats)
        QgsProject.instance().layersRemoved.connect(self.refresh_stats)

    def setup_ui(self):
        """Set up the panel UI."""
        # Main widget with scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameStyle(QFrame.NoFrame)

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        header = QLabel('Sudan Data Dashboard')
        header.setStyleSheet('font-size: 16px; font-weight: bold;')
        header_layout.addWidget(header)

        refresh_btn = QPushButton('Refresh')
        refresh_btn.setFixedWidth(80)
        refresh_btn.clicked.connect(self.refresh_stats)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # KPI Cards
        kpi_group = QGroupBox('Key Statistics')
        kpi_layout = QGridLayout(kpi_group)
        kpi_layout.setSpacing(10)

        self.states_card = KPICard('States', '--', 'Admin 1', '#3498db')
        kpi_layout.addWidget(self.states_card, 0, 0)

        self.localities_card = KPICard('Localities', '--', 'Admin 2', '#27ae60')
        kpi_layout.addWidget(self.localities_card, 0, 1)

        self.area_card = KPICard('Total Area', '--', 'km²', '#9b59b6')
        kpi_layout.addWidget(self.area_card, 1, 0)

        self.layers_card = KPICard('Layers', '--', 'Loaded', '#e67e22')
        kpi_layout.addWidget(self.layers_card, 1, 1)

        layout.addWidget(kpi_group)

        # Data Status
        status_group = QGroupBox('Data Status')
        status_layout = QVBoxLayout(status_group)

        self.status_labels = {}
        status_items = [
            ('Admin 0 (Country)', 'admin0'),
            ('Admin 1 (States)', 'admin1'),
            ('Admin 2 (Localities)', 'admin2'),
            ('Admin Lines', 'admin_lines'),
            ('Admin Points', 'admin_points')
        ]

        for label_text, key in status_items:
            row = QHBoxLayout()
            name_label = QLabel(label_text)
            row.addWidget(name_label)

            status_label = QLabel('Not loaded')
            status_label.setStyleSheet('color: gray;')
            row.addWidget(status_label)

            self.status_labels[key] = status_label
            status_layout.addLayout(row)

        layout.addWidget(status_group)

        # Quick Actions
        actions_group = QGroupBox('Quick Actions')
        actions_layout = QGridLayout(actions_group)
        actions_layout.setSpacing(8)

        quick_actions = [
            ('Load All Data', self._load_all_data, 0, 0),
            ('Zoom to Sudan', self._zoom_to_sudan, 0, 1),
            ('Add OSM Basemap', self._add_basemap, 1, 0),
            ('Open Search', self._open_search, 1, 1),
            ('Generate Report', self._generate_report, 2, 0),
            ('Validate Data', self._validate_data, 2, 1)
        ]

        for text, callback, row, col in quick_actions:
            btn = QPushButton(text)
            btn.clicked.connect(callback)
            btn.setMinimumHeight(35)
            actions_layout.addWidget(btn, row, col)

        layout.addWidget(actions_group)

        # Recent Activity
        activity_group = QGroupBox('Recent Activity')
        activity_layout = QVBoxLayout(activity_group)

        self.activity_label = QLabel('No recent activity')
        self.activity_label.setWordWrap(True)
        self.activity_label.setStyleSheet('color: gray; font-size: 11px;')
        activity_layout.addWidget(self.activity_label)

        layout.addWidget(activity_group)

        # Last updated
        self.updated_label = QLabel('Last updated: Never')
        self.updated_label.setStyleSheet('color: gray; font-size: 10px;')
        layout.addWidget(self.updated_label)

        layout.addStretch()

        scroll.setWidget(main_widget)
        self.setWidget(scroll)

        # Initial refresh
        QTimer.singleShot(100, self.refresh_stats)

    def refresh_stats(self):
        """Refresh all dashboard statistics."""
        project = QgsProject.instance()
        layers = project.mapLayers().values()

        # Count Sudan layers
        sudan_layers = []
        states_count = 0
        localities_count = 0
        total_area = 0

        for layer in layers:
            if isinstance(layer, QgsVectorLayer) and 'sudan' in layer.name().lower():
                sudan_layers.append(layer)

                name_lower = layer.name().lower()

                # Update status
                if 'admin 0' in name_lower or 'country' in name_lower:
                    self.status_labels['admin0'].setText('Loaded')
                    self.status_labels['admin0'].setStyleSheet('color: green;')
                    # Calculate total area
                    total_area = self._calculate_area(layer)

                elif 'admin 1' in name_lower or 'states' in name_lower:
                    self.status_labels['admin1'].setText('Loaded')
                    self.status_labels['admin1'].setStyleSheet('color: green;')
                    states_count = layer.featureCount()

                elif 'admin 2' in name_lower or 'localities' in name_lower:
                    self.status_labels['admin2'].setText('Loaded')
                    self.status_labels['admin2'].setStyleSheet('color: green;')
                    localities_count = layer.featureCount()

                elif 'lines' in name_lower:
                    self.status_labels['admin_lines'].setText('Loaded')
                    self.status_labels['admin_lines'].setStyleSheet('color: green;')

                elif 'points' in name_lower:
                    self.status_labels['admin_points'].setText('Loaded')
                    self.status_labels['admin_points'].setStyleSheet('color: green;')

        # Update KPI cards
        self.states_card.set_value(states_count if states_count else '--')
        self.localities_card.set_value(localities_count if localities_count else '--')

        if total_area > 0:
            self.area_card.set_value(f'{total_area:,.0f}')
        else:
            self.area_card.set_value('--')

        self.layers_card.set_value(len(sudan_layers))

        # Reset unloaded status
        for key, label in self.status_labels.items():
            if 'Loaded' not in label.text():
                label.setText('Not loaded')
                label.setStyleSheet('color: gray;')

        # Update timestamp
        self.updated_label.setText(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

    def _calculate_area(self, layer):
        """Calculate total area of a polygon layer in km²."""
        if layer.geometryType() != 2:  # Not polygon
            return 0

        total_area = 0
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom:
                area = self.distance_area.measureArea(geom) / 1_000_000  # to km²
                total_area += area

        return total_area

    def _load_all_data(self):
        """Quick action: Load all Sudan data."""
        # Find and trigger the load action from main plugin
        for action in self.iface.mainWindow().findChildren(QPushButton):
            if 'Load All' in action.text():
                action.click()
                return

        self.log_activity('Load All Data requested')

    def _zoom_to_sudan(self):
        """Quick action: Zoom to Sudan extent."""
        # Sudan approximate extent
        from qgis.core import QgsRectangle
        sudan_extent = QgsRectangle(21.5, 8.5, 39.0, 23.5)
        self.iface.mapCanvas().setExtent(sudan_extent)
        self.iface.mapCanvas().refresh()
        self.log_activity('Zoomed to Sudan')

    def _add_basemap(self):
        """Quick action: Add OSM basemap."""
        uri = 'type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png&zmax=19&zmin=0'
        from qgis.core import QgsRasterLayer
        layer = QgsRasterLayer(uri, 'OpenStreetMap', 'wms')
        if layer.isValid():
            QgsProject.instance().addMapLayer(layer, False)
            root = QgsProject.instance().layerTreeRoot()
            root.insertLayer(-1, layer)
            self.log_activity('Added OpenStreetMap basemap')

    def _open_search(self):
        """Quick action: Open search panel."""
        self.log_activity('Search panel requested')
        # This should be connected to the main plugin

    def _generate_report(self):
        """Quick action: Generate report."""
        self.log_activity('Report generation requested')
        # This should be connected to the main plugin

    def _validate_data(self):
        """Quick action: Validate data."""
        self.log_activity('Data validation requested')
        # This should be connected to the main plugin

    def log_activity(self, message):
        """Log an activity to the recent activity list."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        current = self.activity_label.text()

        if current == 'No recent activity':
            self.activity_label.setText(f"[{timestamp}] {message}")
        else:
            lines = current.split('\n')
            lines.insert(0, f"[{timestamp}] {message}")
            # Keep only last 5 activities
            self.activity_label.setText('\n'.join(lines[:5]))
