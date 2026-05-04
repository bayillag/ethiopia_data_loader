# -*- coding: utf-8 -*-
"""
OSM Client for Ethiopia Data Loader.

Provides access to OpenStreetMap data via Overpass API for Ethiopia.
"""

import json
import os
import tempfile
from urllib.parse import quote

from qgis.PyQt.QtCore import QUrl, QObject, pyqtSignal, QByteArray
from qgis.core import QgsBlockingNetworkRequest, QgsMessageLog, Qgis
from qgis.PyQt.QtNetwork import QNetworkRequest


class OSMClient(QObject):
    """Client for accessing OpenStreetMap data via Overpass API."""

    # Overpass API endpoints (multiple for load balancing)
    OVERPASS_ENDPOINTS = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
    ]

    # Sudan bounding box (approximate)
    SUDAN_BBOX = {
        'south': 8.5,
        'west': 21.5,
        'north': 23.5,
        'east': 39.0
    }

    # Sudan admin1 regions with approximate bounding boxes
    SUDAN_STATES = {
        'Khartoum': {'south': 15.2, 'west': 31.5, 'north': 16.2, 'east': 34.0},
        'Northern': {'south': 18.0, 'west': 25.0, 'north': 22.5, 'east': 34.0},
        'River Nile': {'south': 16.5, 'west': 31.5, 'north': 20.0, 'east': 35.5},
        'Red Sea': {'south': 17.5, 'west': 35.0, 'north': 22.5, 'east': 39.0},
        'Kassala': {'south': 14.5, 'west': 34.5, 'north': 17.5, 'east': 37.0},
        'Gedaref': {'south': 12.5, 'west': 33.5, 'north': 15.5, 'east': 36.5},
        'Gezira': {'south': 13.5, 'west': 32.0, 'north': 15.5, 'east': 34.0},
        'Sennar': {'south': 12.5, 'west': 32.5, 'north': 14.5, 'east': 35.0},
        'Blue Nile': {'south': 9.5, 'west': 33.0, 'north': 12.5, 'east': 35.5},
        'White Nile': {'south': 12.0, 'west': 30.0, 'north': 15.0, 'east': 33.0},
        'North Kordofan': {'south': 12.5, 'west': 27.0, 'north': 16.5, 'east': 32.0},
        'South Kordofan': {'south': 9.5, 'west': 28.0, 'north': 13.0, 'east': 32.0},
        'West Kordofan': {'south': 10.5, 'west': 25.5, 'north': 14.0, 'east': 29.5},
        'North Darfur': {'south': 14.0, 'west': 22.0, 'north': 20.0, 'east': 27.5},
        'West Darfur': {'south': 11.0, 'west': 21.5, 'north': 14.0, 'east': 24.0},
        'Central Darfur': {'south': 11.5, 'west': 23.0, 'north': 14.5, 'east': 26.0},
        'South Darfur': {'south': 9.5, 'west': 23.5, 'north': 12.5, 'east': 28.0},
        'East Darfur': {'south': 10.0, 'west': 25.0, 'north': 14.0, 'east': 28.0}
    }

    # POI categories with Overpass tags
    POI_CATEGORIES = {
        'Hospitals': {
            'tags': [('amenity', 'hospital')],
            'color': '#e74c3c',
            'icon': 'cross',
            'description': 'Hospitals and medical centers'
        },
        'Health Clinics': {
            'tags': [('amenity', 'clinic')],
            'color': '#e67e22',
            'icon': 'circle',
            'description': 'Health clinics and dispensaries'
        },
        'Pharmacies': {
            'tags': [('amenity', 'pharmacy')],
            'color': '#27ae60',
            'icon': 'square',
            'description': 'Pharmacies and drug stores'
        },
        'Schools': {
            'tags': [('amenity', 'school')],
            'color': '#3498db',
            'icon': 'triangle',
            'description': 'Primary and secondary schools'
        },
        'Universities': {
            'tags': [('amenity', 'university')],
            'color': '#9b59b6',
            'icon': 'star',
            'description': 'Universities and colleges'
        },
        'Places of Worship': {
            'tags': [('amenity', 'place_of_worship')],
            'color': '#f39c12',
            'icon': 'diamond',
            'description': 'Mosques, churches, and temples'
        },
        'Markets': {
            'tags': [('amenity', 'marketplace')],
            'color': '#1abc9c',
            'icon': 'circle',
            'description': 'Markets and bazaars'
        },
        'Banks': {
            'tags': [('amenity', 'bank')],
            'color': '#2c3e50',
            'icon': 'square',
            'description': 'Banks and financial institutions'
        },
        'Fuel Stations': {
            'tags': [('amenity', 'fuel')],
            'color': '#c0392b',
            'icon': 'circle',
            'description': 'Petrol/gas stations'
        },
        'Water Points': {
            'tags': [('amenity', 'drinking_water'), ('man_made', 'water_well'), ('man_made', 'water_tower')],
            'color': '#3498db',
            'icon': 'circle',
            'description': 'Water sources and wells'
        },
        'Police Stations': {
            'tags': [('amenity', 'police')],
            'color': '#34495e',
            'icon': 'square',
            'description': 'Police stations'
        },
        'Fire Stations': {
            'tags': [('amenity', 'fire_station')],
            'color': '#e74c3c',
            'icon': 'triangle',
            'description': 'Fire stations'
        },
        'Airports': {
            'tags': [('aeroway', 'aerodrome')],
            'color': '#8e44ad',
            'icon': 'star',
            'description': 'Airports and airfields'
        },
        'Bus Stations': {
            'tags': [('amenity', 'bus_station')],
            'color': '#16a085',
            'icon': 'circle',
            'description': 'Bus terminals and stations'
        },
        'Hotels': {
            'tags': [('tourism', 'hotel')],
            'color': '#f1c40f',
            'icon': 'square',
            'description': 'Hotels and accommodation'
        },
        'Restaurants': {
            'tags': [('amenity', 'restaurant')],
            'color': '#e67e22',
            'icon': 'circle',
            'description': 'Restaurants and eateries'
        },
        'Government Buildings': {
            'tags': [('office', 'government')],
            'color': '#7f8c8d',
            'icon': 'square',
            'description': 'Government offices'
        },
        'Embassies': {
            'tags': [('office', 'diplomatic')],
            'color': '#2980b9',
            'icon': 'star',
            'description': 'Embassies and consulates'
        }
    }

    # Infrastructure categories
    INFRASTRUCTURE_CATEGORIES = {
        'Main Roads': {
            'tags': [('highway', 'primary'), ('highway', 'secondary'), ('highway', 'trunk')],
            'color': '#e74c3c',
            'geometry': 'line',
            'description': 'Primary and secondary roads'
        },
        'Railways': {
            'tags': [('railway', 'rail')],
            'color': '#2c3e50',
            'geometry': 'line',
            'description': 'Railway lines'
        },
        'Rivers': {
            'tags': [('waterway', 'river')],
            'color': '#3498db',
            'geometry': 'line',
            'description': 'Major rivers'
        }
    }

    # Signals
    query_complete = pyqtSignal(dict)  # GeoJSON result
    query_error = pyqtSignal(str)
    query_progress = pyqtSignal(str)  # Status message

    def __init__(self):
        """Initialize the OSM client."""
        super().__init__()
        self.cache_dir = os.path.join(tempfile.gettempdir(), 'sudan_osm_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.current_endpoint_index = 0
        self.timeout = 120000  # 2 minutes timeout

    def get_categories(self):
        """Get list of POI categories."""
        return list(self.POI_CATEGORIES.keys())

    def get_infrastructure_categories(self):
        """Get list of infrastructure categories."""
        return list(self.INFRASTRUCTURE_CATEGORIES.keys())

    def get_states(self):
        """Get list of Sudan states."""
        return list(self.SUDAN_STATES.keys())

    def get_category_info(self, category):
        """Get info for a category."""
        if category in self.POI_CATEGORIES:
            return self.POI_CATEGORIES[category]
        return self.INFRASTRUCTURE_CATEGORIES.get(category, {})

    def get_bbox_for_state(self, state_name):
        """Get bounding box for a state."""
        return self.SUDAN_STATES.get(state_name, self.SUDAN_BBOX)

    def _build_overpass_query(self, tags_list, bbox, geometry_type='nwr', need_geometry=False):
        """
        Build an Overpass QL query.

        :param tags_list: List of (key, value) tuples for tag filters
        :param bbox: Bounding box dict with south, west, north, east
        :param geometry_type: 'node', 'way', 'relation', or 'nwr' (all)
        :param need_geometry: If True, return full geometry for ways (for lines/polygons)
        :returns: Overpass QL query string
        """
        bbox_str = f"{bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']}"

        # Build tag queries
        tag_queries = []
        for key, value in tags_list:
            tag_queries.append(f'  {geometry_type}["{key}"="{value}"]({bbox_str});')

        query_body = '\n'.join(tag_queries)

        # Use 'out geom' for lines/polygons to get full geometry, 'out center' for points
        if need_geometry:
            output_mode = "out geom;"
        else:
            output_mode = "out center;"

        query = f"""[out:json][timeout:90];
(
{query_body}
);
{output_mode}"""
        return query

    def _execute_query(self, query):
        """
        Execute an Overpass query with fallback endpoints.

        :param query: Overpass QL query string
        :returns: JSON response or None
        """
        for i in range(len(self.OVERPASS_ENDPOINTS)):
            endpoint_index = (self.current_endpoint_index + i) % len(self.OVERPASS_ENDPOINTS)
            endpoint = self.OVERPASS_ENDPOINTS[endpoint_index]

            self.query_progress.emit(f"Querying {endpoint}...")
            QgsMessageLog.logMessage(f"OSM: Using endpoint {endpoint}", "Sudan Data Loader", Qgis.Info)

            try:
                # URL-encode the query data properly
                encoded_query = quote(query, safe='')
                post_data = f"data={encoded_query}"

                request = QNetworkRequest(QUrl(endpoint))
                request.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')

                blocking = QgsBlockingNetworkRequest()

                # Convert to QByteArray
                data_bytes = QByteArray(post_data.encode('utf-8'))

                error = blocking.post(request, data_bytes)

                if error == QgsBlockingNetworkRequest.NoError:
                    content = bytes(blocking.reply().content())
                    if content:
                        try:
                            result = json.loads(content.decode('utf-8'))
                            if 'elements' in result:
                                self.current_endpoint_index = endpoint_index
                                return result
                            elif 'remark' in result:
                                # Overpass error message
                                QgsMessageLog.logMessage(
                                    f"OSM: Overpass error: {result.get('remark', 'Unknown error')}",
                                    "Sudan Data Loader", Qgis.Warning
                                )
                        except json.JSONDecodeError as e:
                            QgsMessageLog.logMessage(
                                f"OSM: JSON decode error: {str(e)}",
                                "Sudan Data Loader", Qgis.Warning
                            )
                else:
                    QgsMessageLog.logMessage(
                        f"OSM: Endpoint {endpoint} failed: {blocking.errorMessage()}",
                        "Sudan Data Loader", Qgis.Warning
                    )

            except Exception as e:
                QgsMessageLog.logMessage(
                    f"OSM: Exception with {endpoint}: {str(e)}",
                    "Sudan Data Loader", Qgis.Warning
                )
                continue

        return None

    def query_pois(self, category, state=None, custom_bbox=None):
        """
        Query POIs for a category in Sudan.

        :param category: POI category name
        :param state: Optional state name to limit query (RECOMMENDED)
        :param custom_bbox: Optional custom bounding box
        :returns: GeoJSON dict or None
        """
        if category not in self.POI_CATEGORIES:
            self.query_error.emit(f"Unknown category: {category}")
            return None

        cat_info = self.POI_CATEGORIES[category]
        tags = cat_info['tags']

        # Determine bounding box - prefer state for better performance
        if custom_bbox:
            bbox = custom_bbox
        elif state:
            bbox = self.get_bbox_for_state(state)
        else:
            # Warn about large query
            self.query_progress.emit("Warning: Querying all of Sudan may be slow...")
            bbox = self.SUDAN_BBOX

        # Build and execute query
        query = self._build_overpass_query(tags, bbox, 'nwr')
        self.query_progress.emit(f"Fetching {category}...")

        result = self._execute_query(query)
        if not result:
            self.query_error.emit(f"Failed to fetch {category} data. Try selecting a specific state.")
            return None

        # Convert to GeoJSON
        geojson = self._osm_to_geojson(result, category)
        self.query_complete.emit(geojson)
        return geojson

    def query_infrastructure(self, category, state=None, custom_bbox=None):
        """
        Query infrastructure for a category in Sudan.

        :param category: Infrastructure category name
        :param state: Optional state name to limit query (RECOMMENDED)
        :param custom_bbox: Optional custom bounding box
        :returns: GeoJSON dict or None
        """
        if category not in self.INFRASTRUCTURE_CATEGORIES:
            self.query_error.emit(f"Unknown category: {category}")
            return None

        cat_info = self.INFRASTRUCTURE_CATEGORIES[category]
        tags = cat_info['tags']
        geom_type = cat_info.get('geometry', 'line')

        # Determine geometry type for query
        if geom_type == 'line':
            osm_type = 'way'
        elif geom_type == 'polygon':
            osm_type = 'way'
        else:
            osm_type = 'nwr'

        # Determine bounding box
        if custom_bbox:
            bbox = custom_bbox
        elif state:
            bbox = self.get_bbox_for_state(state)
        else:
            self.query_progress.emit("Warning: Querying all of Sudan may be slow...")
            bbox = self.SUDAN_BBOX

        # Build and execute query - use need_geometry=True for lines/polygons
        need_geometry = geom_type in ('line', 'polygon')
        query = self._build_overpass_query(tags, bbox, osm_type, need_geometry=need_geometry)
        self.query_progress.emit(f"Fetching {category}...")

        result = self._execute_query(query)
        if not result:
            self.query_error.emit(f"Failed to fetch {category} data. Try selecting a specific state.")
            return None

        # Convert to GeoJSON
        geojson = self._osm_to_geojson(result, category)
        self.query_complete.emit(geojson)
        return geojson

    def query_custom(self, overpass_query):
        """
        Execute a custom Overpass query.

        :param overpass_query: Full Overpass QL query string
        :returns: GeoJSON dict or None
        """
        self.query_progress.emit("Executing custom query...")
        result = self._execute_query(overpass_query)

        if not result:
            self.query_error.emit("Custom query failed")
            return None

        geojson = self._osm_to_geojson(result, "Custom Query")
        self.query_complete.emit(geojson)
        return geojson

    def _osm_to_geojson(self, osm_data, category_name):
        """
        Convert OSM JSON response to GeoJSON.

        :param osm_data: OSM Overpass JSON response
        :param category_name: Name of the category (for metadata)
        :returns: GeoJSON dict
        """
        features = []
        elements = osm_data.get('elements', [])

        # Build node lookup for ways
        nodes = {}
        for element in elements:
            if element.get('type') == 'node':
                nodes[element['id']] = {
                    'lat': element.get('lat'),
                    'lon': element.get('lon')
                }

        for element in elements:
            elem_type = element.get('type')

            if elem_type == 'node':
                # Point feature
                lat = element.get('lat')
                lon = element.get('lon')
                if lat is not None and lon is not None:
                    feature = {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [lon, lat]
                        },
                        'properties': self._extract_properties(element)
                    }
                    features.append(feature)

            elif elem_type == 'way':
                # Line or polygon feature
                coords = []

                # Check for geometry array (from 'out geom;')
                geom_array = element.get('geometry', [])
                if geom_array:
                    for point in geom_array:
                        if point.get('lat') is not None and point.get('lon') is not None:
                            coords.append([point['lon'], point['lat']])
                else:
                    # Fall back to nodes array (from 'out;' or 'out skel;')
                    node_ids = element.get('nodes', [])
                    for node_id in node_ids:
                        if node_id in nodes:
                            node = nodes[node_id]
                            if node['lat'] is not None and node['lon'] is not None:
                                coords.append([node['lon'], node['lat']])

                if len(coords) >= 2:
                    # Check if it's a closed way (polygon) by comparing first and last coordinates
                    is_closed = (coords[0] == coords[-1]) if len(coords) > 2 else False
                    tags = element.get('tags', {})

                    # Determine if it should be a polygon
                    is_polygon = is_closed and (
                        'building' in tags or
                        'landuse' in tags or
                        'area' in tags or
                        tags.get('area') == 'yes'
                    )

                    if is_polygon and len(coords) >= 4:
                        feature = {
                            'type': 'Feature',
                            'geometry': {
                                'type': 'Polygon',
                                'coordinates': [coords]
                            },
                            'properties': self._extract_properties(element)
                        }
                    else:
                        feature = {
                            'type': 'Feature',
                            'geometry': {
                                'type': 'LineString',
                                'coordinates': coords
                            },
                            'properties': self._extract_properties(element)
                        }
                    features.append(feature)

                # Also check for center point (from out center)
                center = element.get('center')
                if center and not coords:
                    feature = {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [center['lon'], center['lat']]
                        },
                        'properties': self._extract_properties(element)
                    }
                    features.append(feature)

        return {
            'type': 'FeatureCollection',
            'features': features,
            'metadata': {
                'category': category_name,
                'source': 'OpenStreetMap via Overpass API',
                'count': len(features)
            }
        }

    def _extract_properties(self, element):
        """Extract properties from an OSM element."""
        props = {
            'osm_id': element.get('id'),
            'osm_type': element.get('type')
        }

        # Add all tags
        tags = element.get('tags', {})
        for key, value in tags.items():
            # Clean key names for GIS compatibility
            clean_key = key.replace(':', '_').replace(' ', '_')
            props[clean_key] = value

        # Add common name field
        props['name'] = tags.get('name', tags.get('name:en', tags.get('name:ar', '')))

        return props

    def save_geojson(self, geojson, filename):
        """
        Save GeoJSON to cache directory.

        :param geojson: GeoJSON dict
        :param filename: Output filename
        :returns: Full file path
        """
        filepath = os.path.join(self.cache_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)
        return filepath

    def clear_cache(self):
        """Clear the OSM cache directory."""
        import shutil
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
            os.makedirs(self.cache_dir, exist_ok=True)
