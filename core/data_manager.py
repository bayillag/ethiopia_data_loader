# -*- coding: utf-8 -*-
"""
Data Manager for Sudan Data Loader.

Handles data loading, style application, and layer management.
"""

import os
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsDistanceArea
)


class DataManager:
    """Manages data loading and layer operations."""

    # Sudan administrative data - 18 States with coordinates
    SUDAN_STATES = [
        {'name_en': 'Khartoum', 'name_ar': 'الخرطوم', 'pcode': 'SD01', 'lat': 15.5007, 'lon': 32.5599},
        {'name_en': 'Northern', 'name_ar': 'الشمالية', 'pcode': 'SD02', 'lat': 19.5, 'lon': 30.0},
        {'name_en': 'River Nile', 'name_ar': 'نهر النيل', 'pcode': 'SD03', 'lat': 18.5, 'lon': 33.5},
        {'name_en': 'Red Sea', 'name_ar': 'البحر الأحمر', 'pcode': 'SD04', 'lat': 19.5, 'lon': 36.0},
        {'name_en': 'Kassala', 'name_ar': 'كسلا', 'pcode': 'SD05', 'lat': 15.5, 'lon': 36.0},
        {'name_en': 'Gedaref', 'name_ar': 'القضارف', 'pcode': 'SD06', 'lat': 14.0, 'lon': 35.5},
        {'name_en': 'Sennar', 'name_ar': 'سنار', 'pcode': 'SD07', 'lat': 13.5, 'lon': 33.5},
        {'name_en': 'Blue Nile', 'name_ar': 'النيل الأزرق', 'pcode': 'SD08', 'lat': 11.5, 'lon': 34.5},
        {'name_en': 'White Nile', 'name_ar': 'النيل الأبيض', 'pcode': 'SD09', 'lat': 13.0, 'lon': 32.0},
        {'name_en': 'Gezira', 'name_ar': 'الجزيرة', 'pcode': 'SD10', 'lat': 14.5, 'lon': 33.0},
        {'name_en': 'North Kordofan', 'name_ar': 'شمال كردفان', 'pcode': 'SD11', 'lat': 14.5, 'lon': 29.5},
        {'name_en': 'South Kordofan', 'name_ar': 'جنوب كردفان', 'pcode': 'SD12', 'lat': 11.0, 'lon': 29.5},
        {'name_en': 'West Kordofan', 'name_ar': 'غرب كردفان', 'pcode': 'SD13', 'lat': 12.0, 'lon': 27.5},
        {'name_en': 'North Darfur', 'name_ar': 'شمال دارفور', 'pcode': 'SD14', 'lat': 16.0, 'lon': 25.0},
        {'name_en': 'West Darfur', 'name_ar': 'غرب دارفور', 'pcode': 'SD15', 'lat': 13.0, 'lon': 23.0},
        {'name_en': 'Central Darfur', 'name_ar': 'وسط دارفور', 'pcode': 'SD16', 'lat': 14.0, 'lon': 24.0},
        {'name_en': 'South Darfur', 'name_ar': 'جنوب دارفور', 'pcode': 'SD17', 'lat': 11.5, 'lon': 25.0},
        {'name_en': 'East Darfur', 'name_ar': 'شرق دارفور', 'pcode': 'SD18', 'lat': 12.5, 'lon': 26.5},
    ]

    # Layer configuration
    LAYERS_CONFIG = [
        {'gpkg': 'admin0.gpkg', 'style': 'admin0.qml', 'name': 'Sudan Admin 0 - Country', 'id': 'admin0'},
        {'gpkg': 'admin1.gpkg', 'style': 'admin1.qml', 'name': 'Sudan Admin 1 - States', 'id': 'admin1'},
        {'gpkg': 'admin2.gpkg', 'style': 'admin2.qml', 'name': 'Sudan Admin 2 - Localities', 'id': 'admin2'},
        {'gpkg': 'admin_lines.gpkg', 'style': None, 'name': 'Sudan Admin Lines', 'id': 'admin_lines'},
        {'gpkg': 'admin_points.gpkg', 'style': None, 'name': 'Sudan Admin Points', 'id': 'admin_points'},
    ]

    # Basemap configurations
    BASEMAPS = {
        'osm_standard': {
            'name': 'OpenStreetMap',
            'url': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            'zmin': 0, 'zmax': 19,
            'attribution': '© OpenStreetMap contributors'
        },
        'osm_humanitarian': {
            'name': 'Humanitarian OSM',
            'url': 'https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
            'zmin': 0, 'zmax': 19,
            'attribution': '© OpenStreetMap contributors, Humanitarian OpenStreetMap Team'
        },
        'esri_satellite': {
            'name': 'ESRI Satellite',
            'url': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            'zmin': 0, 'zmax': 18,
            'attribution': '© Esri, Maxar, Earthstar Geographics'
        },
        'esri_topo': {
            'name': 'ESRI Topographic',
            'url': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
            'zmin': 0, 'zmax': 18,
            'attribution': '© Esri'
        },
        'carto_light': {
            'name': 'CartoDB Positron (Light)',
            'url': 'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
            'zmin': 0, 'zmax': 19,
            'attribution': '© OpenStreetMap contributors, © CARTO'
        },
        'carto_dark': {
            'name': 'CartoDB Dark Matter',
            'url': 'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
            'zmin': 0, 'zmax': 19,
            'attribution': '© OpenStreetMap contributors, © CARTO'
        }
    }

    def __init__(self, data_dir, styles_dir):
        """
        Initialize the data manager.

        :param data_dir: Path to data directory
        :param styles_dir: Path to styles directory
        """
        self.data_dir = data_dir
        self.styles_dir = styles_dir

    def set_directories(self, data_dir, styles_dir):
        """Update data directories."""
        self.data_dir = data_dir
        self.styles_dir = styles_dir

    def get_layer_config(self, layer_id):
        """Get configuration for a specific layer."""
        for config in self.LAYERS_CONFIG:
            if config['id'] == layer_id:
                return config
        return None

    def load_layer(self, layer_id, apply_style=True):
        """
        Load a layer by its ID.

        :param layer_id: Layer identifier
        :param apply_style: Whether to apply default style
        :returns: QgsVectorLayer or None
        """
        config = self.get_layer_config(layer_id)
        if not config:
            return None

        gpkg_path = os.path.join(self.data_dir, config['gpkg'])
        if not os.path.exists(gpkg_path):
            return None

        layer = QgsVectorLayer(gpkg_path, config['name'], 'ogr')
        if not layer.isValid():
            return None

        if apply_style and config['style']:
            style_path = os.path.join(self.styles_dir, config['style'])
            if os.path.exists(style_path):
                layer.loadNamedStyle(style_path)

        return layer

    def load_layers(self, layer_ids, apply_styles=True):
        """
        Load multiple layers.

        :param layer_ids: List of layer IDs to load
        :param apply_styles: Whether to apply styles
        :returns: List of loaded layers
        """
        layers = []
        for layer_id in layer_ids:
            layer = self.load_layer(layer_id, apply_styles)
            if layer:
                layers.append(layer)
        return layers

    def get_sudan_layers(self):
        """Get all Sudan-related layers from the current project."""
        layers = []
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and 'Sudan' in layer.name():
                layers.append(layer)
        return layers

    def get_admin1_layer(self):
        """Get the Admin 1 (States) layer from the project."""
        for layer in QgsProject.instance().mapLayersByName('Sudan Admin 1 - States'):
            return layer
        return None

    def get_admin2_layer(self):
        """Get the Admin 2 (Localities) layer from the project."""
        for layer in QgsProject.instance().mapLayersByName('Sudan Admin 2 - Localities'):
            return layer
        return None

    def add_basemap(self, basemap_id):
        """
        Add a basemap layer to the project.

        :param basemap_id: Basemap identifier
        :returns: QgsRasterLayer or None
        """
        if basemap_id not in self.BASEMAPS:
            return None

        config = self.BASEMAPS[basemap_id]
        uri = f"type=xyz&url={config['url']}&zmax={config['zmax']}&zmin={config['zmin']}"
        layer = QgsRasterLayer(uri, config['name'], 'wms')

        if layer.isValid():
            # Add at the bottom of the layer tree
            QgsProject.instance().addMapLayer(layer, False)
            root = QgsProject.instance().layerTreeRoot()
            root.insertLayer(-1, layer)
            return layer

        return None

    def remove_basemaps(self):
        """Remove all basemap layers from the project."""
        for basemap_id, config in self.BASEMAPS.items():
            layers = QgsProject.instance().mapLayersByName(config['name'])
            for layer in layers:
                QgsProject.instance().removeMapLayer(layer)

    def apply_style_preset(self, preset_name, styles_presets_dir):
        """
        Apply a style preset to all Sudan layers.

        :param preset_name: Name of the preset (default, satellite, grayscale, humanitarian)
        :param styles_presets_dir: Directory containing preset styles
        """
        preset_dir = os.path.join(styles_presets_dir, preset_name)
        if not os.path.isdir(preset_dir):
            return False

        for config in self.LAYERS_CONFIG:
            if config['style']:
                layers = QgsProject.instance().mapLayersByName(config['name'])
                for layer in layers:
                    style_path = os.path.join(preset_dir, config['style'])
                    if os.path.exists(style_path):
                        layer.loadNamedStyle(style_path)
                        layer.triggerRepaint()

        return True

    def get_layer_statistics(self, layer):
        """
        Get statistics for a layer.

        :param layer: QgsVectorLayer
        :returns: Dictionary with statistics
        """
        if not layer or not layer.isValid():
            return {}

        stats = {
            'name': layer.name(),
            'feature_count': layer.featureCount(),
            'geometry_type': layer.geometryType(),
            'crs': layer.crs().authid(),
            'extent': {
                'xmin': layer.extent().xMinimum(),
                'xmax': layer.extent().xMaximum(),
                'ymin': layer.extent().yMinimum(),
                'ymax': layer.extent().yMaximum(),
            },
            'fields': [f.name() for f in layer.fields()],
            'selected_count': layer.selectedFeatureCount(),
        }

        # Calculate total area for polygon layers using ellipsoidal calculation
        if layer.geometryType() == 2:  # Polygon
            total_area = 0
            # Set up distance area calculator for accurate measurements
            distance_area = QgsDistanceArea()
            distance_area.setSourceCrs(layer.crs(), QgsProject.instance().transformContext())
            distance_area.setEllipsoid('WGS84')

            for feature in layer.getFeatures():
                geom = feature.geometry()
                if geom and not geom.isNull():
                    # Use ellipsoidal area calculation
                    area_calc = distance_area.measureArea(geom)
                    total_area += area_calc
            stats['total_area_sq_km'] = total_area / 1_000_000  # Convert to sq km

        return stats
