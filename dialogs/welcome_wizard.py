# -*- coding: utf-8 -*-
"""
Welcome Wizard for Ethiopia Data Loader.

Provides a first-run onboarding experience for new users.
"""

from qgis.PyQt.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QGroupBox, QRadioButton,
    QListWidget, QListWidgetItem, QFrame, QProgressBar,
    QSpacerItem, QSizePolicy, QWidget, QButtonGroup
)
from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QFont, QPixmap, QIcon, QColor


class WelcomePage(QWizardPage):
    """Welcome page - Introduction."""

    def __init__(self, plugin_dir, parent=None):
        super().__init__(parent)
        self.plugin_dir = plugin_dir
        self.setTitle("")
        self.setSubTitle("")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Header
        header = QLabel()
        header.setText(
            '<div style="text-align: center;">'
            '<h1 style="color: #2c3e50; margin-bottom: 5px;">Welcome to Sudan Data Loader</h1>'
            '<p style="color: #7f8c8d; font-size: 14px;">Your comprehensive GIS toolkit for Sudan</p>'
            '</div>'
        )
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Version badge
        version_label = QLabel('<span style="background-color: #3498db; color: white; padding: 5px 15px; border-radius: 10px;">Version 2.1.0</span>')
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

        layout.addSpacing(20)

        # Feature highlights
        features_frame = QFrame()
        features_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        features_layout = QVBoxLayout(features_frame)

        features_title = QLabel('<b style="font-size: 13px;">What\'s Included:</b>')
        features_layout.addWidget(features_title)

        features = [
            ("Administrative Boundaries", "18 States, Localities, and more"),
            ("Humanitarian Data (HDX)", "Health, Education, Conflict data"),
            ("Analysis Tools", "Statistics, Reports, Validation"),
            ("Export & Share", "Multiple formats, Print layouts"),
        ]

        for title, desc in features:
            feature_widget = QWidget()
            feature_layout = QHBoxLayout(feature_widget)
            feature_layout.setContentsMargins(0, 5, 0, 5)

            bullet = QLabel("✓")
            bullet.setStyleSheet("color: #27ae60; font-size: 16px; font-weight: bold;")
            bullet.setFixedWidth(25)
            feature_layout.addWidget(bullet)

            text = QLabel(f"<b>{title}</b><br><span style='color: #666;'>{desc}</span>")
            feature_layout.addWidget(text, 1)

            features_layout.addWidget(feature_widget)

        layout.addWidget(features_frame)

        layout.addStretch()

        # Footer
        footer = QLabel(
            '<p style="color: #95a5a6; text-align: center; font-size: 11px;">'
            'This wizard will help you get started in just a few steps.'
            '</p>'
        )
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)


class DataSetupPage(QWizardPage):
    """Data setup page - Check/download data."""

    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.setTitle("Data Setup")
        self.setSubTitle("Let's make sure you have the Sudan administrative data")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Status check
        self.status_frame = QFrame()
        self.status_frame.setStyleSheet("""
            QFrame {
                background-color: #fff3cd;
                border: 1px solid #ffc107;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        status_layout = QVBoxLayout(self.status_frame)

        self.status_icon = QLabel("⏳")
        self.status_icon.setStyleSheet("font-size: 24px;")
        self.status_icon.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.status_icon)

        self.status_label = QLabel("Checking data availability...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)

        layout.addWidget(self.status_frame)

        # Data layers info
        layers_group = QGroupBox("Included Data Layers")
        layers_layout = QVBoxLayout(layers_group)

        layers = [
            ("Admin 0 - Country", "Sudan national boundary"),
            ("Admin 1 - States", "18 state boundaries"),
            ("Admin 2 - Localities", "Locality boundaries"),
            ("Admin Lines", "Boundary lines"),
            ("Admin Points", "Key locations"),
        ]

        for name, desc in layers:
            layer_label = QLabel(f"• <b>{name}</b> - {desc}")
            layers_layout.addWidget(layer_label)

        layout.addWidget(layers_group)

        # Download button (hidden initially)
        self.download_btn = QPushButton("Download Data Now")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.download_btn.clicked.connect(self.download_data)
        self.download_btn.setVisible(False)
        layout.addWidget(self.download_btn)

        layout.addStretch()

    def initializePage(self):
        """Check data status when page is shown."""
        self.check_data_status()

    def check_data_status(self):
        """Check if data is available."""
        import os

        data_dir, _ = self.plugin._get_data_directories()

        if data_dir and os.path.exists(data_dir):
            # Check for actual data files
            gpkg_files = [f for f in os.listdir(data_dir) if f.endswith('.gpkg')]
            if gpkg_files:
                self.show_success(f"Data found! ({len(gpkg_files)} layers available)")
                return

        self.show_need_download()

    def show_success(self, message):
        """Show success status."""
        self.status_frame.setStyleSheet("""
            QFrame {
                background-color: #d4edda;
                border: 1px solid #28a745;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        self.status_icon.setText("✅")
        self.status_label.setText(f"<b>{message}</b><br>You're ready to go!")
        self.download_btn.setVisible(False)

    def show_need_download(self):
        """Show download needed status."""
        self.status_frame.setStyleSheet("""
            QFrame {
                background-color: #fff3cd;
                border: 1px solid #ffc107;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        self.status_icon.setText("⚠️")
        self.status_label.setText(
            "<b>Data not found</b><br>"
            "Click the button below to download the Sudan administrative data."
        )
        self.download_btn.setVisible(True)

    def download_data(self):
        """Trigger data download."""
        self.download_btn.setEnabled(False)
        self.download_btn.setText("Downloading...")
        self.status_label.setText("Downloading data, please wait...")

        # Call the plugin's download method
        try:
            self.plugin.download_update()
            self.check_data_status()
        except Exception as e:
            self.status_label.setText(f"Download failed: {str(e)}")
        finally:
            self.download_btn.setEnabled(True)
            self.download_btn.setText("Download Data Now")


class QuickStartPage(QWizardPage):
    """Quick start options page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Quick Start Options")
        self.setSubTitle("Choose what you'd like to do first")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Quick actions
        self.action_group = QButtonGroup(self)

        actions = [
            ("load_all", "Load All Sudan Layers", "Load all administrative boundaries to the map", True),
            ("load_select", "Choose Specific Layers", "Select which layers to load", False),
            ("browse_hdx", "Browse Humanitarian Data", "Explore HDX datasets (Health, Education, etc.)", False),
            ("explore", "Just Explore the Menu", "I'll explore the features myself", False),
        ]

        for i, (action_id, title, desc, checked) in enumerate(actions):
            action_frame = QFrame()
            action_frame.setStyleSheet("""
                QFrame {
                    background-color: #f8f9fa;
                    border: 2px solid #dee2e6;
                    border-radius: 8px;
                    padding: 10px;
                }
                QFrame:hover {
                    border-color: #3498db;
                    background-color: #e8f4fc;
                }
            """)
            action_layout = QHBoxLayout(action_frame)

            radio = QRadioButton()
            radio.setChecked(checked)
            self.action_group.addButton(radio, i)
            action_layout.addWidget(radio)

            text_widget = QWidget()
            text_layout = QVBoxLayout(text_widget)
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(2)

            title_label = QLabel(f"<b>{title}</b>")
            text_layout.addWidget(title_label)

            desc_label = QLabel(f"<span style='color: #666;'>{desc}</span>")
            text_layout.addWidget(desc_label)

            action_layout.addWidget(text_widget, 1)

            # Store action_id
            radio.setProperty("action_id", action_id)

            layout.addWidget(action_frame)

        layout.addStretch()

        # Register field for wizard
        self.registerField("quick_action", self.action_group.buttons()[0])

    def get_selected_action(self):
        """Get the selected quick action."""
        for btn in self.action_group.buttons():
            if btn.isChecked():
                return btn.property("action_id")
        return "explore"


class FeaturesOverviewPage(QWizardPage):
    """Features overview page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Feature Overview")
        self.setSubTitle("Here's what you can do with Sudan Data Loader")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)

        # Use a scroll area for the features
        from qgis.PyQt.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(8)
        scroll_layout.setContentsMargins(5, 5, 5, 5)

        # Feature categories - simplified without emojis for better compatibility
        categories = [
            ("Data & Layers", "#3498db", [
                "Load administrative boundaries",
                "Download humanitarian data from HDX",
                "Add basemaps (OSM, Satellite, etc.)"
            ]),
            ("Search & Navigate", "#27ae60", [
                "Search by state/locality name",
                "Quick bookmarks for all 18 states",
                "Zoom to any administrative area"
            ]),
            ("Analysis & Reports", "#9b59b6", [
                "View statistics and area calculations",
                "Generate PDF/HTML reports",
                "Query and filter data"
            ]),
            ("Styling & Labels", "#e67e22", [
                "Quick labeling (English/Arabic)",
                "Style presets for different uses",
                "Sketching and drawing tools"
            ]),
            ("Export & Share", "#e74c3c", [
                "Export to GeoJSON, Shapefile, KML",
                "Processing tools (Clip, Buffer)",
                "Data validation checker"
            ]),
        ]

        for cat_title, color, features in categories:
            cat_frame = QFrame()
            cat_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: #f8f9fa;
                    border-left: 4px solid {color};
                    border-radius: 4px;
                    padding: 5px;
                }}
            """)
            cat_frame.setMinimumHeight(70)

            cat_layout = QVBoxLayout(cat_frame)
            cat_layout.setSpacing(2)
            cat_layout.setContentsMargins(10, 8, 10, 8)

            title = QLabel(f"<b style='color: {color};'>{cat_title}</b>")
            cat_layout.addWidget(title)

            features_text = " | ".join(features)
            feat_label = QLabel(features_text)
            feat_label.setWordWrap(True)
            feat_label.setStyleSheet("color: #555; font-size: 10px;")
            cat_layout.addWidget(feat_label)

            scroll_layout.addWidget(cat_frame)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        # Tip at the bottom (outside scroll area)
        tip_label = QLabel(
            '<p style="color: #666; font-style: italic;">'
            'Tip: Access all features from the <b>Sudan Data Loader</b> menu'
            '</p>'
        )
        tip_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(tip_label)


class FinishPage(QWizardPage):
    """Finish page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("You're All Set!")
        self.setSubTitle("")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Success message
        success_label = QLabel(
            '<div style="text-align: center;">'
            '<p style="font-size: 48px;">🎉</p>'
            '<h2 style="color: #27ae60;">Ready to Go!</h2>'
            '<p style="color: #666;">You can now start using Sudan Data Loader</p>'
            '</div>'
        )
        success_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(success_label)

        layout.addSpacing(20)

        # Quick links
        links_frame = QFrame()
        links_frame.setStyleSheet("""
            QFrame {
                background-color: #e8f4fc;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        links_layout = QVBoxLayout(links_frame)

        links_title = QLabel("<b>Quick Access:</b>")
        links_layout.addWidget(links_title)

        links = [
            "• Menu: <b>Sudan Data Loader</b> in the menu bar",
            "• Toolbar: Quick buttons for common actions",
            "• Panels: View → Panels for Search, Bookmarks, Statistics",
        ]

        for link in links:
            link_label = QLabel(link)
            links_layout.addWidget(link_label)

        layout.addWidget(links_frame)

        layout.addStretch()

        # Don't show again checkbox
        self.dont_show_cb = QCheckBox("Don't show this wizard again")
        self.dont_show_cb.setChecked(False)
        layout.addWidget(self.dont_show_cb)

        # Register field
        self.registerField("dont_show_again", self.dont_show_cb)


class WelcomeWizard(QWizard):
    """Welcome wizard for first-time users."""

    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.iface = plugin.iface
        self.settings_manager = plugin.settings_manager

        self.setWindowTitle("Sudan Data Loader - Welcome")
        self.setMinimumSize(550, 500)
        self.setWizardStyle(QWizard.ModernStyle)

        # Set button text
        self.setButtonText(QWizard.NextButton, "Next →")
        self.setButtonText(QWizard.BackButton, "← Back")
        self.setButtonText(QWizard.FinishButton, "Get Started!")
        self.setButtonText(QWizard.CancelButton, "Skip")

        # Add pages
        self.welcome_page = WelcomePage(plugin.plugin_dir)
        self.data_page = DataSetupPage(plugin)
        self.quick_start_page = QuickStartPage()
        self.features_page = FeaturesOverviewPage()
        self.finish_page = FinishPage()

        self.addPage(self.welcome_page)
        self.addPage(self.data_page)
        self.addPage(self.quick_start_page)
        self.addPage(self.features_page)
        self.addPage(self.finish_page)

        # Style the wizard
        self.setStyleSheet("""
            QWizard {
                background-color: white;
            }
            QWizardPage {
                background-color: white;
            }
        """)

    def accept(self):
        """Handle wizard completion."""
        # Save "don't show again" preference
        if self.finish_page.dont_show_cb.isChecked():
            self.settings_manager.set('wizard_shown', True)

        # Execute selected quick action
        action = self.quick_start_page.get_selected_action()

        super().accept()

        # Perform the selected action after wizard closes
        if action == "load_all":
            self.plugin.load_all_layers()
        elif action == "load_select":
            self.plugin.show_layer_selection()
        elif action == "browse_hdx":
            self.plugin.show_hdx_browser()
        # "explore" does nothing - user will explore themselves

    def reject(self):
        """Handle wizard cancellation (Skip)."""
        # Still mark as shown if skipped
        self.settings_manager.set('wizard_shown', True)
        super().reject()

    @staticmethod
    def should_show(settings_manager):
        """Check if wizard should be shown."""
        return not settings_manager.get('wizard_shown', False)
