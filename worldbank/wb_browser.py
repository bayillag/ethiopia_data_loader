# -*- coding: utf-8 -*-
"""
World Bank Browser Dialog for Ethiopia Data Loader.

Provides a UI for browsing and visualizing World Bank development indicators for Ethiopia.
"""

import os
from datetime import datetime

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QGroupBox, QLabel, QComboBox, QPushButton, QSpinBox,
    QProgressBar, QMessageBox, QListWidget, QListWidgetItem,
    QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QLineEdit, QFileDialog
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor

from .wb_client import WorldBankClient


class WorldBankBrowserDialog(QDialog):
    """Dialog for browsing World Bank development indicators for Ethiopia."""

    def __init__(self, iface, parent=None):
        """
        Initialize the World Bank browser dialog.

        :param iface: QGIS interface instance
        :param parent: Parent widget
        """
        super().__init__(parent)
        self.iface = iface
        self.client = WorldBankClient()
        self.current_data = None

        self.setWindowTitle('World Bank Development Indicators - Ethiopia')
        self.setMinimumSize(900, 700)
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel('World Bank Development Indicators')
        header.setStyleSheet('font-size: 16px; font-weight: bold; padding: 10px;')
        layout.addWidget(header)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._create_browse_tab(), 'Browse by Category')
        tabs.addTab(self._create_search_tab(), 'Search Indicators')
        tabs.addTab(self._create_compare_tab(), 'Compare Indicators')
        layout.addWidget(tabs)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel('Ready - Select an indicator to view data')
        self.status_label.setStyleSheet('color: gray;')
        layout.addWidget(self.status_label)

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _create_browse_tab(self):
        """Create the browse by category tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Splitter for left/right panels
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Category and indicator selection
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # Category selection
        cat_group = QGroupBox('Category')
        cat_layout = QVBoxLayout(cat_group)

        self.category_combo = QComboBox()
        for category in self.client.get_categories():
            self.category_combo.addItem(category)
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        cat_layout.addWidget(self.category_combo)

        left_layout.addWidget(cat_group)

        # Indicator list
        ind_group = QGroupBox('Indicators')
        ind_layout = QVBoxLayout(ind_group)

        self.indicator_list = QListWidget()
        self.indicator_list.currentItemChanged.connect(self._on_indicator_selected)
        ind_layout.addWidget(self.indicator_list)

        left_layout.addWidget(ind_group)

        # Year range
        year_group = QGroupBox('Year Range')
        year_layout = QFormLayout(year_group)

        year_range_layout = QHBoxLayout()
        self.start_year_spin = QSpinBox()
        self.start_year_spin.setRange(1960, datetime.now().year)
        self.start_year_spin.setValue(1990)
        year_range_layout.addWidget(self.start_year_spin)

        year_range_layout.addWidget(QLabel('to'))

        self.end_year_spin = QSpinBox()
        self.end_year_spin.setRange(1960, datetime.now().year)
        self.end_year_spin.setValue(datetime.now().year)
        year_range_layout.addWidget(self.end_year_spin)

        year_layout.addRow('Years:', year_range_layout)

        left_layout.addWidget(year_group)

        # Fetch button
        self.fetch_btn = QPushButton('Fetch Data')
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.clicked.connect(self._fetch_indicator_data)
        left_layout.addWidget(self.fetch_btn)

        splitter.addWidget(left_widget)

        # Right panel - Data display
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Indicator info
        info_group = QGroupBox('Indicator Information')
        info_layout = QVBoxLayout(info_group)

        self.indicator_info_label = QLabel('Select an indicator')
        self.indicator_info_label.setWordWrap(True)
        info_layout.addWidget(self.indicator_info_label)

        right_layout.addWidget(info_group)

        # Statistics
        stats_group = QGroupBox('Statistics')
        stats_layout = QFormLayout(stats_group)

        self.stats_labels = {}
        for stat_name in ['Latest Value', 'Year Range', 'Min', 'Max', 'Mean', 'Trend']:
            label = QLabel('N/A')
            stats_layout.addRow(f'{stat_name}:', label)
            self.stats_labels[stat_name] = label

        right_layout.addWidget(stats_group)

        # Data table
        data_group = QGroupBox('Data')
        data_layout = QVBoxLayout(data_group)

        self.data_table = QTableWidget()
        self.data_table.setColumnCount(2)
        self.data_table.setHorizontalHeaderLabels(['Year', 'Value'])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.data_table.setAlternatingRowColors(True)
        data_layout.addWidget(self.data_table)

        # Export button
        export_btn_layout = QHBoxLayout()
        self.export_csv_btn = QPushButton('Export to CSV')
        self.export_csv_btn.setEnabled(False)
        self.export_csv_btn.clicked.connect(self._export_to_csv)
        export_btn_layout.addWidget(self.export_csv_btn)
        data_layout.addLayout(export_btn_layout)

        right_layout.addWidget(data_group)

        splitter.addWidget(right_widget)
        splitter.setSizes([350, 500])

        layout.addWidget(splitter)

        # Populate initial category
        self._on_category_changed(self.category_combo.currentText())

        return widget

    def _create_search_tab(self):
        """Create the search tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Search box
        search_group = QGroupBox('Search Indicators')
        search_layout = QHBoxLayout(search_group)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Enter search keywords (e.g., "population", "education")')
        self.search_input.returnPressed.connect(self._search_indicators)
        search_layout.addWidget(self.search_input)

        search_btn = QPushButton('Search')
        search_btn.clicked.connect(self._search_indicators)
        search_layout.addWidget(search_btn)

        layout.addWidget(search_group)

        # Results
        results_group = QGroupBox('Search Results')
        results_layout = QVBoxLayout(results_group)

        self.search_results_list = QListWidget()
        self.search_results_list.itemDoubleClicked.connect(self._on_search_result_double_clicked)
        results_layout.addWidget(self.search_results_list)

        layout.addWidget(results_group)

        # Instructions
        instructions = QLabel(
            'Double-click an indicator to fetch its data. '
            'Results show indicators available in the World Bank database.'
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet('color: gray; font-style: italic;')
        layout.addWidget(instructions)

        return widget

    def _create_compare_tab(self):
        """Create the comparison tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Instructions
        instructions = QLabel(
            'Select multiple indicators to compare their trends over time. '
            'This feature allows side-by-side comparison of different development metrics.'
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Quick comparisons
        compare_group = QGroupBox('Quick Comparisons')
        compare_layout = QVBoxLayout(compare_group)

        comparisons = [
            ('Population vs GDP', ['SP.POP.TOTL', 'NY.GDP.MKTP.CD']),
            ('Education Enrollment', ['SE.PRM.ENRR', 'SE.SEC.ENRR', 'SE.TER.ENRR']),
            ('Health Indicators', ['SH.DYN.MORT', 'SH.DYN.NMRT', 'SP.DYN.IMRT.IN']),
            ('Infrastructure Access', ['EG.ELC.ACCS.ZS', 'IT.NET.USER.ZS', 'SH.H2O.SMDW.ZS'])
        ]

        for name, indicators in comparisons:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, ind=indicators: self._compare_indicators(ind))
            compare_layout.addWidget(btn)

        layout.addWidget(compare_group)

        # Comparison results
        self.compare_table = QTableWidget()
        self.compare_table.setColumnCount(4)
        self.compare_table.setHorizontalHeaderLabels(['Indicator', 'Latest Value', 'Year', 'Trend'])
        self.compare_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.compare_table)

        return widget

    def connect_signals(self):
        """Connect client signals."""
        self.client.data_loaded.connect(self._on_data_loaded)
        self.client.indicators_loaded.connect(self._on_indicators_loaded)
        self.client.error_occurred.connect(self._on_error)
        self.client.progress_update.connect(self._on_progress)

    def _on_category_changed(self, category):
        """Handle category selection change."""
        self.indicator_list.clear()
        indicators = self.client.get_indicators_by_category(category)

        for ind in indicators:
            item = QListWidgetItem(f"{ind['name']}")
            item.setData(Qt.UserRole, ind['id'])
            item.setToolTip(f"ID: {ind['id']}")
            self.indicator_list.addItem(item)

    def _on_indicator_selected(self, current, previous):
        """Handle indicator selection."""
        if current:
            ind_id = current.data(Qt.UserRole)
            ind_name = current.text()
            self.indicator_info_label.setText(
                f"<b>{ind_name}</b><br><br>"
                f"<b>Indicator ID:</b> {ind_id}<br>"
                f"<b>Country:</b> Sudan"
            )
            self.fetch_btn.setEnabled(True)
        else:
            self.fetch_btn.setEnabled(False)

    def _fetch_indicator_data(self):
        """Fetch data for selected indicator."""
        current = self.indicator_list.currentItem()
        if not current:
            return

        ind_id = current.data(Qt.UserRole)
        start_year = self.start_year_spin.value()
        end_year = self.end_year_spin.value()

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.client.fetch_indicator(ind_id, start_year, end_year)

    def _on_data_loaded(self, data):
        """Handle data loaded signal."""
        self.progress_bar.setVisible(False)
        self.current_data = data

        # Update data table
        self.data_table.setRowCount(len(data.get('data', [])))
        for row, point in enumerate(data.get('data', [])):
            self.data_table.setItem(row, 0, QTableWidgetItem(str(point['year'])))
            self.data_table.setItem(row, 1, QTableWidgetItem(f"{point['value']:,.2f}"))

        # Update statistics
        stats = self.client.get_statistics(data)
        if stats:
            latest = stats.get('latest')
            if latest:
                self.stats_labels['Latest Value'].setText(f"{latest['value']:,.2f} ({latest['year']})")
            self.stats_labels['Year Range'].setText(stats.get('year_range', 'N/A'))
            self.stats_labels['Min'].setText(f"{stats.get('min', 0):,.2f}")
            self.stats_labels['Max'].setText(f"{stats.get('max', 0):,.2f}")
            self.stats_labels['Mean'].setText(f"{stats.get('mean', 0):,.2f}")

            trend = stats.get('trend', 'N/A')
            trend_pct = stats.get('trend_pct', 0)
            if trend != 'N/A':
                trend_text = f"{trend.capitalize()} ({trend_pct:+.1f}%)"
                color = 'green' if trend == 'increasing' else ('red' if trend == 'decreasing' else 'gray')
                self.stats_labels['Trend'].setText(trend_text)
                self.stats_labels['Trend'].setStyleSheet(f'color: {color};')
            else:
                self.stats_labels['Trend'].setText('N/A')

        self.export_csv_btn.setEnabled(True)
        self.status_label.setText(f"Loaded {len(data.get('data', []))} data points for {data.get('indicator_name', '')}")

    def _on_indicators_loaded(self, indicators):
        """Handle search results."""
        self.progress_bar.setVisible(False)
        self.search_results_list.clear()

        for ind in indicators:
            item = QListWidgetItem(f"{ind['name']}")
            item.setData(Qt.UserRole, ind['id'])
            item.setToolTip(f"ID: {ind['id']}\nSource: {ind.get('source', 'N/A')}")
            self.search_results_list.addItem(item)

        self.status_label.setText(f"Found {len(indicators)} indicators")

    def _on_error(self, error):
        """Handle errors."""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Error: {error}")
        QMessageBox.warning(self, 'Error', error)

    def _on_progress(self, message):
        """Handle progress updates."""
        self.status_label.setText(message)

    def _search_indicators(self):
        """Search for indicators."""
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, 'Empty Search', 'Please enter search keywords.')
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.client.search_indicators(query)

    def _on_search_result_double_clicked(self, item):
        """Handle double-click on search result."""
        ind_id = item.data(Qt.UserRole)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.client.fetch_indicator(ind_id)

    def _compare_indicators(self, indicator_ids):
        """Compare multiple indicators."""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText('Fetching comparison data...')

        results = self.client.fetch_multiple_indicators(indicator_ids)

        self.progress_bar.setVisible(False)
        self.compare_table.setRowCount(len(results))

        row = 0
        for ind_id, data in results.items():
            stats = self.client.get_statistics(data)

            self.compare_table.setItem(row, 0, QTableWidgetItem(data.get('indicator_name', ind_id)))

            latest = stats.get('latest')
            if latest:
                self.compare_table.setItem(row, 1, QTableWidgetItem(f"{latest['value']:,.2f}"))
                self.compare_table.setItem(row, 2, QTableWidgetItem(str(latest['year'])))
            else:
                self.compare_table.setItem(row, 1, QTableWidgetItem('N/A'))
                self.compare_table.setItem(row, 2, QTableWidgetItem('N/A'))

            trend = stats.get('trend', 'N/A')
            trend_item = QTableWidgetItem(trend.capitalize() if trend != 'N/A' else 'N/A')
            if trend == 'increasing':
                trend_item.setForeground(QColor('green'))
            elif trend == 'decreasing':
                trend_item.setForeground(QColor('red'))
            self.compare_table.setItem(row, 3, trend_item)

            row += 1

        self.status_label.setText(f'Compared {len(results)} indicators')

    def _export_to_csv(self):
        """Export current data to CSV."""
        if not self.current_data:
            QMessageBox.warning(self, 'No Data', 'Please fetch indicator data first.')
            return

        filepath = self.client.export_to_csv(self.current_data)

        # Ask for save location
        save_path, _ = QFileDialog.getSaveFileName(
            self, 'Save CSV',
            os.path.expanduser(f"~/sudan_worldbank_{self.current_data.get('indicator_id', 'data')}.csv"),
            'CSV Files (*.csv)'
        )

        if save_path:
            import shutil
            shutil.copy(filepath, save_path)
            QMessageBox.information(self, 'Export Complete', f'Data exported to:\n{save_path}')
