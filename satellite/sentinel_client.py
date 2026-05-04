# -*- coding: utf-8 -*-
"""
Sentinel Hub Client for Ethiopia Data Loader.

Provides access to Sentinel-2 satellite imagery for Ethiopia via Sentinel Hub API.
Requires a free Sentinel Hub account for API access.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from urllib.parse import urlencode

from qgis.PyQt.QtCore import QUrl, QObject, pyqtSignal, QByteArray
from qgis.core import QgsBlockingNetworkRequest, QgsMessageLog, Qgis
from qgis.PyQt.QtNetwork import QNetworkRequest


class SentinelClient(QObject):
    """Client for accessing Sentinel Hub satellite imagery API."""

    # Sentinel Hub API endpoints
    AUTH_URL = "https://services.sentinel-hub.com/oauth/token"
    CATALOG_URL = "https://services.sentinel-hub.com/api/v1/catalog/search"
    PROCESS_URL = "https://services.sentinel-hub.com/api/v1/process"
    WMS_URL = "https://services.sentinel-hub.com/ogc/wms"

    # Sudan bounding box
    SUDAN_BBOX = [21.5, 8.5, 39.0, 23.5]  # [west, south, east, north]

    # Sudan states with bounding boxes
    SUDAN_STATES = {
        'Khartoum': [31.5, 15.2, 34.0, 16.2],
        'Northern': [25.0, 18.0, 34.0, 22.5],
        'River Nile': [31.5, 16.5, 35.5, 20.0],
        'Red Sea': [35.0, 17.5, 39.0, 22.5],
        'Kassala': [34.5, 14.5, 37.0, 17.5],
        'Gedaref': [33.5, 12.5, 36.5, 15.5],
        'Gezira': [32.0, 13.5, 34.0, 15.5],
        'Sennar': [32.5, 12.5, 35.0, 14.5],
        'Blue Nile': [33.0, 9.5, 35.5, 12.5],
        'White Nile': [30.0, 12.0, 33.0, 15.0],
        'North Kordofan': [27.0, 12.5, 32.0, 16.5],
        'South Kordofan': [28.0, 9.5, 32.0, 13.0],
        'West Kordofan': [25.5, 10.5, 29.5, 14.0],
        'North Darfur': [22.0, 14.0, 27.5, 20.0],
        'West Darfur': [21.5, 11.0, 24.0, 14.0],
        'Central Darfur': [23.0, 11.5, 26.0, 14.5],
        'South Darfur': [23.5, 9.5, 28.0, 12.5],
        'East Darfur': [25.0, 10.0, 28.0, 14.0]
    }

    # Visualization presets (evalscripts)
    VISUALIZATION_PRESETS = {
        'True Color': {
            'id': 'TRUE_COLOR',
            'description': 'Natural color composite (B04, B03, B02)',
            'evalscript': '''//VERSION=3
function setup() {
    return {
        input: ["B04", "B03", "B02"],
        output: { bands: 3 }
    };
}
function evaluatePixel(sample) {
    return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02];
}'''
        },
        'False Color (Urban)': {
            'id': 'FALSE_COLOR_URBAN',
            'description': 'Urban areas appear cyan (B12, B11, B04)',
            'evalscript': '''//VERSION=3
function setup() {
    return {
        input: ["B12", "B11", "B04"],
        output: { bands: 3 }
    };
}
function evaluatePixel(sample) {
    return [2.5 * sample.B12, 2.5 * sample.B11, 2.5 * sample.B04];
}'''
        },
        'False Color (Vegetation)': {
            'id': 'FALSE_COLOR_VEG',
            'description': 'Vegetation appears red (B08, B04, B03)',
            'evalscript': '''//VERSION=3
function setup() {
    return {
        input: ["B08", "B04", "B03"],
        output: { bands: 3 }
    };
}
function evaluatePixel(sample) {
    return [2.5 * sample.B08, 2.5 * sample.B04, 2.5 * sample.B03];
}'''
        },
        'NDVI': {
            'id': 'NDVI',
            'description': 'Normalized Difference Vegetation Index',
            'evalscript': '''//VERSION=3
function setup() {
    return {
        input: ["B04", "B08"],
        output: { bands: 3 }
    };
}
function evaluatePixel(sample) {
    let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
    if (ndvi < -0.2) return [0.05, 0.05, 0.05];
    else if (ndvi < 0) return [0.75, 0.75, 0.75];
    else if (ndvi < 0.1) return [0.86, 0.86, 0.86];
    else if (ndvi < 0.2) return [0.92, 0.92, 0.76];
    else if (ndvi < 0.3) return [0.87, 0.87, 0.61];
    else if (ndvi < 0.4) return [0.65, 0.85, 0.42];
    else if (ndvi < 0.5) return [0.44, 0.64, 0.28];
    else if (ndvi < 0.6) return [0.26, 0.48, 0.17];
    else return [0.13, 0.32, 0.09];
}'''
        },
        'NDWI (Water)': {
            'id': 'NDWI',
            'description': 'Normalized Difference Water Index',
            'evalscript': '''//VERSION=3
function setup() {
    return {
        input: ["B03", "B08"],
        output: { bands: 3 }
    };
}
function evaluatePixel(sample) {
    let ndwi = (sample.B03 - sample.B08) / (sample.B03 + sample.B08);
    if (ndwi > 0.3) return [0, 0.3, 0.8];
    else if (ndwi > 0.1) return [0.2, 0.5, 0.8];
    else if (ndwi > 0) return [0.4, 0.7, 0.9];
    else return [0.8, 0.8, 0.6];
}'''
        },
        'Moisture Index': {
            'id': 'MOISTURE',
            'description': 'Soil moisture indicator',
            'evalscript': '''//VERSION=3
function setup() {
    return {
        input: ["B8A", "B11"],
        output: { bands: 3 }
    };
}
function evaluatePixel(sample) {
    let moisture = (sample.B8A - sample.B11) / (sample.B8A + sample.B11);
    if (moisture > 0.4) return [0, 0.4, 0.8];
    else if (moisture > 0.2) return [0.2, 0.5, 0.7];
    else if (moisture > 0) return [0.5, 0.6, 0.5];
    else if (moisture > -0.2) return [0.8, 0.7, 0.4];
    else return [0.9, 0.5, 0.2];
}'''
        },
        'Agriculture': {
            'id': 'AGRICULTURE',
            'description': 'Agricultural monitoring (B11, B08, B02)',
            'evalscript': '''//VERSION=3
function setup() {
    return {
        input: ["B11", "B08", "B02"],
        output: { bands: 3 }
    };
}
function evaluatePixel(sample) {
    return [2.5 * sample.B11, 2.5 * sample.B08, 2.5 * sample.B02];
}'''
        }
    }

    # Signals
    auth_complete = pyqtSignal(bool)  # success
    search_complete = pyqtSignal(list)  # list of scenes
    download_complete = pyqtSignal(str)  # file path
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(str)

    def __init__(self, client_id=None, client_secret=None):
        """
        Initialize the Sentinel Hub client.

        :param client_id: Sentinel Hub OAuth client ID
        :param client_secret: Sentinel Hub OAuth client secret
        """
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expiry = None

        self.cache_dir = os.path.join(tempfile.gettempdir(), 'sudan_sentinel_cache')
        os.makedirs(self.cache_dir, exist_ok=True)

    def set_credentials(self, client_id, client_secret):
        """Set OAuth credentials."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expiry = None

    def has_credentials(self):
        """Check if credentials are configured."""
        return bool(self.client_id and self.client_secret)

    def authenticate(self):
        """
        Authenticate with Sentinel Hub OAuth.

        :returns: True if successful, False otherwise
        """
        if not self.has_credentials():
            self.error_occurred.emit("No Sentinel Hub credentials configured")
            return False

        self.progress_update.emit("Authenticating with Sentinel Hub...")

        # Prepare OAuth request
        post_data = urlencode({
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        })

        request = QNetworkRequest(QUrl(self.AUTH_URL))
        request.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')

        blocking = QgsBlockingNetworkRequest()
        error = blocking.post(request, QByteArray(post_data.encode('utf-8')))

        if error != QgsBlockingNetworkRequest.NoError:
            error_msg = blocking.errorMessage()
            self.error_occurred.emit(f"Authentication failed: {error_msg}")
            self.auth_complete.emit(False)
            return False

        try:
            content = bytes(blocking.reply().content())
            response = json.loads(content)
            self.access_token = response.get('access_token')
            expires_in = response.get('expires_in', 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)

            if self.access_token:
                QgsMessageLog.logMessage(
                    "Sentinel Hub: Authentication successful",
                    "Sudan Data Loader", Qgis.Info
                )
                self.auth_complete.emit(True)
                return True

        except (json.JSONDecodeError, KeyError) as e:
            self.error_occurred.emit(f"Failed to parse auth response: {str(e)}")

        self.auth_complete.emit(False)
        return False

    def _ensure_authenticated(self):
        """Ensure we have a valid access token."""
        if not self.access_token or (self.token_expiry and datetime.now() >= self.token_expiry):
            return self.authenticate()
        return True

    def get_presets(self):
        """Get list of visualization presets."""
        return list(self.VISUALIZATION_PRESETS.keys())

    def get_preset_info(self, preset_name):
        """Get info for a preset."""
        return self.VISUALIZATION_PRESETS.get(preset_name, {})

    def get_states(self):
        """Get list of Sudan states."""
        return list(self.SUDAN_STATES.keys())

    def get_bbox_for_state(self, state_name):
        """Get bounding box for a state."""
        return self.SUDAN_STATES.get(state_name, self.SUDAN_BBOX)

    def search_scenes(self, bbox=None, state=None, start_date=None, end_date=None,
                      max_cloud_cover=30, limit=20):
        """
        Search for Sentinel-2 scenes.

        :param bbox: Bounding box [west, south, east, north]
        :param state: State name to use for bbox
        :param start_date: Start date (YYYY-MM-DD)
        :param end_date: End date (YYYY-MM-DD)
        :param max_cloud_cover: Maximum cloud cover percentage
        :param limit: Maximum number of results
        :returns: List of scene dictionaries
        """
        if not self._ensure_authenticated():
            return []

        # Determine bbox
        if state:
            bbox = self.get_bbox_for_state(state)
        elif not bbox:
            bbox = self.SUDAN_BBOX

        # Default dates (last 30 days)
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        self.progress_update.emit(f"Searching scenes from {start_date} to {end_date}...")

        # Build catalog search request
        search_body = {
            "bbox": bbox,
            "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
            "collections": ["sentinel-2-l2a"],
            "limit": limit,
            "filter": f"eo:cloud_cover < {max_cloud_cover}"
        }

        request = QNetworkRequest(QUrl(self.CATALOG_URL))
        request.setHeader(QNetworkRequest.ContentTypeHeader, 'application/json')
        request.setRawHeader(b'Authorization', f'Bearer {self.access_token}'.encode())

        blocking = QgsBlockingNetworkRequest()
        error = blocking.post(request, QByteArray(json.dumps(search_body).encode('utf-8')))

        if error != QgsBlockingNetworkRequest.NoError:
            self.error_occurred.emit(f"Search failed: {blocking.errorMessage()}")
            return []

        try:
            content = bytes(blocking.reply().content())
            response = json.loads(content)

            scenes = []
            for feature in response.get('features', []):
                props = feature.get('properties', {})
                scenes.append({
                    'id': feature.get('id', ''),
                    'datetime': props.get('datetime', ''),
                    'cloud_cover': props.get('eo:cloud_cover', 0),
                    'bbox': feature.get('bbox', []),
                    'geometry': feature.get('geometry', {}),
                    'thumbnail': self._get_thumbnail_url(feature)
                })

            # Sort by date descending
            scenes.sort(key=lambda x: x['datetime'], reverse=True)
            self.search_complete.emit(scenes)
            return scenes

        except (json.JSONDecodeError, KeyError) as e:
            self.error_occurred.emit(f"Failed to parse search response: {str(e)}")
            return []

    def _get_thumbnail_url(self, feature):
        """Get thumbnail URL for a scene feature."""
        links = feature.get('links', [])
        for link in links:
            if link.get('rel') == 'thumbnail':
                return link.get('href', '')
        return ''

    def download_image(self, bbox, start_date, end_date, preset='True Color',
                       width=1024, height=1024, filename=None):
        """
        Download a processed satellite image.

        :param bbox: Bounding box [west, south, east, north]
        :param start_date: Start date (YYYY-MM-DD)
        :param end_date: End date (YYYY-MM-DD)
        :param preset: Visualization preset name
        :param width: Output image width
        :param height: Output image height
        :param filename: Output filename (optional)
        :returns: File path or None
        """
        if not self._ensure_authenticated():
            return None

        preset_info = self.VISUALIZATION_PRESETS.get(preset)
        if not preset_info:
            self.error_occurred.emit(f"Unknown preset: {preset}")
            return None

        self.progress_update.emit(f"Downloading {preset} image...")

        # Build process request
        request_body = {
            "input": {
                "bounds": {
                    "bbox": bbox,
                    "properties": {
                        "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
                    }
                },
                "data": [{
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {
                            "from": f"{start_date}T00:00:00Z",
                            "to": f"{end_date}T23:59:59Z"
                        },
                        "maxCloudCoverage": 30
                    }
                }]
            },
            "output": {
                "width": width,
                "height": height,
                "responses": [{
                    "identifier": "default",
                    "format": {
                        "type": "image/tiff"
                    }
                }]
            },
            "evalscript": preset_info['evalscript']
        }

        request = QNetworkRequest(QUrl(self.PROCESS_URL))
        request.setHeader(QNetworkRequest.ContentTypeHeader, 'application/json')
        request.setRawHeader(b'Authorization', f'Bearer {self.access_token}'.encode())
        request.setRawHeader(b'Accept', b'image/tiff')

        blocking = QgsBlockingNetworkRequest()
        error = blocking.post(request, QByteArray(json.dumps(request_body).encode('utf-8')))

        if error != QgsBlockingNetworkRequest.NoError:
            self.error_occurred.emit(f"Download failed: {blocking.errorMessage()}")
            return None

        # Save image
        content = bytes(blocking.reply().content())
        if len(content) < 1000:  # Likely an error response
            try:
                error_response = json.loads(content)
                self.error_occurred.emit(f"API error: {error_response.get('error', {}).get('message', 'Unknown')}")
                return None
            except json.JSONDecodeError:
                pass

        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"sentinel_{preset.lower().replace(' ', '_')}_{timestamp}.tif"

        filepath = os.path.join(self.cache_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(content)

        self.download_complete.emit(filepath)
        return filepath

    def get_wms_url(self, preset='True Color'):
        """
        Get WMS URL for a preset (for adding as XYZ layer).

        :param preset: Visualization preset name
        :returns: WMS URL or None
        """
        if not self.has_credentials():
            return None

        # Note: WMS requires instance ID which is set up in Sentinel Hub dashboard
        # This returns a template URL - user needs to configure their own instance
        return (
            f"{self.WMS_URL}/<YOUR_INSTANCE_ID>?"
            f"SERVICE=WMS&REQUEST=GetMap&"
            f"LAYERS={self.VISUALIZATION_PRESETS.get(preset, {}).get('id', 'TRUE_COLOR')}"
        )

    def clear_cache(self):
        """Clear the image cache."""
        import shutil
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
            os.makedirs(self.cache_dir, exist_ok=True)
