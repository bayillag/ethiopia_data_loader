# -*- coding: utf-8 -*-
"""
Credential Manager for Sudan Data Loader.

Provides secure storage for API keys using QGIS authentication system.
"""

from qgis.core import (
    QgsApplication, QgsAuthMethodConfig,
    QgsMessageLog, Qgis, QgsSettings
)
from qgis.PyQt.QtCore import QObject, pyqtSignal


class CredentialManager(QObject):
    """Manager for secure credential storage."""

    # Service identifiers
    SERVICE_ACLED = 'sudan_loader_acled'
    SERVICE_SENTINEL = 'sudan_loader_sentinel'
    SERVICE_FIRMS = 'sudan_loader_firms'
    SERVICE_HDX = 'sudan_loader_hdx'

    # Signals
    credentials_updated = pyqtSignal(str)  # service name

    def __init__(self):
        """Initialize the credential manager."""
        super().__init__()
        self.auth_manager = QgsApplication.authManager()
        self.settings = QgsSettings()

        # Check if auth database is available
        self.auth_available = self.auth_manager.isDisabled() is False

        if not self.auth_available:
            QgsMessageLog.logMessage(
                "Authentication system not available. Credentials will be stored in settings.",
                "Sudan Data Loader",
                Qgis.Warning
            )

    def _get_config_id(self, service):
        """Get or create auth config ID for a service."""
        config_id_key = f'SudanDataLoader/auth_{service}_id'
        return self.settings.value(config_id_key, '')

    def _set_config_id(self, service, config_id):
        """Store auth config ID for a service."""
        config_id_key = f'SudanDataLoader/auth_{service}_id'
        self.settings.setValue(config_id_key, config_id)

    def store_credentials(self, service, username, password, description=''):
        """
        Store credentials securely.

        :param service: Service identifier
        :param username: Username/email
        :param password: Password/API key
        :param description: Optional description
        :returns: True if successful
        """
        if self.auth_available:
            return self._store_in_auth_manager(service, username, password, description)
        else:
            return self._store_in_settings(service, username, password)

    def _store_in_auth_manager(self, service, username, password, description):
        """Store credentials in QGIS auth manager."""
        try:
            config = QgsAuthMethodConfig()
            config.setName(f'Sudan Data Loader - {service}')
            config.setMethod('Basic')
            config.setConfig('username', username)
            config.setConfig('password', password)

            if description:
                config.setConfig('description', description)

            # Check if config already exists
            existing_id = self._get_config_id(service)
            if existing_id:
                config.setId(existing_id)
                success = self.auth_manager.updateAuthenticationConfig(config)
            else:
                success = self.auth_manager.storeAuthenticationConfig(config)
                if success:
                    self._set_config_id(service, config.id())

            if success:
                self.credentials_updated.emit(service)
                QgsMessageLog.logMessage(
                    f"Credentials stored for {service}",
                    "Sudan Data Loader",
                    Qgis.Info
                )

            return success

        except Exception as e:
            QgsMessageLog.logMessage(
                f"Failed to store credentials: {str(e)}",
                "Sudan Data Loader",
                Qgis.Critical
            )
            # Fallback to settings
            return self._store_in_settings(service, username, password)

    def _store_in_settings(self, service, username, password):
        """Store credentials in QSettings (less secure fallback)."""
        self.settings.setValue(f'SudanDataLoader/{service}_username', username)
        self.settings.setValue(f'SudanDataLoader/{service}_password', password)
        self.credentials_updated.emit(service)
        return True

    def get_credentials(self, service):
        """
        Retrieve stored credentials.

        :param service: Service identifier
        :returns: Tuple of (username, password) or (None, None)
        """
        if self.auth_available:
            creds = self._get_from_auth_manager(service)
            if creds[0] is not None:
                return creds

        return self._get_from_settings(service)

    def _get_from_auth_manager(self, service):
        """Get credentials from QGIS auth manager."""
        try:
            config_id = self._get_config_id(service)
            if not config_id:
                return (None, None)

            config = QgsAuthMethodConfig()
            if self.auth_manager.loadAuthenticationConfig(config_id, config, True):
                username = config.config('username', '')
                password = config.config('password', '')
                return (username, password) if username and password else (None, None)

        except Exception as e:
            QgsMessageLog.logMessage(
                f"Failed to retrieve credentials: {str(e)}",
                "Sudan Data Loader",
                Qgis.Warning
            )

        return (None, None)

    def _get_from_settings(self, service):
        """Get credentials from QSettings."""
        username = self.settings.value(f'SudanDataLoader/{service}_username', '')
        password = self.settings.value(f'SudanDataLoader/{service}_password', '')
        return (username, password) if username and password else (None, None)

    def has_credentials(self, service):
        """
        Check if credentials exist for a service.

        :param service: Service identifier
        :returns: True if credentials exist
        """
        username, password = self.get_credentials(service)
        return username is not None and password is not None

    def delete_credentials(self, service):
        """
        Delete stored credentials.

        :param service: Service identifier
        :returns: True if successful
        """
        success = True

        # Try auth manager
        if self.auth_available:
            config_id = self._get_config_id(service)
            if config_id:
                success = self.auth_manager.removeAuthenticationConfig(config_id)
                if success:
                    self._set_config_id(service, '')

        # Also clear from settings
        self.settings.remove(f'SudanDataLoader/{service}_username')
        self.settings.remove(f'SudanDataLoader/{service}_password')

        self.credentials_updated.emit(service)
        return success

    def get_all_services(self):
        """Get list of all service identifiers."""
        return [
            self.SERVICE_ACLED,
            self.SERVICE_SENTINEL,
            self.SERVICE_FIRMS,
            self.SERVICE_HDX
        ]

    def get_service_info(self, service):
        """
        Get information about a service.

        :param service: Service identifier
        :returns: Dictionary with service info
        """
        info = {
            self.SERVICE_ACLED: {
                'name': 'ACLED',
                'full_name': 'Armed Conflict Location & Event Data',
                'fields': ['Email', 'API Key'],
                'url': 'https://acleddata.com/register/'
            },
            self.SERVICE_SENTINEL: {
                'name': 'Sentinel Hub',
                'full_name': 'Copernicus Sentinel Hub',
                'fields': ['Client ID', 'Client Secret'],
                'url': 'https://www.sentinel-hub.com/'
            },
            self.SERVICE_FIRMS: {
                'name': 'NASA FIRMS',
                'full_name': 'Fire Information for Resource Management',
                'fields': ['Email', 'API Key'],
                'url': 'https://firms.modaps.eosdis.nasa.gov/api/area/'
            },
            self.SERVICE_HDX: {
                'name': 'HDX',
                'full_name': 'Humanitarian Data Exchange',
                'fields': ['Username', 'API Key'],
                'url': 'https://data.humdata.org/'
            }
        }
        return info.get(service, {'name': service, 'fields': ['Username', 'Password']})


# Global credential manager instance
_credential_manager = None


def get_credential_manager():
    """Get the global credential manager instance."""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager
