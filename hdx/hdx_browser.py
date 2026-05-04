# -*- coding: utf-8 -*-
"""
HDX Browser Dialog for Ethiopia Data Loader.

Provides a user interface for browsing and downloading HDX datasets.
"""

import os
import zipfile
import tempfile

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLineEdit, QPushButton, QLabel, QListWidget, QListWidgetItem,
    QTextBrowser, QComboBox, QProgressBar, QMessageBox,
    QSplitter, QGroupBox, QCheckBox, QFrame, QToolButton,
    QSizePolicy, QApplication
)
from qgis.PyQt.QtCore import Qt, QSize, QThread, pyqtSignal, QUrl
from qgis.PyQt.QtGui import QIcon, QColor, QFont, QDesktopServices
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer,
    QgsCoordinateReferenceSystem
)

from .hdx_client import HDXClient


class DownloadThread(QThread):
    """Background thread for downloading files."""

    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, client, url, filename=None):
        super().__init__()
        self.client = client
        self.url = url
        self.filename = filename

    def run(self):
        """Run the download."""
        try:
            path = self.client.download_resource(self.url, self.filename)
            if path:
                self.finished.emit(path)
            else:
                self.error.emit("Download failed")
        except Exception as e:
            self.error.emit(str(e))


class HDXBrowserDialog(QDialog):
    """Dialog for browsing and downloading HDX datasets."""

    def __init__(self, iface, parent=None):
        """Initialize the HDX browser dialog."""
        super().__init__(parent)
        self.iface = iface
        self.client = HDXClient()
        self.current_dataset = None
        self.download_thread = None

        # Store layers to add after dialog closes (prevents QGIS crash)
        self.pending_layers = []

        self.setWindowTitle('HDX Humanitarian Data Browser - Sudan')
        self.setMinimumSize(900, 600)
        self.setup_ui()
        self.load_featured_datasets()

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Main content with splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Dataset list
        left_panel = self._create_dataset_panel()
        splitter.addWidget(left_panel)

        # Right panel - Dataset details
        right_panel = self._create_details_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([350, 550])
        layout.addWidget(splitter)

        # Bottom bar
        bottom_bar = self._create_bottom_bar()
        layout.addWidget(bottom_bar)

    def _create_header(self):
        """Create the header with search and filters."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(frame)

        # Title row
        title_layout = QHBoxLayout()

        title = QLabel('<b style="font-size: 14px;">Humanitarian Data Exchange (HDX)</b>')
        title_layout.addWidget(title)

        title_layout.addStretch()

        hdx_link = QPushButton('Open HDX Website')
        hdx_link.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl('https://data.humdata.org/group/sdn')
        ))
        title_layout.addWidget(hdx_link)

        layout.addLayout(title_layout)

        # Search row
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Type to filter featured / Press Enter to search HDX...')
        self.search_input.returnPressed.connect(self.search_datasets)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        search_layout.addWidget(self.search_input)

        self.category_combo = QComboBox()
        self.category_combo.addItem('All Categories', None)
        for cat in self.client.get_categories():
            self.category_combo.addItem(cat, cat)
        self.category_combo.setMinimumWidth(150)
        # Filter featured datasets when category changes
        self.category_combo.currentIndexChanged.connect(self.on_category_changed)
        search_layout.addWidget(self.category_combo)

        search_btn = QPushButton('Search')
        search_btn.clicked.connect(self.search_datasets)
        search_layout.addWidget(search_btn)

        # Clear filter button
        clear_btn = QPushButton('Clear')
        clear_btn.setMaximumWidth(60)
        clear_btn.clicked.connect(self.clear_filters)
        search_layout.addWidget(clear_btn)

        layout.addLayout(search_layout)

        return frame

    def _create_dataset_panel(self):
        """Create the left panel with dataset list."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tabs for Featured / Search Results
        self.tabs = QTabWidget()

        # Featured tab
        featured_widget = QWidget()
        featured_layout = QVBoxLayout(featured_widget)
        featured_layout.setContentsMargins(5, 5, 5, 5)

        self.featured_list = QListWidget()
        self.featured_list.setAlternatingRowColors(True)
        self.featured_list.itemClicked.connect(self.on_dataset_selected)
        featured_layout.addWidget(self.featured_list)

        self.tabs.addTab(featured_widget, 'Featured')

        # Search results tab
        search_widget = QWidget()
        search_layout = QVBoxLayout(search_widget)
        search_layout.setContentsMargins(5, 5, 5, 5)

        self.search_list = QListWidget()
        self.search_list.setAlternatingRowColors(True)
        self.search_list.itemClicked.connect(self.on_search_result_selected)
        search_layout.addWidget(self.search_list)

        self.tabs.addTab(search_widget, 'Search Results')

        layout.addWidget(self.tabs)

        return widget

    def _create_details_panel(self):
        """Create the right panel with dataset details."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Dataset info
        info_group = QGroupBox('Dataset Information')
        info_layout = QVBoxLayout(info_group)

        self.dataset_title = QLabel('<i>Select a dataset to view details</i>')
        self.dataset_title.setWordWrap(True)
        self.dataset_title.setStyleSheet('font-size: 13px; font-weight: bold;')
        info_layout.addWidget(self.dataset_title)

        self.dataset_org = QLabel('')
        self.dataset_org.setStyleSheet('color: #666;')
        info_layout.addWidget(self.dataset_org)

        self.dataset_desc = QTextBrowser()
        self.dataset_desc.setMaximumHeight(120)
        self.dataset_desc.setOpenExternalLinks(True)
        info_layout.addWidget(self.dataset_desc)

        layout.addWidget(info_group)

        # Resources list
        resources_group = QGroupBox('Available Downloads')
        resources_layout = QVBoxLayout(resources_group)

        self.resources_list = QListWidget()
        self.resources_list.setAlternatingRowColors(True)
        self.resources_list.itemDoubleClicked.connect(self.download_resource)
        resources_layout.addWidget(self.resources_list)

        # Download options
        options_layout = QHBoxLayout()

        self.auto_add_cb = QCheckBox('Add to map after download')
        self.auto_add_cb.setChecked(True)
        options_layout.addWidget(self.auto_add_cb)

        options_layout.addStretch()

        self.download_btn = QPushButton('Download Selected')
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.download_selected)
        options_layout.addWidget(self.download_btn)

        resources_layout.addLayout(options_layout)

        layout.addWidget(resources_group)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        return widget

    def _create_bottom_bar(self):
        """Create the bottom status bar."""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)

        self.status_label = QLabel('Ready')
        layout.addWidget(self.status_label)

        layout.addStretch()

        clear_cache_btn = QPushButton('Clear Cache')
        clear_cache_btn.clicked.connect(self.clear_cache)
        layout.addWidget(clear_cache_btn)

        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        return frame

    def load_featured_datasets(self, category_filter=None, text_filter=None):
        """Load the featured datasets list with optional filters."""
        self.featured_list.clear()

        all_datasets = self.client.get_featured_datasets()
        datasets = all_datasets

        # Filter by category if specified
        if category_filter:
            datasets = [d for d in datasets if d.get('category') == category_filter]

        # Filter by text if specified
        if text_filter:
            text_lower = text_filter.lower()
            datasets = [d for d in datasets if
                       text_lower in d.get('name', '').lower() or
                       text_lower in d.get('description', '').lower() or
                       text_lower in d.get('category', '').lower() or
                       text_lower in d.get('organization', '').lower()]

        for dataset in datasets:
            item = QListWidgetItem()

            # Show category badge in the item
            category = dataset.get('category', 'General')
            item.setText(f"[{category}] {dataset['name']}\n{dataset['description'][:50]}...")
            item.setData(Qt.UserRole, dataset)

            # Set category color indicator
            color = self.client.get_category_color(category)
            item.setBackground(QColor(color).lighter(180))

            self.featured_list.addItem(item)

        # Update status with filter info
        filter_parts = []
        if category_filter:
            filter_parts.append(f"Category: {category_filter}")
        if text_filter:
            filter_parts.append(f"Search: '{text_filter}'")

        if filter_parts:
            self.status_label.setText(f"Showing {len(datasets)} of {len(all_datasets)} datasets ({', '.join(filter_parts)})")
        else:
            self.status_label.setText(f"Loaded {len(datasets)} featured datasets")

        # Switch to Featured tab when filtering
        if category_filter or text_filter:
            self.tabs.setCurrentIndex(0)

    def on_search_text_changed(self, text):
        """Handle real-time text filtering of featured datasets."""
        category = self.category_combo.currentData()
        self.load_featured_datasets(category, text if text else None)

    def on_category_changed(self, index):
        """Handle category selection change - filter featured datasets."""
        category = self.category_combo.currentData()
        text = self.search_input.text().strip()
        self.load_featured_datasets(category, text if text else None)

    def clear_filters(self):
        """Clear all filters and reset the view."""
        self.search_input.clear()
        self.category_combo.setCurrentIndex(0)  # "All Categories"
        self.load_featured_datasets()
        self.search_list.clear()
        self.tabs.setCurrentIndex(0)
        self.status_label.setText("Filters cleared")

    def search_datasets(self):
        """Search for datasets on HDX."""
        query = self.search_input.text().strip()
        category = self.category_combo.currentData()

        self.status_label.setText('Searching...')
        QApplication.processEvents()

        results = self.client.search_datasets(query, category)

        self.search_list.clear()
        for dataset in results:
            item = QListWidgetItem()
            title = dataset['title'][:50] + '...' if len(dataset['title']) > 50 else dataset['title']
            item.setText(f"{title}\n{dataset['organization']} | {dataset['num_resources']} files")
            item.setData(Qt.UserRole, dataset)
            self.search_list.addItem(item)

        self.tabs.setCurrentIndex(1)  # Switch to search results tab
        self.status_label.setText(f"Found {len(results)} datasets")

    def on_dataset_selected(self, item):
        """Handle featured dataset selection."""
        dataset = item.data(Qt.UserRole)
        self.load_dataset_details(dataset['id'])

    def on_search_result_selected(self, item):
        """Handle search result selection."""
        dataset = item.data(Qt.UserRole)
        self.load_dataset_details(dataset['id'])

    def load_dataset_details(self, dataset_id):
        """Load and display dataset details."""
        self.status_label.setText('Loading dataset details...')
        QApplication.processEvents()

        details = self.client.get_dataset_details(dataset_id)

        if not details:
            self.status_label.setText('Failed to load dataset details')
            return

        self.current_dataset = details

        # Update UI
        self.dataset_title.setText(details['title'])
        self.dataset_org.setText(f"Organization: {details['organization']} | License: {details['license']}")

        desc_html = f"""
        <p>{details['description']}</p>
        <p><a href="{details['url']}">View on HDX</a></p>
        """
        if details.get('caveats'):
            desc_html += f"<p><b>Caveats:</b> {details['caveats']}</p>"
        self.dataset_desc.setHtml(desc_html)

        # Load resources
        self.resources_list.clear()
        for res in details['resources']:
            item = QListWidgetItem()
            size_str = self._format_size(res['size']) if res['size'] else 'Unknown size'

            # Highlight GIS formats
            if res['is_gis']:
                item.setText(f"[{res['format']}] {res['name']} ({size_str})")
                item.setBackground(QColor('#e8f5e9'))  # Light green
            else:
                item.setText(f"[{res['format']}] {res['name']} ({size_str})")

            item.setData(Qt.UserRole, res)
            self.resources_list.addItem(item)

        self.download_btn.setEnabled(True)
        self.status_label.setText(f"Loaded: {details['title']}")

    def _format_size(self, size):
        """Format file size in human readable format."""
        if not size:
            return 'Unknown'

        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def download_selected(self):
        """Download the selected resource."""
        item = self.resources_list.currentItem()
        if not item:
            QMessageBox.warning(self, 'No Selection', 'Please select a resource to download.')
            return

        self.download_resource(item)

    def download_resource(self, item):
        """Download a resource and optionally add to map."""
        resource = item.data(Qt.UserRole)

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_label.setText(f"Downloading {resource['name']}...")
        self.download_btn.setEnabled(False)
        QApplication.processEvents()

        # Download in main thread (blocking request handles it well)
        file_path = self.client.download_resource(resource['url'])

        self.progress_bar.setVisible(False)
        self.download_btn.setEnabled(True)

        if file_path:
            self.status_label.setText(f"Downloaded: {os.path.basename(file_path)}")

            if self.auto_add_cb.isChecked():
                # Store layer info to add after dialog closes (prevents QGIS crash)
                self.pending_layers.append({
                    'file_path': file_path,
                    'resource': resource
                })
                self.status_label.setText(f"Downloaded: {os.path.basename(file_path)} (will be added when dialog closes)")

                QMessageBox.information(
                    self, 'Download Complete',
                    f"Downloaded: {resource['name']}\n\n"
                    f"The layer will be added to the map when you close this dialog.\n"
                    f"(This prevents QGIS stability issues)"
                )
        else:
            self.status_label.setText('Download failed')
            QMessageBox.warning(self, 'Download Failed', 'Failed to download the resource.')

    def get_pending_layers(self):
        """Get list of layers to add after dialog closes."""
        return self.pending_layers

    def add_layer_to_map(self, file_path, resource):
        """Add downloaded file to QGIS map. Called from main plugin after dialog closes."""
        format_type = resource['format'].upper()
        layer_name = resource['name'] or os.path.basename(file_path)

        try:
            # Handle ZIP files (shapefiles)
            if file_path.endswith('.zip') or format_type == 'SHP':
                file_path = self._extract_shapefile(file_path)
                if not file_path:
                    return False, "Could not extract shapefile from ZIP"

            # Determine layer type and load
            layer = None
            if format_type in ['GEOJSON', 'SHP', 'GPKG', 'GEOPACKAGE', 'KML', 'SHAPEFILE']:
                layer = QgsVectorLayer(file_path, layer_name, 'ogr')
            elif format_type == 'CSV':
                # Try to load CSV with coordinates
                uri = f"file:///{file_path}?delimiter=,&xField=longitude&yField=latitude&crs=EPSG:4326"
                layer = QgsVectorLayer(uri, layer_name, 'delimitedtext')

                if not layer.isValid():
                    # Try alternate column names
                    uri = f"file:///{file_path}?delimiter=,&xField=lon&yField=lat&crs=EPSG:4326"
                    layer = QgsVectorLayer(uri, layer_name, 'delimitedtext')

                if not layer.isValid():
                    # Load as non-spatial
                    layer = QgsVectorLayer(file_path, layer_name, 'ogr')
            elif format_type in ['TIF', 'TIFF', 'GEOTIFF']:
                layer = QgsRasterLayer(file_path, layer_name)
            else:
                # Try as vector
                layer = QgsVectorLayer(file_path, layer_name, 'ogr')

            if layer and layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                return True, layer_name
            else:
                return False, f"Could not load file as layer: {file_path}"

        except Exception as e:
            return False, str(e)

    def _extract_shapefile(self, zip_path):
        """Extract shapefile from ZIP and return path to .shp file."""
        try:
            extract_dir = os.path.join(self.client.cache_dir, 'extracted')
            os.makedirs(extract_dir, exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)

            # Find .shp file
            for root, dirs, files in os.walk(extract_dir):
                for f in files:
                    if f.endswith('.shp'):
                        return os.path.join(root, f)

            # If no .shp, look for other formats
            for root, dirs, files in os.walk(extract_dir):
                for f in files:
                    if f.endswith(('.geojson', '.gpkg', '.kml')):
                        return os.path.join(root, f)

            return None

        except zipfile.BadZipFile:
            return zip_path  # Not a zip file, return original

    def clear_cache(self):
        """Clear the download cache."""
        reply = QMessageBox.question(
            self, 'Clear Cache',
            'This will delete all downloaded HDX files from the cache.\nContinue?',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.client.clear_cache()
            self.status_label.setText('Cache cleared')

    def closeEvent(self, event):
        """Handle dialog close."""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.terminate()
            self.download_thread.wait()
        super().closeEvent(event)
