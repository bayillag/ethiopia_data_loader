# -*- coding: utf-8 -*-
"""
Join Attributes Algorithm for Ethiopia Data Loader.

Joins attributes from one layer to another based on spatial relationship or field match.
"""

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterField,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsFeatureSink,
    QgsFeature,
    QgsFields,
    QgsField,
    QgsProcessing
)
from qgis.PyQt.QtCore import QCoreApplication, QVariant


class JoinAttributesAlgorithm(QgsProcessingAlgorithm):
    """Algorithm to join attributes between layers."""

    INPUT = 'INPUT'
    JOIN_LAYER = 'JOIN_LAYER'
    JOIN_TYPE = 'JOIN_TYPE'
    INPUT_FIELD = 'INPUT_FIELD'
    JOIN_FIELD = 'JOIN_FIELD'
    OUTPUT = 'OUTPUT'

    JOIN_TYPES = [
        'Spatial Join (Within)',
        'Spatial Join (Intersects)',
        'Field Join'
    ]

    def name(self):
        """Return algorithm name."""
        return 'joinattributes'

    def displayName(self):
        """Return algorithm display name."""
        return self.tr('Join Attributes')

    def group(self):
        """Return algorithm group."""
        return self.tr('Sudan Analysis')

    def groupId(self):
        """Return algorithm group ID."""
        return 'sudananalysis'

    def shortHelpString(self):
        """Return short help string."""
        return self.tr(
            'Joins attributes from a join layer to an input layer.\n\n'
            'Join types:\n'
            '- Spatial Join (Within): Joins features that are within the join geometry\n'
            '- Spatial Join (Intersects): Joins features that intersect\n'
            '- Field Join: Joins based on matching field values\n\n'
            'Use this to attach state names to localities, or to join external '
            'statistics to administrative boundaries.'
        )

    def tr(self, string):
        """Translate string."""
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        """Create new algorithm instance."""
        return JoinAttributesAlgorithm()

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
            QgsProcessingParameterVectorLayer(
                self.JOIN_LAYER,
                self.tr('Join Layer'),
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.JOIN_TYPE,
                self.tr('Join Type'),
                options=self.JOIN_TYPES,
                defaultValue=1
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.INPUT_FIELD,
                self.tr('Input Join Field (for Field Join)'),
                parentLayerParameterName=self.INPUT,
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.JOIN_FIELD,
                self.tr('Join Layer Field (for Field Join)'),
                parentLayerParameterName=self.JOIN_LAYER,
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Joined Output')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """Execute the algorithm."""
        input_layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        join_layer = self.parameterAsVectorLayer(parameters, self.JOIN_LAYER, context)
        join_type_index = self.parameterAsEnum(parameters, self.JOIN_TYPE, context)
        input_field = self.parameterAsString(parameters, self.INPUT_FIELD, context)
        join_field = self.parameterAsString(parameters, self.JOIN_FIELD, context)

        join_type = self.JOIN_TYPES[join_type_index]
        feedback.pushInfo(f'Join type: {join_type}')

        # Build output fields (input fields + join fields with prefix)
        output_fields = QgsFields(input_layer.fields())
        join_prefix = 'join_'

        for field in join_layer.fields():
            new_field = QgsField(field)
            new_field.setName(join_prefix + field.name())
            output_fields.append(new_field)

        # Create output
        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            output_fields,
            input_layer.wkbType(),
            input_layer.crs()
        )

        if sink is None:
            feedback.reportError('Could not create output sink!')
            return {}

        # Build spatial index for join layer
        if join_type != 'Field Join':
            feedback.pushInfo('Building spatial index...')
            join_index = {}
            for join_feature in join_layer.getFeatures():
                join_index[join_feature.id()] = {
                    'geometry': join_feature.geometry(),
                    'attributes': join_feature.attributes()
                }

        # Process features
        total = input_layer.featureCount()
        processed = 0
        joined_count = 0

        for feature in input_layer.getFeatures():
            if feedback.isCanceled():
                break

            input_geom = feature.geometry()
            input_attrs = feature.attributes()

            # Find matching join feature
            join_attrs = [None] * len(join_layer.fields())
            matched = False

            if join_type == 'Field Join':
                # Field-based join
                if input_field and join_field:
                    input_value = feature[input_field]
                    for join_feature in join_layer.getFeatures():
                        if join_feature[join_field] == input_value:
                            join_attrs = join_feature.attributes()
                            matched = True
                            break
            else:
                # Spatial join
                for jid, jdata in join_index.items():
                    join_geom = jdata['geometry']

                    if join_type == 'Spatial Join (Within)':
                        if input_geom.within(join_geom):
                            join_attrs = jdata['attributes']
                            matched = True
                            break
                    else:  # Intersects
                        if input_geom.intersects(join_geom):
                            join_attrs = jdata['attributes']
                            matched = True
                            break

            if matched:
                joined_count += 1

            # Create output feature
            new_feature = QgsFeature()
            new_feature.setGeometry(input_geom)
            new_feature.setAttributes(input_attrs + join_attrs)
            sink.addFeature(new_feature, QgsFeatureSink.FastInsert)

            processed += 1
            feedback.setProgress(int(processed / total * 100))

        feedback.pushInfo(f'Joined {joined_count} of {total} features')

        return {self.OUTPUT: dest_id}
