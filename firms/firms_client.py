# -*- coding: utf-8 -*-
"""
NASA FIRMS Client for Ethiopia Data Loader.

Provides access to NASA Fire Information for Resource Management System (FIRMS)
for real-time fire/hotspot detection in Ethiopia.
"""

import json
import os
import csv
import tempfile
from datetime import datetime, timedelta
from io import StringIO

from qgis.PyQt.QtCore import QUrl, QObject, pyqtSignal
from qgis.core import QgsBlockingNetworkRequest, QgsMessageLog, Qgis
from qgis.PyQt.QtNetwork import QNetworkRequest


class FIRMSClient(QObject):
    """Client for accessing NASA FIRMS fire data API."""

    # FIRMS API endpoint (requires API key for full access)
    # Using the open CSV endpoint for country data
    BASE_URL = "https://firms.modaps.eosdis.nasa.gov"

    # Data sources
    DATA_SOURCES = {
        'VIIRS_SNPP': {
            'name': 'VIIRS S-NPP',
            'description': 'Visible Infrared Imaging Radiometer Suite on Suomi NPP',
            'resolution': '375m'
        },
        'VIIRS_NOAA20': {
            'name': 'VIIRS NOAA-20',
            'description': 'VIIRS on NOAA-20 satellite',
            'resolution': '375m'
        },
        'MODIS_NRT': {
            'name': 'MODIS NRT',
            'description': 'Moderate Resolution Imaging Spectroradiometer (Near Real-Time)',
            'resolution': '1km'
        },
        'MODIS_SP': {
            'name': 'MODIS SP',
            'description': 'MODIS Standard Processing',
            'resolution': '1km'
        }
    }

    # Time ranges
    TIME_RANGES = {
        '24h': {'days': 1, 'label': 'Last 24 hours'},
        '48h': {'days': 2, 'label': 'Last 48 hours'},
        '7d': {'days': 7, 'label': 'Last 7 days'},
        '10d': {'days': 10, 'label': 'Last 10 days'}
    }

    # Sudan country code for FIRMS
    SUDAN_COUNTRY_CODE = "SDN"

    # Sudan bounding box
    SUDAN_BBOX = {
        'west': 21.5,
        'south': 8.5,
        'east': 39.0,
        'north': 23.5
    }

    # Confidence levels
    CONFIDENCE_LEVELS = {
        'low': {'min': 0, 'max': 30, 'color': '#f1c40f'},
        'nominal': {'min': 30, 'max': 80, 'color': '#e67e22'},
        'high': {'min': 80, 'max': 100, 'color': '#e74c3c'}
    }

    # Signals
    data_loaded = pyqtSignal(list)  # list of fire points
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(str)

    def __init__(self, api_key=None):
        """
        Initialize the FIRMS client.

        :param api_key: NASA FIRMS API key (optional, for extended access)
        """
        super().__init__()
        self.api_key = api_key
        self.cache_dir = os.path.join(tempfile.gettempdir(), 'sudan_firms_cache')
        os.makedirs(self.cache_dir, exist_ok=True)

    def set_api_key(self, api_key):
        """Set the API key."""
        self.api_key = api_key

    def has_api_key(self):
        """Check if API key is set."""
        return bool(self.api_key)

    def get_data_sources(self):
        """Get list of available data sources."""
        return list(self.DATA_SOURCES.keys())

    def get_data_source_info(self, source):
        """Get info for a data source."""
        return self.DATA_SOURCES.get(source, {})

    def get_time_ranges(self):
        """Get available time ranges."""
        return list(self.TIME_RANGES.keys())

    def get_time_range_info(self, range_key):
        """Get info for a time range."""
        return self.TIME_RANGES.get(range_key, {})

    def fetch_fire_data(self, source='VIIRS_SNPP', time_range='24h', min_confidence=0):
        """
        Fetch fire/hotspot data for Sudan.

        :param source: Data source (VIIRS_SNPP, VIIRS_NOAA20, MODIS_NRT, MODIS_SP)
        :param time_range: Time range (24h, 48h, 7d, 10d)
        :param min_confidence: Minimum confidence level (0-100)
        :returns: List of fire point dictionaries
        """
        range_info = self.TIME_RANGES.get(time_range, {'days': 1})
        days = range_info['days']

        self.progress_update.emit(f"Fetching {source} fire data for last {days} days...")

        # Build URL based on whether we have an API key
        if self.api_key:
            # Use API key endpoint for more data
            url = f"{self.BASE_URL}/api/country/csv/{self.api_key}/{source}/{self.SUDAN_COUNTRY_CODE}/{days}"
        else:
            # Use open data endpoint (limited)
            # Alternative: Use area-based query with bbox
            url = f"{self.BASE_URL}/api/area/csv/{source}/{self.SUDAN_BBOX['west']},{self.SUDAN_BBOX['south']},{self.SUDAN_BBOX['east']},{self.SUDAN_BBOX['north']}/{days}"

        request = QNetworkRequest(QUrl(url))
        blocking = QgsBlockingNetworkRequest()
        error = blocking.get(request)

        if error != QgsBlockingNetworkRequest.NoError:
            # Try alternative open data source
            self.progress_update.emit("Trying alternative data source...")
            return self._fetch_from_open_data(source, days, min_confidence)

        try:
            content = bytes(blocking.reply().content()).decode('utf-8')

            # Check for error responses
            if content.startswith('<!DOCTYPE') or 'error' in content.lower()[:100]:
                self.progress_update.emit("API error, trying alternative source...")
                return self._fetch_from_open_data(source, days, min_confidence)

            # Parse CSV data
            fires = self._parse_csv_data(content, min_confidence)
            self.data_loaded.emit(fires)
            return fires

        except Exception as e:
            self.error_occurred.emit(f"Failed to parse fire data: {str(e)}")
            return []

    def _fetch_from_open_data(self, source, days, min_confidence):
        """
        Fetch from open data archive as fallback.

        :returns: List of fire points
        """
        # Use the Active Fire Map web service
        # This endpoint provides recent data without requiring API key
        bbox = f"{self.SUDAN_BBOX['west']},{self.SUDAN_BBOX['south']},{self.SUDAN_BBOX['east']},{self.SUDAN_BBOX['north']}"

        # Try the public CSV feed
        source_map = {
            'VIIRS_SNPP': 'viirs-snpp-nrt',
            'VIIRS_NOAA20': 'viirs-noaa20-nrt',
            'MODIS_NRT': 'modis-nrt',
            'MODIS_SP': 'modis-sp'
        }
        source_name = source_map.get(source, 'viirs-snpp-nrt')

        # Use active fire data download endpoint
        url = f"{self.BASE_URL}/active_fire/c6/{source_name}/csv/{self.SUDAN_COUNTRY_CODE}"

        self.progress_update.emit(f"Trying public data feed: {source_name}...")

        request = QNetworkRequest(QUrl(url))
        blocking = QgsBlockingNetworkRequest()
        error = blocking.get(request)

        if error != QgsBlockingNetworkRequest.NoError:
            self.error_occurred.emit(
                f"Could not fetch fire data. Consider registering for a free NASA FIRMS API key "
                f"at https://firms.modaps.eosdis.nasa.gov/api/area/"
            )
            return []

        try:
            content = bytes(blocking.reply().content()).decode('utf-8')
            fires = self._parse_csv_data(content, min_confidence)

            # Filter by date if needed
            if days < 10:
                cutoff = datetime.now() - timedelta(days=days)
                fires = [f for f in fires if self._parse_date(f.get('acq_date', '')) >= cutoff]

            self.data_loaded.emit(fires)
            return fires

        except Exception as e:
            self.error_occurred.emit(f"Failed to parse fire data: {str(e)}")
            return []

    def _parse_date(self, date_str):
        """Parse date string to datetime."""
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except (ValueError, TypeError):
            return datetime.min

    def _parse_csv_data(self, csv_content, min_confidence=0):
        """
        Parse CSV fire data.

        :param csv_content: CSV content string
        :param min_confidence: Minimum confidence filter
        :returns: List of fire point dictionaries
        """
        fires = []
        reader = csv.DictReader(StringIO(csv_content))

        for row in reader:
            try:
                lat = float(row.get('latitude', 0))
                lon = float(row.get('longitude', 0))

                # Skip if outside Sudan bbox
                if not (self.SUDAN_BBOX['south'] <= lat <= self.SUDAN_BBOX['north'] and
                        self.SUDAN_BBOX['west'] <= lon <= self.SUDAN_BBOX['east']):
                    continue

                # Parse confidence
                confidence = row.get('confidence', '0')
                if isinstance(confidence, str):
                    # VIIRS uses 'n', 'l', 'h' for nominal, low, high
                    confidence_map = {'l': 20, 'n': 50, 'h': 90, 'low': 20, 'nominal': 50, 'high': 90}
                    confidence = confidence_map.get(confidence.lower(), int(confidence) if confidence.isdigit() else 50)
                else:
                    confidence = int(confidence)

                if confidence < min_confidence:
                    continue

                fire = {
                    'latitude': lat,
                    'longitude': lon,
                    'brightness': float(row.get('bright_ti4', row.get('brightness', 0))),
                    'scan': float(row.get('scan', 0)),
                    'track': float(row.get('track', 0)),
                    'acq_date': row.get('acq_date', ''),
                    'acq_time': row.get('acq_time', ''),
                    'satellite': row.get('satellite', ''),
                    'instrument': row.get('instrument', ''),
                    'confidence': confidence,
                    'version': row.get('version', ''),
                    'frp': float(row.get('frp', 0)),  # Fire Radiative Power
                    'daynight': row.get('daynight', '')
                }
                fires.append(fire)

            except (ValueError, TypeError) as e:
                continue

        return fires

    def fires_to_geojson(self, fires):
        """
        Convert fire points to GeoJSON.

        :param fires: List of fire dictionaries
        :returns: GeoJSON dictionary
        """
        features = []

        for fire in fires:
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [fire['longitude'], fire['latitude']]
                },
                'properties': {
                    'brightness': fire.get('brightness', 0),
                    'confidence': fire.get('confidence', 0),
                    'confidence_level': self._get_confidence_level(fire.get('confidence', 0)),
                    'acq_date': fire.get('acq_date', ''),
                    'acq_time': fire.get('acq_time', ''),
                    'satellite': fire.get('satellite', ''),
                    'instrument': fire.get('instrument', ''),
                    'frp': fire.get('frp', 0),
                    'daynight': fire.get('daynight', '')
                }
            }
            features.append(feature)

        return {
            'type': 'FeatureCollection',
            'features': features,
            'metadata': {
                'source': 'NASA FIRMS',
                'count': len(features),
                'timestamp': datetime.now().isoformat()
            }
        }

    def _get_confidence_level(self, confidence):
        """Get confidence level category."""
        if confidence >= 80:
            return 'high'
        elif confidence >= 30:
            return 'nominal'
        else:
            return 'low'

    def get_statistics(self, fires):
        """
        Calculate statistics from fire data.

        :param fires: List of fire dictionaries
        :returns: Statistics dictionary
        """
        if not fires:
            return {}

        # Count by confidence level
        by_confidence = {'low': 0, 'nominal': 0, 'high': 0}
        for fire in fires:
            level = self._get_confidence_level(fire.get('confidence', 0))
            by_confidence[level] += 1

        # Count by date
        by_date = {}
        for fire in fires:
            date = fire.get('acq_date', 'Unknown')
            by_date[date] = by_date.get(date, 0) + 1

        # Average FRP
        frp_values = [f.get('frp', 0) for f in fires if f.get('frp', 0) > 0]
        avg_frp = sum(frp_values) / len(frp_values) if frp_values else 0

        return {
            'total_fires': len(fires),
            'by_confidence': by_confidence,
            'by_date': by_date,
            'avg_frp': avg_frp,
            'max_frp': max(frp_values) if frp_values else 0,
            'date_range': {
                'start': min(f.get('acq_date', '') for f in fires),
                'end': max(f.get('acq_date', '') for f in fires)
            }
        }

    def save_geojson(self, geojson, filename=None):
        """
        Save GeoJSON to cache.

        :param geojson: GeoJSON dictionary
        :param filename: Output filename
        :returns: File path
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"firms_fires_{timestamp}.geojson"

        filepath = os.path.join(self.cache_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2)

        return filepath

    def clear_cache(self):
        """Clear cache directory."""
        import shutil
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
            os.makedirs(self.cache_dir, exist_ok=True)
