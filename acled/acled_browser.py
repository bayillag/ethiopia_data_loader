import os
from datetime import datetime, timedelta
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QDateEdit, QPushButton, QProgressBar, QMessageBox
)
from qgis.PyQt.QtCore import Qt, QSettings, QDate
from qgis.core import QgsApplication, QgsTask
from .acled_ethiopia_api import ACLEDEthiopiaFetcher

class ACLEDBrowserDialog(QDialog):
    def __init__(self, parent=None, plugin_instance=None):
        super(ACLEDBrowserDialog, self).__init__(parent)
        self.plugin = plugin_instance
        self.setWindowTitle("ACLED Ethiopia Conflict Browser")
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 1. Date Range Section
        layout.addWidget(QLabel("<b>Date Range:</b>"))
        date_layout = QHBoxLayout()
        
        self.start_date_input = QDateEdit()
        self.start_date_input.setCalendarPopup(True)
        # Default to 30 days ago
        thirty_days_ago = datetime.now() - timedelta(days=30)
        self.start_date_input.setDate(QDate(thirty_days_ago.year, thirty_days_ago.month, thirty_days_ago.day))
        
        date_layout.addWidget(QLabel("From:"))
        date_layout.addWidget(self.start_date_input)
        layout.addLayout(date_layout)

        # 2. Event Type Filter
        layout.addWidget(QLabel("<b>Filter by Event Type:</b>"))
        self.event_type_combo = QComboBox()
        self.event_type_combo.addItems([
            "All Events",
            "Battles",
            "Protests",
            "Riots",
            "Explosions/Remote violence",
            "Violence against civilians",
            "Strategic developments"
        ])
        layout.addWidget(self.event_type_combo)

        # 3. Ethiopia Region Filter (Admin 1)
        layout.addWidget(QLabel("<b>Filter by Region (Admin 1):</b>"))
        self.region_combo = QComboBox()
        # Official 15 Regions + General option
        self.region_combo.addItems([
            "All Regions", "Addis Ababa", "Afar", "Amhara", "Benishangul-Gumuz", 
            "Central Ethiopia", "Dire Dawa", "Gambela", "Harari", "Oromia", 
            "Sidama", "Somali", "South Ethiopia", "South West Ethiopia", "Tigray"
        ])
        layout.addWidget(self.region_combo)

        # 4. Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 5. Buttons
        button_layout = QHBoxLayout()
        self.btn_fetch = QPushButton("Fetch Conflict Data")
        self.btn_fetch.clicked.connect(self.run_fetch)
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.reject)
        
        button_layout.addWidget(self.btn_close)
        button_layout.addWidget(self.btn_fetch)
        layout.addLayout(button_layout)

    def run_fetch(self):
        """Validates credentials and starts the background task."""
        settings = QSettings()
        email = settings.value("ethiopia_data_loader/acled_email", "")
        api_key = settings.value("ethiopia_data_loader/acled_api_key", "")

        if not email or not api_key:
            QMessageBox.warning(self, "Credentials Missing", 
                                "Please set your ACLED API Email and Key via the plugin menu first.")
            return

        start_date_str = self.start_date_input.date().toString("yyyy-MM-dd")
        
        self.btn_fetch.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0) # Pulsing busy indicator

        # Create Task
        fetcher = ACLEDEthiopiaFetcher(email, api_key, start_date_str)
        fetcher.signals.finished.connect(self.on_fetch_success)
        fetcher.signals.error.connect(self.on_fetch_error)
        
        task = QgsTask.fromFunction("Fetching ACLED Ethiopia Data", fetcher.run)
        QgsApplication.taskManager().addTask(task)

    def on_fetch_success(self, data):
        """Filters the results based on UI selection and passes to layer creator."""
        self.btn_fetch.setEnabled(True)
        self.progress_bar.setVisible(False)

        selected_event = self.event_type_combo.currentText()
        selected_region = self.region_combo.currentText()

        # Perform UI-side filtering
        filtered_data = data
        if selected_event != "All Events":
            filtered_data = [d for d in filtered_data if d.get('event_type') == selected_event]
        
        if selected_region != "All Regions":
            filtered_data = [d for d in filtered_data if d.get('admin1') == selected_region]

        if not filtered_data:
            QMessageBox.information(self, "No Results", "No conflict events matched your filters.")
            return

        # Pass the final list back to the main plugin instance to create the layer
        self.plugin.create_acled_layer(filtered_data)
        self.accept()

    def on_fetch_error(self, message):
        self.btn_fetch.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "ACLED API Error", message)
