# -*- coding: utf-8 -*-
"""
ACLED Browser Dialog for Ethiopia Data Loader.

Provides a modern user interface for browsing, filtering, and loading 
live ACLED conflict data for Ethiopia.
"""

import os
from datetime import datetime
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QGroupBox, QComboBox, QProgressBar, QMessageBox,
    QSplitter, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QDateEdit, QTabWidget, QWidget, QTextBrowser,
    QApplication, QAbstractItemView
)
from qgis.PyQt.QtCore import Qt, QDate, QVariant
from qgis.PyQt.QtGui import QColor, QBrush
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsField, QgsFeature,
    QgsGeometry, QgsPointXY, QgsCategorizedSymbolRenderer,
    QgsRendererCategory, QgsMarkerSymbol, QgsMessageLog, Qgis
)

from .acled_client import ACLEDClient

class ACLEDBrowserDialog(QDialog):
    """Dialog for browsing and loading ACLED conflict data."""

    def __init__(self, iface, settings_manager=None, parent=None):
        """Initialize the ACLED browser dialog."""
        super().__init__(parent)
        self.iface = iface
        self.settings_manager = settings_manager
        self.client = ACLEDClient()
        self.current_events = []
        self.pending_layer_data = None

        # Load API credentials from settings if available
        from qgis.core import QgsMessageLog, Qgis
        if self.settings_manager and self.settings_manager.has_acled_credentials():
            api_key, email = self.settings_manager.get_acled_credentials()
            QgsMessageLog.logMessage(f"ACLED: Loading credentials for {email}", "Ethiopia Data Loader", Qgis.Info)
            self.client.set_credentials(api_key, email)
        else:
            QgsMessageLog.logMessage("ACLED: No credentials found in settings", "Ethiopia Data Loader", Qgis.Warning)

        self.setWindowTitle('ACLED Conflict Data - Ethiopia')
        self.setMinimumSize(900, 650)
        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Main content
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Filters
        left_panel = self._create_filters_panel()
        splitter.addWidget(left_panel)

        # Right panel - Results and Stats
        right_panel = self._create_results_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([300, 600])
        layout.addWidget(splitter)

        # Bottom bar
        bottom_bar = self._create_bottom_bar()
        layout.addWidget(bottom_bar)

    def _create_header(self):
        """Create the header."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #c0392b;
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                color: white;
            }
        """)
        layout = QVBoxLayout(frame)

        title = QLabel('<b style="font-size: 16px;">Armed Conflict Location & Event Data (ACLED)</b>')
        title.setStyleSheet("color: white;")
        layout.addWidget(title)

        subtitle = QLabel('Real-time conflict tracking for Sudan | Data source: acleddata.com')
        subtitle.setStyleSheet("color: #ffcccc; font-size: 11px;")
        layout.addWidget(subtitle)

        # API status indicator
        if self.settings_manager and self.settings_manager.has_acled_credentials():
            api_status = QLabel('API: Credentials configured')
            api_status.setStyleSheet("color: #2ecc71; font-size: 10px; font-weight: bold;")
        else:
            api_status = QLabel('API: No credentials - Add myACLED account in Settings > API Keys')
            api_status.setStyleSheet("color: #f39c12; font-size: 10px;")
        layout.addWidget(api_status)

        return frame

    def _create_filters_panel(self):
        """Create the filters panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Date range group
        date_group = QGroupBox("Date Range")
        date_layout = QVBoxLayout(date_group)

        # Quick date buttons
        quick_layout = QHBoxLayout()

        btn_30 = QPushButton("Last 30 Days")
        btn_30.clicked.connect(lambda: self.set_date_range(30))
        quick_layout.addWidget(btn_30)

        btn_90 = QPushButton("Last 90 Days")
        btn_90.clicked.connect(lambda: self.set_date_range(90))
        quick_layout.addWidget(btn_90)

        date_layout.addLayout(quick_layout)

        quick_layout2 = QHBoxLayout()

        btn_year = QPushButton("This Year")
        btn_year.clicked.connect(self.set_this_year)
        quick_layout2.addWidget(btn_year)

        btn_2023 = QPushButton("2023")
        btn_2023.clicked.connect(lambda: self.set_year(2023))
        quick_layout2.addWidget(btn_2023)

        date_layout.addLayout(quick_layout2)

        # Custom date range
        date_layout.addWidget(QLabel("Custom Range:"))

        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("From:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        start_layout.addWidget(self.start_date)
        date_layout.addLayout(start_layout)

        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("To:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        end_layout.addWidget(self.end_date)
        date_layout.addLayout(end_layout)

        layout.addWidget(date_group)

        # Event types group
        events_group = QGroupBox("Event Types")
        events_layout = QVBoxLayout(events_group)

        self.event_checkboxes = {}
        for event_type, info in self.client.EVENT_TYPES.items():
            cb = QCheckBox(event_type)
            cb.setChecked(True)
            cb.setStyleSheet(f"QCheckBox {{ color: {info['color']}; font-weight: bold; }}")
            self.event_checkboxes[event_type] = cb
            events_layout.addWidget(cb)

        # Select/Deselect all
        select_layout = QHBoxLayout()
        select_all = QPushButton("All")
        select_all.clicked.connect(self.select_all_events)
        select_layout.addWidget(select_all)

        select_none = QPushButton("None")
        select_none.clicked.connect(self.select_no_events)
        select_layout.addWidget(select_none)

        events_layout.addLayout(select_layout)

        layout.addWidget(events_group)

        # Region filter
        region_group = QGroupBox("Region Filter")
        region_layout = QVBoxLayout(region_group)

        self.region_combo = QComboBox()
        self.region_combo.addItem("All States", None)
        for region in self.client.get_sudan_admin1_regions():
            self.region_combo.addItem(region, region)
        region_layout.addWidget(self.region_combo)

        layout.addWidget(region_group)

        # Fetch button
        self.fetch_btn = QPushButton("Fetch Conflict Data")
        self.fetch_btn.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                color: white;
                padding: 12px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #a93226;
            }
        """)
        self.fetch_btn.clicked.connect(self.fetch_data)
        layout.addWidget(self.fetch_btn)

        layout.addStretch()

        return widget

    def _create_results_panel(self):
        """Create the results panel with tabs."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()

        # Events table tab
        events_widget = QWidget()
        events_layout = QVBoxLayout(events_widget)

        self.events_table = QTableWidget()
        self.events_table.setColumnCount(7)
        self.events_table.setHorizontalHeaderLabels([
            'Date', 'Event Type', 'Location', 'Admin1', 'Fatalities', 'Actor 1', 'Actor 2'
        ])
        self.events_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.events_table.setAlternatingRowColors(True)
        self.events_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.events_table.itemClicked.connect(self.on_event_clicked)
        events_layout.addWidget(self.events_table)

        self.tabs.addTab(events_widget, "Events")

        # Statistics tab
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)

        self.stats_browser = QTextBrowser()
        self.stats_browser.setOpenExternalLinks(True)
        stats_layout.addWidget(self.stats_browser)

        self.tabs.addTab(stats_widget, "Statistics")

        # Event details tab
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)

        self.details_browser = QTextBrowser()
        details_layout.addWidget(self.details_browser)

        self.tabs.addTab(details_widget, "Event Details")

        layout.addWidget(self.tabs)

        # Results count
        self.results_label = QLabel("No data loaded")
        self.results_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.results_label)

        return widget

    def _create_bottom_bar(self):
        """Create the bottom bar."""
        frame = QFrame()
        layout = QHBoxLayout(frame)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Add to map button
        self.add_to_map_btn = QPushButton("Add to Map")
        self.add_to_map_btn.setEnabled(False)
        self.add_to_map_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.add_to_map_btn.clicked.connect(self.prepare_layer_for_map)
        layout.addWidget(self.add_to_map_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        return frame

    def set_date_range(self, days):
        """Set date range to last N days."""
        end = QDate.currentDate()
        start = end.addDays(-days)
        self.start_date.setDate(start)
        self.end_date.setDate(end)

    def set_this_year(self):
        """Set date range to current year."""
        year = QDate.currentDate().year()
        self.start_date.setDate(QDate(year, 1, 1))
        self.end_date.setDate(QDate.currentDate())

    def set_year(self, year):
        """Set date range to specific year."""
        self.start_date.setDate(QDate(year, 1, 1))
        self.end_date.setDate(QDate(year, 12, 31))

    def select_all_events(self):
        """Select all event types."""
        for cb in self.event_checkboxes.values():
            cb.setChecked(True)

    def select_no_events(self):
        """Deselect all event types."""
        for cb in self.event_checkboxes.values():
            cb.setChecked(False)

    def fetch_data(self):
        """Fetch conflict data from ACLED."""
        # Get selected event types
        event_types = [et for et, cb in self.event_checkboxes.items() if cb.isChecked()]

        if not event_types:
            QMessageBox.warning(self, "No Event Types", "Please select at least one event type.")
            return

        # Get date range
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")

        # Get region filter
        region = self.region_combo.currentData()

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("Fetching data from ACLED...")
        self.fetch_btn.setEnabled(False)
        QApplication.processEvents()

        # Fetch data
        events = self.client.fetch_events(
            start_date=start_date,
            end_date=end_date,
            event_types=event_types,
            admin1=region
        )

        # Hide progress
        self.progress_bar.setVisible(False)
        self.fetch_btn.setEnabled(True)

        if events:
            self.current_events = events
            self.display_events(events)
            self.display_statistics(events)
            self.results_label.setText(f"Loaded {len(events)} conflict events")
            self.status_label.setText(f"Found {len(events)} events")
            self.add_to_map_btn.setEnabled(True)
        else:
            self.status_label.setText("No events found or API error")
            self.results_label.setText("No data loaded")
            QMessageBox.information(
                self, "No Data",
                "No conflict events found for the selected criteria.\n\n"
                "Try expanding the date range or selecting more event types."
            )

    def display_events(self, events):
        """Display events in the table."""
        self.events_table.setRowCount(len(events))

        for row, event in enumerate(events):
            # Date
            date_item = QTableWidgetItem(event.get('event_date', ''))
            self.events_table.setItem(row, 0, date_item)

            # Event type with color
            event_type = event.get('event_type', '')
            type_item = QTableWidgetItem(event_type)
            color = self.client.get_event_color(event_type)
            type_item.setForeground(QBrush(QColor(color)))
            self.events_table.setItem(row, 1, type_item)

            # Location
            self.events_table.setItem(row, 2, QTableWidgetItem(event.get('location', '')))

            # Admin1
            self.events_table.setItem(row, 3, QTableWidgetItem(event.get('admin1', '')))

            # Fatalities
            fatalities = int(event.get('fatalities', 0))
            fat_item = QTableWidgetItem(str(fatalities))
            if fatalities > 0:
                fat_item.setForeground(QBrush(QColor('#e74c3c')))
                fat_item.setFont(fat_item.font())
            self.events_table.setItem(row, 4, fat_item)

            # Actors
            self.events_table.setItem(row, 5, QTableWidgetItem(event.get('actor1', '')[:30]))
            self.events_table.setItem(row, 6, QTableWidgetItem(event.get('actor2', '')[:30]))

            # Store event data in first column
            date_item.setData(Qt.UserRole, event)

    def display_statistics(self, events):
        """Display statistics."""
        stats = self.client.get_statistics(events)

        html = f"""
        <h2>Conflict Statistics</h2>
        <p><b>Total Events:</b> {stats.get('total_events', 0)}</p>
        <p><b>Total Fatalities:</b> <span style="color: #e74c3c;">{stats.get('total_fatalities', 0)}</span></p>
        <p><b>Date Range:</b> {stats.get('date_range', {}).get('start', '')} to {stats.get('date_range', {}).get('end', '')}</p>

        <h3>By Event Type</h3>
        <table border="1" cellpadding="5" style="border-collapse: collapse;">
        <tr><th>Event Type</th><th>Count</th><th>Fatalities</th></tr>
        """

        for event_type, data in sorted(stats.get('by_event_type', {}).items(),
                                        key=lambda x: x[1]['count'], reverse=True):
            color = self.client.get_event_color(event_type)
            html += f"""
            <tr>
                <td style="color: {color};"><b>{event_type}</b></td>
                <td>{data['count']}</td>
                <td>{data['fatalities']}</td>
            </tr>
            """

        html += "</table>"

        html += """
        <h3>By State (Top 10)</h3>
        <table border="1" cellpadding="5" style="border-collapse: collapse;">
        <tr><th>State</th><th>Events</th><th>Fatalities</th></tr>
        """

        sorted_admin1 = sorted(stats.get('by_admin1', {}).items(),
                               key=lambda x: x[1]['count'], reverse=True)[:10]

        for admin1, data in sorted_admin1:
            html += f"""
            <tr>
                <td>{admin1}</td>
                <td>{data['count']}</td>
                <td>{data['fatalities']}</td>
            </tr>
            """

        html += "</table>"

        self.stats_browser.setHtml(html)

    def on_event_clicked(self, item):
        """Handle event row click."""
        row = item.row()
        event = self.events_table.item(row, 0).data(Qt.UserRole)

        if event:
            self.display_event_details(event)
            self.tabs.setCurrentIndex(2)  # Switch to details tab

    def display_event_details(self, event):
        """Display details for a single event."""
        color = self.client.get_event_color(event.get('event_type', ''))

        html = f"""
        <h2 style="color: {color};">{event.get('event_type', 'Unknown')}</h2>
        <p><b>Date:</b> {event.get('event_date', '')}</p>
        <p><b>Location:</b> {event.get('location', '')} ({event.get('admin1', '')}, {event.get('admin2', '')})</p>
        <p><b>Coordinates:</b> {event.get('latitude', '')}, {event.get('longitude', '')}</p>

        <h3>Actors</h3>
        <p><b>Actor 1:</b> {event.get('actor1', 'N/A')}</p>
        <p><b>Actor 2:</b> {event.get('actor2', 'N/A')}</p>

        <h3>Impact</h3>
        <p><b>Fatalities:</b> <span style="color: #e74c3c; font-size: 18px;">{event.get('fatalities', 0)}</span></p>

        <h3>Description</h3>
        <p>{event.get('notes', 'No description available.')}</p>

        <h3>Source</h3>
        <p>{event.get('source', 'N/A')} ({event.get('source_scale', '')})</p>
        """

        self.details_browser.setHtml(html)

    def prepare_layer_for_map(self):
        """Prepare layer data and close dialog."""
        if not self.current_events:
            return

        # Convert to GeoJSON
        geojson = self.client.events_to_geojson(self.current_events)

        # Generate layer name with date range
        start = self.start_date.date().toString("yyyy-MM-dd")
        end = self.end_date.date().toString("yyyy-MM-dd")
        layer_name = f"Sudan Conflict Events ({start} to {end})"

        # Store for adding after dialog closes
        self.pending_layers = [{
            'geojson': geojson,
            'layer_name': layer_name,
            'style_events': True
        }]

        self.status_label.setText("Layer ready - closing dialog...")
        self.accept()

    def get_pending_layers(self):
        """Get list of pending layers to add after dialog closes."""
        return getattr(self, 'pending_layers', [])

    def add_layer_to_map(self, geojson_data, layer_name, style_events=True):
        """
        Add conflict layer to map.
        Called from main plugin after dialog closes.

        :param geojson_data: GeoJSON data dict
        :param layer_name: Name for the layer
        :param style_events: Whether to apply event type styling
        :returns: Tuple (success, layer_name or error_message)
        """
        if not geojson_data or not geojson_data.get('features'):
            return False, "No features to add"

        # Create the layer
        layer, error = self.create_conflict_layer(geojson_data, layer_name)

        if error:
            return False, error

        # Add to project
        QgsProject.instance().addMapLayer(layer)
        return True, layer.name()

    def create_conflict_layer(self, geojson_data, layer_name='Sudan Conflict Events (ACLED)'):
        """
        Create a styled vector layer from GeoJSON data.
        Called from main plugin after dialog closes.

        :param geojson_data: GeoJSON data dict
        :param layer_name: Name for the layer
        :returns: Tuple (layer, error_message)
        """
        if not geojson_data or not geojson_data.get('features'):
            return None, "No features to add"

        # Create memory layer
        layer = QgsVectorLayer('Point?crs=EPSG:4326', layer_name, 'memory')
        provider = layer.dataProvider()

        # Add fields
        fields = [
            QgsField('event_id', QVariant.String),
            QgsField('event_date', QVariant.String),
            QgsField('year', QVariant.Int),
            QgsField('event_type', QVariant.String),
            QgsField('sub_event_type', QVariant.String),
            QgsField('actor1', QVariant.String),
            QgsField('actor2', QVariant.String),
            QgsField('admin1', QVariant.String),
            QgsField('admin2', QVariant.String),
            QgsField('location', QVariant.String),
            QgsField('fatalities', QVariant.Int),
            QgsField('notes', QVariant.String),
            QgsField('source', QVariant.String),
        ]
        provider.addAttributes(fields)
        layer.updateFields()

        # Add features
        features = []
        for f in geojson_data['features']:
            feat = QgsFeature(layer.fields())

            coords = f['geometry']['coordinates']
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(coords[0], coords[1])))

            props = f['properties']
            feat['event_id'] = props.get('event_id', '')
            feat['event_date'] = props.get('event_date', '')
            feat['year'] = int(props.get('year', 0)) if props.get('year') else 0
            feat['event_type'] = props.get('event_type', '')
            feat['sub_event_type'] = props.get('sub_event_type', '')
            feat['actor1'] = props.get('actor1', '')
            feat['actor2'] = props.get('actor2', '')
            feat['admin1'] = props.get('admin1', '')
            feat['admin2'] = props.get('admin2', '')
            feat['location'] = props.get('location', '')
            feat['fatalities'] = props.get('fatalities', 0)
            feat['notes'] = props.get('notes', '')[:254] if props.get('notes') else ''
            feat['source'] = props.get('source', '')

            features.append(feat)

        provider.addFeatures(features)

        # Apply categorized styling by event type
        self._apply_conflict_styling(layer)

        return layer, None

    def _apply_conflict_styling(self, layer):
        """Apply categorized styling to conflict layer."""
        categories = []

        for event_type, info in ACLEDClient.EVENT_TYPES.items():
            symbol = QgsMarkerSymbol.createSimple({
                'name': 'circle',
                'color': info['color'],
                'size': '3',
                'outline_color': '#000000',
                'outline_width': '0.3'
            })

            category = QgsRendererCategory(event_type, symbol, event_type)
            categories.append(category)

        # Default for unknown types
        default_symbol = QgsMarkerSymbol.createSimple({
            'name': 'circle',
            'color': '#95a5a6',
            'size': '3'
        })

        renderer = QgsCategorizedSymbolRenderer('event_type', categories)
        layer.setRenderer(renderer)
