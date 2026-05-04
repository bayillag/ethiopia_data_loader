# -*- coding: utf-8 -*-
"""
Publication Export for Ethiopia Data Loader.

High-quality export for academic publications.
"""

import os
from datetime import datetime
from qgis.core import (
    QgsProject, QgsLayoutExporter, QgsPrintLayout,
    QgsLayoutItemMap, QgsLayoutItemLabel, QgsLayoutItemLegend,
    QgsLayoutItemScaleBar, QgsLayoutItemPicture,
    QgsLayoutSize, QgsLayoutPoint, QgsUnitTypes,
    QgsRectangle, QgsMapSettings
)
from qgis.PyQt.QtCore import QRectF, QSizeF
from qgis.PyQt.QtGui import QFont

# Try to import QgsLegendStyle, handle if not available
try:
    from qgis.core import QgsLegendStyle
except ImportError:
    # Create a simple fallback for older QGIS versions
    class QgsLegendStyle:
        Title = 0
        Group = 1
        Subgroup = 2
        SymbolLabel = 3


class PublicationExporter:
    """Exports maps and data for publication."""

    # Journal-specific templates
    JOURNAL_TEMPLATES = {
        'nature': {
            'width_mm': 180,
            'height_mm': 180,
            'dpi': 300,
            'font_family': 'Arial',
            'title_size': 10,
            'label_size': 8,
            'format': 'tiff'
        },
        'plos_one': {
            'width_mm': 174,
            'height_mm': 234,
            'dpi': 300,
            'font_family': 'Arial',
            'title_size': 12,
            'label_size': 10,
            'format': 'tiff'
        },
        'elsevier': {
            'width_mm': 190,
            'height_mm': 275,
            'dpi': 300,
            'font_family': 'Times New Roman',
            'title_size': 11,
            'label_size': 9,
            'format': 'pdf'
        },
        'springer': {
            'width_mm': 170,
            'height_mm': 240,
            'dpi': 300,
            'font_family': 'Times New Roman',
            'title_size': 10,
            'label_size': 8,
            'format': 'pdf'
        },
        'mdpi': {
            'width_mm': 180,
            'height_mm': 180,
            'dpi': 300,
            'font_family': 'Palatino Linotype',
            'title_size': 10,
            'label_size': 8,
            'format': 'png'
        },
        'thesis': {
            'width_mm': 210,
            'height_mm': 297,
            'dpi': 300,
            'font_family': 'Times New Roman',
            'title_size': 14,
            'label_size': 10,
            'format': 'pdf'
        },
        'poster': {
            'width_mm': 841,
            'height_mm': 1189,
            'dpi': 150,
            'font_family': 'Arial',
            'title_size': 48,
            'label_size': 24,
            'format': 'pdf'
        }
    }

    def __init__(self):
        """Initialize the publication exporter."""
        self.project = QgsProject.instance()

    def export_map(self, output_path, title=None, template='nature',
                   extent=None, layers=None, include_legend=True,
                   include_scalebar=True, include_north_arrow=True,
                   figure_number=None, caption=None):
        """
        Export a publication-ready map.

        :param output_path: Output file path
        :param title: Map title
        :param template: Journal template name or custom dict
        :param extent: Map extent (QgsRectangle)
        :param layers: List of layers to include (None = all visible)
        :param include_legend: Whether to include legend
        :param include_scalebar: Whether to include scale bar
        :param include_north_arrow: Whether to include north arrow
        :param figure_number: Figure number for caption
        :param caption: Figure caption
        :returns: Export result dictionary
        """
        # Get template settings
        if isinstance(template, dict):
            settings = template
        else:
            settings = self.JOURNAL_TEMPLATES.get(template, self.JOURNAL_TEMPLATES['nature'])

        # Create layout
        layout = QgsPrintLayout(self.project)
        layout.initializeDefaults()
        layout.setName(f"Publication Export - {datetime.now().strftime('%Y%m%d_%H%M%S')}")

        # Set page size
        page = layout.pageCollection().page(0)
        page.setPageSize(
            QgsLayoutSize(settings['width_mm'], settings['height_mm'], QgsUnitTypes.LayoutMillimeters)
        )

        # Calculate margins and map area
        margin = 10  # mm
        map_top = 25 if title else 10
        legend_width = 40 if include_legend else 0
        bottom_space = 25 if include_scalebar else 10

        map_width = settings['width_mm'] - 2 * margin - legend_width
        map_height = settings['height_mm'] - map_top - bottom_space - margin

        # Add map
        map_item = QgsLayoutItemMap(layout)
        map_item.setRect(QRectF(0, 0, map_width, map_height))
        map_item.attemptMove(QgsLayoutPoint(margin, map_top, QgsUnitTypes.LayoutMillimeters))
        map_item.attemptResize(QgsLayoutSize(map_width, map_height, QgsUnitTypes.LayoutMillimeters))

        # Set extent
        if extent:
            map_item.setExtent(extent)
        else:
            canvas = self.project.instance()
            # Use current canvas extent if available
            map_item.setExtent(map_item.extent())

        # Set layers
        if layers:
            map_item.setLayers(layers)

        layout.addLayoutItem(map_item)

        # Add title
        if title:
            title_label = QgsLayoutItemLabel(layout)
            title_label.setText(title)

            font = QFont(settings['font_family'], settings['title_size'])
            font.setBold(True)
            title_label.setFont(font)

            title_label.attemptMove(QgsLayoutPoint(margin, 5, QgsUnitTypes.LayoutMillimeters))
            title_label.attemptResize(
                QgsLayoutSize(settings['width_mm'] - 2 * margin, 15, QgsUnitTypes.LayoutMillimeters)
            )
            layout.addLayoutItem(title_label)

        # Add legend
        if include_legend:
            legend = QgsLayoutItemLegend(layout)
            legend.setLinkedMap(map_item)
            legend.setTitle("")

            font = QFont(settings['font_family'], settings['label_size'])
            legend.setStyleFont(QgsLegendStyle.Title, font)
            legend.setStyleFont(QgsLegendStyle.Group, font)
            legend.setStyleFont(QgsLegendStyle.Subgroup, font)
            legend.setStyleFont(QgsLegendStyle.SymbolLabel, font)

            legend.attemptMove(
                QgsLayoutPoint(margin + map_width + 5, map_top, QgsUnitTypes.LayoutMillimeters)
            )
            layout.addLayoutItem(legend)

        # Add scale bar
        if include_scalebar:
            scalebar = QgsLayoutItemScaleBar(layout)
            scalebar.setLinkedMap(map_item)
            scalebar.setStyle('Single Box')
            scalebar.setUnits(QgsUnitTypes.DistanceKilometers)
            scalebar.setNumberOfSegments(4)
            scalebar.setNumberOfSegmentsLeft(0)

            font = QFont(settings['font_family'], settings['label_size'])
            scalebar.setFont(font)

            scalebar.attemptMove(
                QgsLayoutPoint(margin, map_top + map_height + 5, QgsUnitTypes.LayoutMillimeters)
            )
            layout.addLayoutItem(scalebar)

        # Add figure caption
        if figure_number or caption:
            caption_text = ""
            if figure_number:
                caption_text = f"Figure {figure_number}. "
            if caption:
                caption_text += caption

            caption_label = QgsLayoutItemLabel(layout)
            caption_label.setText(caption_text)

            font = QFont(settings['font_family'], settings['label_size'])
            font.setItalic(True)
            caption_label.setFont(font)

            caption_label.attemptMove(
                QgsLayoutPoint(margin, settings['height_mm'] - 10, QgsUnitTypes.LayoutMillimeters)
            )
            caption_label.attemptResize(
                QgsLayoutSize(settings['width_mm'] - 2 * margin, 8, QgsUnitTypes.LayoutMillimeters)
            )
            layout.addLayoutItem(caption_label)

        # Export
        exporter = QgsLayoutExporter(layout)

        # Determine format from settings or output path
        ext = os.path.splitext(output_path)[1].lower()
        if not ext:
            ext = f".{settings.get('format', 'png')}"
            output_path += ext

        export_settings = QgsLayoutExporter.ImageExportSettings()
        export_settings.dpi = settings['dpi']

        if ext in ['.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp']:
            result = exporter.exportToImage(output_path, export_settings)
        elif ext == '.pdf':
            pdf_settings = QgsLayoutExporter.PdfExportSettings()
            pdf_settings.dpi = settings['dpi']
            result = exporter.exportToPdf(output_path, pdf_settings)
        elif ext == '.svg':
            svg_settings = QgsLayoutExporter.SvgExportSettings()
            result = exporter.exportToSvg(output_path, svg_settings)
        else:
            result = exporter.exportToImage(output_path, export_settings)

        success = result == QgsLayoutExporter.Success

        return {
            'success': success,
            'output_path': output_path,
            'format': ext[1:],
            'dpi': settings['dpi'],
            'width_mm': settings['width_mm'],
            'height_mm': settings['height_mm'],
            'template': template if isinstance(template, str) else 'custom'
        }

    def export_figure_series(self, output_dir, base_name, extents, template='nature', **kwargs):
        """
        Export a series of figures.

        :param output_dir: Output directory
        :param base_name: Base filename
        :param extents: List of (extent, title) tuples
        :param template: Journal template
        :param kwargs: Additional arguments for export_map
        :returns: List of export results
        """
        results = []

        for i, (extent, title) in enumerate(extents, 1):
            output_path = os.path.join(output_dir, f"{base_name}_{i}")
            result = self.export_map(
                output_path=output_path,
                title=title,
                template=template,
                extent=extent,
                figure_number=i,
                **kwargs
            )
            results.append(result)

        return results

    def get_available_templates(self):
        """Get list of available journal templates."""
        return [
            {
                'id': k,
                'name': k.replace('_', ' ').title(),
                'width_mm': v['width_mm'],
                'height_mm': v['height_mm'],
                'dpi': v['dpi'],
                'format': v['format']
            }
            for k, v in self.JOURNAL_TEMPLATES.items()
        ]

    def create_custom_template(self, name, width_mm, height_mm, dpi=300,
                                font_family='Arial', title_size=12,
                                label_size=10, format='png'):
        """
        Create a custom export template.

        :param name: Template name
        :param width_mm: Page width in mm
        :param height_mm: Page height in mm
        :param dpi: Resolution
        :param font_family: Font family
        :param title_size: Title font size
        :param label_size: Label font size
        :param format: Export format
        """
        self.JOURNAL_TEMPLATES[name] = {
            'width_mm': width_mm,
            'height_mm': height_mm,
            'dpi': dpi,
            'font_family': font_family,
            'title_size': title_size,
            'label_size': label_size,
            'format': format
        }

    def export_data_table(self, layer, output_path, fields=None,
                          format='csv', include_geometry=False):
        """
        Export attribute table for publication.

        :param layer: QgsVectorLayer
        :param output_path: Output file path
        :param fields: List of field names (None = all)
        :param format: Export format (csv, latex, html)
        :param include_geometry: Include WKT geometry
        :returns: Export result dictionary
        """
        if not layer or not layer.isValid():
            return {'error': 'Invalid layer'}

        # Get fields
        if fields is None:
            fields = [f.name() for f in layer.fields()]
        else:
            fields = [f for f in fields if f in [fld.name() for fld in layer.fields()]]

        if include_geometry:
            fields.append('geometry')

        # Collect data
        rows = []
        for feature in layer.getFeatures():
            row = []
            for field in fields:
                if field == 'geometry':
                    geom = feature.geometry()
                    row.append(geom.asWkt() if geom else '')
                else:
                    value = feature[field]
                    row.append(str(value) if value is not None else '')
            rows.append(row)

        # Export based on format
        if format == 'csv':
            self._export_csv(output_path, fields, rows)
        elif format == 'latex':
            self._export_latex(output_path, fields, rows)
        elif format == 'html':
            self._export_html(output_path, fields, rows)
        else:
            self._export_csv(output_path, fields, rows)

        return {
            'success': True,
            'output_path': output_path,
            'format': format,
            'rows': len(rows),
            'columns': len(fields)
        }

    def _export_csv(self, output_path, headers, rows):
        """Export data as CSV."""
        import csv

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)

    def _export_latex(self, output_path, headers, rows):
        """Export data as LaTeX table."""
        with open(output_path, 'w', encoding='utf-8') as f:
            # Table header
            col_spec = '|' + 'l|' * len(headers)
            f.write('\\begin{table}[htbp]\n')
            f.write('\\centering\n')
            f.write(f'\\begin{{tabular}}{{{col_spec}}}\n')
            f.write('\\hline\n')

            # Header row
            escaped_headers = [self._escape_latex(h) for h in headers]
            f.write(' & '.join(escaped_headers) + ' \\\\\n')
            f.write('\\hline\n')

            # Data rows
            for row in rows[:50]:  # Limit to 50 rows for readability
                escaped_row = [self._escape_latex(str(cell)) for cell in row]
                f.write(' & '.join(escaped_row) + ' \\\\\n')

            if len(rows) > 50:
                f.write(f'\\multicolumn{{{len(headers)}}}{{|c|}}{{... {len(rows) - 50} more rows ...}} \\\\\n')

            f.write('\\hline\n')
            f.write('\\end{tabular}\n')
            f.write('\\caption{Data table}\n')
            f.write('\\label{tab:data}\n')
            f.write('\\end{table}\n')

    def _export_html(self, output_path, headers, rows):
        """Export data as HTML table."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('<!DOCTYPE html>\n')
            f.write('<html>\n<head>\n')
            f.write('<style>\n')
            f.write('table { border-collapse: collapse; width: 100%; }\n')
            f.write('th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }\n')
            f.write('th { background-color: #4CAF50; color: white; }\n')
            f.write('tr:nth-child(even) { background-color: #f2f2f2; }\n')
            f.write('</style>\n')
            f.write('</head>\n<body>\n')
            f.write('<table>\n<thead>\n<tr>\n')

            # Headers
            for h in headers:
                f.write(f'<th>{h}</th>\n')
            f.write('</tr>\n</thead>\n<tbody>\n')

            # Rows
            for row in rows:
                f.write('<tr>\n')
                for cell in row:
                    f.write(f'<td>{cell}</td>\n')
                f.write('</tr>\n')

            f.write('</tbody>\n</table>\n')
            f.write('</body>\n</html>\n')

    def _escape_latex(self, text):
        """Escape special LaTeX characters."""
        special_chars = {
            '&': '\\&',
            '%': '\\%',
            '$': '\\$',
            '#': '\\#',
            '_': '\\_',
            '{': '\\{',
            '}': '\\}',
            '~': '\\textasciitilde{}',
            '^': '\\textasciicircum{}'
        }

        for char, escaped in special_chars.items():
            text = text.replace(char, escaped)

        return text
