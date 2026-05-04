# -*- coding: utf-8 -*-
"""
Bookmarks Panel for Ethiopia Data Loader.

Pre-populated bookmarks for Ethiopia's 14 states plus custom bookmarks.
"""

from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QGroupBox,
    QInputDialog, QMessageBox, QMenu
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsRectangle


class BookmarksPanel(QDockWidget):
    """Dock widget for quick navigation bookmarks."""

    # Pre-defined Ethiopia state bookmarks (approximate centers and extents)
    SUDAN_STATES = [
        {'name': 'Khartoum', 'name_ar': 'الخرطوم', 'xmin': 31.5, 'ymin': 15.0, 'xmax': 34.0, 'ymax': 16.5},
        {'name': 'Northern', 'name_ar': 'الشمالية', 'xmin': 26.0, 'ymin': 17.5, 'xmax': 33.0, 'ymax': 22.0},
        {'name': 'River Nile', 'name_ar': 'نهر النيل', 'xmin': 32.0, 'ymin': 16.5, 'xmax': 35.0, 'ymax': 20.0},
        {'name': 'Red Sea', 'name_ar': 'البحر الأحمر', 'xmin': 34.5, 'ymin': 17.5, 'xmax': 38.5, 'ymax': 22.0},
        {'name': 'Kassala', 'name_ar': 'كسلا', 'xmin': 35.0, 'ymin': 14.0, 'xmax': 37.0, 'ymax': 17.0},
        {'name': 'Gedaref', 'name_ar': 'القضارف', 'xmin': 33.5, 'ymin': 12.5, 'xmax': 36.5, 'ymax': 15.5},
        {'name': 'Sennar', 'name_ar': 'سنار', 'xmin': 32.5, 'ymin': 12.5, 'xmax': 35.0, 'ymax': 14.5},
        {'name': 'Blue Nile', 'name_ar': 'النيل الأزرق', 'xmin': 33.0, 'ymin': 10.0, 'xmax': 35.5, 'ymax': 12.5},
        {'name': 'White Nile', 'name_ar': 'النيل الأبيض', 'xmin': 31.0, 'ymin': 12.0, 'xmax': 33.0, 'ymax': 15.0},
        {'name': 'Gezira', 'name_ar': 'الجزيرة', 'xmin': 32.0, 'ymin': 13.5, 'xmax': 34.0, 'ymax': 15.5},
        {'name': 'North Kordofan', 'name_ar': 'شمال كردفان', 'xmin': 27.0, 'ymin': 12.5, 'xmax': 32.0, 'ymax': 16.5},
        {'name': 'South Kordofan', 'name_ar': 'جنوب كردفان', 'xmin': 28.0, 'ymin': 9.5, 'xmax': 31.5, 'ymax': 12.5},
        {'name': 'West Kordofan', 'name_ar': 'غرب كردفان', 'xmin': 25.5, 'ymin': 10.0, 'xmax': 29.0, 'ymax': 14.0},
        {'name': 'North Darfur', 'name_ar': 'شمال دارفور', 'xmin': 22.0, 'ymin': 14.0, 'xmax': 27.5, 'ymax': 20.0},
        {'name': 'West Darfur', 'name_ar': 'غرب دارفور', 'xmin': 21.5, 'ymin': 11.5, 'xmax': 24.0, 'ymax': 14.5},
        {'name': 'Central Darfur', 'name_ar': 'وسط دارفور', 'xmin': 22.5, 'ymin': 12.5, 'xmax': 25.5, 'ymax': 15.0},
        {'name': 'South Darfur', 'name_ar': 'جنوب دارفور', 'xmin': 23.0, 'ymin': 9.5, 'xmax': 27.0, 'ymax': 13.0},
        {'name': 'East Darfur', 'name_ar': 'شرق دارفور', 'xmin': 24.5, 'ymin': 10.5, 'xmax': 28.0, 'ymax': 14.0},
    ]

    # Full Ethiopia extent
    SUDAN_EXTENT = {'name': 'Sudan (Full)', 'xmin': 21.5, 'ymin': 8.5, 'xmax': 38.5, 'ymax': 22.5}

    def __init__(self, iface, settings_manager=None, parent=None):
        """
        Initialize the bookmarks panel.

        :param iface: QGIS interface instance
        :param settings_manager: SettingsManager instance (optional)
        :param parent: Parent widget
        """
        super().__init__('Sudan Bookmarks', parent)
        self.iface = iface
        self.settings_manager = settings_manager
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.custom_bookmarks = []
        self.setup_ui()
        self.load_custom_bookmarks()

    def setup_ui(self):
        """Set up the panel UI."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Sudan extent button
        full_sudan_btn = QPushButton('Zoom to Sudan')
        full_sudan_btn.setStyleSheet('font-weight: bold;')
        full_sudan_btn.clicked.connect(self.zoom_to_sudan)
        layout.addWidget(full_sudan_btn)

        # States bookmarks
        states_group = QGroupBox('States (18)')
        states_layout = QVBoxLayout(states_group)

        self.states_list = QListWidget()
        self.states_list.itemDoubleClicked.connect(self.on_state_double_clicked)
        self.states_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.states_list.customContextMenuRequested.connect(self.show_states_context_menu)

        # Populate states
        for state in self.SUDAN_STATES:
            item = QListWidgetItem(f"{state['name']} ({state['name_ar']})")
            item.setData(Qt.UserRole, state)
            self.states_list.addItem(item)

        states_layout.addWidget(self.states_list)

        layout.addWidget(states_group)

        # Custom bookmarks
        custom_group = QGroupBox('Custom Bookmarks')
        custom_layout = QVBoxLayout(custom_group)

        self.custom_list = QListWidget()
        self.custom_list.itemDoubleClicked.connect(self.on_custom_double_clicked)
        self.custom_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.custom_list.customContextMenuRequested.connect(self.show_custom_context_menu)
        custom_layout.addWidget(self.custom_list)

        # Custom bookmark buttons
        btn_layout = QHBoxLayout()

        add_btn = QPushButton('Add Current View')
        add_btn.clicked.connect(self.add_current_view)
        btn_layout.addWidget(add_btn)

        remove_btn = QPushButton('Remove')
        remove_btn.clicked.connect(self.remove_custom_bookmark)
        btn_layout.addWidget(remove_btn)

        custom_layout.addLayout(btn_layout)

        layout.addWidget(custom_group)

        self.setWidget(widget)

    def zoom_to_sudan(self):
        """Zoom to full Sudan extent."""
        extent = self.SUDAN_EXTENT
        rect = QgsRectangle(extent['xmin'], extent['ymin'], extent['xmax'], extent['ymax'])
        self.iface.mapCanvas().setExtent(rect)
        self.iface.mapCanvas().refresh()

    def on_state_double_clicked(self, item):
        """Handle double-click on state bookmark."""
        state = item.data(Qt.UserRole)
        if state:
            rect = QgsRectangle(state['xmin'], state['ymin'], state['xmax'], state['ymax'])
            self.iface.mapCanvas().setExtent(rect)
            self.iface.mapCanvas().refresh()

    def on_custom_double_clicked(self, item):
        """Handle double-click on custom bookmark."""
        bookmark = item.data(Qt.UserRole)
        if bookmark:
            rect = QgsRectangle(
                bookmark['xmin'], bookmark['ymin'],
                bookmark['xmax'], bookmark['ymax']
            )
            self.iface.mapCanvas().setExtent(rect)
            self.iface.mapCanvas().refresh()

    def show_states_context_menu(self, position):
        """Show context menu for states list."""
        item = self.states_list.itemAt(position)
        if not item:
            return

        menu = QMenu()
        zoom_action = menu.addAction('Zoom to State')
        zoom_action.triggered.connect(lambda: self.on_state_double_clicked(item))

        menu.exec_(self.states_list.mapToGlobal(position))

    def show_custom_context_menu(self, position):
        """Show context menu for custom bookmarks list."""
        item = self.custom_list.itemAt(position)
        if not item:
            return

        menu = QMenu()
        zoom_action = menu.addAction('Zoom to Bookmark')
        zoom_action.triggered.connect(lambda: self.on_custom_double_clicked(item))

        rename_action = menu.addAction('Rename')
        rename_action.triggered.connect(lambda: self.rename_bookmark(item))

        delete_action = menu.addAction('Delete')
        delete_action.triggered.connect(lambda: self.delete_bookmark(item))

        menu.exec_(self.custom_list.mapToGlobal(position))

    def add_current_view(self):
        """Add current map view as a custom bookmark."""
        # Get current extent
        extent = self.iface.mapCanvas().extent()

        # Ask for bookmark name
        name, ok = QInputDialog.getText(
            self, 'Add Bookmark',
            'Enter bookmark name:'
        )

        if ok and name:
            bookmark = {
                'name': name,
                'xmin': extent.xMinimum(),
                'ymin': extent.yMinimum(),
                'xmax': extent.xMaximum(),
                'ymax': extent.yMaximum()
            }
            self.custom_bookmarks.append(bookmark)

            # Add to list
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, bookmark)
            self.custom_list.addItem(item)

            # Save
            self.save_custom_bookmarks()

    def remove_custom_bookmark(self):
        """Remove the selected custom bookmark."""
        current_item = self.custom_list.currentItem()
        if current_item:
            self.delete_bookmark(current_item)

    def delete_bookmark(self, item):
        """Delete a bookmark item."""
        bookmark = item.data(Qt.UserRole)
        if bookmark in self.custom_bookmarks:
            self.custom_bookmarks.remove(bookmark)

        row = self.custom_list.row(item)
        self.custom_list.takeItem(row)
        self.save_custom_bookmarks()

    def rename_bookmark(self, item):
        """Rename a bookmark."""
        current_name = item.text()
        new_name, ok = QInputDialog.getText(
            self, 'Rename Bookmark',
            'Enter new name:',
            text=current_name
        )

        if ok and new_name:
            item.setText(new_name)
            bookmark = item.data(Qt.UserRole)
            bookmark['name'] = new_name
            self.save_custom_bookmarks()

    def load_custom_bookmarks(self):
        """Load custom bookmarks from settings."""
        if self.settings_manager:
            self.custom_bookmarks = self.settings_manager.get_custom_bookmarks()
            for bookmark in self.custom_bookmarks:
                item = QListWidgetItem(bookmark['name'])
                item.setData(Qt.UserRole, bookmark)
                self.custom_list.addItem(item)

    def save_custom_bookmarks(self):
        """Save custom bookmarks to settings."""
        if self.settings_manager:
            self.settings_manager.set_custom_bookmarks(self.custom_bookmarks)
