# -*- coding: utf-8 -*-
"""
Clip by State Algorithm for Ethiopia Data Loader.

Clips input layer by selected Ethiopia state boundary.
"""

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingOutputVectorLayer,
    QgsFeatureSink,
    QgsFeature,
    QgsGeometry,
    QgsProject,
    QgsVectorLayer,
    QgsWkbTypes,
    QgsProcessing
)
from qgis.PyQt.QtCore import QCoreApplication


class ClipByStateAlgorithm(QgsProcessingAlgorithm):
    """Algorithm to clip a layer by Ethiopia state boundary."""

    INPUT = 'INPUT'
    STATE = 'STATE'
    OUTPUT = 'OUTPUT'

    # Sudan states list
    STATES = [
        'Blue Nile', 'Central Darfur', 'East Darfur', 'Gedaref',
        'Gezira', 'Kassala', 'Khartoum', 'North Darfur',
        'North Kordofan', 'Northern', 'Red Sea', 'River Nile',
        'Sennar', 'South Darfur', 'South Kordofan', 'West Darfur',
        'West Kordofan', 'White Nile'
    ]

    def name(self):
        """Return algorithm name."""
        return 'clipbystate'

    def displayName(self):
        """Return algorithm display name."""
        return self.tr('Clip by Sudan State')

    def group(self):
        """Return algorithm group."""
        return self.tr('Sudan Analysis')

    def groupId(self):
        """Return algorithm group ID."""
        return 'sudananalysis'

    def shortHelpString(self):
        """Return short help string."""
        return self.tr(
            'Clips an input layer by the boundary of a selected Sudan state.\n\n'
            'The algorithm finds the Admin 1 (States) layer in the current project '
            'and uses the selected state boundary to clip the input layer.\n\n'
            'Parameters:\n'
            '- Input Layer: The layer to clip\n'
            '- State: The Sudan state to use as clip boundary\n'
            '- Output: The clipped result'
        )

    def tr(self, string):
        """Translate string."""
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        """Create new algorithm instance."""
        return ClipByStateAlgorithm()

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
            QgsProcessingParameterEnum(
                self.STATE,
                self.tr('Sudan State'),
                options=self.STATES,
                defaultValue=6  # Khartoum
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Clipped Output')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """Execute the algorithm."""
        input_layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        state_index = self.parameterAsEnum(parameters, self.STATE, context)
        state_name = self.STATES[state_index]

        feedback.pushInfo(f'Clipping by state: {state_name}')

        # Find Admin 1 layer
        admin1_layer = None
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                name = layer.name().lower()
                if ('admin 1' in name or 'states' in name) and 'sudan' in name:
                    admin1_layer = layer
                    break

        if not admin1_layer:
            feedback.reportError('Admin 1 (States) layer not found in project!')
            return {}

        # Find state feature
        state_geom = None
        for feature in admin1_layer.getFeatures():
            for field_name in ['ADM1_EN', 'admin1Name_en', 'name', 'STATE_NAME']:
                if field_name in [f.name() for f in admin1_layer.fields()]:
                    if feature[field_name] and state_name.lower() in str(feature[field_name]).lower():
                        state_geom = feature.geometry()
                        break
            if state_geom:
                break

        if not state_geom:
            feedback.reportError(f'Could not find state: {state_name}')
            return {}

        feedback.pushInfo(f'Found state boundary with area: {state_geom.area():.2f}')

        # Create output
        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            input_layer.fields(),
            input_layer.wkbType(),
            input_layer.crs()
        )

        if sink is None:
            feedback.reportError('Could not create output sink!')
            return {}

        # Process features
        total = input_layer.featureCount()
        processed = 0
        clipped_count = 0

        for feature in input_layer.getFeatures():
            if feedback.isCanceled():
                break

            geom = feature.geometry()
            if geom and geom.intersects(state_geom):
                clipped_geom = geom.intersection(state_geom)
                if clipped_geom and not clipped_geom.isEmpty():
                    new_feature = QgsFeature(feature)
                    new_feature.setGeometry(clipped_geom)
                    sink.addFeature(new_feature, QgsFeatureSink.FastInsert)
                    clipped_count += 1

            processed += 1
            feedback.setProgress(int(processed / total * 100))

        feedback.pushInfo(f'Clipped {clipped_count} features')

        return {self.OUTPUT: dest_id}
