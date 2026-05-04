# -*- coding: utf-8 -*-
"""
ACLEDBrowserDialog - Ethiopia Data Loader
A professional QGIS 4.x (PyQt6) interface for ACLED Conflict Data.

Author: Bayilla Geda
Version: 1.0.0
Target: QGIS 4.0 - 4.99
"""

import json
import os
import datetime
import csv
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QGroupBox, QComboBox, QProgressBar, QMessageBox,
    QSplitter, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QDateEdit, QTabWidget, QWidget, QTextBrowser,
    QApplication, QAbstractItemView, QSizePolicy, QLineEdit
)
from qgis.PyQt.QtCore import (
    Qt, QDate, QVariant, QObject, pyqtSignal, 
    QSettings, QSize
)
from qgis.PyQt.QtGui import QColor, QBrush, QFont, QIcon, QCursor
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsField, QgsFeature,
    QgsGeometry, QgsPointXY, QgsCategorizedSymbolRenderer,
    QgsRendererCategory, QgsMarkerSymbol, Qgis, QgsMessageLog,
    QgsApplication, QgsTask
)

# -----------------------------------------------------------------------------
# ACLED CLIENT LOGIC
# -----------------------------------------------------------------------------

class ACLEDClient:
    """Helper class to handle ACLED API requests and data transformation."""
    
    BASE_URL = "https://api.acleddata.com/acled/read/"
    
    EVENT_TYPES = {
        'Battles': {'color': '#e74c3c'},
        'Explosions/Remote violence': {'color': '#e67e22'},
        'Protests': {'color': '#3498db'},
        'Riots': {'color': '#9b59b6'},
        'Strategic developments': {'color': '#34495e'},
        'Violence against civilians': {'color': '#c0392b'}
    }

    def __init__(self):
        self.api_key = ""
        self.email = ""

    def set_credentials(self, api_key, email):
        self.api_key = api_key
        self.email = email

    def fetch_events(self, start_date, end_date, event_types=None, admin1=None):
        """Fetches data from ACLED API for Ethiopia."""
        import urllib.request
        import urllib.parse

        # Ethiopia ISO code is 231, but we use country name for readability in API
        params = {
            'key': self.api_key,
            'email': self.email,
            'country': 'Ethiopia',
            'event_date': start_date,
            'event_date_where': '>=',
            'limit': 5000
        }

        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'EthiopiaDataLoader/4.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data.get('success'):
                    raw_events = data.get('data', [])
                    # Client-side filtering for sub-params
                    return self._filter_results(raw_events, end_date, event_types, admin1)
                return []
        except Exception as e:
            QgsMessageLog.logMessage(f"ACLED API Error: {str(e)}", "Ethiopia Data Loader", Qgis.MessageLevel.Critical)
            return []

    def _filter_results(self, events, end_date, event_types, admin1):
        filtered = []
        end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        
        for e in events:
            e_dt = datetime.datetime.strptime(e['event_date'], '%Y-%m-%d')
            if e_dt > end_dt: continue
            if event_types and e['event_type'] not in event_types: continue
            if admin1 and e['admin1'] != admin1: continue
            filtered.append(e)
        return filtered

# -----------------------------------------------------------------------------
# MAIN DIALOG CLASS
# -----------------------------------------------------------------------------

class ACLEDBrowserDialog(QDialog):
    """Advanced Browser for Ethiopia Conflict Data - Professional UI."""

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.client = ACLEDClient()
        self.current_events = []
        
        # Load Settings
        settings = QSettings()
        key = settings.value("ethiopia_data_loader/acled_api_key", "")
        email = settings.value("ethiopia_data_loader/acled_email", "")
        self.client.set_credentials(key, email)

        self.setWindowTitle('ACLED Ethiopia Conflict Monitor')
        self.setMinimumSize(1100, 800)
        self.setup_ui()

    def setup_ui(self):
        """Builds the complex PyQt6 UI Layout."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(5)

        # 1. HEADER SECTION
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_frame.setStyleSheet("""
            #HeaderFrame {
                background-color: #2c3e50;
                border-radius: 5px;
                padding: 10px;
            }
            QLabel { color: #ffffff; }
        """)
        header_layout = QHBoxLayout(header_frame)
        
        title_vbox = QVBoxLayout()
        main_title = QLabel('<span style="font-size: 18px; font-weight: bold;">Ethiopia Conflict Browser</span>')
        sub_title = QLabel('Humanitarian monitoring for Subnational Ethiopia | Source: ACLED Data')
        title_vbox.addWidget(main_title)
        title_vbox.addWidget(sub_title)
        header_layout.addLayout(title_vbox)
        
        header_layout.addStretch()
        
        self.cred_status = QLabel()
        self.update_cred_status()
        header_layout.addWidget(self.cred_status)
        
        self.main_layout.addWidget(header_frame)

        # 2. MAIN BODY (SPLITTER)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- LEFT PANEL: FILTERS ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 5, 5, 0)

        # Date Filter
        date_box = QGroupBox("Temporal Scope")
        date_vbox = QVBoxLayout(date_box)
        
        quick_dates = QHBoxLayout()
        btn_30 = QPushButton("30 Days")
        btn_30.clicked.connect(lambda: self.set_quick_date(30))
        btn_90 = QPushButton("90 Days")
        btn_90.clicked.connect(lambda: self.set_quick_date(90))
        quick_dates.addWidget(btn_30)
        quick_dates.addWidget(btn_90)
        date_vbox.addLayout(quick_dates)

        self.date_start = QDateEdit(QDate.currentDate().addDays(-30))
        self.date_start.setCalendarPopup(True)
        self.date_end = QDateEdit(QDate.currentDate())
        self.date_end.setCalendarPopup(True)
        date_vbox.addWidget(QLabel("Start Date:"))
        date_vbox.addWidget(self.date_start)
        date_vbox.addWidget(QLabel("End Date:"))
        date_vbox.addWidget(self.date_end)
        left_layout.addWidget(date_box)

        # Event Type Filter
        event_box = QGroupBox("Conflict Event Types")
        event_vbox = QVBoxLayout(event_box)
        self.event_checks = {}
        for etype, info in self.client.EVENT_TYPES.items():
            cb = QCheckBox(etype)
            cb.setChecked(True)
            cb.setStyleSheet(f"color: {info['color']}; font-weight: bold;")
            self.event_checks[etype] = cb
            event_vbox.addWidget(cb)
        left_layout.addWidget(event_box)

        # Region Filter (Standard Ethiopia Regions COD-AB v04)
        region_box = QGroupBox("Ethiopia Regions")
        region_vbox = QVBoxLayout(region_box)
        self.region_combo = QComboBox()
        self.region_combo.addItem("National (All Regions)", None)
        eth_regions = [
            "Addis Ababa", "Afar", "Amhara", "Benishangul-Gumuz", "Central Ethiopia",
            "Dire Dawa", "Gambela", "Harari", "Oromia", "Sidama", "Somali", 
            "South Ethiopia", "South West Ethiopia", "Tigray"
        ]
        self.region_combo.addItems(eth_regions)
        region_vbox.addWidget(self.region_combo)
        left_layout.addWidget(region_box)

        # Action Buttons
        self.btn_fetch = QPushButton("FETCH RECENT EVENTS")
        self.btn_fetch.setFixedHeight(45)
        self.btn_fetch.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white; 
                font-weight: bold; border-radius: 3px;
            }
            QPushButton:hover { background-color: #219150; }
        """)
        self.btn_fetch.clicked.connect(self.run_async_fetch)
        left_layout.addWidget(self.btn_fetch)

        self.btn_export = QPushButton("Export to CSV")
        self.btn_export.clicked.connect(self.export_to_csv)
        left_layout.addWidget(self.btn_export)
        
        left_layout.addStretch()
        self.splitter.addWidget(left_widget)

        # --- RIGHT PANEL: RESULTS ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Search Bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search in results:"))
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Filter by actor, location, or notes...")
        self.search_bar.textChanged.connect(self.filter_table)
        search_layout.addWidget(self.search_bar)
        right_layout.addLayout(search_layout)

        self.tabs = QTabWidget()
        
        # Tab 1: List
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['Date', 'Type', 'Region', 'Location', 'Fatalities', 'Primary Actor'])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.itemClicked.connect(self.show_event_details)
        self.tabs.addTab(self.table, "Table View")
        
        # Tab 2: Stats
        self.stats_view = QTextBrowser()
        self.tabs.addTab(self.stats_view, "Statistics Summary")
        
        # Tab 3: Details & Citation
        self.details_view = QTextBrowser()
        self.tabs.addTab(self.details_view, "Details & Citations")
        
        right_layout.addWidget(self.tabs)
        self.splitter.addWidget(right_widget)

        self.splitter.setSizes([280, 820])
        self.main_layout.addWidget(self.splitter)

        # 3. FOOTER SECTION
        footer_layout = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        footer_layout.addWidget(self.progress)
        
        self.status_label = QLabel("Waiting for input...")
        footer_layout.addWidget(self.status_label)
        
        footer_layout.addStretch()
        
        self.btn_cite = QPushButton("Generate Citation")
        self.btn_cite.clicked.connect(self.generate_citation)
        footer_layout.addWidget(self.btn_cite)

        self.btn_map = QPushButton("ADD TO QGIS MAP")
        self.btn_map.setEnabled(False)
        self.btn_map.setMinimumWidth(180)
        self.btn_map.setStyleSheet("""
            QPushButton {
                background-color: #e67e22; color: white; 
                padding: 8px; font-weight: bold;
            }
            QPushButton:disabled { background-color: #bdc3c7; }
        """)
        self.btn_map.clicked.connect(self.load_to_qgis)
        footer_layout.addWidget(self.btn_map)
        
        self.main_layout.addLayout(footer_layout)

    # -------------------------------------------------------------------------
    # CORE LOGIC
    # -------------------------------------------------------------------------

    def update_cred_status(self):
        if self.client.api_key and self.client.email:
            self.cred_status.setText('<span style="color: #2ecc71;">● ACLED API Active</span>')
        else:
            self.cred_status.setText('<span style="color: #e74c3c;">○ Credentials Missing</span>')

    def set_quick_date(self, days):
        self.date_start.setDate(QDate.currentDate().addDays(-days))
        self.date_end.setDate(QDate.currentDate())

    def run_async_fetch(self):
        if not self.client.api_key:
            QMessageBox.critical(self, "Setup Error", "Enter ACLED Credentials in Plugin Settings first.")
            return

        self.btn_fetch.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.status_label.setText("Querying ACLED API...")
        
        selected_types = [t for t, cb in self.event_checks.items() if cb.isChecked()]
        start = self.date_start.date().toString("yyyy-MM-dd")
        end = self.date_end.date().toString("yyyy-MM-dd")
        region = self.region_combo.currentText() if self.region_combo.currentIndex() != 0 else None

        # Execute as QgsTask
        task = QgsTask.fromFunction(
            "Fetch Ethiopia Conflict Data", 
            self._do_fetch,
            start=start, end=end, types=selected_types, region=region,
            on_finished=self.on_fetch_finished
        )
        QgsApplication.taskManager().addTask(task)

    def _do_fetch(self, task, start, end, types, region):
        return self.client.fetch_events(start, end, types, region)

    def on_fetch_finished(self, exception, result):
        self.btn_fetch.setEnabled(True)
        self.progress.setVisible(False)
        
        if exception:
            self.status_label.setText("Fetch failed.")
            return

        self.current_events = result
        self.populate_table(result)
        self.generate_statistics(result)
        self.status_label.setText(f"Found {len(result)} records.")
        self.btn_map.setEnabled(len(result) > 0)

    def populate_table(self, events):
        self.table.setRowCount(0)
        for e in events:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            date_item = QTableWidgetItem(e.get('event_date'))
            date_item.setData(Qt.ItemDataRole.UserRole, e)
            
            etype = e.get('event_type')
            type_item = QTableWidgetItem(etype)
            color = self.client.EVENT_TYPES.get(etype, {}).get('color', '#000000')
            type_item.setForeground(QBrush(QColor(color)))
            
            fatals = int(e.get('fatalities', 0))
            fat_item = QTableWidgetItem(str(fatals))
            if fatals > 5: fat_item.setFont(QFont("Arial", weight=QFont.Weight.Bold))

            self.table.setItem(row, 0, date_item)
            self.table.setItem(row, 1, type_item)
            self.table.setItem(row, 2, QTableWidgetItem(e.get('admin1')))
            self.table.setItem(row, 3, QTableWidgetItem(e.get('location')))
            self.table.setItem(row, 4, fat_item)
            self.table.setItem(row, 5, QTableWidgetItem(e.get('actor1', '')[:50]))

    def filter_table(self):
        txt = self.search_bar.text().lower()
        for i in range(self.table.rowCount()):
            match = False
            for j in range(self.table.columnCount()):
                if txt in self.table.item(i, j).text().lower():
                    match = True
                    break
            self.table.setRowHidden(i, not match)

    def show_event_details(self, item):
        e = self.table.item(item.row(), 0).data(Qt.ItemDataRole.UserRole)
        color = self.client.EVENT_TYPES.get(e.get('event_type'), {}).get('color', '#333')
        
        html = f"""
        <body style="font-family: sans-serif; padding: 15px;">
            <h2 style="color: {color};">{e.get('event_type')}</h2>
            <p><b>Date:</b> {e.get('event_date')}</p>
            <p><b>Location:</b> {e.get('location')}, {e.get('admin2')}, {e.get('admin1')}</p>
            <p><b>Coordinates:</b> {e.get('latitude')}, {e.get('longitude')}</p>
            <hr>
            <p><b>Fatalities:</b> <span style="color: red; font-size: 18px;">{e.get('fatalities')}</span></p>
            <p><b>Actors:</b> {e.get('actor1')} vs. {e.get('actor2') or 'N/A'}</p>
            <hr>
            <p><b>Narrative:</b><br>{e.get('notes')}</p>
            <p style="font-size: 10px; color: gray;">Source: {e.get('source')}</p>
        </body>
        """
        self.details_view.setHtml(html)
        self.tabs.setCurrentIndex(2)

    def generate_statistics(self, events):
        if not events: return
        total = len(events)
        fats = sum(int(e.get('fatalities', 0)) for e in events)
        
        reg_stats = {}
        for e in events:
            r = e.get('admin1')
            reg_stats[r] = reg_stats.get(r, 0) + 1
            
        html = f"""
        <h2 style='color: #2c3e50;'>Ethiopia Data Grid: Conflict Stats</h2>
        <p><b>Total Events:</b> {total} | <b>Total Fatalities:</b> <span style='color: red;'>{fats}</span></p>
        <hr>
        <h3>Distribution by Region</h3>
        <table width='100%' style='border-collapse: collapse;'>
        """
        for r, count in sorted(reg_stats.items(), key=lambda x: x[1], reverse=True):
            width = (count/total) * 100
            html += f"<tr><td width='150'>{r}</td><td><div style='background:#3498db; width:{width}%; height:15px;'></div></td><td width='40'>{count}</td></tr>"
        
        html += "</table>"
        self.stats_view.setHtml(html)

    def generate_citation(self):
        start = self.date_start.date().toString("MMMM d, yyyy")
        end = self.date_end.date().toString("MMMM d, yyyy")
        today = datetime.datetime.now().strftime("%B %d, %Y")
        
        html = f"""
        <div style="background: #fdfefe; border: 1px solid #ddd; padding: 20px;">
            <h3>Data Citation (ACLED Ethiopia)</h3>
            <p><b>APA:</b><br>Armed Conflict Location & Event Data Project (ACLED). (2025). <i>Conflict Events in Ethiopia [{start} - {end}]</i>. Retrieved {today}.</p>
            <p><b>BibTeX:</b><br><pre>@misc{{acled_eth_2025,\n author={{ACLED}},\n title={{Events in Ethiopia {start}-{end}}},\n year={{2025}}\n}}</pre></p>
        </div>
        """
        self.details_view.setHtml(html)
        self.tabs.setCurrentIndex(2)

    def export_to_csv(self):
        if not self.current_events: return
        from qgis.PyQt.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "ethiopia_conflict.csv", "CSV (*.csv)")
        if path:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=self.current_events[0].keys())
                w.writeheader()
                w.writerows(self.current_events)
            QMessageBox.information(self, "Done", "Exported successfully.")

    # -------------------------------------------------------------------------
    # QGIS MAPPING
    # -------------------------------------------------------------------------

    def load_to_qgis(self):
        """Transforms the fetched JSON into a styled QGIS memory layer."""
        if not self.current_events: return

        uri = "Point?crs=EPSG:4326&index=yes"
        layer = QgsVectorLayer(uri, "ACLED Ethiopia Conflict Events", "memory")
        prov = layer.dataProvider()

        fields = [
            QgsField("date", QVariant.Type.String),
            QgsField("type", QVariant.Type.String),
            QgsField("fatalities", QVariant.Type.Int),
            QgsField("region", QVariant.Type.String),
            QgsField("location", QVariant.Type.String),
            QgsField("actor1", QVariant.Type.String),
            QgsField("notes", QVariant.Type.String)
        ]
        prov.addAttributes(fields)
        layer.updateFields()

        feats = []
        for e in self.current_events:
            f = QgsFeature(layer.fields())
            f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(e['longitude']), float(e['latitude']))))
            f.setAttributes([
                e.get('event_date'), e.get('event_type'), int(e.get('fatalities', 0)),
                e.get('admin1'), e.get('location'), e.get('actor1'), e.get('notes')[:250]
            ])
            feats.append(f)
        
        prov.addFeatures(feats)
        
        # CATEGORIZED RENDERING
        categories = []
        for etype, info in self.client.EVENT_TYPES.items():
            sym = QgsMarkerSymbol.createSimple({
                'name': 'circle', 'color': info['color'], 'size': '3.2',
                'outline_color': '#ffffff', 'outline_width': '0.4'
            })
            categories.append(QgsRendererCategory(etype, sym, etype))
        
        layer.setRenderer(QgsCategorizedSymbolRenderer("type", categories))
        QgsProject.instance().addMapLayer(layer)
        self.accept()
