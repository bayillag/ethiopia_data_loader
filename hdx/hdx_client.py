# -*- coding: utf-8 -*-
"""
HDX Client for Ethiopia Data Loader.

Provides API access to Humanitarian Data Exchange (HDX) datasets for Ethiopia.
"""

import json
import os
import tempfile
from urllib.parse import urlencode

from qgis.PyQt.QtCore import QUrl, QObject, pyqtSignal
from qgis.core import QgsBlockingNetworkRequest, QgsNetworkAccessManager
from qgis.PyQt.QtNetwork import QNetworkRequest


class HDXClient(QObject):
    """Client for accessing HDX API and downloading datasets."""

    # HDX API endpoints
    BASE_URL = "https://data.humdata.org"
    API_URL = f"{BASE_URL}/api/3/action"

    # Pre-defined Ethiopia humanitarian datasets (verified IDs)
    FEATURED_DATASETS = [
        {
            'id': 'cod-ab-et',
            'name': 'Sudan - Administrative Boundaries (COD)',
            'description': 'Common Operational Datasets for administrative boundaries',
            'category': 'Administrative',
            'organization': 'OCHA'
        },
        {
            'id': 'cod-ps-sdn',
            'name': 'Sudan - Population Statistics',
            'description': 'Subnational population statistics',
            'category': 'Population',
            'organization': 'UNFPA'
        },
        {
            'id': 'sudan-healthsites',
            'name': 'Sudan Health Facilities',
            'description': 'Locations of health facilities across Sudan',
            'category': 'Health',
            'organization': 'Healthsites'
        },
        {
            'id': 'sudan-schools',
            'name': 'Sudan Schools',
            'description': 'Educational facilities locations',
            'category': 'Education',
            'organization': 'OCHA'
        },
        {
            'id': 'sudan-road-network',
            'name': 'Sudan Roads Network',
            'description': 'Road infrastructure across Sudan',
            'category': 'Infrastructure',
            'organization': 'OCHA'
        },
        {
            'id': 'sudan-settlements',
            'name': 'Sudan Settlements',
            'description': 'Settlement locations',
            'category': 'Population',
            'organization': 'OCHA'
        },
        {
            'id': 'sudan-idp-camps',
            'name': 'Sudan IDP Camps',
            'description': 'Internally displaced persons camp locations',
            'category': 'Refugees/IDPs',
            'organization': 'OCHA'
        },
        {
            'id': 'unhcr-refugee-camps',
            'name': 'Sudan Refugee Camps',
            'description': 'UNHCR refugee camp locations',
            'category': 'Refugees/IDPs',
            'organization': 'UNHCR'
        },
        {
            'id': 'sudan-acled-conflict-data',
            'name': 'Sudan Conflict Events',
            'description': 'Armed conflict and protest events data',
            'category': 'Conflict',
            'organization': 'ACLED'
        },
        {
            'id': 'sudan-aerodromes',
            'name': 'Sudan Airfields',
            'description': 'Airport and airfield locations',
            'category': 'Infrastructure',
            'organization': 'OCHA'
        },
        {
            'id': 'wfp-food-prices-for-sudan',
            'name': 'Sudan Food Prices',
            'description': 'Food price monitoring data',
            'category': 'Food Security',
            'organization': 'WFP'
        },
        {
            'id': 'sudan-river-nile-line',
            'name': 'Sudan River Nile',
            'description': 'Nile River course through Sudan',
            'category': 'Environment',
            'organization': 'OCHA'
        },
        {
            'id': 'border-crossing-points-sudan',
            'name': 'Sudan Border Crossings',
            'description': 'International border crossing points',
            'category': 'Infrastructure',
            'organization': 'OCHA'
        },
        {
            'id': 'sudan-people-affected-by-floods',
            'name': 'Sudan Flood Affected Areas',
            'description': 'People affected by floods data',
            'category': 'Hazards',
            'organization': 'OCHA'
        },
        {
            'id': 'sudan-humanitarian-needs',
            'name': 'Sudan Humanitarian Needs',
            'description': 'Humanitarian needs overview',
            'category': 'General',
            'organization': 'OCHA'
        }
    ]

    # Category colors for visualization
    CATEGORY_COLORS = {
        'Administrative': '#3498db',
        'Health': '#e74c3c',
        'Population': '#9b59b6',
        'Infrastructure': '#f39c12',
        'Education': '#2ecc71',
        'Environment': '#1abc9c',
        'Hazards': '#e67e22',
        'Conflict': '#c0392b',
        'General': '#95a5a6',
        'Food Security': '#27ae60',
        'Refugees/IDPs': '#8e44ad'
    }

    # Signals
    download_progress = pyqtSignal(int, int)  # received, total
    download_complete = pyqtSignal(str)  # file path
    download_error = pyqtSignal(str)  # error message

    def __init__(self):
        """Initialize the HDX client."""
        super().__init__()
        self.cache_dir = os.path.join(tempfile.gettempdir(), 'sudan_hdx_cache')
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_featured_datasets(self):
        """Get list of featured Sudan datasets."""
        return self.FEATURED_DATASETS.copy()

    def get_categories(self):
        """Get list of dataset categories."""
        return list(self.CATEGORY_COLORS.keys())

    def get_category_color(self, category):
        """Get color for a category."""
        return self.CATEGORY_COLORS.get(category, '#95a5a6')

    def search_datasets(self, query='', category=None, limit=50):
        """
        Search HDX for Sudan datasets.

        :param query: Search query string
        :param category: Filter by category
        :param limit: Maximum results
        :returns: List of dataset info dicts
        """
        params = {
            'q': f'sudan {query}' if query else 'sudan',
            'fq': 'groups:sdn',
            'rows': limit,
            'start': 0
        }

        url = f"{self.API_URL}/package_search?{urlencode(params)}"

        request = QNetworkRequest(QUrl(url))
        request.setHeader(QNetworkRequest.ContentTypeHeader, 'application/json')

        blocking = QgsBlockingNetworkRequest()
        error = blocking.get(request)

        if error != QgsBlockingNetworkRequest.NoError:
            return []

        try:
            response = json.loads(bytes(blocking.reply().content()))
            if response.get('success'):
                datasets = []
                for pkg in response['result']['results']:
                    datasets.append({
                        'id': pkg.get('name', ''),
                        'title': pkg.get('title', ''),
                        'description': pkg.get('notes', '')[:200] + '...' if pkg.get('notes', '') else '',
                        'organization': pkg.get('organization', {}).get('title', 'Unknown'),
                        'last_modified': pkg.get('metadata_modified', ''),
                        'num_resources': len(pkg.get('resources', [])),
                        'tags': [t['name'] for t in pkg.get('tags', [])],
                        'resources': pkg.get('resources', [])
                    })
                return datasets
        except (json.JSONDecodeError, KeyError):
            pass

        return []

    def get_dataset_details(self, dataset_id):
        """
        Get detailed information about a dataset.

        :param dataset_id: HDX dataset ID
        :returns: Dataset details dict or None
        """
        url = f"{self.API_URL}/package_show?id={dataset_id}"

        request = QNetworkRequest(QUrl(url))
        blocking = QgsBlockingNetworkRequest()
        error = blocking.get(request)

        if error != QgsBlockingNetworkRequest.NoError:
            return None

        try:
            response = json.loads(bytes(blocking.reply().content()))
            if response.get('success'):
                pkg = response['result']
                return {
                    'id': pkg.get('name', ''),
                    'title': pkg.get('title', ''),
                    'description': pkg.get('notes', ''),
                    'organization': pkg.get('organization', {}).get('title', 'Unknown'),
                    'maintainer': pkg.get('maintainer', ''),
                    'last_modified': pkg.get('metadata_modified', ''),
                    'license': pkg.get('license_title', 'Unknown'),
                    'methodology': pkg.get('methodology', ''),
                    'caveats': pkg.get('caveats', ''),
                    'tags': [t['name'] for t in pkg.get('tags', [])],
                    'resources': self._parse_resources(pkg.get('resources', [])),
                    'url': f"{self.BASE_URL}/dataset/{dataset_id}"
                }
        except (json.JSONDecodeError, KeyError):
            pass

        return None

    def _parse_resources(self, resources):
        """Parse resource list from HDX API response."""
        parsed = []
        for res in resources:
            format_type = res.get('format', '').upper()
            # Prioritize GIS formats
            is_gis = format_type in ['GEOJSON', 'SHP', 'GPKG', 'KML', 'GEOPACKAGE', 'SHAPEFILE', 'CSV']
            parsed.append({
                'id': res.get('id', ''),
                'name': res.get('name', res.get('description', 'Unnamed')),
                'format': format_type,
                'url': res.get('url', ''),
                'size': res.get('size', 0),
                'last_modified': res.get('last_modified', ''),
                'is_gis': is_gis
            })
        # Sort GIS formats first
        parsed.sort(key=lambda x: (not x['is_gis'], x['format']))
        return parsed

    def download_resource(self, resource_url, filename=None):
        """
        Download a resource file.

        :param resource_url: URL of the resource
        :param filename: Optional filename (auto-generated if not provided)
        :returns: Local file path or None
        """
        if not filename:
            filename = resource_url.split('/')[-1].split('?')[0]

        local_path = os.path.join(self.cache_dir, filename)

        request = QNetworkRequest(QUrl(resource_url))
        request.setAttribute(
            QNetworkRequest.RedirectPolicyAttribute,
            QNetworkRequest.NoLessSafeRedirectPolicy
        )

        blocking = QgsBlockingNetworkRequest()
        error = blocking.get(request, forceRefresh=True)

        if error != QgsBlockingNetworkRequest.NoError:
            self.download_error.emit(f"Download failed: {blocking.errorMessage()}")
            return None

        data = bytes(blocking.reply().content())

        if len(data) == 0:
            self.download_error.emit("Downloaded file is empty")
            return None

        try:
            with open(local_path, 'wb') as f:
                f.write(data)
            self.download_complete.emit(local_path)
            return local_path
        except IOError as e:
            self.download_error.emit(f"Failed to save file: {str(e)}")
            return None

    def get_gis_resources(self, dataset_id):
        """
        Get only GIS-compatible resources from a dataset.

        :param dataset_id: HDX dataset ID
        :returns: List of GIS resources
        """
        details = self.get_dataset_details(dataset_id)
        if not details:
            return []

        gis_formats = ['GEOJSON', 'SHP', 'GPKG', 'KML', 'GEOPACKAGE', 'SHAPEFILE', 'CSV']
        return [r for r in details['resources'] if r['format'] in gis_formats]

    def clear_cache(self):
        """Clear the download cache."""
        import shutil
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
            os.makedirs(self.cache_dir, exist_ok=True)
