# -*- coding: utf-8 -*-
"""
Report Generator for Ethiopia Data Loader.

Generates PDF and HTML reports for Ethiopia administrative data.
"""

import os
from datetime import datetime
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QPushButton, QGroupBox, QLabel,
    QDialogButtonBox, QCheckBox, QLineEdit, QTextEdit,
    QFileDialog, QMessageBox, QProgressDialog
)
from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QImage, QPainter
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsLayoutExporter,
    QgsLayout, QgsLayoutItemMap, QgsLayoutItemLabel,
    QgsLayoutItemScaleBar, QgsLayoutItemLegend,
    QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes,
    QgsDistanceArea, QgsCoordinateReferenceSystem
)


class ReportGenerator:
    """Generates reports for Ethiopia data."""

    def __init__(self, iface):
        """
        Initialize the report generator.

        :param iface: QGIS interface instance
        """
        self.iface = iface

    def generate_summary_report(self, output_path, format='html'):
        """
        Generate a summary report of all Ethiopia data.

        :param output_path: Path to save the report
        :param format: 'html' or 'pdf'
        :returns: True if successful
        """
        # Collect data
        layers_info = []
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and 'Ethiopia' in layer.name().lower():
                layers_info.append({
                    'name': layer.name(),
                    'features': layer.featureCount(),
                    'crs': layer.crs().authid(),
                    'type': ['Point', 'Line', 'Polygon'][layer.geometryType()]
                })

        # Generate HTML content
        html = self._generate_summary_html(layers_info)

        if format == 'html':
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            return True

        elif format == 'pdf':
            return self._html_to_pdf(html, output_path)

        return False

    def generate_state_profile(self, state_name, output_path, format='html'):
        """
        Generate a profile report for a specific state.

        :param state_name: Name of the state
        :param output_path: Path to save the report
        :param format: 'html' or 'pdf'
        :returns: True if successful
        """
        # Find state data
        state_data = self._get_state_data(state_name)
        if not state_data:
            return False

        # Generate HTML content
        html = self._generate_state_html(state_data)

        if format == 'html':
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            return True

        elif format == 'pdf':
            return self._html_to_pdf(html, output_path)

        return False

    def _get_state_data(self, state_name):
        """Get data for a specific state."""
        # Find states layer
        states_layer = None
        localities_layer = None

        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                if 'Admin 1' in layer.name() or 'States' in layer.name():
                    states_layer = layer
                elif 'Admin 2' in layer.name() or 'Localities' in layer.name():
                    localities_layer = layer

        if not states_layer:
            return None

        # Find state feature
        state_feature = None
        name_field = None

        for field_name in ['ADM1_EN', 'admin1Name_en', 'name', 'NAME']:
            if field_name in [f.name() for f in states_layer.fields()]:
                name_field = field_name
                break

        if not name_field:
            return None

        for feature in states_layer.getFeatures():
            if feature[name_field] == state_name:
                state_feature = feature
                break

        if not state_feature:
            return None

        # Calculate area
        da = QgsDistanceArea()
        da.setSourceCrs(states_layer.crs(), QgsProject.instance().transformContext())
        da.setEllipsoid('WGS84')
        area_km2 = da.measureArea(state_feature.geometry()) / 1_000_000

        # Count localities
        locality_count = 0
        if localities_layer:
            # Try to find matching pcode field in localities layer
            pcode_field = None
            for field_name in ['ADM1_PCODE', 'admin1Pcode', 'ADM1PCODE']:
                if field_name in [f.name() for f in localities_layer.fields()]:
                    pcode_field = field_name
                    break

            # Try to get state pcode from state feature
            state_pcode = None
            for field_name in ['ADM1_PCODE', 'admin1Pcode', 'ADM1PCODE']:
                if field_name in [f.name() for f in states_layer.fields()]:
                    state_pcode = state_feature[field_name]
                    break

            if pcode_field and state_pcode:
                # Match by pcode (case-insensitive)
                state_pcode_upper = str(state_pcode).upper().strip()
                for feature in localities_layer.getFeatures():
                    loc_pcode = feature[pcode_field]
                    if loc_pcode and str(loc_pcode).upper().strip() == state_pcode_upper:
                        locality_count += 1
            elif state_feature.geometry():
                # Fallback: count localities that intersect with state geometry
                state_geom = state_feature.geometry()
                for feature in localities_layer.getFeatures():
                    if feature.geometry() and feature.geometry().intersects(state_geom):
                        locality_count += 1

        return {
            'name': state_name,
            'area_km2': area_km2,
            'locality_count': locality_count,
            'extent': state_feature.geometry().boundingBox(),
        }

    def _generate_summary_html(self, layers_info):
        """Generate HTML for summary report."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Sudan Data Summary Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>Ethiopia Administrative Data Summary</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

    <h2>Loaded Layers</h2>
    <table>
        <tr>
            <th>Layer Name</th>
            <th>Feature Count</th>
            <th>Geometry Type</th>
            <th>CRS</th>
        </tr>
"""
        for layer in layers_info:
            html += f"""
        <tr>
            <td>{layer['name']}</td>
            <td>{layer['features']}</td>
            <td>{layer['type']}</td>
            <td>{layer['crs']}</td>
        </tr>
"""

        html += """
    </table>

    <div class="footer">
        Generated by Sudan Data Loader QGIS Plugin
    </div>
</body>
</html>
"""
        return html

    def _generate_state_html(self, state_data):
        """Generate HTML for state profile report."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>State Profile: {state_data['name']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #27ae60; padding-bottom: 10px; }}
        h2 {{ color: #34495e; }}
        .stat-box {{ background: #ecf0f1; padding: 20px; margin: 10px 0; border-radius: 5px; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #27ae60; }}
        .stat-label {{ color: #7f8c8d; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>State Profile: {state_data['name']}</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

    <h2>Statistics</h2>
    <div class="stat-box">
        <span class="stat-value">{state_data['area_km2']:,.2f} km²</span><br>
        <span class="stat-label">Total Area</span>
    </div>

    <div class="stat-box">
        <span class="stat-value">{state_data['locality_count']}</span><br>
        <span class="stat-label">Number of Localities</span>
    </div>

    <h2>Geographic Extent</h2>
    <ul>
        <li>X Min: {state_data['extent'].xMinimum():.4f}</li>
        <li>X Max: {state_data['extent'].xMaximum():.4f}</li>
        <li>Y Min: {state_data['extent'].yMinimum():.4f}</li>
        <li>Y Max: {state_data['extent'].yMaximum():.4f}</li>
    </ul>

    <div class="footer">
        Generated by Ethiopia Data Loader QGIS Plugin
    </div>
</body>
</html>
"""
        return html

    def _html_to_pdf(self, html, output_path):
        """Convert HTML to PDF (requires additional libraries)."""
        # Try to use available PDF libraries
        try:
            from qgis.PyQt.QtPrintSupport import QPrinter
            from qgis.PyQt.QtWidgets import QTextDocument

            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(output_path)

            doc = QTextDocument()
            doc.setHtml(html)
            doc.print_(printer)

            return True
        except Exception as e:
            # Fallback: save as HTML
            html_path = output_path.replace('.pdf', '.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
            return False

    def export_map_image(self, output_path, width=800, height=600):
        """
        Export current map view as an image.

        :param output_path: Path to save the image
        :param width: Image width
        :param height: Image height
        :returns: True if successful
        """
        canvas = self.iface.mapCanvas()

        # Create image
        image = QImage(QSize(width, height), QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.white)

        # Render map
        painter = QPainter(image)
        canvas.render(painter)
        painter.end()

        # Save
        return image.save(output_path)


class ReportDialog(QDialog):
    """Dialog for generating reports."""

    def __init__(self, iface, parent=None):
        """
        Initialize the report dialog.

        :param iface: QGIS interface instance
        :param parent: Parent widget
        """
        super().__init__(parent)
        self.iface = iface
        self.report_generator = ReportGenerator(iface)
        self.setWindowTitle('Generate Sudan Report')
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Report type
        type_group = QGroupBox('Report Type')
        type_layout = QFormLayout(type_group)

        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems([
            'Summary Report',
            'State Profile',
            'Map Export'
        ])
        self.report_type_combo.currentIndexChanged.connect(self.on_type_changed)
        type_layout.addRow('Type:', self.report_type_combo)

        # State selector (for state profile)
        self.state_combo = QComboBox()
        self.state_combo.addItems([
            'Khartoum', 'Northern', 'River Nile', 'Red Sea', 'Kassala',
            'Gedaref', 'Sennar', 'Blue Nile', 'White Nile', 'Gezira',
            'North Kordofan', 'South Kordofan', 'West Kordofan',
            'North Darfur', 'West Darfur', 'Central Darfur', 'South Darfur', 'East Darfur'
        ])
        self.state_label = QLabel('State:')
        type_layout.addRow(self.state_label, self.state_combo)

        layout.addWidget(type_group)

        # Output format
        format_group = QGroupBox('Output Format')
        format_layout = QFormLayout(format_group)

        self.format_combo = QComboBox()
        self.format_combo.addItems(['HTML', 'PDF', 'PNG (Map only)'])
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

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.button(QDialogButtonBox.Ok).setText('Generate')
        button_box.accepted.connect(self.generate_report)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Initial visibility
        self.on_type_changed(0)

    def on_type_changed(self, index):
        """Handle report type change."""
        report_type = self.report_type_combo.currentText()
        self.state_label.setVisible(report_type == 'State Profile')
        self.state_combo.setVisible(report_type == 'State Profile')

    def browse_output(self):
        """Browse for output file."""
        format_text = self.format_combo.currentText()
        if 'HTML' in format_text:
            file_filter = 'HTML Files (*.html)'
            ext = 'html'
        elif 'PDF' in format_text:
            file_filter = 'PDF Files (*.pdf)'
            ext = 'pdf'
        else:
            file_filter = 'PNG Images (*.png)'
            ext = 'png'

        file_path, _ = QFileDialog.getSaveFileName(
            self, 'Save Report',
            os.path.expanduser(f'~/sudan_report.{ext}'),
            file_filter
        )

        if file_path:
            self.output_edit.setText(file_path)

    def generate_report(self):
        """Generate the selected report."""
        output_path = self.output_edit.text()
        if not output_path:
            QMessageBox.warning(self, 'No Output', 'Please specify an output file.')
            return

        report_type = self.report_type_combo.currentText()
        format_text = self.format_combo.currentText().lower()

        if 'html' in format_text:
            format_type = 'html'
        elif 'pdf' in format_text:
            format_type = 'pdf'
        else:
            format_type = 'png'

        success = False

        try:
            if report_type == 'Summary Report':
                success = self.report_generator.generate_summary_report(
                    output_path, format_type
                )
            elif report_type == 'State Profile':
                state = self.state_combo.currentText()
                success = self.report_generator.generate_state_profile(
                    state, output_path, format_type
                )
            elif report_type == 'Map Export':
                success = self.report_generator.export_map_image(output_path)

            if success:
                QMessageBox.information(
                    self, 'Report Generated',
                    f'Report saved to:\n{output_path}'
                )
                self.accept()
            else:
                QMessageBox.warning(
                    self, 'Generation Failed',
                    'Failed to generate report. Check that all required data is loaded.'
                )

        except Exception as e:
            QMessageBox.critical(
                self, 'Error',
                f'Report generation failed:\n{str(e)}'
            )
