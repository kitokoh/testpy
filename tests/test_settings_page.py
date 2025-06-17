# tests/test_settings_page.py
import unittest
from unittest.mock import MagicMock, patch

# Add project root to sys.path to allow importing settings_page and utils
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now import the class to be tested
# This import might fail if settings_page.py has top-level Qt imports that
# can't resolve without a QApplication. We'll mock relevant Qt parts.

# Mock PyQt5 classes before importing SettingsPage
mock_qwidget = MagicMock()
mock_qlineedit = MagicMock()
mock_qcombobox = MagicMock()
mock_qspinbox = MagicMock()
mock_qcheckbox = MagicMock()
mock_qmessagebox = MagicMock()
mock_qfiledialog = MagicMock()
mock_qicon = MagicMock()
mock_qdialog = MagicMock() # Added QDialog mock

sys.modules['PyQt5.QtWidgets'] = MagicMock()
sys.modules['PyQt5.QtWidgets'].QWidget = mock_qwidget
sys.modules['PyQt5.QtWidgets'].QLineEdit = mock_qlineedit
sys.modules['PyQt5.QtWidgets'].QComboBox = mock_qcombobox
sys.modules['PyQt5.QtWidgets'].QSpinBox = mock_qspinbox
sys.modules['PyQt5.QtWidgets'].QCheckBox = mock_qcheckbox
sys.modules['PyQt5.QtWidgets'].QMessageBox = mock_qmessagebox
sys.modules['PyQt5.QtWidgets'].QFileDialog = mock_qfiledialog
sys.modules['PyQt5.QtWidgets'].QDialog = mock_qdialog # Added QDialog to QtWidgets mock
sys.modules['PyQt5.QtWidgets'].QDialogButtonBox = MagicMock() # Mock QDialogButtonBox
sys.modules['PyQt5.QtWidgets'].QFormLayout = MagicMock()
sys.modules['PyQt5.QtWidgets'].QVBoxLayout = MagicMock()
sys.modules['PyQt5.QtWidgets'].QHBoxLayout = MagicMock()
sys.modules['PyQt5.QtWidgets'].QLabel = MagicMock()
sys.modules['PyQt5.QtWidgets'].QTableWidget = MagicMock()
sys.modules['PyQt5.QtWidgets'].QTableWidgetItem = MagicMock()
sys.modules['PyQt5.QtWidgets'].QAbstractItemView = MagicMock()
sys.modules['PyQt5.QtWidgets'].QPushButton = MagicMock()


sys.modules['PyQt5.QtGui'] = MagicMock()
sys.modules['PyQt5.QtGui'].QIcon = mock_qicon
sys.modules['PyQt5.QtCore'] = MagicMock()
sys.modules['PyQt5.QtCore'].Qt = MagicMock() # Mock Qt attributes like Qt.UserRole


# Mock other dependencies that might be problematic in a non-GUI environment
sys.modules['db'] = MagicMock()
# Mock specific CRUD instances if settings_page imports them directly
# For now, assuming 'db' module mock is enough for top-level import.
# If settings_page.py does "from db.cruds.users_crud import users_crud_instance",
# that needs specific mocking as done for users_crud_instance below.

sys.modules['dialogs.transporter_dialog'] = MagicMock()
sys.modules['dialogs.freight_forwarder_dialog'] = MagicMock()
sys.modules['dialogs.user_dialog'] = MagicMock() # UserDialog is part of UserManagementTab
sys.modules['company_management'] = MagicMock()
sys.modules['auth.roles'] = MagicMock()

# Mock users_crud_instance as it's imported at the top level of settings_page.py
mock_users_crud = MagicMock()
sys.modules['db.cruds.users_crud'] = MagicMock()
sys.modules['db.cruds.users_crud'].users_crud_instance = mock_users_crud

# Mock utils module as it's imported by settings_page for save_config
# and potentially other functions like get_default_db_path
mock_utils = MagicMock()
sys.modules['utils'] = mock_utils


from settings_page import SettingsPage # Now this should import

class TestSettingsPageDataHandling(unittest.TestCase):

    @patch('settings_page.users_crud_instance.get_user_by_id') # Patch for __init__
    @patch('settings_page.db_manager.get_all_transporters') # Patch for _load_transporters_table
    @patch('settings_page.db_manager.get_all_freight_forwarders') # Patch for _load_forwarders_table
    def setUp(self, mock_get_all_ff, mock_get_all_trans, mock_get_user_init):
        # Mock main_config that SettingsPage expects
        self.mock_main_config = {
            "templates_dir": "path/to/templates",
            "clients_dir": "path/to/clients",
            "language": "en",
            "default_reminder_days": 15,
            "session_timeout_minutes": 60,
            "database_path": "app.db",
            "google_maps_review_url": "https://maps.google.com",
            "show_initial_setup_on_startup": True,
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "smtp_user": "user@example.com",
            "smtp_password": "password123"
            # Add any other keys SettingsPage expects from main_config during init or loading
        }

        self.mock_app_root_dir = "/fake/app/root"
        self.mock_current_user_id = "test_user_123"

        # Setup return values for patched methods called during setUp / __init__
        mock_get_user_init.return_value = {'role': 'administrator'} # Assume admin for full UI setup
        mock_get_all_trans.return_value = [] # No transporters for basic setup
        mock_get_all_ff.return_value = [] # No forwarders for basic setup

        # Mock os.getcwd for db_path_input default in _load_general_tab_data
        with patch('os.getcwd', return_value='/fake/cwd'):
            self.settings_page = SettingsPage(
                main_config=self.mock_main_config.copy(),
                app_root_dir=self.mock_app_root_dir,
                current_user_id=self.mock_current_user_id,
                parent=None # In tests, parent is often None or a MagicMock
            )

        # Mock UI elements that get_general_settings_data reads from
        # These are created in _setup_general_tab, so we assign our mocks to the instance
        self.settings_page.templates_dir_input = MagicMock(spec=mock_qlineedit)
        self.settings_page.clients_dir_input = MagicMock(spec=mock_qlineedit)
        self.settings_page.interface_lang_combo = MagicMock(spec=mock_qcombobox)
        # lang_display_to_code is populated in _setup_general_tab, mock it directly if self.tr is complex
        self.settings_page.lang_display_to_code = {self.tr("English (en)"): "en", self.tr("French (fr)"): "fr"}

        self.settings_page.reminder_days_spinbox = MagicMock(spec=mock_qspinbox)
        self.settings_page.session_timeout_spinbox = MagicMock(spec=mock_qspinbox)
        self.settings_page.google_maps_url_input = MagicMock(spec=mock_qlineedit)
        self.settings_page.show_setup_prompt_checkbox = MagicMock(spec=mock_qcheckbox)
        self.settings_page.db_path_input = MagicMock(spec=mock_qlineedit)

        # Mock UI elements for email settings (created in _setup_email_tab)
        self.settings_page.smtp_server_input = MagicMock(spec=mock_qlineedit)
        self.settings_page.smtp_port_spinbox = MagicMock(spec=mock_qspinbox)
        self.settings_page.smtp_user_input = MagicMock(spec=mock_qlineedit)
        self.settings_page.smtp_pass_input = MagicMock(spec=mock_qlineedit)

    def tearDown(self):
        # If other patchers are started in tests, stop them here or ensure they are context managers
        pass # Patchers started in setUp with @patch decorator are handled automatically

    def test_get_general_settings_data(self):
        # Set mock return values for UI elements
        self.settings_page.templates_dir_input.text.return_value = "/new/templates"
        self.settings_page.clients_dir_input.text.return_value = "/new/clients"
        # Simulate self.tr behavior for interface_lang_combo
        self.settings_page.interface_lang_combo.currentText.return_value = self.tr("English (en)")

        self.settings_page.reminder_days_spinbox.value.return_value = 20
        self.settings_page.session_timeout_spinbox.value.return_value = 120
        self.settings_page.google_maps_url_input.text.return_value = "https://new.maps.url"
        self.settings_page.show_setup_prompt_checkbox.isChecked.return_value = False
        self.settings_page.db_path_input.text.return_value = "/new/app.db"

        expected_data = {
            "templates_dir": "/new/templates",
            "clients_dir": "/new/clients",
            "language": "en", # Derived from "English (en)" via lang_display_to_code
            "default_reminder_days": 20,
            "session_timeout_minutes": 120,
            "google_maps_review_url": "https://new.maps.url",
            "show_initial_setup_on_startup": False,
            "database_path": "/new/app.db",
        }
        self.assertEqual(self.settings_page.get_general_settings_data(), expected_data)

    def test_get_email_settings_data(self):
        self.settings_page.smtp_server_input.text.return_value = "mail.newserver.com"
        self.settings_page.smtp_port_spinbox.value.return_value = 465
        self.settings_page.smtp_user_input.text.return_value = "new_user"
        self.settings_page.smtp_pass_input.text.return_value = "new_password"

        expected_data = {
            "smtp_server": "mail.newserver.com",
            "smtp_port": 465,
            "smtp_user": "new_user",
            "smtp_password": "new_password",
        }
        self.assertEqual(self.settings_page.get_email_settings_data(), expected_data)

    @patch('settings_page.utils.save_config')
    @patch('settings_page.QMessageBox.information') # Mock QMessageBox
    def test_save_all_settings(self, mock_qmessagebox_info, mock_save_config_util):
        # Mock the data gathering methods
        self.settings_page.get_general_settings_data = MagicMock(return_value={"language": "de", "templates_dir": "/test"})
        self.settings_page.get_email_settings_data = MagicMock(return_value={"smtp_server": "test.smtp"})
        # Assuming UserManagementTab and CompanyTabWidget don't have specific save methods called here,
        # or they are mocked if they do. SettingsPage._save_all_settings focuses on general/email.

        # Call the method to test
        self.settings_page._save_all_settings()

        # Assertions
        # 1. main_config should be updated
        self.assertEqual(self.settings_page.main_config["language"], "de")
        self.assertEqual(self.settings_page.main_config["templates_dir"], "/test")
        self.assertEqual(self.settings_page.main_config["smtp_server"], "test.smtp")

        # 2. utils.save_config should be called with the updated main_config
        mock_save_config_util.assert_called_once_with(self.settings_page.main_config)

        # 3. QMessageBox.information should have been called
        mock_qmessagebox_info.assert_called_once()


    # Helper for self.tr within the test class, as SettingsPage uses it
    def tr(self, text, disambiguation=None, n=-1):
        # This is a simplified mock. A real QObject.tr() is more complex.
        return text

if __name__ == '__main__':
    # This allows running the tests from the command line
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
