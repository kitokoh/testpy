import unittest
from unittest.mock import MagicMock, patch, call
from PyQt5.QtWidgets import QApplication, QListWidgetItem
from PyQt5.QtGui import QFont

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


# Assuming dialogs.create_document_dialog is the path to your module
# Adjust the import path based on your project structure
from dialogs.create_document_dialog import CreateDocumentDialog
# Mock db_manager before it's imported by the dialog
# This is a common pattern but might need adjustment if db_manager is imported differently
# For now, we will patch it directly where CreateDocumentDialog uses it.


class TestCreateDocumentDialog(unittest.TestCase):

    def setUp(self):
        """Set up for each test."""
        self.mock_client_info = {
            'client_id': 'test_client_1',
            'selected_languages': ['fr', 'en'],
            'category': 'SomeCategory'
            # Add other fields as minimally required by CreateDocumentDialog constructor
        }
        self.mock_config = {
            'templates_dir': '/fake/templates/dir'
            # Add other config fields as needed
        }

        # It's important that db_manager is patched *before* CreateDocumentDialog instance is created
        # if the dialog imports db_manager at the module level and uses it in __init__ or setup_ui.
        # However, the provided dialog seems to call db_manager.get_all_templates within load_templates,
        # so patching it via @patch decorator on the test method or setUp should be fine.

    @patch('dialogs.create_document_dialog.db_manager')
    def test_load_templates_no_default_templates(self, mock_db_manager):
        """Test load_templates when no default templates are returned."""
        mock_db_manager.get_all_templates.return_value = [
            {'template_id': 1, 'template_name': 'T1', 'language_code': 'fr', 'base_file_name': 't1.html', 'template_type': 'document_html', 'is_default_for_type_lang': False, 'client_id': None},
            {'template_id': 2, 'template_name': 'T2', 'language_code': 'en', 'base_file_name': 't2.html', 'template_type': 'document_html', 'is_default_for_type_lang': False, 'client_id': 'test_client_1'},
        ]

        dialog = CreateDocumentDialog(self.mock_client_info, self.mock_config)

        # Call load_templates directly or ensure it's called by dialog setup
        # dialog.load_templates() # setup_ui calls load_templates, so this might be redundant if instance creation is enough

        self.assertEqual(dialog.templates_list.count(), 2)
        for i in range(dialog.templates_list.count()):
            item = dialog.templates_list.item(i)
            self.assertFalse(item.text().startswith("[D]"))
            self.assertFalse(item.font().bold())

            # Verify data stored in item
            item_data = item.data(Qt.UserRole)
            self.assertIsNotNone(item_data)
            # is_display_default should be False based on the refined logic
            self.assertFalse(item_data.get('is_display_default', False))


    @patch('dialogs.create_document_dialog.db_manager')
    def test_load_templates_global_default_only(self, mock_db_manager):
        """Test with only a global default template."""
        mock_db_manager.get_all_templates.return_value = [
            {'template_id': 1, 'template_name': 'GlobalDefault', 'language_code': 'fr', 'base_file_name': 'gd.html', 'template_type': 'document_html', 'is_default_for_type_lang': True, 'client_id': None},
            {'template_id': 2, 'template_name': 'T2', 'language_code': 'en', 'base_file_name': 't2.html', 'template_type': 'document_html', 'is_default_for_type_lang': False, 'client_id': 'test_client_1'},
        ]
        dialog = CreateDocumentDialog(self.mock_client_info, self.mock_config)

        self.assertEqual(dialog.templates_list.count(), 2)

        item0_data = dialog.templates_list.item(0).data(Qt.UserRole) # Assuming sort puts default first
        item1_data = dialog.templates_list.item(1).data(Qt.UserRole)

        # Determine which item is the default one based on 'is_display_default'
        default_item_text_prefix = "[D] GlobalDefault"
        non_default_item_text_prefix = "T2"

        found_default = False
        found_non_default = False

        for i in range(dialog.templates_list.count()):
            item = dialog.templates_list.item(i)
            item_data = item.data(Qt.UserRole)
            if item_data.get('is_display_default'):
                self.assertTrue(item.text().startswith(default_item_text_prefix))
                self.assertTrue(item.font().bold())
                found_default = True
            else:
                self.assertTrue(item.text().startswith(non_default_item_text_prefix)) # Check actual name
                self.assertFalse(item.font().bold())
                found_non_default = True

        self.assertTrue(found_default, "Global default template was not marked as display default.")
        self.assertTrue(found_non_default, "Non-default template was not found or processed correctly.")


    @patch('dialogs.create_document_dialog.db_manager')
    def test_load_templates_client_specific_default_only(self, mock_db_manager):
        """Test with only a client-specific default template."""
        mock_db_manager.get_all_templates.return_value = [
            {'template_id': 1, 'template_name': 'T1', 'language_code': 'fr', 'base_file_name': 't1.html', 'template_type': 'document_html', 'is_default_for_type_lang': False, 'client_id': None},
            {'template_id': 2, 'template_name': 'ClientDefault', 'language_code': 'en', 'base_file_name': 'cd.html', 'template_type': 'document_html', 'is_default_for_type_lang': True, 'client_id': 'test_client_1'},
        ]
        dialog = CreateDocumentDialog(self.mock_client_info, self.mock_config)
        self.assertEqual(dialog.templates_list.count(), 2)

        default_item_text_prefix = "[D] ClientDefault"
        non_default_item_text_prefix = "T1"

        found_default = False
        found_non_default = False

        for i in range(dialog.templates_list.count()):
            item = dialog.templates_list.item(i)
            item_data = item.data(Qt.UserRole)
            if item_data.get('is_display_default'):
                self.assertTrue(item.text().startswith(default_item_text_prefix))
                self.assertTrue(item.font().bold())
                self.assertEqual(item_data.get('client_id'), 'test_client_1')
                found_default = True
            else:
                self.assertTrue(item.text().startswith(non_default_item_text_prefix))
                self.assertFalse(item.font().bold())
                found_non_default = True

        self.assertTrue(found_default, "Client-specific default template was not marked as display default.")
        self.assertTrue(found_non_default, "Non-default template was not found.")


    @patch('dialogs.create_document_dialog.db_manager')
    def test_load_templates_client_overrides_global_default(self, mock_db_manager):
        """Test client-specific default overrides global default for the same type/lang."""
        mock_db_manager.get_all_templates.return_value = [
            {'template_id': 1, 'template_name': 'GlobalFR', 'language_code': 'fr', 'base_file_name': 'gfr.html', 'template_type': 'document_html', 'is_default_for_type_lang': True, 'client_id': None},
            {'template_id': 2, 'template_name': 'ClientFR', 'language_code': 'fr', 'base_file_name': 'cfr.html', 'template_type': 'document_html', 'is_default_for_type_lang': True, 'client_id': 'test_client_1'},
            {'template_id': 3, 'template_name': 'OtherEN', 'language_code': 'en', 'base_file_name': 'oen.html', 'template_type': 'document_html', 'is_default_for_type_lang': False, 'client_id': None},
        ]
        dialog = CreateDocumentDialog(self.mock_client_info, self.mock_config)
        self.assertEqual(dialog.templates_list.count(), 3)

        client_default_count = 0
        displayed_as_default_count = 0

        for i in range(dialog.templates_list.count()):
            item = dialog.templates_list.item(i)
            item_data = item.data(Qt.UserRole)
            is_display_default = item_data.get('is_display_default', False)

            if is_display_default:
                displayed_as_default_count +=1
                # This one MUST be the client-specific one
                self.assertEqual(item_data.get('template_name'), 'ClientFR', "ClientFR should be the one displayed as default.")
                self.assertTrue(item.text().startswith("[D] ClientFR"))
                self.assertTrue(item.font().bold())

            if item_data.get('template_name') == 'GlobalFR':
                self.assertFalse(is_display_default, "GlobalFR should NOT be displayed as default when client-specific one exists.")
                self.assertFalse(item.text().startswith("[D]"), "GlobalFR text should not have [D] prefix.")
                self.assertFalse(item.font().bold(), "GlobalFR font should not be bold.")


        self.assertEqual(displayed_as_default_count, 1, "Only one template (ClientFR) should be marked as display default for fr/document_html.")

    @patch('dialogs.create_document_dialog.db_manager')
    def test_load_templates_multiple_defaults_different_type_lang(self, mock_db_manager):
        """Test multiple defaults for different types/languages are handled correctly."""
        mock_db_manager.get_all_templates.return_value = [
            {'template_id': 1, 'template_name': 'GlobalFR_HTML', 'language_code': 'fr', 'base_file_name': 'gfr.html', 'template_type': 'document_html', 'is_default_for_type_lang': True, 'client_id': None},
            {'template_id': 2, 'template_name': 'ClientEN_HTML', 'language_code': 'en', 'base_file_name': 'cen.html', 'template_type': 'document_html', 'is_default_for_type_lang': True, 'client_id': 'test_client_1'},
            {'template_id': 3, 'template_name': 'GlobalFR_DOCX', 'language_code': 'fr', 'base_file_name': 'gfr.docx', 'template_type': 'document_word', 'is_default_for_type_lang': True, 'client_id': None},
            {'template_id': 4, 'template_name': 'NonDefault', 'language_code': 'fr', 'base_file_name': 'nd.html', 'template_type': 'document_html', 'is_default_for_type_lang': False, 'client_id': None},
        ]
        dialog = CreateDocumentDialog(self.mock_client_info, self.mock_config)
        # Simulate selecting "All" for language and extension to ensure all these are processed
        dialog.language_filter_combo.setCurrentText("All")
        dialog.extension_filter_combo.setCurrentText("All") # This will trigger load_templates
        # Note: direct call to dialog.load_templates() might be needed if signals aren't firing in test env
        # or if setup_ui's initial call isn't sufficient after filter changes.
        # The provided CreateDocumentDialog calls load_templates in setup_ui, and signals connect to it.
        # Forcing a reload after filter changes:
        dialog.load_templates()


        self.assertEqual(dialog.templates_list.count(), 4)

        display_default_names = []
        for i in range(dialog.templates_list.count()):
            item = dialog.templates_list.item(i)
            item_data = item.data(Qt.UserRole)
            if item_data.get('is_display_default'):
                display_default_names.append(item_data.get('template_name'))
                self.assertTrue(item.text().startswith("[D]"))
                self.assertTrue(item.font().bold())
            else:
                self.assertFalse(item.text().startswith("[D]"))
                self.assertFalse(item.font().bold())

        self.assertEqual(len(display_default_names), 3, "Should be 3 templates marked as display default.")
        self.assertIn('GlobalFR_HTML', display_default_names)
        self.assertIn('ClientEN_HTML', display_default_names)
        self.assertIn('GlobalFR_DOCX', display_default_names)

    # TODO: Add tests for filter functionality (language, extension, search text)

if __name__ == '__main__':
    unittest.main()
