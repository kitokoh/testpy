# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QTextBrowser, QApplication, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize # Added QSize
import sys
import os

# Adjust path to import from root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from db.cruds import transporters_crud
except ImportError:
    # Fallback for direct execution if db module structure is not immediately found
    # This might happen if the script is run directly without the project root in PYTHONPATH
    print("Attempting fallback import for transporters_crud due to ImportError")
    from db.cruds import transporters_crud


class CarrierMapDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Carrier Map and Information"))
        self.setMinimumSize(800, 600)
        self.transporters = []  # Initialize transporters list
        self.setup_ui()
        self.load_carrier_data()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)

        # --- Left Pane (Carrier List & Details) ---
        left_pane_layout = QVBoxLayout()

        self.carrier_list_widget = QListWidget()
        self.carrier_list_widget.setObjectName("carrierListWidget")
        self.carrier_list_widget.currentItemChanged.connect(self.display_carrier_details)
        left_pane_layout.addWidget(self.carrier_list_widget)

        details_label = QLabel(self.tr("Carrier Details:"))
        left_pane_layout.addWidget(details_label)

        self.carrier_details_browser = QTextBrowser()
        self.carrier_details_browser.setObjectName("carrierDetailsBrowser")
        self.carrier_details_browser.setMinimumHeight(200) # Ensure it has some height
        left_pane_layout.addWidget(self.carrier_details_browser)

        left_pane_widget = QLabel() # Using QLabel as a container for the layout
        left_pane_widget.setLayout(left_pane_layout)
        left_pane_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)


        # --- Right Pane (Map Placeholder) ---
        right_pane_layout = QVBoxLayout()
        self.map_placeholder_label = QLabel(self.tr("Map Placeholder - Integration Pending"))
        self.map_placeholder_label.setObjectName("mapPlaceholderLabel")
        self.map_placeholder_label.setAlignment(Qt.AlignCenter)
        self.map_placeholder_label.setStyleSheet("background-color: lightgrey; border: 1px solid grey;")
        self.map_placeholder_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Make it expand
        right_pane_layout.addWidget(self.map_placeholder_label)

        right_pane_widget = QLabel() # Using QLabel as a container
        right_pane_widget.setLayout(right_pane_layout)
        right_pane_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


        main_layout.addWidget(left_pane_widget, 1) # Give left pane a stretch factor of 1
        main_layout.addWidget(right_pane_widget, 2) # Give right pane a stretch factor of 2 (larger)


        # --- Bottom Pane for Close Button ---
        # To ensure the button is below everything and centered, we'll wrap main_layout in another QVBoxLayout
        outer_layout = QVBoxLayout(self)
        outer_layout.addLayout(main_layout)

        self.close_button = QPushButton(self.tr("Close"))
        self.close_button.setObjectName("closeButton")
        self.close_button.clicked.connect(self.accept)

        button_layout = QHBoxLayout() # To center the button
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        button_layout.addStretch()
        outer_layout.addLayout(button_layout)

        self.setLayout(outer_layout) # Set the outermost layout for the dialog


    def load_carrier_data(self):
        self.carrier_list_widget.clear()
        try:
            self.transporters = transporters_crud.get_all_transporters()
            if not self.transporters:
                item = QListWidgetItem(self.tr("No carriers found."))
                item.setData(Qt.UserRole, None) # No data
                self.carrier_list_widget.addItem(item)
                return

            for transporter in self.transporters:
                item_text = transporter.get('name', self.tr('Unnamed Carrier'))
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, transporter)  # Store the whole dict
                self.carrier_list_widget.addItem(item)

            if self.carrier_list_widget.count() > 0:
                self.carrier_list_widget.setCurrentRow(0) # Select the first item

        except Exception as e:
            print(f"Error loading carrier data: {e}")
            item = QListWidgetItem(self.tr("Error loading carriers."))
            item.setData(Qt.UserRole, None)
            self.carrier_list_widget.addItem(item)
            self.carrier_details_browser.setHtml(f"<p style='color:red;'>{self.tr('Could not load carrier data:')}<br>{e}</p>")


    def display_carrier_details(self, current_item, previous_item):
        # previous_item is unused but part of the signal
        if not current_item:
            self.carrier_details_browser.clear()
            return

        transporter_data = current_item.data(Qt.UserRole)
        if not transporter_data:
            self.carrier_details_browser.setHtml(f"<p>{self.tr('No details available for this item.')}</p>")
            return

        details_html = f"""
            <h3>{self.tr('Carrier Details')}</h3>
            <p><b>{self.tr('Name:')}</b> {transporter_data.get('name', 'N/A')}</p>
            <p><b>{self.tr('Contact Person:')}</b> {transporter_data.get('contact_person', 'N/A')}</p>
            <p><b>{self.tr('Phone:')}</b> {transporter_data.get('phone', 'N/A')}</p>
            <p><b>{self.tr('Email:')}</b> {transporter_data.get('email', 'N/A')}</p>
            <p><b>{self.tr('Address:')}</b> {transporter_data.get('address', 'N/A')}</p>
            <p><b>{self.tr('Service Area:')}</b> {transporter_data.get('service_area', 'N/A')}</p>
            <hr>
            <p><b>{self.tr('Latitude:')}</b> {transporter_data.get('latitude', 'N/A')}</p>
            <p><b>{self.tr('Longitude:')}</b> {transporter_data.get('longitude', 'N/A')}</p>
            <p><b>{self.tr('Current Cargo:')}</b> {transporter_data.get('current_cargo') if transporter_data.get('current_cargo') else 'N/A'}</p>
        """
        self.carrier_details_browser.setHtml(details_html)

    # Optional: Override sizeHint for better default sizing if needed
    # def sizeHint(self):
    #     return QSize(800, 600)

if __name__ == '__main__':
    # Ensure the path includes the project root for db imports if run directly
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root_from_main = os.path.dirname(current_dir) # Go up one level from 'dialogs'
    if project_root_from_main not in sys.path:
        sys.path.insert(0, project_root_from_main)

    # Need to re-import if path was adjusted, for the __main__ block's context
    # This is a bit tricky for scripts run directly vs imported.
    # The try-except block for transporters_crud import at the top should handle most cases.

    app = QApplication(sys.argv)

    # Initialize DB (example, replace with your actual DB init logic if needed for testing)
    # This is crucial if get_all_transporters() relies on an initialized DB
    try:
        from db.init_schema import initialize_database
        # Determine DB path relative to project root
        db_path = os.path.join(project_root_from_main, "app_data.db") # Example path

        # A simple way to ensure config.py is findable and sets DATABASE_PATH
        # This is a workaround for direct script execution; normally config is imported from root
        class MockConfig:
            DATABASE_PATH = db_path
            DEFAULT_ADMIN_USERNAME = "admin_test" # Dummy value
            DEFAULT_ADMIN_PASSWORD = "password_test" # Dummy value

        import config as app_config # Try to import actual config
        app_config.DATABASE_PATH = db_path # Override if needed for testing

        if not os.path.exists(db_path):
            print(f"Database not found at {db_path}, initializing for test...")
            # Temporarily patch config if it's used by init_schema directly
            sys.modules['config'] = MockConfig
            initialize_database()
            # Restore original config module if it was loaded
            if 'app_config' in locals():
                 sys.modules['config'] = app_config
            print("Test database initialized.")
        else:
            print(f"Using existing database at {db_path} for test.")

    except ImportError as e:
        print(f"Could not import or initialize database for test: {e}")
    except Exception as e_db_init:
        print(f"Error during test database initialization: {e_db_init}")


    dialog = CarrierMapDialog()
    dialog.show()
    sys.exit(app.exec_())
