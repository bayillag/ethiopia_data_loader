# -*- coding: utf-8 -*-
"""
ACLED Client for Ethiopia Data Loader.

Provides access to Armed Conflict Location & Event Data (ACLED) for Ethiopia.
Uses OAuth authentication for API access.
"""

import json
from datetime import datetime, timedelta
from urllib.parse import urlencode

from qgis.PyQt.QtCore import QUrl, QObject, pyqtSignal, QByteArray
from qgis.core import QgsBlockingNetworkRequest
from qgis.PyQt.QtNetwork import QNetworkRequest


class ACLEDClient(QObject):
    """Client for accessing ACLED API with OAuth authentication."""

    # ACLED API endpoints
    TOKEN_URL = "https://acleddata.com/oauth/token"
    API_URL = "https://acleddata.com/api/acled/read"

    # Ethiopia ISO code
    ETHIOPIA_ISO = 231
    ETHIOPIA_COUNTRY = "Ethiopia"

    # Event types with colors for visualization
    EVENT_TYPES = {
        'Battles': {
            'color': '#e74c3c',
            'icon': 'circle',
            'description': 'Armed clashes between organized groups'
        },
        'Violence against civilians': {
            'color': '#9b59b6',
            'icon': 'circle',
            'description': 'Attacks on unarmed civilians'
        },
        'Explosions/Remote violence': {
            'color': '#e67e22',
            'icon': 'triangle',
            'description': 'Bombs, IEDs, shelling, airstrikes'
        },
        'Riots': {
            'color': '#f39c12',
            'icon': 'square',
            'description': 'Violent demonstrations and mobs'
        },
        'Protests': {
            'color': '#3498db',
            'icon': 'diamond',
            'description': 'Non-violent demonstrations'
        },
        'Strategic developments': {
            'color': '#1abc9c',
            'icon': 'star',
            'description': 'Strategic military/political events'
        }
    }

    # Actor types
    ACTOR_TYPES = [
        'Military Forces of Ethiopia (ENDF)',
        'RSF: Rapid Support Forces',
        'Police Forces of Ethiopia',
        'Rebel Groups',
        'Political Militias',
        'Civilians',
        'Protesters'
    ]

    # Signals
    data_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, api_key=None, email=None):
        """
        Initialize the ACLED client.

        :param api_key: ACLED API key (password for OAuth)
        :param email: Email associated with API key (username for OAuth)
        """
        super().__init__()
        self.api_key = api_key  # Used as password
        self.email = email      # Used as username
        self.access_token = None

    def set_credentials(self, api_key, email):
        """Set API credentials."""
        self.api_key = api_key
        self.email = email
        self.access_token = None  # Clear token when credentials change

    def _get_access_token(self):
        """
        Get OAuth access token from ACLED.

        :returns: Access token string or None if failed
        """
        from qgis.core import QgsMessageLog, Qgis

        if not self.email or not self.api_key:
            QgsMessageLog.logMessage("ACLED: No credentials provided", "Sudan Data Loader", Qgis.Warning)
            return None

        QgsMessageLog.logMessage(f"ACLED: Requesting OAuth token for {self.email}", "Sudan Data Loader", Qgis.Info)

        # Prepare OAuth request
        post_data = urlencode({
            'grant_type': 'password',
            'client_id': 'acled',
            'username': self.email,
            'password': self.api_key
        })

        request = QNetworkRequest(QUrl(self.TOKEN_URL))
        request.setHeader(QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')

        blocking = QgsBlockingNetworkRequest()
        error = blocking.post(request, QByteArray(post_data.encode('utf-8')))

        if error != QgsBlockingNetworkRequest.NoError:
            error_msg = blocking.errorMessage()
            QgsMessageLog.logMessage(f"ACLED OAuth failed: {error_msg}", "Sudan Data Loader", Qgis.Critical)
            self.error_occurred.emit(f"OAuth token request failed: {error_msg}")
            return None

        try:
            content = bytes(blocking.reply().content())
            QgsMessageLog.logMessage(f"ACLED OAuth response: {content.decode('utf-8', errors='ignore')[:500]}", "Sudan Data Loader", Qgis.Info)

            response = json.loads(content)
            self.access_token = response.get('access_token')

            if self.access_token:
                QgsMessageLog.logMessage("ACLED: OAuth token obtained successfully", "Sudan Data Loader", Qgis.Info)
            else:
                QgsMessageLog.logMessage(f"ACLED: No access_token in response: {response}", "Sudan Data Loader", Qgis.Warning)

            return self.access_token
        except (json.JSONDecodeError, KeyError) as e:
            QgsMessageLog.logMessage(f"ACLED OAuth parse error: {str(e)}", "Sudan Data Loader", Qgis.Critical)
            self.error_occurred.emit(f"Failed to parse OAuth response: {str(e)}")
            return None

    def get_event_types(self):
        """Get list of event types."""
        return list(self.EVENT_TYPES.keys())

    def get_event_color(self, event_type):
        """Get color for an event type."""
        return self.EVENT_TYPES.get(event_type, {}).get('color', '#95a5a6')

    def get_event_info(self, event_type):
        """Get info for an event type."""
        return self.EVENT_TYPES.get(event_type, {})

    def fetch_events(self, start_date=None, end_date=None, event_types=None,
                     admin1=None, limit=5000):
        """
        Fetch conflict events from ACLED API.

        :param start_date: Start date (YYYY-MM-DD)
        :param end_date: End date (YYYY-MM-DD)
        :param event_types: List of event types to filter
        :param admin1: Admin1 region to filter
        :param limit: Maximum number of events
        :returns: List of event dictionaries
        """
        # Get access token if we have credentials
        if self.email and self.api_key and not self.access_token:
            self._get_access_token()

        # Build query parameters
        params = {
            'country': self.SUDAN_COUNTRY,
            'limit': limit
        }

        # Date filtering - ACLED API uses separate start/end date parameters
        if start_date and end_date:
            # For date range, use both parameters
            params['event_date'] = start_date
            params['event_date_where'] = '>='
            params['event_date_end'] = end_date
            params['event_date_end_where'] = '<='
        elif start_date:
            params['event_date'] = start_date
            params['event_date_where'] = '>='
        elif end_date:
            params['event_date'] = end_date
            params['event_date_where'] = '<='

        # Event type filtering
        if event_types and len(event_types) > 0:
            params['event_type'] = '|'.join(event_types)

        # Admin1 filtering
        if admin1:
            params['admin1'] = admin1

        # Make API request
        url = f"{self.API_URL}?{urlencode(params)}"

        request = QNetworkRequest(QUrl(url))
        request.setHeader(QNetworkRequest.ContentTypeHeader, 'application/json')

        # Add authorization header if we have a token
        if self.access_token:
            request.setRawHeader(b'Authorization', f'Bearer {self.access_token}'.encode())

        blocking = QgsBlockingNetworkRequest()
        error = blocking.get(request)

        if error != QgsBlockingNetworkRequest.NoError:
            error_msg = blocking.errorMessage()
            # Check if it's an auth error
            if '401' in error_msg or 'Unauthorized' in error_msg:
                self.error_occurred.emit(
                    "ACLED API requires authentication. Please configure your API credentials in Settings.\n"
                    "Register at: https://acleddata.com/register/"
                )
            else:
                self.error_occurred.emit(f"API request failed: {error_msg}")
            return []

        try:
            content = bytes(blocking.reply().content())

            # Debug: Log response for troubleshooting
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(f"ACLED API URL: {url}", "Sudan Data Loader", Qgis.Info)
            QgsMessageLog.logMessage(f"ACLED Response length: {len(content)} bytes", "Sudan Data Loader", Qgis.Info)
            if len(content) < 1000:
                QgsMessageLog.logMessage(f"ACLED Response: {content.decode('utf-8', errors='ignore')}", "Sudan Data Loader", Qgis.Info)

            # Check if response is empty
            if not content:
                self.error_occurred.emit("Empty response from ACLED API. Please check your credentials.")
                return []

            response = json.loads(content)

            # Handle different response formats
            if isinstance(response, dict):
                if response.get('success', False):
                    events = response.get('data', [])
                    self.data_loaded.emit(events)
                    return events
                elif 'error' in response:
                    error_msg = response.get('error', {})
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get('message', 'Unknown error')
                    self.error_occurred.emit(f"ACLED API error: {error_msg}")
                    return []
                elif 'data' in response:
                    # Some responses have data without success flag
                    events = response.get('data', [])
                    self.data_loaded.emit(events)
                    return events
            elif isinstance(response, list):
                # Direct list response
                self.data_loaded.emit(response)
                return response

            self.error_occurred.emit("Unexpected response format from ACLED API")
            return []

        except json.JSONDecodeError as e:
            self.error_occurred.emit(f"Failed to parse API response: {str(e)}")
            return []

    def fetch_recent_events(self, days=30, event_types=None):
        """
        Fetch recent conflict events.

        :param days: Number of days to look back
        :param event_types: Event types to filter
        :returns: List of events
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        return self.fetch_events(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            event_types=event_types
        )

    def fetch_events_by_year(self, year, event_types=None):
        """
        Fetch conflict events for a specific year.

        :param year: Year to fetch
        :param event_types: Event types to filter
        :returns: List of events
        """
        return self.fetch_events(
            start_date=f"{year}-01-01",
            end_date=f"{year}-12-31",
            event_types=event_types
        )

    def events_to_geojson(self, events):
        """
        Convert events to GeoJSON format.

        :param events: List of event dictionaries
        :returns: GeoJSON dictionary
        """
        features = []

        for event in events:
            try:
                lat = float(event.get('latitude', 0))
                lon = float(event.get('longitude', 0))

                if lat == 0 and lon == 0:
                    continue

                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [lon, lat]
                    },
                    'properties': {
                        'event_id': event.get('event_id_cnty', ''),
                        'event_date': event.get('event_date', ''),
                        'year': event.get('year', ''),
                        'event_type': event.get('event_type', ''),
                        'sub_event_type': event.get('sub_event_type', ''),
                        'actor1': event.get('actor1', ''),
                        'actor2': event.get('actor2', ''),
                        'admin1': event.get('admin1', ''),
                        'admin2': event.get('admin2', ''),
                        'admin3': event.get('admin3', ''),
                        'location': event.get('location', ''),
                        'fatalities': int(event.get('fatalities', 0)),
                        'notes': event.get('notes', ''),
                        'source': event.get('source', ''),
                        'source_scale': event.get('source_scale', '')
                    }
                }
                features.append(feature)

            except (ValueError, TypeError):
                continue

        return {
            'type': 'FeatureCollection',
            'features': features
        }

    def get_statistics(self, events):
        """
        Calculate statistics from events.

        :param events: List of events
        :returns: Statistics dictionary
        """
        if not events:
            return {}

        stats = {
            'total_events': len(events),
            'total_fatalities': sum(int(e.get('fatalities', 0)) for e in events),
            'by_event_type': {},
            'by_admin1': {},
            'by_actor': {},
            'date_range': {
                'start': min(e.get('event_date', '') for e in events),
                'end': max(e.get('event_date', '') for e in events)
            }
        }

        # Count by event type
        for event in events:
            event_type = event.get('event_type', 'Unknown')
            if event_type not in stats['by_event_type']:
                stats['by_event_type'][event_type] = {'count': 0, 'fatalities': 0}
            stats['by_event_type'][event_type]['count'] += 1
            stats['by_event_type'][event_type]['fatalities'] += int(event.get('fatalities', 0))

        # Count by admin1
        for event in events:
            admin1 = event.get('admin1', 'Unknown')
            if admin1 not in stats['by_admin1']:
                stats['by_admin1'][admin1] = {'count': 0, 'fatalities': 0}
            stats['by_admin1'][admin1]['count'] += 1
            stats['by_admin1'][admin1]['fatalities'] += int(event.get('fatalities', 0))

        # Count by actor
        for event in events:
            for actor_field in ['actor1', 'actor2']:
                actor = event.get(actor_field, '')
                if actor:
                    if actor not in stats['by_actor']:
                        stats['by_actor'][actor] = 0
                    stats['by_actor'][actor] += 1

        return stats

    def get_sudan_admin1_regions(self):
        """Get list of Sudan admin1 regions from ACLED."""
        # Sudan's 18 states
        return [
            'Blue Nile',
            'Central Darfur',
            'East Darfur',
            'Gedaref',
            'Gezira',
            'Kassala',
            'Khartoum',
            'North Darfur',
            'North Kordofan',
            'Northern',
            'Red Sea',
            'River Nile',
            'Sennar',
            'South Darfur',
            'South Kordofan',
            'West Darfur',
            'West Kordofan',
            'White Nile'
        ]
