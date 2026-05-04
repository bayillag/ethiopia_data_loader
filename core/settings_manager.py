# -*- coding: utf-8 -*-
"""
Settings Manager for Ethiopia Data Loader.

Handles all plugin settings using QSettings for persistence.
"""

from qgis.PyQt.QtCore import QSettings


class SettingsManager:
    """Manages plugin settings with QSettings persistence."""

    SETTINGS_PREFIX = "SudanDataLoader"

    # Default settings
    DEFAULTS = {
        'server_url': 'https://raw.githubusercontent.com/bayillag/ethiopia_data_loader/master',
        'auto_update_check': True,
        'default_layers': ['admin0', 'admin1', 'admin2'],
        'remember_layer_selection': True,
        'last_layer_selection': [],
        'default_style_preset': 'default',
        'show_data_info_panel': False,
        'show_search_panel': False,
        'show_bookmarks_panel': False,
        'show_statistics_panel': False,
        'custom_bookmarks': [],
        'last_export_format': 'GeoPackage',
        'last_export_path': '',
        'sketching_layer_name': 'Sudan Sketches',
        'label_language': 'english',  # 'english', 'arabic', 'both'
        # ACLED API credentials
        'acled_api_key': '',
        'acled_email': '',
    }

    def __init__(self):
        """Initialize the settings manager."""
        self.settings = QSettings()

    def _key(self, name):
        """Get the full settings key."""
        return f"{self.SETTINGS_PREFIX}/{name}"

    def get(self, name, default=None):
        """
        Get a setting value.

        :param name: Setting name
        :param default: Default value if not set
        :returns: Setting value
        """
        if default is None:
            default = self.DEFAULTS.get(name)
        value = self.settings.value(self._key(name), default)

        # Handle boolean conversion (QSettings stores as strings)
        if isinstance(default, bool) and isinstance(value, str):
            return value.lower() == 'true'

        return value

    def set(self, name, value):
        """
        Set a setting value.

        :param name: Setting name
        :param value: Value to set
        """
        self.settings.setValue(self._key(name), value)

    def get_server_url(self):
        """Get the configured server URL."""
        return self.get('server_url')

    def set_server_url(self, url):
        """Set the server URL."""
        self.set('server_url', url)

    def get_auto_update_check(self):
        """Get whether to auto-check for updates."""
        return self.get('auto_update_check')

    def set_auto_update_check(self, enabled):
        """Set auto-update check preference."""
        self.set('auto_update_check', enabled)

    def get_default_layers(self):
        """Get list of default layers to load."""
        value = self.get('default_layers')
        if isinstance(value, str):
            return value.split(',') if value else []
        return value if value else []

    def set_default_layers(self, layers):
        """Set default layers to load."""
        if isinstance(layers, list):
            self.set('default_layers', ','.join(layers))
        else:
            self.set('default_layers', layers)

    def get_remember_layer_selection(self):
        """Get whether to remember layer selection."""
        return self.get('remember_layer_selection')

    def set_remember_layer_selection(self, enabled):
        """Set remember layer selection preference."""
        self.set('remember_layer_selection', enabled)

    def get_last_layer_selection(self):
        """Get the last layer selection."""
        value = self.get('last_layer_selection')
        if isinstance(value, str):
            return value.split(',') if value else []
        return value if value else []

    def set_last_layer_selection(self, layers):
        """Set last layer selection."""
        if isinstance(layers, list):
            self.set('last_layer_selection', ','.join(layers))
        else:
            self.set('last_layer_selection', layers)

    def get_style_preset(self):
        """Get the current style preset."""
        return self.get('default_style_preset')

    def set_style_preset(self, preset):
        """Set the style preset."""
        self.set('default_style_preset', preset)

    def get_panel_visibility(self, panel_name):
        """Get visibility of a dock panel."""
        return self.get(f'show_{panel_name}_panel')

    def set_panel_visibility(self, panel_name, visible):
        """Set visibility of a dock panel."""
        self.set(f'show_{panel_name}_panel', visible)

    def get_custom_bookmarks(self):
        """Get custom bookmarks list."""
        value = self.get('custom_bookmarks')
        if isinstance(value, str):
            import json
            try:
                return json.loads(value) if value else []
            except (json.JSONDecodeError, ValueError, TypeError):
                return []
        return value if value else []

    def set_custom_bookmarks(self, bookmarks):
        """Set custom bookmarks list."""
        import json
        if isinstance(bookmarks, list):
            self.set('custom_bookmarks', json.dumps(bookmarks))
        else:
            self.set('custom_bookmarks', bookmarks)

    def get_label_language(self):
        """Get the label language preference."""
        return self.get('label_language')

    def set_label_language(self, language):
        """Set the label language preference."""
        self.set('label_language', language)

    def get_last_export_format(self):
        """Get the last used export format."""
        return self.get('last_export_format')

    def set_last_export_format(self, format_name):
        """Set the last used export format."""
        self.set('last_export_format', format_name)

    def get_last_export_path(self):
        """Get the last used export path."""
        return self.get('last_export_path')

    def set_last_export_path(self, path):
        """Set the last used export path."""
        self.set('last_export_path', path)

    def get_acled_api_key(self):
        """Get the ACLED API key."""
        return self.get('acled_api_key')

    def set_acled_api_key(self, api_key):
        """Set the ACLED API key."""
        self.set('acled_api_key', api_key)

    def get_acled_email(self):
        """Get the ACLED email."""
        return self.get('acled_email')

    def set_acled_email(self, email):
        """Set the ACLED email."""
        self.set('acled_email', email)

    def get_acled_credentials(self):
        """Get ACLED API credentials as tuple (api_key, email)."""
        return (self.get_acled_api_key(), self.get_acled_email())

    def has_acled_credentials(self):
        """Check if ACLED credentials are configured."""
        api_key = self.get_acled_api_key()
        email = self.get_acled_email()
        return bool(api_key and email)

    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        for name, value in self.DEFAULTS.items():
            self.set(name, value)
