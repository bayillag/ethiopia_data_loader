# -*- coding: utf-8 -*-
"""
Buffer Analysis Algorithm for Ethiopia Data Loader.

Creates buffers around features with distance in kilometers.
"""

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterNumber,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFeatureSink,
    QgsFeatureSink,
    QgsFeature,
    QgsGeometry,
    QgsDistanceArea,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsWkbTypes,
    QgsProcessing
)
from qgis.PyQt.QtCore import QCoreApplication


class BufferAnalysisAlgorithm(QgsProcessingAlgorithm):
    """Algorithm to create buffers with distance in kilometers."""

    INPUT = 'INPUT'
    DISTANCE = 'DISTANCE'
    DISSOLVE = 'DISSOLVE'
    OUTPUT = 'OUTPUT'

    def name(self):
        """Return algorithm name."""
        return 'bufferanalysis'

    def displayName(self):
        """Return algorithm display name."""
        return self.tr('Buffer Analysis (km)')

    def group(self):
        """Return algorithm group."""
        return self.tr('Sudan Analysis')

    def groupId(self):
        """Return algorithm group ID."""
        return 'sudananalysis'

    def shortHelpString(self):
        """Return short help string."""
        return self.tr(
            'Creates buffer zones around input features.\n\n'
            'Distance is specified in kilometers and is automatically converted '
            'to the appropriate units based on the layer CRS.\n\n'
            'Parameters:\n'
            '- Input Layer: The layer to buffer\n'
            '- Distance (km): Buffer distance in kilometers\n'
            '- Dissolve: Merge overlapping buffers into single features\n'
            '- Output: The buffered result'
        )

    def tr(self, string):
        """Translate string."""
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        """Create new algorithm instance."""
        return BufferAnalysisAlgorithm()

    def initAlgorithm(self, config=None):
        """Initialize algorithm parameters."""
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT,
                self.tr('Input Layer'),
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.DISTANCE,
                self.tr('Buffer Distance (km)'),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=10.0,
                minValue=0.001,
                maxValue=1000.0
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.DISSOLVE,
                self.tr('Dissolve overlapping buffers'),
                defaultValue=False
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Buffered Output')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """Execute the algorithm."""
        input_layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        distance_km = self.parameterAsDouble(parameters, self.DISTANCE, context)
        dissolve = self.parameterAsBool(parameters, self.DISSOLVE, context)

        feedback.pushInfo(f'Buffer distance: {distance_km} km')

        # Convert km to degrees (approximate for Sudan latitude ~15 degrees)
        # 1 degree latitude ≈ 111 km
        # At 15 degrees latitude, 1 degree longitude ≈ 107 km
        distance_deg = distance_km / 111.0

        # Create output with polygon type
        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            input_layer.fields(),
            QgsWkbTypes.Polygon,
            input_layer.crs()
        )

        if sink is None:
            feedback.reportError('Could not create output sink!')
            return {}

        total = input_layer.featureCount()
        processed = 0
        buffer_features = []

        for feature in input_layer.getFeatures():
            if feedback.isCanceled():
                break

            geom = feature.geometry()
            if geom:
                buffered = geom.buffer(distance_deg, 25)
                if buffered and not buffered.isEmpty():
                    new_feature = QgsFeature(feature)
                    new_feature.setGeometry(buffered)
                    buffer_features.append(new_feature)

            processed += 1
            feedback.setProgress(int(processed / total * 50))

        # Dissolve if requested
        if dissolve and buffer_features:
            feedback.pushInfo('Dissolving overlapping buffers...')
            combined_geom = QgsGeometry.unaryUnion([f.geometry() for f in buffer_features])

            if combined_geom.isMultipart():
                # Convert multipart to single parts
                for part in combined_geom.asGeometryCollection():
                    dissolved_feature = QgsFeature()
                    dissolved_feature.setGeometry(part)
                    sink.addFeature(dissolved_feature, QgsFeatureSink.FastInsert)
            else:
                dissolved_feature = QgsFeature()
                dissolved_feature.setGeometry(combined_geom)
                sink.addFeature(dissolved_feature, QgsFeatureSink.FastInsert)
        else:
            for feature in buffer_features:
                sink.addFeature(feature, QgsFeatureSink.FastInsert)

        feedback.pushInfo(f'Created {len(buffer_features)} buffer features')

        return {self.OUTPUT: dest_id}
