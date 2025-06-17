import unittest
from unittest.mock import MagicMock, patch, call
from PyQt5.QtWidgets import QApplication, QDialog

# Ensure QApplication instance exists
app = None
def setUpModule():
    global app
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

def tearDownModule():
    global app
    app = None

from dialogs.send_email_dialog import SendEmailDialog
# Assuming templates_crud is also used directly or via db_manager by SendEmailDialog
# For consistency, we'll patch db_manager where SendEmailDialog uses it.

class TestSendEmailDialog(unittest.TestCase):

    def setUp(self):
        self.mock_config = {
            "smtp_server": "smtp.test.com",
            "smtp_port": 587,
            "smtp_user": "user@test.com",
            "smtp_password": "password",
            "templates_dir": "/fake/templates"
        }
        self.client_email = "client@example.com"
        self.client_id = "client123"
        self.mock_client_info = {
            'client_id': self.client_id,
            'client_name': 'Test Client',
            'selected_languages': 'fr,en', # Example
            # Other fields that might be used by get_document_context_data
        }
        self.EMAIL_CATEGORY_ID = 2 # As assumed for email templates
        self.EMAIL_TEMPLATE_TYPES = ['EMAIL_BODY_HTML', 'EMAIL_BODY_TXT']


    @patch('dialogs.send_email_dialog.db_manager')
    @patch('dialogs.send_email_dialog.clients_crud_instance') # If get_client_by_id is called
    def test_load_email_templates_successful_load(self, mock_clients_crud, mock_db_manager):
        """Test load_email_templates populates combo box correctly."""
        mock_clients_crud.get_client_by_id.return_value = self.mock_client_info

        mock_templates_data = [
            {'template_id': 't_html_1', 'template_name': 'HTML Welcome FR', 'language_code': 'fr', 'template_type': 'EMAIL_BODY_HTML'},
            {'template_id': 't_txt_1', 'template_name': 'Text Update FR', 'language_code': 'fr', 'template_type': 'EMAIL_BODY_TXT'},
        ]
        mock_db_manager.get_all_templates.return_value = mock_templates_data

        # Mock get_distinct_languages_for_template_type called by load_available_languages
        # For simplicity, assume 'fr' is the only language with email templates
        mock_db_manager.get_distinct_languages_for_template_type.return_value = [('fr',)]

        dialog = SendEmailDialog(self.client_email, self.mock_config, self.client_id)

        # load_available_languages is called in setup_ui, which calls load_email_templates for current lang
        # Check the call to get_all_templates made by load_email_templates
        mock_db_manager.get_all_templates.assert_called_with(
            language_code_filter='fr', # Assuming 'fr' is selected or default
            category_id_filter=self.EMAIL_CATEGORY_ID,
            template_type_filter_list=self.EMAIL_TEMPLATE_TYPES,
            client_id_filter=None
        )

        self.assertEqual(dialog.template_combo.count(), len(mock_templates_data) + 1) # +1 for "--- Aucun Modèle ---"
        self.assertEqual(dialog.template_combo.itemText(1), 'HTML Welcome FR')
        self.assertEqual(dialog.template_combo.itemData(1), 't_html_1')
        self.assertEqual(dialog.template_combo.itemText(2), 'Text Update FR')
        self.assertEqual(dialog.template_combo.itemData(2), 't_txt_1')

    @patch('dialogs.send_email_dialog.db_manager')
    @patch('dialogs.send_email_dialog.clients_crud_instance')
    def test_load_email_templates_no_templates_for_language(self, mock_clients_crud, mock_db_manager):
        """Test load_email_templates when no templates exist for the selected language."""
        mock_clients_crud.get_client_by_id.return_value = self.mock_client_info
        mock_db_manager.get_all_templates.return_value = [] # No templates for this call
        mock_db_manager.get_distinct_languages_for_template_type.return_value = [('fr',)]

        dialog = SendEmailDialog(self.client_email, self.mock_config, self.client_id)

        # Call for 'fr'
        mock_db_manager.get_all_templates.assert_called_with(
            language_code_filter='fr', category_id_filter=self.EMAIL_CATEGORY_ID,
            template_type_filter_list=self.EMAIL_TEMPLATE_TYPES, client_id_filter=None
        )
        self.assertEqual(dialog.template_combo.count(), 1) # Only "--- Aucun Modèle ---"
        self.assertEqual(dialog.template_combo.itemText(0), dialog.tr("--- Aucun Modèle ---"))

    @patch('dialogs.send_email_dialog.os.path.exists')
    @patch('dialogs.send_email_dialog.open', new_callable=unittest.mock.mock_open, read_data="Test HTML Body {{client.client_name}}")
    @patch('dialogs.send_email_dialog.db_manager')
    @patch('dialogs.send_email_dialog.clients_crud_instance')
    def test_on_template_selected_html_template(self, mock_clients_crud, mock_db_manager, mock_file_open, mock_path_exists):
        """Test selecting an HTML email template."""
        mock_clients_crud.get_client_by_id.return_value = self.mock_client_info
        mock_path_exists.return_value = True # Template file exists

        template_id_selected = 't_html_1'
        mock_template_details = {
            'template_id': template_id_selected, 'template_name': 'HTML Welcome FR',
            'language_code': 'fr', 'base_file_name': 'welcome.html',
            'template_type': 'EMAIL_BODY_HTML',
            'email_subject_template': 'Welcome {{client.client_name}}!'
        }
        mock_db_manager.get_template_details_by_id.return_value = mock_template_details

        mock_context_data = {'client': {'client_name': 'Test Client'}, 'seller': {'company_name': 'My Company'}}
        mock_db_manager.get_document_context_data.return_value = mock_context_data

        # Initial setup to populate language and trigger first load_email_templates
        mock_db_manager.get_distinct_languages_for_template_type.return_value = [('fr',)]
        mock_db_manager.get_all_templates.return_value = [mock_template_details] # So it's in the combo

        dialog = SendEmailDialog(self.client_email, self.mock_config, self.client_id)

        # Simulate selecting the template (index 1, after "--- Aucun Modèle ---")
        dialog.template_combo.setCurrentIndex(1) # This triggers on_template_selected

        mock_db_manager.get_template_details_by_id.assert_called_with(template_id_selected)
        expected_subject = "Welcome Test Client!"
        expected_body_html = "Test HTML Body Test Client" # Simplified, real replacement is more complex

        self.assertEqual(dialog.subject_edit.text(), expected_subject)
        # For HTML, check if setHtml was called with something containing the processed body
        # A direct string match for complex HTML might be fragile.
        self.assertIn("Test HTML Body Test Client", dialog.body_edit.toHtml())
        self.assertTrue(dialog.body_edit.isReadOnly())
        self.assertEqual(dialog.active_template_type, 'EMAIL_BODY_HTML')

    @patch('dialogs.send_email_dialog.os.path.exists')
    @patch('dialogs.send_email_dialog.open', new_callable=unittest.mock.mock_open, read_data="Test Text Body {{client.client_name}}")
    @patch('dialogs.send_email_dialog.db_manager')
    @patch('dialogs.send_email_dialog.clients_crud_instance')
    def test_on_template_selected_txt_template(self, mock_clients_crud, mock_db_manager, mock_file_open, mock_path_exists):
        """Test selecting a TXT email template."""
        mock_clients_crud.get_client_by_id.return_value = self.mock_client_info
        mock_path_exists.return_value = True

        template_id_selected = 't_txt_1'
        mock_template_details = {
            'template_id': template_id_selected, 'template_name': 'Text Update FR',
            'language_code': 'fr', 'base_file_name': 'update.txt',
            'template_type': 'EMAIL_BODY_TXT',
            'email_subject_template': 'Update for {{client.client_name}}'
        }
        mock_db_manager.get_template_details_by_id.return_value = mock_template_details

        mock_context_data = {'client': {'client_name': 'Test Client'}, 'seller': {'company_name': 'My Company'}}
        mock_db_manager.get_document_context_data.return_value = mock_context_data

        mock_db_manager.get_distinct_languages_for_template_type.return_value = [('fr',)]
        mock_db_manager.get_all_templates.return_value = [mock_template_details]

        dialog = SendEmailDialog(self.client_email, self.mock_config, self.client_id)
        dialog.template_combo.setCurrentIndex(1)

        mock_db_manager.get_template_details_by_id.assert_called_with(template_id_selected)
        expected_subject = "Update for Test Client"
        expected_body_text = "Test Text Body Test Client"

        self.assertEqual(dialog.subject_edit.text(), expected_subject)
        self.assertEqual(dialog.body_edit.toPlainText(), expected_body_text)
        self.assertTrue(dialog.body_edit.isReadOnly())
        self.assertEqual(dialog.active_template_type, 'EMAIL_BODY_TXT')

    # TODO: Add tests for cases like template file not found, no template selected, etc.

if __name__ == '__main__':
    unittest.main()
