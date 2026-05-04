# -*- coding: utf-8 -*-
"""
Style Manager for Ethiopia Data Loader.

Manages style presets and basemap integration.
"""

import os
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer,
    QgsSymbol, QgsSingleSymbolRenderer, QgsFillSymbol,
    QgsLineSymbol, QgsSimpleFillSymbolLayer, QgsSimpleLineSymbolLayer
)
from qgis.PyQt.QtGui import QColor


class StyleManager:
    """Manages style presets for Sudan layers."""

    # Style presets definitions
    PRESETS = {
        'default': {
            'admin0': {
                'fill_color': '#f0e6d2',
                'outline_color': '#8b7355',
                'outline_width': 1.0
            },
            'admin1': {
                'fill_color': '#e8dcc8',
                'outline_color': '#6b5344',
                'outline_width': 0.6
            },
            'admin2': {
                'fill_color': '#f5f0e6',
                'outline_color': '#a0917f',
                'outline_width': 0.3
            }
        },
        'satellite': {
            'admin0': {
                'fill_color': 'transparent',
                'outline_color': '#ffff00',
                'outline_width': 2.0
            },
            'admin1': {
                'fill_color': 'transparent',
                'outline_color': '#00ffff',
                'outline_width': 1.5
            },
            'admin2': {
                'fill_color': 'transparent',
                'outline_color': '#ff00ff',
                'outline_width': 0.8
            }
        },
        'grayscale': {
            'admin0': {
                'fill_color': '#d0d0d0',
                'outline_color': '#404040',
                'outline_width': 1.0
            },
            'admin1': {
                'fill_color': '#e0e0e0',
                'outline_color': '#606060',
                'outline_width': 0.6
            },
            'admin2': {
                'fill_color': '#f0f0f0',
                'outline_color': '#808080',
                'outline_width': 0.3
            }
        },
        'humanitarian': {
            'admin0': {
                'fill_color': '#fff5eb',
                'outline_color': '#d95f02',
                'outline_width': 1.5
            },
            'admin1': {
                'fill_color': '#fee6ce',
                'outline_color': '#e6550d',
                'outline_width': 0.8
            },
            'admin2': {
                'fill_color': '#fdd0a2',
                'outline_color': '#fd8d3c',
                'outline_width': 0.4
            }
        }
    }

    # Basemap definitions
    BASEMAPS = {
        'osm_standard': {
            'name': 'OpenStreetMap',
            'url': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            'zmin': 0, 'zmax': 19
        },
        'osm_humanitarian': {
            'name': 'Humanitarian OSM',
            'url': 'https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
            'zmin': 0, 'zmax': 19
        },
        'esri_satellite': {
            'name': 'ESRI World Imagery',
            'url': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            'zmin': 0, 'zmax': 18
        },
        'esri_topo': {
            'name': 'ESRI Topographic',
            'url': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
            'zmin': 0, 'zmax': 18
        },
        'carto_light': {
            'name': 'CartoDB Positron',
            'url': 'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
            'zmin': 0, 'zmax': 19
        },
        'carto_dark': {
            'name': 'CartoDB Dark Matter',
            'url': 'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
            'zmin': 0, 'zmax': 19
        },
        'stamen_terrain': {
            'name': 'Stadia Stamen Terrain',
            'url': 'https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}.png',
            'zmin': 0, 'zmax': 18
        }
    }

    def __init__(self, plugin_dir=None):
        """
        Initialize the style manager.

        :param plugin_dir: Plugin directory path
        """
        self.plugin_dir = plugin_dir
        self.presets_dir = os.path.join(plugin_dir, 'styles', 'presets') if plugin_dir else None

    def get_available_presets(self):
        """Get list of available style presets."""
        return list(self.PRESETS.keys())

    def apply_preset(self, preset_name):
        """
        Apply a style preset to all Sudan layers.

        :param preset_name: Name of the preset
        :returns: True if successful
        """
        if preset_name not in self.PRESETS:
            return False

        preset = self.PRESETS[preset_name]

        for layer in QgsProject.instance().mapLayers().values():
            if not isinstance(layer, QgsVectorLayer):
                continue

            name_lower = layer.name().lower()

            # Determine layer type
            layer_type = None
            if 'admin 0' in name_lower or 'country' in name_lower:
                layer_type = 'admin0'
            elif 'admin 1' in name_lower or 'state' in name_lower:
                layer_type = 'admin1'
            elif 'admin 2' in name_lower or 'local' in name_lower:
                layer_type = 'admin2'

            if layer_type and layer_type in preset:
                self._apply_style(layer, preset[layer_type])

        return True

    def _apply_style(self, layer, style_config):
        """
        Apply style configuration to a layer.

        :param layer: QgsVectorLayer
        :param style_config: Style configuration dict
        """
        if layer.geometryType() != 2:  # Only for polygons
            return

        # Create symbol
        symbol = QgsFillSymbol.createSimple({})

        # Fill color
        fill_color = style_config.get('fill_color', '#ffffff')
        if fill_color == 'transparent':
            symbol.setColor(QColor(0, 0, 0, 0))
        else:
            symbol.setColor(QColor(fill_color))

        # Outline
        symbol_layer = symbol.symbolLayer(0)
        if isinstance(symbol_layer, QgsSimpleFillSymbolLayer):
            symbol_layer.setStrokeColor(QColor(style_config.get('outline_color', '#000000')))
            symbol_layer.setStrokeWidth(style_config.get('outline_width', 0.5))

        # Apply renderer
        layer.setRenderer(QgsSingleSymbolRenderer(symbol))
        layer.triggerRepaint()

    def add_basemap(self, basemap_id):
        """
        Add a basemap layer.

        :param basemap_id: Basemap identifier
        :returns: QgsRasterLayer or None
        """
        if basemap_id not in self.BASEMAPS:
            return None

        config = self.BASEMAPS[basemap_id]

        # Build URI
        uri = f"type=xyz&url={config['url']}&zmax={config['zmax']}&zmin={config['zmin']}"

        # Create layer
        layer = QgsRasterLayer(uri, config['name'], 'wms')

        if layer.isValid():
            # Add at the bottom of the layer tree
            QgsProject.instance().addMapLayer(layer, False)
            root = QgsProject.instance().layerTreeRoot()
            root.insertLayer(-1, layer)
            return layer

        return None

    def remove_basemap(self, basemap_name):
        """
        Remove a basemap layer by name.

        :param basemap_name: Name of the basemap layer
        """
        layers = QgsProject.instance().mapLayersByName(basemap_name)
        for layer in layers:
            QgsProject.instance().removeMapLayer(layer)

    def remove_all_basemaps(self):
        """Remove all basemap layers."""
        for basemap_id, config in self.BASEMAPS.items():
            self.remove_basemap(config['name'])

    def get_available_basemaps(self):
        """Get list of available basemaps."""
        return [(bid, config['name']) for bid, config in self.BASEMAPS.items()]

    def save_layer_style(self, layer, preset_name):
        """
        Save a layer's current style to a preset.

        :param layer: QgsVectorLayer
        :param preset_name: Preset name to save to
        """
        if not self.presets_dir:
            return False

        preset_dir = os.path.join(self.presets_dir, preset_name)
        os.makedirs(preset_dir, exist_ok=True)

        # Determine filename based on layer
        name_lower = layer.name().lower()
        if 'admin 0' in name_lower:
            filename = 'admin0.qml'
        elif 'admin 1' in name_lower:
            filename = 'admin1.qml'
        elif 'admin 2' in name_lower:
            filename = 'admin2.qml'
        else:
            filename = f'{layer.name()}.qml'

        style_path = os.path.join(preset_dir, filename)
        layer.saveNamedStyle(style_path)
        return True
