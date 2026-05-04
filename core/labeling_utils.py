# -*- coding: utf-8 -*-
"""
Labeling Utilities for Sudan Data Loader.

Provides quick labeling tools for Sudan administrative layers.
"""

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling, QgsTextFormat, QgsTextBufferSettings,
    QgsPropertyCollection
)
from qgis.PyQt.QtGui import QFont, QColor


class LabelingUtils:
    """Utilities for applying labels to Sudan layers."""

    # Label presets
    LABEL_PRESETS = {
        'state_english': {
            'field': 'ADM1_EN',
            'fallback_fields': ['admin1Name_en', 'name', 'NAME'],
            'size': 12,
            'color': '#2c3e50',
            'buffer': True
        },
        'state_arabic': {
            'field': 'ADM1_AR',
            'fallback_fields': ['admin1Name_ar', 'name_ar'],
            'size': 14,
            'color': '#2c3e50',
            'buffer': True
        },
        'state_pcode': {
            'field': 'ADM1_PCODE',
            'fallback_fields': ['admin1Pcode', 'pcode'],
            'size': 10,
            'color': '#7f8c8d',
            'buffer': True
        },
        'locality_english': {
            'field': 'ADM2_EN',
            'fallback_fields': ['admin2Name_en', 'name', 'NAME'],
            'size': 9,
            'color': '#34495e',
            'buffer': True
        },
        'locality_arabic': {
            'field': 'ADM2_AR',
            'fallback_fields': ['admin2Name_ar', 'name_ar'],
            'size': 10,
            'color': '#34495e',
            'buffer': True
        },
        'locality_pcode': {
            'field': 'ADM2_PCODE',
            'fallback_fields': ['admin2Pcode', 'pcode'],
            'size': 8,
            'color': '#95a5a6',
            'buffer': True
        }
    }

    @staticmethod
    def get_label_field(layer, preset_name):
        """
        Find the appropriate label field for a layer.

        :param layer: QgsVectorLayer
        :param preset_name: Name of the label preset
        :returns: Field name or None
        """
        preset = LabelingUtils.LABEL_PRESETS.get(preset_name)
        if not preset:
            return None

        field_names = [f.name() for f in layer.fields()]

        # Try primary field
        if preset['field'] in field_names:
            return preset['field']

        # Try fallback fields
        for field in preset.get('fallback_fields', []):
            if field in field_names:
                return field

        return None

    @staticmethod
    def apply_labels(layer, preset_name, enabled=True):
        """
        Apply labels to a layer using a preset.

        :param layer: QgsVectorLayer
        :param preset_name: Name of the label preset
        :param enabled: Whether labels should be enabled
        :returns: True if successful
        """
        if not layer or not isinstance(layer, QgsVectorLayer):
            return False

        preset = LabelingUtils.LABEL_PRESETS.get(preset_name)
        if not preset:
            return False

        # Find label field
        label_field = LabelingUtils.get_label_field(layer, preset_name)
        if not label_field:
            return False

        # Create label settings
        settings = QgsPalLayerSettings()
        settings.fieldName = label_field
        settings.enabled = enabled

        # Text format
        text_format = QgsTextFormat()
        font = QFont('Arial', preset['size'])
        text_format.setFont(font)
        text_format.setSize(preset['size'])
        text_format.setColor(QColor(preset['color']))

        # Buffer settings
        if preset.get('buffer', False):
            buffer_settings = QgsTextBufferSettings()
            buffer_settings.setEnabled(True)
            buffer_settings.setSize(1.5)
            buffer_settings.setColor(QColor(255, 255, 255))
            text_format.setBuffer(buffer_settings)

        settings.setFormat(text_format)

        # Apply labeling
        labeling = QgsVectorLayerSimpleLabeling(settings)
        layer.setLabeling(labeling)
        layer.setLabelsEnabled(enabled)
        layer.triggerRepaint()

        return True

    @staticmethod
    def apply_state_labels(language='english'):
        """
        Apply labels to the states layer.

        :param language: 'english', 'arabic', or 'both'
        """
        # Find states layer
        layer = None
        for l in QgsProject.instance().mapLayers().values():
            if isinstance(l, QgsVectorLayer):
                if 'Admin 1' in l.name() or 'States' in l.name():
                    layer = l
                    break

        if not layer:
            return False

        if language == 'english':
            return LabelingUtils.apply_labels(layer, 'state_english')
        elif language == 'arabic':
            return LabelingUtils.apply_labels(layer, 'state_arabic')
        elif language == 'both':
            # For both, we'll use a combined expression
            return LabelingUtils._apply_combined_labels(layer, 'state')
        elif language == 'pcode':
            return LabelingUtils.apply_labels(layer, 'state_pcode')

        return False

    @staticmethod
    def apply_locality_labels(language='english'):
        """
        Apply labels to the localities layer.

        :param language: 'english', 'arabic', or 'both'
        """
        # Find localities layer
        layer = None
        for l in QgsProject.instance().mapLayers().values():
            if isinstance(l, QgsVectorLayer):
                if 'Admin 2' in l.name() or 'Localities' in l.name():
                    layer = l
                    break

        if not layer:
            return False

        if language == 'english':
            return LabelingUtils.apply_labels(layer, 'locality_english')
        elif language == 'arabic':
            return LabelingUtils.apply_labels(layer, 'locality_arabic')
        elif language == 'both':
            return LabelingUtils._apply_combined_labels(layer, 'locality')
        elif language == 'pcode':
            return LabelingUtils.apply_labels(layer, 'locality_pcode')

        return False

    @staticmethod
    def _apply_combined_labels(layer, level):
        """
        Apply combined English/Arabic labels.

        :param layer: QgsVectorLayer
        :param level: 'state' or 'locality'
        """
        if level == 'state':
            en_field = LabelingUtils.get_label_field(layer, 'state_english')
            ar_field = LabelingUtils.get_label_field(layer, 'state_arabic')
            size = 11
        else:
            en_field = LabelingUtils.get_label_field(layer, 'locality_english')
            ar_field = LabelingUtils.get_label_field(layer, 'locality_arabic')
            size = 8

        if not en_field or not ar_field:
            return False

        # Create expression for combined label
        expression = f'"{en_field}" || \'\\n\' || "{ar_field}"'

        settings = QgsPalLayerSettings()
        settings.fieldName = expression
        settings.isExpression = True
        settings.enabled = True

        # Text format
        text_format = QgsTextFormat()
        font = QFont('Arial', size)
        text_format.setFont(font)
        text_format.setSize(size)
        text_format.setColor(QColor('#2c3e50'))

        # Buffer
        buffer_settings = QgsTextBufferSettings()
        buffer_settings.setEnabled(True)
        buffer_settings.setSize(1.5)
        buffer_settings.setColor(QColor(255, 255, 255))
        text_format.setBuffer(buffer_settings)

        settings.setFormat(text_format)

        labeling = QgsVectorLayerSimpleLabeling(settings)
        layer.setLabeling(labeling)
        layer.setLabelsEnabled(True)
        layer.triggerRepaint()

        return True

    @staticmethod
    def remove_labels(layer):
        """
        Remove labels from a layer.

        :param layer: QgsVectorLayer
        """
        if layer and isinstance(layer, QgsVectorLayer):
            layer.setLabelsEnabled(False)
            layer.triggerRepaint()

    @staticmethod
    def remove_all_labels():
        """Remove labels from all Sudan layers."""
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                if 'sudan' in layer.name().lower():
                    LabelingUtils.remove_labels(layer)
