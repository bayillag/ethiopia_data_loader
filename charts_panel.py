# -*- coding: utf-8 -*-
"""
Charts Panel for Ethiopia Data Loader.

Provides interactive data visualization with charts and graphs.
Uses matplotlib for chart rendering.
"""

import os
from io import BytesIO

from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QGroupBox, QComboBox, QPushButton,
    QTabWidget, QScrollArea, QFrame, QFileDialog,
    QMessageBox, QSizePolicy
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QPixmap, QImage
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsDistanceArea,
    QgsCoordinateReferenceSystem
)

# Try to import matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class ChartWidget(QLabel):
    """Widget for displaying a matplotlib chart."""

    def __init__(self, parent=None):
        """Initialize the chart widget."""
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(300, 250)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet('background-color: white; border: 1px solid #ddd; border-radius: 5px;')
        self.current_figure = None

    def render_figure(self, fig):
        """
        Render a matplotlib figure to this widget.

        :param fig: matplotlib Figure object
        """
        self.current_figure = fig

        # Render to buffer
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        buf.seek(0)

        # Convert to QPixmap
        image = QImage.fromData(buf.getvalue())
        pixmap = QPixmap.fromImage(image)

        # Scale to fit widget while maintaining aspect ratio
        scaled = pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.setPixmap(scaled)

        plt.close(fig)

    def save_chart(self, filepath, dpi=300):
        """
        Save the current chart to a file.

        :param filepath: Output file path
        :param dpi: Resolution in dots per inch
        """
        if self.current_figure:
            self.current_figure.savefig(filepath, dpi=dpi, bbox_inches='tight')

    def clear(self):
        """Clear the chart."""
        self.current_figure = None
        self.setText('No data')


class ChartsPanel(QDockWidget):
    """Dock panel for data visualization charts."""

    def __init__(self, iface, parent=None):
        """
        Initialize the charts panel.

        :param iface: QGIS interface instance
        :param parent: Parent widget
        """
        super().__init__('Sudan Charts', parent)
        self.iface = iface
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        # Distance calculator
        self.distance_area = QgsDistanceArea()
        self.distance_area.setSourceCrs(
            QgsCoordinateReferenceSystem('EPSG:4326'),
            QgsProject.instance().transformContext()
        )
        self.distance_area.setEllipsoid('WGS84')

        self.setup_ui()

    def setup_ui(self):
        """Set up the panel UI."""
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)

        # Check matplotlib availability
        if not HAS_MATPLOTLIB:
            warning = QLabel(
                'Matplotlib is not installed.\n\n'
                'Charts require matplotlib. Install with:\n'
                'pip install matplotlib'
            )
            warning.setAlignment(Qt.AlignCenter)
            warning.setStyleSheet('color: orange; padding: 20px;')
            layout.addWidget(warning)
            self.setWidget(main_widget)
            return

        # Tab widget for different chart types
        tabs = QTabWidget()
        tabs.addTab(self._create_area_tab(), 'Area Distribution')
        tabs.addTab(self._create_comparison_tab(), 'State Comparison')
        tabs.addTab(self._create_summary_tab(), 'Summary')
        layout.addWidget(tabs)

        self.setWidget(main_widget)

    def _create_area_tab(self):
        """Create the area distribution tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Controls
        controls = QHBoxLayout()

        controls.addWidget(QLabel('Layer:'))
        self.area_layer_combo = QComboBox()
        self.area_layer_combo.setMinimumWidth(200)
        controls.addWidget(self.area_layer_combo)

        refresh_btn = QPushButton('Refresh')
        refresh_btn.clicked.connect(self._refresh_area_chart)
        controls.addWidget(refresh_btn)

        controls.addStretch()

        layout.addLayout(controls)

        # Chart type
        chart_type_layout = QHBoxLayout()
        chart_type_layout.addWidget(QLabel('Chart Type:'))

        self.area_chart_type = QComboBox()
        self.area_chart_type.addItems(['Pie Chart', 'Bar Chart', 'Horizontal Bar'])
        self.area_chart_type.currentIndexChanged.connect(self._refresh_area_chart)
        chart_type_layout.addWidget(self.area_chart_type)

        chart_type_layout.addStretch()

        layout.addLayout(chart_type_layout)

        # Chart widget
        self.area_chart = ChartWidget()
        layout.addWidget(self.area_chart, 1)

        # Export button
        export_btn = QPushButton('Export Chart')
        export_btn.clicked.connect(lambda: self._export_chart(self.area_chart))
        layout.addWidget(export_btn)

        # Populate layers
        self._populate_layer_combos()

        return widget

    def _create_comparison_tab(self):
        """Create the state comparison tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Controls
        controls = QHBoxLayout()

        controls.addWidget(QLabel('Metric:'))
        self.comparison_metric = QComboBox()
        self.comparison_metric.addItems(['Area (km²)', 'Feature Count', 'Perimeter (km)'])
        self.comparison_metric.currentIndexChanged.connect(self._refresh_comparison_chart)
        controls.addWidget(self.comparison_metric)

        refresh_btn = QPushButton('Refresh')
        refresh_btn.clicked.connect(self._refresh_comparison_chart)
        controls.addWidget(refresh_btn)

        controls.addStretch()

        layout.addLayout(controls)

        # Top N selection
        top_n_layout = QHBoxLayout()
        top_n_layout.addWidget(QLabel('Show Top:'))

        self.top_n_combo = QComboBox()
        self.top_n_combo.addItems(['5', '10', '15', '18 (All)'])
        self.top_n_combo.setCurrentIndex(1)
        self.top_n_combo.currentIndexChanged.connect(self._refresh_comparison_chart)
        top_n_layout.addWidget(self.top_n_combo)

        top_n_layout.addStretch()

        layout.addLayout(top_n_layout)

        # Chart widget
        self.comparison_chart = ChartWidget()
        layout.addWidget(self.comparison_chart, 1)

        # Export button
        export_btn = QPushButton('Export Chart')
        export_btn.clicked.connect(lambda: self._export_chart(self.comparison_chart))
        layout.addWidget(export_btn)

        return widget

    def _create_summary_tab(self):
        """Create the summary statistics tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Controls
        controls = QHBoxLayout()

        refresh_btn = QPushButton('Generate Summary')
        refresh_btn.clicked.connect(self._refresh_summary_charts)
        controls.addWidget(refresh_btn)

        controls.addStretch()

        layout.addLayout(controls)

        # Summary charts in a scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Multiple summary charts
        self.summary_chart1 = ChartWidget()
        self.summary_chart1.setMinimumHeight(200)
        scroll_layout.addWidget(QLabel('States by Area'))
        scroll_layout.addWidget(self.summary_chart1)

        self.summary_chart2 = ChartWidget()
        self.summary_chart2.setMinimumHeight(200)
        scroll_layout.addWidget(QLabel('Data Coverage'))
        scroll_layout.addWidget(self.summary_chart2)

        scroll_layout.addStretch()

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        return widget

    def _populate_layer_combos(self):
        """Populate layer combo boxes with Sudan layers."""
        self.area_layer_combo.clear()

        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and 'sudan' in layer.name().lower():
                if layer.geometryType() == 2:  # Polygon
                    self.area_layer_combo.addItem(layer.name(), layer.id())

    def _refresh_area_chart(self):
        """Refresh the area distribution chart."""
        if not HAS_MATPLOTLIB:
            return

        layer_id = self.area_layer_combo.currentData()
        if not layer_id:
            return

        layer = QgsProject.instance().mapLayer(layer_id)
        if not layer:
            return

        # Calculate areas
        name_field = self._find_name_field(layer)
        data = []

        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom:
                area = self.distance_area.measureArea(geom) / 1_000_000
                name = feature[name_field] if name_field else f"Feature {feature.id()}"
                data.append((name, area))

        # Sort by area descending
        data.sort(key=lambda x: x[1], reverse=True)

        # Create chart
        fig, ax = plt.subplots(figsize=(8, 6))

        names = [d[0] for d in data[:10]]  # Top 10
        values = [d[1] for d in data[:10]]

        chart_type = self.area_chart_type.currentText()

        if chart_type == 'Pie Chart':
            colors = plt.cm.Set3(range(len(names)))
            ax.pie(values, labels=names, autopct='%1.1f%%', colors=colors)
            ax.set_title('Area Distribution (Top 10)')
        elif chart_type == 'Bar Chart':
            bars = ax.bar(range(len(names)), values, color='#3498db')
            ax.set_xticks(range(len(names)))
            ax.set_xticklabels(names, rotation=45, ha='right')
            ax.set_ylabel('Area (km²)')
            ax.set_title('Area by Region')
        else:  # Horizontal Bar
            y_pos = range(len(names))
            ax.barh(y_pos, values, color='#27ae60')
            ax.set_yticks(y_pos)
            ax.set_yticklabels(names)
            ax.set_xlabel('Area (km²)')
            ax.set_title('Area by Region')
            ax.invert_yaxis()

        fig.tight_layout()
        self.area_chart.render_figure(fig)

    def _refresh_comparison_chart(self):
        """Refresh the state comparison chart."""
        if not HAS_MATPLOTLIB:
            return

        # Find Admin 1 layer
        admin1_layer = None
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                name = layer.name().lower()
                if ('admin 1' in name or 'states' in name) and 'sudan' in name:
                    admin1_layer = layer
                    break

        if not admin1_layer:
            self.comparison_chart.setText('Admin 1 (States) layer not found')
            return

        metric = self.comparison_metric.currentText()
        top_n_text = self.top_n_combo.currentText()
        top_n = int(top_n_text.split()[0]) if top_n_text[0].isdigit() else 18

        # Gather data
        name_field = self._find_name_field(admin1_layer)
        data = []

        for feature in admin1_layer.getFeatures():
            name = feature[name_field] if name_field else f"State {feature.id()}"
            geom = feature.geometry()

            if metric == 'Area (km²)':
                value = self.distance_area.measureArea(geom) / 1_000_000 if geom else 0
            elif metric == 'Feature Count':
                value = 1
            else:  # Perimeter
                value = self.distance_area.measurePerimeter(geom) / 1000 if geom else 0

            data.append((name, value))

        # Sort and limit
        data.sort(key=lambda x: x[1], reverse=True)
        data = data[:top_n]

        # Create chart
        fig, ax = plt.subplots(figsize=(10, 6))

        names = [d[0] for d in data]
        values = [d[1] for d in data]

        colors = plt.cm.viridis([i / len(names) for i in range(len(names))])
        bars = ax.barh(range(len(names)), values, color=colors)

        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names)
        ax.set_xlabel(metric)
        ax.set_title(f'Sudan States by {metric}')
        ax.invert_yaxis()

        # Add value labels
        for i, (name, value) in enumerate(data):
            ax.text(value, i, f' {value:,.1f}', va='center', fontsize=8)

        fig.tight_layout()
        self.comparison_chart.render_figure(fig)

    def _refresh_summary_charts(self):
        """Refresh summary statistics charts."""
        if not HAS_MATPLOTLIB:
            return

        # Chart 1: States by area (donut chart)
        admin1_layer = None
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                name = layer.name().lower()
                if ('admin 1' in name or 'states' in name) and 'sudan' in name:
                    admin1_layer = layer
                    break

        if admin1_layer:
            name_field = self._find_name_field(admin1_layer)
            data = []

            for feature in admin1_layer.getFeatures():
                name = feature[name_field] if name_field else f"State {feature.id()}"
                geom = feature.geometry()
                area = self.distance_area.measureArea(geom) / 1_000_000 if geom else 0
                data.append((name, area))

            data.sort(key=lambda x: x[1], reverse=True)

            fig1, ax1 = plt.subplots(figsize=(8, 5))
            names = [d[0] for d in data[:8]]
            values = [d[1] for d in data[:8]]
            if len(data) > 8:
                names.append('Others')
                values.append(sum(d[1] for d in data[8:]))

            colors = plt.cm.Set2(range(len(names)))
            wedges, texts, autotexts = ax1.pie(
                values, labels=names, autopct='%1.1f%%',
                colors=colors, pctdistance=0.75
            )

            # Draw center circle for donut effect
            centre_circle = plt.Circle((0, 0), 0.50, fc='white')
            ax1.add_patch(centre_circle)
            ax1.set_title('States by Area')

            fig1.tight_layout()
            self.summary_chart1.render_figure(fig1)

        # Chart 2: Data coverage
        coverage = []
        layer_types = ['Admin 0', 'Admin 1', 'Admin 2', 'Lines', 'Points']

        for layer_type in layer_types:
            found = False
            for layer in QgsProject.instance().mapLayers().values():
                if isinstance(layer, QgsVectorLayer):
                    name = layer.name().lower()
                    if layer_type.lower() in name and 'sudan' in name:
                        found = True
                        break
            coverage.append(1 if found else 0)

        fig2, ax2 = plt.subplots(figsize=(8, 4))

        colors = ['#27ae60' if c else '#e74c3c' for c in coverage]
        bars = ax2.barh(layer_types, coverage, color=colors)

        ax2.set_xlim(0, 1.2)
        ax2.set_xlabel('Loaded')
        ax2.set_title('Data Layer Coverage')

        # Add labels
        for i, (lt, c) in enumerate(zip(layer_types, coverage)):
            label = 'Loaded' if c else 'Not Loaded'
            ax2.text(c + 0.1, i, label, va='center')

        ax2.set_xticks([])

        fig2.tight_layout()
        self.summary_chart2.render_figure(fig2)

    def _find_name_field(self, layer):
        """Find the best name field in a layer."""
        field_names = [f.name() for f in layer.fields()]
        candidates = ['ADM1_EN', 'ADM2_EN', 'name', 'NAME', 'Name',
                      'admin1Name_en', 'admin2Name_en', 'STATE_NAME']

        for candidate in candidates:
            if candidate in field_names:
                return candidate

        return field_names[0] if field_names else None

    def _export_chart(self, chart_widget):
        """Export a chart to file."""
        if not chart_widget.current_figure:
            QMessageBox.warning(self, 'No Chart', 'Please generate a chart first.')
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, 'Export Chart',
            os.path.expanduser('~/sudan_chart.png'),
            'PNG Files (*.png);;SVG Files (*.svg);;PDF Files (*.pdf)'
        )

        if filepath:
            try:
                chart_widget.save_chart(filepath, dpi=300)
                QMessageBox.information(
                    self, 'Export Complete',
                    f'Chart exported to:\n{filepath}'
                )
            except Exception as e:
                QMessageBox.critical(self, 'Export Error', str(e))

    def showEvent(self, event):
        """Handle show event."""
        super().showEvent(event)
        self._populate_layer_combos()
