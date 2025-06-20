import unittest
from unittest.mock import MagicMock, patch, call, ANY
from PyQt5.QtWidgets import QApplication, QListWidgetItem
from PyQt5.QtGui import QFont # Keep if used, though my new test doesn't directly assert font
import sys
import os

# Adjust path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from dialogs.create_document_dialog import CreateDocumentDialog

# Ensure QApplication instance exists
app = None
def setUpModule():
    global app
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

def tearDownModule():
    global app # Unused, but good practice if app needed cleanup
    app = None


class TestCreateDocumentDialog(unittest.TestCase):

    def setUp(self):
        """Set up for each test."""
        self.mock_client_info = {
            'client_id': 'test_client_1',
            'selected_languages': ['fr', 'en'], # Primary language 'fr'
            'category': 'SomeCategory',
            'project_id': 'proj456',
            'project_identifier': 'PROJ_ID_001'
        }
        self.mock_config = {
            'templates_dir': '/fake/templates/dir'
        }

        # Common mocks - applied to all tests in this class via setUp/tearDown
        self.patch_qmessagebox = patch('PyQt5.QtWidgets.QMessageBox')
        self.mock_qmessagebox = self.patch_qmessagebox.start()

        self.patch_logging = patch('dialogs.create_document_dialog.logging')
        self.mock_logging = self.patch_logging.start()

        self.patch_os_path_exists = patch('os.path.exists')
        self.mock_os_path_exists = self.patch_os_path_exists.start()
        self.mock_os_path_exists.return_value = True # Default for all tests unless overridden

    def tearDown(self):
        self.patch_qmessagebox.stop()
        self.patch_logging.stop()
        self.patch_os_path_exists.stop()

    # --- Existing tests, adapted for new category filtering ---
    # The key change is how category_id_filter is asserted.
    # Assuming the 'General' category (ID 1 for these tests) has a purpose like 'client_document'.

    @patch('dialogs.create_document_dialog.get_all_template_categories')
    @patch('dialogs.create_document_dialog.db_manager')
    def test_load_templates_no_default_templates(self, mock_db_manager, mock_get_all_categories):
        mock_get_all_categories.return_value = [{'category_id': 1, 'category_name': 'General', 'purpose': 'client_document'}]
        mock_db_manager.get_all_templates.return_value = [
            {'template_id': 1, 'template_name': 'T1', 'language_code': 'fr', 'base_file_name': 't1.html', 'template_type': 'document_html', 'is_default_for_type_lang': False, 'client_id': None, 'category_id': 1},
            {'template_id': 2, 'template_name': 'T2', 'language_code': 'fr', 'base_file_name': 't2.html', 'template_type': 'document_html', 'is_default_for_type_lang': False, 'client_id': 'test_client_1', 'category_id': 1},
        ]
        # client's primary lang is 'fr', default ext is 'HTML'
        dialog = CreateDocumentDialog(self.mock_client_info, self.mock_config)
        mock_db_manager.get_all_templates.assert_called_with(
            template_type_filter='document_html',
            language_code_filter='fr',
            client_id_filter=self.mock_client_info['client_id'],
            category_id_filter=[1] # Filter by 'client_document' category ID
        )
        self.assertEqual(dialog.templates_list.count(), 2)
        for i in range(dialog.templates_list.count()):
            item = dialog.templates_list.item(i)
            self.assertFalse(item.text().startswith("[D]"))


    @patch('dialogs.create_document_dialog.get_all_template_categories')
    @patch('dialogs.create_document_dialog.db_manager')
    def test_load_templates_global_default_only(self, mock_db_manager, mock_get_all_categories):
        mock_get_all_categories.return_value = [{'category_id': 1, 'category_name': 'General', 'purpose': 'client_document'}]
        mock_db_manager.get_all_templates.return_value = [
            {'template_id': 1, 'template_name': 'GlobalDefault', 'language_code': 'fr', 'base_file_name': 'gd.html', 'template_type': 'document_html', 'is_default_for_type_lang': True, 'client_id': None, 'category_id': 1},
            {'template_id': 2, 'template_name': 'T2', 'language_code': 'fr', 'base_file_name': 't2.html', 'template_type': 'document_html', 'is_default_for_type_lang': False, 'client_id': 'test_client_1', 'category_id': 1},
        ]
        dialog = CreateDocumentDialog(self.mock_client_info, self.mock_config)
        self.assertEqual(dialog.templates_list.count(), 2)
        # Expect GlobalDefault to be the one marked [D]
        item_texts = [dialog.templates_list.item(i).text() for i in range(dialog.templates_list.count())]
        self.assertIn("[D] GlobalDefault (fr) - gd.html", item_texts)


    @patch('dialogs.create_document_dialog.get_all_template_categories')
    @patch('dialogs.create_document_dialog.db_manager')
    def test_load_templates_client_specific_default_only(self, mock_db_manager, mock_get_all_categories):
        mock_get_all_categories.return_value = [{'category_id': 1, 'category_name': 'General', 'purpose': 'client_document'}]
        # Test with client's primary lang 'en'
        self.mock_client_info['selected_languages'] = ['en', 'fr']
        mock_db_manager.get_all_templates.return_value = [
            {'template_id': 1, 'template_name': 'T1', 'language_code': 'en', 'base_file_name': 't1.html', 'template_type': 'document_html', 'is_default_for_type_lang': False, 'client_id': None, 'category_id': 1},
            {'template_id': 2, 'template_name': 'ClientDefault', 'language_code': 'en', 'base_file_name': 'cd.html', 'template_type': 'document_html', 'is_default_for_type_lang': True, 'client_id': 'test_client_1', 'category_id': 1},
        ]
        dialog = CreateDocumentDialog(self.mock_client_info, self.mock_config)
        self.assertEqual(dialog.templates_list.count(), 2)
        item_texts = [dialog.templates_list.item(i).text() for i in range(dialog.templates_list.count())]
        self.assertIn("[D] ClientDefault (en) - cd.html", item_texts)

    @patch('dialogs.create_document_dialog.get_all_template_categories')
    @patch('dialogs.create_document_dialog.db_manager')
    def test_load_templates_client_overrides_global_default(self, mock_db_manager, mock_get_all_categories):
        mock_get_all_categories.return_value = [{'category_id': 1, 'category_name': 'General', 'purpose': 'client_document'}]
        # client primary lang 'fr'
        mock_db_manager.get_all_templates.return_value = [
            {'template_id': 1, 'template_name': 'GlobalFR', 'language_code': 'fr', 'base_file_name': 'gfr.html', 'template_type': 'document_html', 'is_default_for_type_lang': True, 'client_id': None, 'category_id': 1},
            {'template_id': 2, 'template_name': 'ClientFR', 'language_code': 'fr', 'base_file_name': 'cfr.html', 'template_type': 'document_html', 'is_default_for_type_lang': True, 'client_id': 'test_client_1', 'category_id': 1},
        ]
        dialog = CreateDocumentDialog(self.mock_client_info, self.mock_config)
        self.assertEqual(dialog.templates_list.count(), 2)
        default_found = False
        for i in range(dialog.templates_list.count()):
            item = dialog.templates_list.item(i)
            item_data = item.data(MagicMock(name="UserRole")) # Qt.UserRole
            if item_data.get('is_display_default'):
                self.assertEqual(item_data.get('template_name'), 'ClientFR', "ClientFR should be the override default.")
                default_found = True
        self.assertTrue(default_found)

    # --- New comprehensive test for category filtering and UI filters ---
    @patch('dialogs.create_document_dialog.get_all_template_categories')
    @patch('dialogs.create_document_dialog.db_manager')
    def test_load_templates_initial_population_and_filtering(self, mock_db_manager, mock_get_all_categories_crud):
        # Setup Mocks for this specific test
        mock_categories_data = [
            {'category_id': 1, 'category_name': 'Client Docs', 'purpose': 'client_document'},
            {'category_id': 2, 'category_name': 'Utilities', 'purpose': 'utility'},
            {'category_id': 3, 'category_name': 'Emails', 'purpose': 'email'}, # Should be filtered out
            {'category_id': 4, 'category_name': 'Global Docs', 'purpose': 'document_global'},
        ]
        mock_get_all_categories_crud.return_value = mock_categories_data
        expected_category_ids_for_query = [1, 2, 4] # client_document, utility, document_global

        # Templates Data
        templates_db_all = [
            {'template_id': 1, 'template_name': 'Client Report EN', 'template_type': 'document_html', 'language_code': 'en', 'base_file_name': 'report_en.html', 'category_id': 1, 'client_id': 'test_client_1', 'is_default_for_type_lang': False},
            {'template_id': 2, 'template_name': 'Utility Tool FR', 'template_type': 'document_word', 'language_code': 'fr', 'base_file_name': 'tool_fr.docx', 'category_id': 2, 'client_id': None, 'is_default_for_type_lang': False},
            {'template_id': 3, 'template_name': 'Email Update EN', 'template_type': 'email_general', 'language_code': 'en', 'base_file_name': 'update_en.html', 'category_id': 3, 'client_id': None, 'is_default_for_type_lang': False}, # Email, should not show
            {'template_id': 4, 'template_name': 'Global Standard EN', 'template_type': 'document_excel', 'language_code': 'en', 'base_file_name': 'standard_en.xlsx', 'category_id': 4, 'client_id': None, 'is_default_for_type_lang': False},
            {'template_id': 6, 'template_name': 'Another Report EN', 'template_type': 'document_html', 'language_code': 'en', 'base_file_name': 'another_report_en.html', 'category_id': 1, 'client_id': 'test_client_1', 'is_default_for_type_lang': False},
            {'template_id': 7, 'template_name': 'Default Report FR', 'template_type': 'document_html', 'language_code': 'fr', 'base_file_name': 'default_report_fr.html', 'category_id': 1, 'client_id': 'test_client_1', 'is_default_for_type_lang': True},
        ]
        # This mock will be called multiple times, make it versatile or reset/reassign for each call.
        mock_db_manager.get_all_templates.return_value = templates_db_all # Initial broad return

        # Client's primary language is 'fr' from setUp
        dialog = CreateDocumentDialog(self.mock_client_info, self.mock_config)

        # Initial call to get_all_templates (HTML, lang 'fr', categories [1,2,4])
        # Templates matching: Default Report FR (template_id 7)
        mock_db_manager.get_all_templates.assert_called_with(
            template_type_filter='document_html', language_code_filter='fr',
            client_id_filter='test_client_1', category_id_filter=expected_category_ids_for_query
        )
        # Filtered list by load_templates:
        # From templates_db_all, those matching HTML, 'fr', and category_id in [1,2,4]
        # - ID 7: Default Report FR (HTML, fr, cat 1)
        self.assertEqual(dialog.templates_list.count(), 1)
        self.assertTrue(dialog.templates_list.item(0).text().startswith("[D] Default Report FR"))

        # --- Test Language Filter "en" ---
        mock_db_manager.get_all_templates.reset_mock()
        dialog.language_filter_combo.setCurrentText("en") # Triggers load_templates
        # Expected call: HTML, lang 'en', categories [1,2,4]
        # Templates matching: Client Report EN (1), Another Report EN (6)
        mock_db_manager.get_all_templates.assert_called_with(
            template_type_filter='document_html', language_code_filter='en',
            client_id_filter='test_client_1', category_id_filter=expected_category_ids_for_query
        )
        self.assertEqual(dialog.templates_list.count(), 2) # Client Report EN, Another Report EN
        item_texts_en_html = sorted([dialog.templates_list.item(i).text() for i in range(dialog.templates_list.count())])
        self.assertIn("Client Report EN (en) - report_en.html", item_texts_en_html[0]) # Sorted alphabetically
        self.assertIn("Another Report EN (en) - another_report_en.html", item_texts_en_html[1])


        # --- Test Extension Filter "DOCX" (lang "fr" still active) ---
        mock_db_manager.get_all_templates.reset_mock()
        dialog.language_filter_combo.setCurrentText("fr") # Set lang to fr
        dialog.extension_filter_combo.setCurrentText("DOCX") # Triggers load_templates
        # Expected call: DOCX, lang 'fr', categories [1,2,4]
        # Templates matching: Utility Tool FR (2)
        mock_db_manager.get_all_templates.assert_called_with(
            template_type_filter='document_word', language_code_filter='fr',
            client_id_filter='test_client_1', category_id_filter=expected_category_ids_for_query
        )
        self.assertEqual(dialog.templates_list.count(), 1)
        self.assertTrue(dialog.templates_list.item(0).text().startswith("Utility Tool FR"))

        # --- Test Search Filter ---
        mock_db_manager.get_all_templates.reset_mock()
        dialog.language_filter_combo.setCurrentText("en")    # lang 'en'
        dialog.extension_filter_combo.setCurrentText("HTML") # ext 'HTML'
        dialog.search_bar.setText("Another")                 # Triggers load_templates

        # get_all_templates is called for (HTML, 'en'). Search is local.
        # Expected items pre-search: Client Report EN (1), Another Report EN (6)
        # Expected items post-search: Another Report EN (6)
        mock_db_manager.get_all_templates.assert_called_with(
            template_type_filter='document_html', language_code_filter='en',
            client_id_filter='test_client_1', category_id_filter=expected_category_ids_for_query
        )
        self.assertEqual(dialog.templates_list.count(), 1)
        self.assertTrue(dialog.templates_list.item(0).text().startswith("Another Report EN"))

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
