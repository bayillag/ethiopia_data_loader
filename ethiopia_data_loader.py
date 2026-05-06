# -*- coding: utf-8 -*-
"""
Ethiopia Data Loader - Main Plugin Class (v1.0)

A comprehensive QGIS plugin for loading, visualizing, and analyzing
Ethiopia administrative boundary data with AI features, modern dashboard,
and research tools.

Features:
- Load administrative boundaries with automatic styling
- Download/update data from GitHub releases
- Quick labeling tools (English, Arabic, P-Codes)
- Style preset switcher (Default, Satellite, Grayscale, Humanitarian)
- Search and filter by admin name
- Quick navigation bookmarks for all 18 states
- Statistics panel with area calculations
- Basemap integration (OSM, Satellite, Humanitarian)
- Report generation (PDF/HTML)
- Export features to multiple formats
- Sketching/drawing tools
- Processing tools (Clip, Buffer, Dissolve)
- Data validation checker
- HDX Humanitarian Data integration
- ACLED Conflict Data integration

v1.0 New Features:
- OpenStreetMap/Overpass API integration
- Sentinel Hub satellite imagery
- World Bank development indicators
- NASA FIRMS fire data
- IOM displacement tracking
- Modern dashboard with KPI cards
- Interactive charts panel
- Dark mode support
- AI-powered natural language query
- Smart report generation
- Anomaly detection
- Predictive analytics
- Research tools (citations, provenance, statistics)
- Publication export
"""

import os
import json
import zipfile
import hashlib
import tempfile
from qgis.PyQt.QtWidgets import (
    QAction, QMessageBox, QProgressDialog, QMenu
)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QStandardPaths, QUrl, QEventLoop, Qt
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsNetworkAccessManager,
    QgsBlockingNetworkRequest, QgsApplication
)
from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply

# Import core modules
from .core.settings_manager import SettingsManager
from .core.data_manager import DataManager
from .core.labeling_utils import LabelingUtils
from .core.style_manager import StyleManager

# Import new v3.0 core modules
from .core.theme_manager import ThemeManager
from .core.notification_manager import NotificationManager
from .core.credential_manager import CredentialManager
from .core.layer_tree_integration import LayerTreeIntegration
from .core import expression_functions

# Import dialogs
from .dialogs.settings_dialog import SettingsDialog
from .dialogs.layer_selection_dialog import LayerSelectionDialog
from .dialogs.query_builder_dialog import QueryBuilderDialog
from .dialogs.export_dialog import ExportDialog
from .dialogs.welcome_wizard import WelcomeWizard

# Import widgets
from .widgets.data_info_panel import DataInfoPanel
from .widgets.search_panel import SearchPanel
from .widgets.bookmarks_panel import BookmarksPanel
from .widgets.statistics_panel import StatisticsPanel

# Import new v3.0 widgets
from .widgets.dashboard_panel import DashboardPanel
from .widgets.charts_panel import ChartsPanel
from .widgets.advanced_search_panel import AdvancedSearchPanel

# Import tools
from .tools.sketching_tools import SketchingToolbar

# Import processing
from .processing.sudan_processing_tools import ProcessingDialog
from .processing.sudan_provider import SudanProcessingProvider

# Import reports
from .reports.report_generator import ReportDialog

# Import validation
from .validation.data_validator import ValidationDialog

# Import HDX integration
from .hdx.hdx_browser import HDXBrowserDialog

# Import ACLED integration
from .acled.acled_browser import ACLEDBrowserDialog

# Import new v3.0 data sources
from .osm.osm_browser import OSMBrowserDialog
from .satellite.sentinel_browser import SentinelBrowserDialog
from .worldbank.wb_browser import WorldBankBrowserDialog
from .firms.firms_browser import FIRMSBrowserDialog
from .iom.iom_browser import IOMBrowserDialog

# Import AI features
from .ai.nl_query import NLQueryDialog

# Import research tools
from .research.citation_generator import CitationGenerator
from .research.statistics import SpatialStatistics
from .research.publication_export import PublicationExporter


class EthiopiaDataLoader:
    """QGIS Plugin for loading and managing Ethiopia administrative boundary data."""

    def __init__(self, iface):
        """
        Initialize the plugin.

        :param iface: A QGIS interface instance.
        :type iface: QgsInterface
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        # Initialize ALL attributes first (before any complex initialization)
        # This ensures unload() can safely check these attributes even if initGui fails
        self.toolbar = None
        self.menu = None
        self.actions = {}
        self.data_info_panel = None
        self.search_panel = None
        self.bookmarks_panel = None
        self.statistics_panel = None
        self.sketching_toolbar = None
        self.data_dir = None
        self.styles_dir = None
        self.settings_manager = None
        self.data_manager = None
        self.style_manager = None

        # New v1.0 attributes
        self.dashboard_panel = None
        self.charts_panel = None
        self.advanced_search_panel = None
        self.theme_manager = None
        self.notification_manager = None
        self.credential_manager = None
        self.layer_tree_integration = None
        self.processing_provider = None

        # Initialize managers
        self.settings_manager = SettingsManager()
        self.data_manager = DataManager(None, None)
        self.style_manager = StyleManager(self.plugin_dir)

        # Initialize new v1.0 managers
        self.theme_manager = ThemeManager()
        self.notification_manager = NotificationManager(iface)
        self.credential_manager = CredentialManager()

        # Bundled data directories (fallback)
        self.bundled_data_dir = os.path.join(self.plugin_dir, 'Data')
        self.bundled_styles_dir = os.path.join(self.plugin_dir, 'styles')

        # Cache directories (user-writable location for downloaded data)
        self.VERSION_URL = "https://raw.githubusercontent.com/Osman-Geomatics93/sudan_data_loader/master/version.json"
        self.cache_dir = os.path.join(
            QStandardPaths.writableLocation(QStandardPaths.AppDataLocation),
            'sudan_data_loader'
        )
        self.cache_data_dir = os.path.join(self.cache_dir, 'Data')
        self.cache_styles_dir = os.path.join(self.cache_dir, 'styles')
        self.local_version_file = os.path.join(self.cache_dir, 'version.json')

        # Define layers configuration
        self.layers_config = [
            {'gpkg': 'admin0.gpkg', 'style': 'admin0.qml', 'name': 'Sudan Admin 0 - Country', 'id': 'admin0'},
            {'gpkg': 'admin1.gpkg', 'style': 'admin1.qml', 'name': 'Sudan Admin 1 - States', 'id': 'admin1'},
            {'gpkg': 'admin2.gpkg', 'style': 'admin2.qml', 'name': 'Sudan Admin 2 - Localities', 'id': 'admin2'},
            {'gpkg': 'admin_lines.gpkg', 'style': None, 'name': 'Sudan Admin Lines', 'id': 'admin_lines'},
            {'gpkg': 'admin_points.gpkg', 'style': None, 'name': 'Sudan Admin Points', 'id': 'admin_points'},
        ]

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        # Create main menu
        self.menu = QMenu('&Sudan Data Loader')
        self.iface.mainWindow().menuBar().addMenu(self.menu)

        # === Data Loading Section ===
        self._create_action('load_data', 'Load Sudan Data...', self.show_layer_selection)
        self._create_action('load_all', 'Load All Layers', self.load_all_layers)
        self._create_action('download_update', 'Download/Update Data', self.download_update)
        self.menu.addSeparator()

        # === Labels Submenu ===
        labels_menu = QMenu('Quick Labels', self.menu)

        self._create_action('label_state_en', 'State Names (English)',
                           lambda: LabelingUtils.apply_state_labels('english'), labels_menu)
        self._create_action('label_state_ar', 'State Names (Arabic)',
                           lambda: LabelingUtils.apply_state_labels('arabic'), labels_menu)
        self._create_action('label_state_both', 'State Names (Both)',
                           lambda: LabelingUtils.apply_state_labels('both'), labels_menu)
        self._create_action('label_state_pcode', 'State P-Codes',
                           lambda: LabelingUtils.apply_state_labels('pcode'), labels_menu)
        labels_menu.addSeparator()
        self._create_action('label_locality_en', 'Locality Names (English)',
                           lambda: LabelingUtils.apply_locality_labels('english'), labels_menu)
        self._create_action('label_locality_ar', 'Locality Names (Arabic)',
                           lambda: LabelingUtils.apply_locality_labels('arabic'), labels_menu)
        labels_menu.addSeparator()
        self._create_action('label_remove', 'Remove All Labels',
                           LabelingUtils.remove_all_labels, labels_menu)

        self.menu.addMenu(labels_menu)

        # === Style Presets Submenu ===
        styles_menu = QMenu('Style Presets', self.menu)

        self._create_action('style_default', 'Default',
                           lambda: self.style_manager.apply_preset('default'), styles_menu)
        self._create_action('style_satellite', 'Satellite-Friendly',
                           lambda: self.style_manager.apply_preset('satellite'), styles_menu)
        self._create_action('style_grayscale', 'Grayscale',
                           lambda: self.style_manager.apply_preset('grayscale'), styles_menu)
        self._create_action('style_humanitarian', 'Humanitarian',
                           lambda: self.style_manager.apply_preset('humanitarian'), styles_menu)

        self.menu.addMenu(styles_menu)

        # === Basemaps Submenu ===
        basemaps_menu = QMenu('Basemaps', self.menu)

        self._create_action('basemap_osm', 'OpenStreetMap',
                           lambda: self.style_manager.add_basemap('osm_standard'), basemaps_menu)
        self._create_action('basemap_humanitarian', 'Humanitarian OSM',
                           lambda: self.style_manager.add_basemap('osm_humanitarian'), basemaps_menu)
        self._create_action('basemap_satellite', 'ESRI Satellite',
                           lambda: self.style_manager.add_basemap('esri_satellite'), basemaps_menu)
        self._create_action('basemap_topo', 'ESRI Topographic',
                           lambda: self.style_manager.add_basemap('esri_topo'), basemaps_menu)
        self._create_action('basemap_carto_light', 'CartoDB Light',
                           lambda: self.style_manager.add_basemap('carto_light'), basemaps_menu)
        self._create_action('basemap_carto_dark', 'CartoDB Dark',
                           lambda: self.style_manager.add_basemap('carto_dark'), basemaps_menu)
        basemaps_menu.addSeparator()
        self._create_action('basemap_remove', 'Remove All Basemaps',
                           self.style_manager.remove_all_basemaps, basemaps_menu)

        self.menu.addMenu(basemaps_menu)
        self.menu.addSeparator()

        # === Panels Section ===
        panels_menu = QMenu('Panels', self.menu)

        self._create_action('panel_dashboard', 'Dashboard Panel', self.toggle_dashboard_panel, panels_menu)
        self._create_action('panel_charts', 'Charts Panel', self.toggle_charts_panel, panels_menu)
        self._create_action('panel_info', 'Data Info Panel', self.toggle_data_info_panel, panels_menu)
        self._create_action('panel_search', 'Search Panel', self.toggle_search_panel, panels_menu)
        self._create_action('panel_advanced_search', 'Advanced Search Panel', self.toggle_advanced_search_panel, panels_menu)
        self._create_action('panel_bookmarks', 'Bookmarks Panel', self.toggle_bookmarks_panel, panels_menu)
        self._create_action('panel_statistics', 'Statistics Panel', self.toggle_statistics_panel, panels_menu)

        self.menu.addMenu(panels_menu)
        self.menu.addSeparator()

        # === Analysis Tools Section ===
        analysis_menu = QMenu('Analysis Tools', self.menu)

        self._create_action('query_builder', 'Query Builder...', self.show_query_builder, analysis_menu)
        self._create_action('processing', 'Processing Tools...', self.show_processing_dialog, analysis_menu)
        self._create_action('ai_query', 'AI Natural Language Query...', self.show_ai_query_dialog, analysis_menu)
        analysis_menu.addSeparator()
        self._create_action('spatial_stats', 'Spatial Statistics...', self.show_spatial_statistics, analysis_menu)

        self.menu.addMenu(analysis_menu)

        # === Reports & Export ===
        reports_menu = QMenu('Reports && Export', self.menu)

        self._create_action('report', 'Generate Report...', self.show_report_dialog, reports_menu)
        self._create_action('export', 'Export Features...', self.show_export_dialog, reports_menu)
        reports_menu.addSeparator()
        self._create_action('publication_export', 'Publication Export...', self.show_publication_export, reports_menu)
        self._create_action('citation_gen', 'Generate Citations...', self.show_citation_generator, reports_menu)

        self.menu.addMenu(reports_menu)

        # === Data Validation ===
        self._create_action('validate', 'Data Validation...', self.show_validation_dialog)
        self._create_action('sketching', 'Sketching Toolbar', self.toggle_sketching_toolbar)
        self.menu.addSeparator()

        # === External Data Sources ===
        external_data_menu = QMenu('External Data Sources', self.menu)

        self._create_action('hdx_browser', 'HDX Humanitarian Data...',
                           self.show_hdx_browser, external_data_menu)
        self._create_action('acled_browser', 'ACLED Conflict Data...',
                           self.show_acled_browser, external_data_menu)
        external_data_menu.addSeparator()
        self._create_action('osm_browser', 'OpenStreetMap Data...',
                           self.show_osm_browser, external_data_menu)
        self._create_action('sentinel_browser', 'Sentinel Satellite Imagery...',
                           self.show_sentinel_browser, external_data_menu)
        self._create_action('worldbank_browser', 'World Bank Indicators...',
                           self.show_worldbank_browser, external_data_menu)
        self._create_action('firms_browser', 'NASA FIRMS Fire Data...',
                           self.show_firms_browser, external_data_menu)
        self._create_action('iom_browser', 'IOM Displacement Data...',
                           self.show_iom_browser, external_data_menu)

        self.menu.addMenu(external_data_menu)
        self.menu.addSeparator()

        # === Help & Settings ===
        self._create_action('welcome_wizard', 'Welcome Wizard...', self.show_welcome_wizard)
        self._create_action('toggle_dark_mode', 'Toggle Dark Mode', self.toggle_dark_mode)
        self._create_action('settings', 'Settings...', self.show_settings)

        # Create toolbar
        self.toolbar = self.iface.addToolBar('Sudan Data Loader')
        self.toolbar.setObjectName('SudanDataLoaderToolbar')

        # Add main actions to toolbar
        self.toolbar.addAction(self.actions['load_data'])
        self.toolbar.addAction(self.actions['download_update'])
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.actions['panel_dashboard'])
        self.toolbar.addAction(self.actions['panel_search'])
        self.toolbar.addAction(self.actions['panel_bookmarks'])
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.actions['ai_query'])

        # Initialize dock widgets (hidden by default)
        self._init_dock_widgets()

        # Initialize sketching toolbar (hidden by default)
        self.sketching_toolbar = SketchingToolbar(self.iface)

        # Register Processing Provider
        self.processing_provider = SudanProcessingProvider()
        QgsApplication.processingRegistry().addProvider(self.processing_provider)

        # Register custom expression functions
        expression_functions.register_functions()

        # Initialize layer tree integration
        self.layer_tree_integration = LayerTreeIntegration(self.iface)

        # Show welcome wizard on first run (use QTimer to show after QGIS fully loads)
        from qgis.PyQt.QtCore import QTimer
        QTimer.singleShot(1000, self._check_first_run)

    def _check_first_run(self):
        """Check if this is first run and show welcome wizard."""
        if WelcomeWizard.should_show(self.settings_manager):
            self.show_welcome_wizard()

    def _create_action(self, name, text, callback, parent=None):
        """Create and register an action."""
        action = QAction(text, self.iface.mainWindow())
        action.triggered.connect(callback)

        if parent is None:
            self.menu.addAction(action)
        else:
            parent.addAction(action)

        self.actions[name] = action
        return action

    def _init_dock_widgets(self):
        """Initialize dock widgets."""
        # Dashboard Panel (new in v3.0)
        self.dashboard_panel = DashboardPanel(self.iface, self.iface.mainWindow())
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dashboard_panel)
        self.dashboard_panel.hide()

        # Charts Panel (new in v3.0)
        self.charts_panel = ChartsPanel(self.iface, self.iface.mainWindow())
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.charts_panel)
        self.charts_panel.hide()

        # Data Info Panel
        self.data_info_panel = DataInfoPanel(self.iface.mainWindow())
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.data_info_panel)
        self.data_info_panel.hide()

        # Search Panel
        self.search_panel = SearchPanel(self.iface, self.iface.mainWindow())
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.search_panel)
        self.search_panel.hide()

        # Advanced Search Panel (new in v3.0)
        self.advanced_search_panel = AdvancedSearchPanel(self.iface, self.settings_manager, self.iface.mainWindow())
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.advanced_search_panel)
        self.advanced_search_panel.hide()

        # Bookmarks Panel
        self.bookmarks_panel = BookmarksPanel(self.iface, self.settings_manager, self.iface.mainWindow())
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.bookmarks_panel)
        self.bookmarks_panel.hide()

        # Statistics Panel
        self.statistics_panel = StatisticsPanel(self.iface, self.iface.mainWindow())
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.statistics_panel)
        self.statistics_panel.hide()

    def unload(self):
        """Remove the plugin menu items and icons from QGIS GUI."""
        # Unregister Processing Provider
        processing_provider = getattr(self, 'processing_provider', None)
        if processing_provider:
            try:
                QgsApplication.processingRegistry().removeProvider(processing_provider)
            except Exception:
                pass

        # Unregister custom expression functions
        try:
            expression_functions.unregister_functions()
        except Exception:
            pass

        # Remove layer tree integration
        layer_tree_integration = getattr(self, 'layer_tree_integration', None)
        if layer_tree_integration:
            try:
                layer_tree_integration.unregister()
            except Exception:
                pass

        # Remove menu (use getattr for safety)
        menu = getattr(self, 'menu', None)
        if menu:
            try:
                self.iface.mainWindow().menuBar().removeAction(menu.menuAction())
            except Exception:
                pass

        # Remove toolbar
        toolbar = getattr(self, 'toolbar', None)
        if toolbar:
            try:
                del self.toolbar
            except Exception:
                pass

        # Remove dock widgets
        dashboard_panel = getattr(self, 'dashboard_panel', None)
        if dashboard_panel:
            try:
                self.iface.removeDockWidget(dashboard_panel)
            except Exception:
                pass

        charts_panel = getattr(self, 'charts_panel', None)
        if charts_panel:
            try:
                self.iface.removeDockWidget(charts_panel)
            except Exception:
                pass

        data_info_panel = getattr(self, 'data_info_panel', None)
        if data_info_panel:
            try:
                self.iface.removeDockWidget(data_info_panel)
            except Exception:
                pass

        search_panel = getattr(self, 'search_panel', None)
        if search_panel:
            try:
                self.iface.removeDockWidget(search_panel)
            except Exception:
                pass

        advanced_search_panel = getattr(self, 'advanced_search_panel', None)
        if advanced_search_panel:
            try:
                self.iface.removeDockWidget(advanced_search_panel)
            except Exception:
                pass

        bookmarks_panel = getattr(self, 'bookmarks_panel', None)
        if bookmarks_panel:
            try:
                self.iface.removeDockWidget(bookmarks_panel)
            except Exception:
                pass

        statistics_panel = getattr(self, 'statistics_panel', None)
        if statistics_panel:
            try:
                self.iface.removeDockWidget(statistics_panel)
            except Exception:
                pass

        # Remove sketching toolbar
        sketching_toolbar = getattr(self, 'sketching_toolbar', None)
        if sketching_toolbar:
            try:
                sketching_toolbar.remove_toolbar()
            except Exception:
                pass

    # ============ Panel Toggles ============

    def toggle_dashboard_panel(self):
        """Toggle the dashboard panel visibility."""
        if self.dashboard_panel.isVisible():
            self.dashboard_panel.hide()
        else:
            self.dashboard_panel.show()
            self.dashboard_panel.refresh_data()

    def toggle_charts_panel(self):
        """Toggle the charts panel visibility."""
        if self.charts_panel.isVisible():
            self.charts_panel.hide()
        else:
            self.charts_panel.show()

    def toggle_data_info_panel(self):
        """Toggle the data info panel visibility."""
        if self.data_info_panel.isVisible():
            self.data_info_panel.hide()
        else:
            self.data_info_panel.show()
            self.data_info_panel.refresh_info()

    def toggle_search_panel(self):
        """Toggle the search panel visibility."""
        if self.search_panel.isVisible():
            self.search_panel.hide()
        else:
            self.search_panel.show()

    def toggle_advanced_search_panel(self):
        """Toggle the advanced search panel visibility."""
        if self.advanced_search_panel.isVisible():
            self.advanced_search_panel.hide()
        else:
            self.advanced_search_panel.show()

    def toggle_bookmarks_panel(self):
        """Toggle the bookmarks panel visibility."""
        if self.bookmarks_panel.isVisible():
            self.bookmarks_panel.hide()
        else:
            self.bookmarks_panel.show()

    def toggle_statistics_panel(self):
        """Toggle the statistics panel visibility."""
        if self.statistics_panel.isVisible():
            self.statistics_panel.hide()
        else:
            self.statistics_panel.show()

    def toggle_sketching_toolbar(self):
        """Toggle the sketching toolbar."""
        if self.sketching_toolbar.sketching_toolbar:
            self.sketching_toolbar.remove_toolbar()
        else:
            self.sketching_toolbar.setup_toolbar()

    def toggle_dark_mode(self):
        """Toggle dark mode."""
        is_dark = self.theme_manager.toggle_dark_mode()
        mode = "Dark" if is_dark else "Light"
        self.notification_manager.show_notification(
            f"{mode} mode enabled",
            "info"
        )

    # ============ Dialog Methods ============

    def show_settings(self):
        """Show the settings dialog."""
        dialog = SettingsDialog(self.settings_manager, self.iface.mainWindow())
        dialog.exec_()

    def show_welcome_wizard(self):
        """Show the welcome wizard."""
        wizard = WelcomeWizard(self, self.iface.mainWindow())
        wizard.exec_()

    def show_layer_selection(self):
        """Show the layer selection dialog."""
        dialog = LayerSelectionDialog(self.settings_manager, self.iface.mainWindow())
        if dialog.exec_():
            selected_layers = dialog.get_selected_layers()
            if selected_layers:
                self.load_selected_layers(selected_layers)

    def show_query_builder(self):
        """Show the query builder dialog."""
        dialog = QueryBuilderDialog(self.iface.mainWindow())
        dialog.exec_()

    def show_export_dialog(self):
        """Show the export dialog."""
        dialog = ExportDialog(self.settings_manager, self.iface.mainWindow())
        dialog.exec_()

    def show_processing_dialog(self):
        """Show the processing tools dialog."""
        dialog = ProcessingDialog(self.iface, self.iface.mainWindow())
        dialog.exec_()

    def show_report_dialog(self):
        """Show the report generation dialog."""
        dialog = ReportDialog(self.iface, self.iface.mainWindow())
        dialog.exec_()

    def show_validation_dialog(self):
        """Show the data validation dialog."""
        dialog = ValidationDialog(self.iface, self.iface.mainWindow())
        dialog.exec_()

    def show_hdx_browser(self):
        """Show the HDX humanitarian data browser dialog."""
        dialog = HDXBrowserDialog(self.iface, self.iface.mainWindow())
        dialog.exec_()

        # Add any pending layers after dialog closes (prevents QGIS crash)
        pending = dialog.get_pending_layers()
        if pending:
            added = []
            failed = []
            for layer_info in pending:
                success, result = dialog.add_layer_to_map(
                    layer_info['file_path'],
                    layer_info['resource']
                )
                if success:
                    added.append(result)
                else:
                    failed.append(result)

            # Show summary
            if added:
                self.iface.mapCanvas().refresh()
                msg = f"Added {len(added)} layer(s) to the map:\n"
                msg += "\n".join(f"  - {name}" for name in added)
                if failed:
                    msg += f"\n\nFailed to add {len(failed)} layer(s)."
                QMessageBox.information(self.iface.mainWindow(), 'HDX Layers Added', msg)
            elif failed:
                QMessageBox.warning(
                    self.iface.mainWindow(),
                    'Layer Load Failed',
                    f"Failed to load {len(failed)} layer(s):\n" + "\n".join(failed)
                )

    def show_acled_browser(self):
        """Show the ACLED conflict data browser dialog."""
        dialog = ACLEDBrowserDialog(self.iface, self.settings_manager, self.iface.mainWindow())
        dialog.exec_()

        # Add any pending layers after dialog closes (prevents QGIS crash)
        pending = dialog.get_pending_layers()
        if pending:
            added = []
            failed = []
            for layer_info in pending:
                success, result = dialog.add_layer_to_map(
                    layer_info['geojson'],
                    layer_info['layer_name'],
                    layer_info['style_events']
                )
                if success:
                    added.append(result)
                else:
                    failed.append(result)

            # Show summary
            if added:
                self.iface.mapCanvas().refresh()
                msg = f"Added {len(added)} conflict data layer(s) to the map:\n"
                msg += "\n".join(f"  - {name}" for name in added)
                if failed:
                    msg += f"\n\nFailed to add {len(failed)} layer(s)."
                QMessageBox.information(self.iface.mainWindow(), 'ACLED Layers Added', msg)
            elif failed:
                QMessageBox.warning(
                    self.iface.mainWindow(),
                    'Layer Load Failed',
                    f"Failed to load {len(failed)} layer(s):\n" + "\n".join(failed)
                )

    # ============ New v3.0 Data Source Dialogs ============

    def show_osm_browser(self):
        """Show the OpenStreetMap data browser dialog."""
        dialog = OSMBrowserDialog(self.iface, self.iface.mainWindow())
        dialog.exec_()

        # Add any pending layers after dialog closes
        pending = dialog.get_pending_layers()
        if pending:
            added = []
            failed = []
            for layer_info in pending:
                success, result = dialog.add_layer_to_map(
                    layer_info['file_path'],
                    layer_info['layer_name'],
                    layer_info['layer_type'],
                    layer_info['category']
                )
                if success:
                    added.append(result)
                else:
                    failed.append(result)

            # Show summary
            if added:
                self.iface.messageBar().pushMessage(
                    'OSM Data',
                    f'Added {len(added)} layer(s): {", ".join(added)}',
                    level=0, duration=5
                )
            if failed:
                self.iface.messageBar().pushMessage(
                    'OSM Data',
                    f'Failed to add: {", ".join(failed)}',
                    level=1, duration=5
                )

            # Zoom to last added layer
            if added:
                layers = QgsProject.instance().mapLayersByName(added[-1])
                if layers:
                    self.iface.mapCanvas().setExtent(layers[0].extent())
                    self.iface.mapCanvas().refresh()

    def show_sentinel_browser(self):
        """Show the Sentinel satellite imagery browser dialog."""
        dialog = SentinelBrowserDialog(self.iface, self.credential_manager, self.iface.mainWindow())
        dialog.exec_()

    def show_worldbank_browser(self):
        """Show the World Bank indicators browser dialog."""
        dialog = WorldBankBrowserDialog(self.iface, self.iface.mainWindow())
        dialog.exec_()

    def show_firms_browser(self):
        """Show the NASA FIRMS fire data browser dialog."""
        dialog = FIRMSBrowserDialog(self.iface, self.credential_manager, self.iface.mainWindow())
        dialog.exec_()

    def show_iom_browser(self):
        """Show the IOM displacement data browser dialog."""
        dialog = IOMBrowserDialog(self.iface, self.iface.mainWindow())
        dialog.exec_()

    # ============ New v3.0 Analysis Dialogs ============

    def show_ai_query_dialog(self):
        """Show the AI natural language query dialog."""
        dialog = NLQueryDialog(self.iface, self.iface.mainWindow())
        dialog.exec_()

    def show_spatial_statistics(self):
        """Show spatial statistics options."""
        from qgis.PyQt.QtWidgets import QInputDialog
        layer = self.iface.activeLayer()
        if not layer:
            QMessageBox.warning(
                self.iface.mainWindow(),
                'No Layer Selected',
                'Please select a layer to analyze.'
            )
            return

        # Get numeric fields
        numeric_fields = [f.name() for f in layer.fields()
                        if f.type() in [2, 4, 6]]  # Int, Double, LongLong

        if not numeric_fields:
            QMessageBox.warning(
                self.iface.mainWindow(),
                'No Numeric Fields',
                'The selected layer has no numeric fields for analysis.'
            )
            return

        field, ok = QInputDialog.getItem(
            self.iface.mainWindow(),
            'Select Field',
            'Choose a field for spatial statistics:',
            numeric_fields, 0, False
        )

        if ok and field:
            stats = SpatialStatistics()
            result = stats.calculate_morans_i(layer, field)

            if 'error' in result:
                QMessageBox.warning(
                    self.iface.mainWindow(),
                    'Analysis Error',
                    result['error']
                )
            else:
                msg = f"Moran's I Spatial Autocorrelation\n"
                msg += f"=" * 40 + "\n\n"
                msg += f"Field: {field}\n"
                msg += f"Features: {result['n_features']}\n\n"
                msg += f"Moran's I: {result['morans_i']:.4f}\n"
                msg += f"Expected I: {result['expected_i']:.4f}\n"
                msg += f"Z-Score: {result['z_score']:.4f}\n"
                msg += f"P-Value: {result['p_value']:.4f}\n\n"
                msg += f"Result: {result['interpretation']}"

                QMessageBox.information(
                    self.iface.mainWindow(),
                    'Spatial Statistics Results',
                    msg
                )

    # ============ New v3.0 Research Dialogs ============

    def show_publication_export(self):
        """Show publication export options."""
        from qgis.PyQt.QtWidgets import QInputDialog, QFileDialog

        templates = ['nature', 'plos_one', 'elsevier', 'springer', 'mdpi', 'thesis', 'poster']
        template, ok = QInputDialog.getItem(
            self.iface.mainWindow(),
            'Select Template',
            'Choose a publication template:',
            templates, 0, False
        )

        if ok:
            output_path, _ = QFileDialog.getSaveFileName(
                self.iface.mainWindow(),
                'Export Map',
                '',
                'PNG (*.png);;PDF (*.pdf);;TIFF (*.tiff);;SVG (*.svg)'
            )

            if output_path:
                exporter = PublicationExporter()
                result = exporter.export_map(
                    output_path,
                    title='Sudan Map',
                    template=template
                )

                if result.get('success'):
                    QMessageBox.information(
                        self.iface.mainWindow(),
                        'Export Complete',
                        f"Map exported successfully to:\n{result['output_path']}"
                    )
                else:
                    QMessageBox.warning(
                        self.iface.mainWindow(),
                        'Export Failed',
                        'Failed to export map. Check the console for details.'
                    )

    def show_citation_generator(self):
        """Show citation generator dialog."""
        from qgis.PyQt.QtWidgets import QInputDialog

        sources = ['hdx_admin', 'acled', 'osm', 'worldbank', 'sentinel', 'firms', 'iom_dtm']
        formats = ['apa', 'bibtex', 'chicago', 'harvard', 'mla']

        source, ok1 = QInputDialog.getItem(
            self.iface.mainWindow(),
            'Select Data Source',
            'Choose a data source to cite:',
            sources, 0, False
        )

        if ok1:
            fmt, ok2 = QInputDialog.getItem(
                self.iface.mainWindow(),
                'Select Format',
                'Choose citation format:',
                formats, 0, False
            )

            if ok2:
                generator = CitationGenerator()
                citation = generator.generate_citation(source, fmt)

                QMessageBox.information(
                    self.iface.mainWindow(),
                    'Citation Generated',
                    f"Citation ({fmt.upper()}):\n\n{citation}"
                )

    # ============ Data Loading Methods ============

    def _get_data_directories(self):
        """
        Resolve which data directories to use.

        Checks if cache directories exist and have files.
        If cache is valid, returns cache paths. Otherwise returns bundled plugin paths.

        :returns: Tuple of (data_dir, styles_dir)
        """
        # Check if cache directories exist and have data files
        cache_valid = (
            os.path.isdir(self.cache_data_dir) and
            os.path.isdir(self.cache_styles_dir) and
            any(f.endswith('.gpkg') for f in os.listdir(self.cache_data_dir)
                if os.path.isfile(os.path.join(self.cache_data_dir, f)))
        )

        if cache_valid:
            return self.cache_data_dir, self.cache_styles_dir
        else:
            return self.bundled_data_dir, self.bundled_styles_dir

    def load_all_layers(self):
        """Load all Sudan admin layers."""
        self.load_selected_layers(['admin0', 'admin1', 'admin2', 'admin_lines', 'admin_points'])

    def load_selected_layers(self, layer_ids):
        """
        Load selected layers.

        :param layer_ids: List of layer IDs to load
        """
        # Resolve which data directories to use
        self.data_dir, self.styles_dir = self._get_data_directories()
        self.data_manager.set_directories(self.data_dir, self.styles_dir)

        # Validate directories exist
        if not self._validate_directories():
            return

        # Load layers
        loaded_layers = []
        for config in self.layers_config:
            if config['id'] not in layer_ids:
                continue

            layer = self._load_gpkg_layer(config['gpkg'], config['name'])
            if layer:
                # Apply style if specified
                if config['style']:
                    self._apply_style(layer, config['style'])

                # Add layer to project
                QgsProject.instance().addMapLayer(layer)
                loaded_layers.append(layer.name())

        if loaded_layers:
            # Zoom to the extent of the first layer
            first_layer = QgsProject.instance().mapLayersByName(self.layers_config[0]['name'])
            if first_layer:
                self.iface.mapCanvas().setExtent(first_layer[0].extent())
                self.iface.mapCanvas().refresh()

            self._show_info(
                'Success',
                f'Successfully loaded {len(loaded_layers)} layers:\n\n' + '\n'.join(loaded_layers)
            )

            # Refresh data info panel if visible
            if self.data_info_panel and self.data_info_panel.isVisible():
                self.data_info_panel.refresh_info()
        else:
            self._show_warning('Warning', 'No layers were loaded.')

    def _load_gpkg_layer(self, gpkg_filename, layer_name):
        """
        Load a layer from a GeoPackage file.

        :param gpkg_filename: Name of the GeoPackage file
        :param layer_name: Display name for the layer
        :returns: QgsVectorLayer or None if loading failed
        """
        gpkg_path = os.path.join(self.data_dir, gpkg_filename)

        layer = QgsVectorLayer(gpkg_path, layer_name, 'ogr')

        if not layer.isValid():
            self._show_warning(
                'Layer Load Failed',
                f'Failed to load layer from: {gpkg_filename}\n\n'
                'The file may be corrupted or in an unsupported format.'
            )
            return None

        return layer

    def _apply_style(self, layer, style_filename):
        """
        Apply a QML style to a layer.

        :param layer: QgsVectorLayer to style
        :param style_filename: Name of the QML style file
        """
        style_path = os.path.join(self.styles_dir, style_filename)

        if os.path.exists(style_path):
            result = layer.loadNamedStyle(style_path)
            if not result[1]:
                self._show_warning(
                    'Style Load Warning',
                    f'Could not apply style {style_filename} to layer {layer.name()}'
                )

    def _validate_directories(self):
        """Check that Data and styles directories exist."""
        if not os.path.isdir(self.data_dir):
            self._show_error(
                'Data Directory Missing',
                f'The Data directory was not found at:\n{self.data_dir}\n\n'
                'Please use "Download/Update Data" to download the data.'
            )
            return False

        if not os.path.isdir(self.styles_dir):
            self._show_error(
                'Styles Directory Missing',
                f'The styles directory was not found at:\n{self.styles_dir}\n\n'
                'Please ensure the plugin is installed correctly.'
            )
            return False

        return True

    # ============ Download/Update Methods ============

    def download_update(self):
        """
        Main method to download or update Sudan data from remote server.
        """
        # Fetch remote version info
        version_info = self._fetch_version_info()
        if version_info is None:
            return

        remote_version = version_info.get('version')
        bundle_url = version_info.get('bundle_url')
        sha256 = version_info.get('sha256')

        if not remote_version or not bundle_url:
            self._show_error(
                'Invalid Version Info',
                'The version information from the server is incomplete.\n'
                'Missing version or bundle_url.'
            )
            return

        # Check local version
        local_version = self._get_local_version()

        if local_version and local_version == remote_version:
            self._show_info(
                'Up to Date',
                f'Data is already up to date (v{local_version})'
            )
            return

        # Download the bundle
        zip_data = self._download_bundle(bundle_url, sha256)
        if zip_data is None:
            return

        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)

        # Extract ZIP safely
        if not self._extract_zip_safely(zip_data, self.cache_dir):
            return

        # Save version info locally
        self._save_local_version(version_info)

        self._show_info(
            'Download Complete',
            f'Successfully downloaded Sudan Data v{remote_version}'
        )

    def _fetch_version_info(self):
        """Fetch version.json from the remote server."""
        request = QgsBlockingNetworkRequest()
        err = request.get(QNetworkRequest(QUrl(self.VERSION_URL)))

        if err != QgsBlockingNetworkRequest.NoError:
            error_msg = request.errorMessage()
            self._show_error(
                'Network Error',
                f'Failed to fetch version info from server:\n{error_msg}'
            )
            return None

        reply = request.reply()
        content = reply.content().data()

        try:
            version_info = json.loads(content.decode('utf-8'))
            return version_info
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self._show_error(
                'Parse Error',
                f'Failed to parse version info:\n{str(e)}'
            )
            return None

    def _get_local_version(self):
        """Read local version.json from cache directory if it exists."""
        if not os.path.exists(self.local_version_file):
            return None

        try:
            with open(self.local_version_file, 'r', encoding='utf-8') as f:
                version_info = json.load(f)
                return version_info.get('version')
        except (json.JSONDecodeError, IOError):
            return None

    def _download_bundle(self, url, sha256=None):
        """Download the data bundle from the given URL (handles redirects)."""
        progress = QProgressDialog(
            'Downloading Sudan Data...',
            None,  # No cancel button for blocking request
            0, 0,  # Indeterminate progress
            self.iface.mainWindow()
        )
        progress.setWindowTitle('Download Progress')
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()

        # Use QgsBlockingNetworkRequest which handles redirects automatically
        request = QNetworkRequest(QUrl(url))
        request.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.NoLessSafeRedirectPolicy)

        blocking_request = QgsBlockingNetworkRequest()
        error_code = blocking_request.get(request, forceRefresh=True)

        progress.close()

        if error_code != QgsBlockingNetworkRequest.NoError:
            self._show_error(
                'Download Error',
                f'Failed to download data bundle:\n{blocking_request.errorMessage()}'
            )
            return None

        reply = blocking_request.reply()
        data = bytes(reply.content())

        # Check if we got data
        if len(data) == 0:
            self._show_error(
                'Download Error',
                'Downloaded file is empty. Please check your internet connection.'
            )
            return None

        # Verify SHA256 if provided
        if sha256:
            calculated_hash = hashlib.sha256(data).hexdigest()
            if calculated_hash.lower() != sha256.lower():
                # Ask user if they want to proceed despite hash mismatch
                msg_reply = QMessageBox.warning(
                    self.iface.mainWindow(),
                    'Hash Verification Warning',
                    'Downloaded file hash does not match expected hash.\n\n'
                    f'Expected: {sha256[:16]}...\n'
                    f'Got: {calculated_hash[:16]}...\n\n'
                    'This could mean:\n'
                    '- The file on the server was updated\n'
                    '- The version.json needs to be updated\n'
                    '- The download may be corrupted\n\n'
                    'Do you want to proceed anyway?',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if msg_reply != QMessageBox.Yes:
                    return None

        return data

    def _extract_zip_safely(self, zip_data, target_dir):
        """Extract ZIP data safely to the target directory."""
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as f:
                temp_file = f.name
                f.write(zip_data)

            with zipfile.ZipFile(temp_file, 'r') as zf:
                for member in zf.namelist():
                    if not self._is_safe_path(target_dir, member):
                        self._show_error(
                            'Security Error',
                            f'Unsafe path detected in ZIP: {member}\n'
                            'Extraction aborted for security.'
                        )
                        return False

                    target_path = os.path.join(target_dir, member)

                    if member.endswith('/'):
                        os.makedirs(target_path, exist_ok=True)
                    else:
                        parent_dir = os.path.dirname(target_path)
                        os.makedirs(parent_dir, exist_ok=True)

                        with zf.open(member) as source, open(target_path, 'wb') as dest:
                            dest.write(source.read())

            return True

        except zipfile.BadZipFile:
            self._show_error(
                'Extraction Error',
                'The downloaded file is not a valid ZIP archive.'
            )
            return False
        except IOError as e:
            self._show_error(
                'Extraction Error',
                f'Failed to extract files:\n{str(e)}'
            )
            return False
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass

    def _is_safe_path(self, base_dir, file_path):
        """Check if a file path is safe (within the base directory)."""
        full_path = os.path.normpath(os.path.join(base_dir, file_path))
        base_path = os.path.normpath(base_dir)

        if '..' in file_path:
            return False

        if os.path.isabs(file_path):
            return False

        return full_path.startswith(base_path + os.sep) or full_path == base_path

    def _save_local_version(self, version_info):
        """Save version info to local cache directory."""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            with open(self.local_version_file, 'w', encoding='utf-8') as f:
                json.dump(version_info, f, indent=2)
        except IOError as e:
            self._show_warning(
                'Version Save Warning',
                f'Could not save version info:\n{str(e)}'
            )

    # ============ Helper Methods ============

    def _show_error(self, title, message):
        """Show an error message dialog."""
        QMessageBox.critical(self.iface.mainWindow(), title, message)

    def _show_warning(self, title, message):
        """Show a warning message dialog."""
        QMessageBox.warning(self.iface.mainWindow(), title, message)

    def _show_info(self, title, message):
        """Show an information message dialog."""
        QMessageBox.information(self.iface.mainWindow(), title, message)
