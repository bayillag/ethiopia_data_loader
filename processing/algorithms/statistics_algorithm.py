# -*- coding: utf-8 -*-
"""
Statistics Algorithm for Ethiopia Data Loader.

Calculates area, perimeter, and other statistics for polygon features.
"""

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterField,
    QgsProcessingParameterFileDestination,
    QgsProcessingOutputString,
    QgsDistanceArea,
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsProcessing
)
from qgis.PyQt.QtCore import QCoreApplication
import csv
import os


class StatisticsAlgorithm(QgsProcessingAlgorithm):
    """Algorithm to calculate statistics for Ethiopia data layers."""

    INPUT = 'INPUT'
    NAME_FIELD = 'NAME_FIELD'
    OUTPUT_FILE = 'OUTPUT_FILE'
    OUTPUT_SUMMARY = 'OUTPUT_SUMMARY'

    def name(self):
        """Return algorithm name."""
        return 'calculatestatistics'

    def displayName(self):
        """Return algorithm display name."""
        return self.tr('Calculate Statistics')

    def group(self):
        """Return algorithm group."""
        return self.tr('Sudan Analysis')

    def groupId(self):
        """Return algorithm group ID."""
        return 'sudananalysis'

    def shortHelpString(self):
        """Return short help string."""
        return self.tr(
            'Calculates area and perimeter statistics for polygon features.\n\n'
            'Statistics are calculated using ellipsoidal measurements for accuracy.\n\n'
            'Output includes:\n'
            '- Area in square kilometers\n'
            '- Perimeter in kilometers\n'
            '- Centroid coordinates\n'
            '- Summary statistics (min, max, mean, total)\n\n'
            'Results are exported to a CSV file.'
        )

    def tr(self, string):
        """Translate string."""
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        """Create new algorithm instance."""
        return StatisticsAlgorithm()

    def initAlgorithm(self, config=None):
        """Initialize algorithm parameters."""
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT,
                self.tr('Input Polygon Layer'),
                [QgsProcessing.TypeVectorPolygon]
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.NAME_FIELD,
                self.tr('Name Field'),
                parentLayerParameterName=self.INPUT,
                type=QgsProcessingParameterField.String,
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_FILE,
                self.tr('Output Statistics CSV'),
                fileFilter='CSV Files (*.csv)'
            )
        )

        self.addOutput(
            QgsProcessingOutputString(
                self.OUTPUT_SUMMARY,
                self.tr('Summary Statistics')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """Execute the algorithm."""
        input_layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        name_field = self.parameterAsString(parameters, self.NAME_FIELD, context)
        output_file = self.parameterAsFileOutput(parameters, self.OUTPUT_FILE, context)

        # Initialize distance calculator
        distance_area = QgsDistanceArea()
        distance_area.setSourceCrs(
            input_layer.crs(),
            QgsProject.instance().transformContext()
        )
        distance_area.setEllipsoid('WGS84')

        # Collect statistics
        stats_data = []
        total = input_layer.featureCount()
        processed = 0

        for feature in input_layer.getFeatures():
            if feedback.isCanceled():
                break

            geom = feature.geometry()
            if geom and not geom.isEmpty():
                # Calculate area in km²
                area_m2 = distance_area.measureArea(geom)
                area_km2 = area_m2 / 1_000_000

                # Calculate perimeter in km
                perimeter_m = distance_area.measurePerimeter(geom)
                perimeter_km = perimeter_m / 1000

                # Get centroid
                centroid = geom.centroid().asPoint()

                # Get name
                if name_field and name_field in [f.name() for f in input_layer.fields()]:
                    name = feature[name_field] or f'Feature {feature.id()}'
                else:
                    name = f'Feature {feature.id()}'

                stats_data.append({
                    'name': name,
                    'area_km2': area_km2,
                    'perimeter_km': perimeter_km,
                    'centroid_lat': centroid.y(),
                    'centroid_lon': centroid.x(),
                    'feature_id': feature.id()
                })

            processed += 1
            feedback.setProgress(int(processed / total * 80))

        # Calculate summary statistics
        if stats_data:
            areas = [s['area_km2'] for s in stats_data]
            perimeters = [s['perimeter_km'] for s in stats_data]

            summary = {
                'feature_count': len(stats_data),
                'total_area_km2': sum(areas),
                'mean_area_km2': sum(areas) / len(areas),
                'min_area_km2': min(areas),
                'max_area_km2': max(areas),
                'total_perimeter_km': sum(perimeters),
                'mean_perimeter_km': sum(perimeters) / len(perimeters)
            }
        else:
            summary = {
                'feature_count': 0,
                'total_area_km2': 0,
                'mean_area_km2': 0,
                'min_area_km2': 0,
                'max_area_km2': 0,
                'total_perimeter_km': 0,
                'mean_perimeter_km': 0
            }

        feedback.pushInfo(f"Calculated statistics for {summary['feature_count']} features")
        feedback.pushInfo(f"Total area: {summary['total_area_km2']:,.2f} km²")

        # Write CSV
        feedback.pushInfo(f'Writing results to: {output_file}')

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'Name', 'Area (km²)', 'Perimeter (km)',
                'Centroid Lat', 'Centroid Lon', 'Feature ID'
            ])

            # Data rows
            for row in sorted(stats_data, key=lambda x: x['area_km2'], reverse=True):
                writer.writerow([
                    row['name'],
                    f"{row['area_km2']:.2f}",
                    f"{row['perimeter_km']:.2f}",
                    f"{row['centroid_lat']:.6f}",
                    f"{row['centroid_lon']:.6f}",
                    row['feature_id']
                ])

            # Summary section
            writer.writerow([])
            writer.writerow(['--- Summary Statistics ---'])
            writer.writerow(['Feature Count', summary['feature_count']])
            writer.writerow(['Total Area (km²)', f"{summary['total_area_km2']:,.2f}"])
            writer.writerow(['Mean Area (km²)', f"{summary['mean_area_km2']:,.2f}"])
            writer.writerow(['Min Area (km²)', f"{summary['min_area_km2']:,.2f}"])
            writer.writerow(['Max Area (km²)', f"{summary['max_area_km2']:,.2f}"])
            writer.writerow(['Total Perimeter (km)', f"{summary['total_perimeter_km']:,.2f}"])
            writer.writerow(['Mean Perimeter (km)', f"{summary['mean_perimeter_km']:,.2f}"])

        # Create summary string
        summary_text = (
            f"Features: {summary['feature_count']}\n"
            f"Total Area: {summary['total_area_km2']:,.2f} km²\n"
            f"Mean Area: {summary['mean_area_km2']:,.2f} km²\n"
            f"Min Area: {summary['min_area_km2']:,.2f} km²\n"
            f"Max Area: {summary['max_area_km2']:,.2f} km²"
        )

        return {
            self.OUTPUT_FILE: output_file,
            self.OUTPUT_SUMMARY: summary_text
        }
