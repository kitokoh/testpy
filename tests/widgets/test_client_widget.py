import unittest
from unittest.mock import MagicMock, patch, call, ANY
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

# Adjust the import path based on your project structure
from client_widget import ClientWidget

# Mock external dependencies that ClientWidget uses directly or indirectly
# These might be imported at the module level of client_widget.py or its imports
# For example, db_manager, various dialogs, etc.

# Mocking MAIN_MODULE_*** globals that ClientWidget._import_main_elements() tries to set.
# This is a bit complex due to the dynamic import mechanism in ClientWidget.
# We need to ensure these are patched *before* ClientWidget is instantiated.

mock_config_for_client_widget = {
    'app_root_dir': '/fake/app_root',
    'templates_dir': '/fake/templates',
    # Add other necessary config keys
}

# It's crucial to patch 'client_widget.MAIN_MODULE_CONFIG' and other MAIN_MODULE_* globals
# if ClientWidget relies on them being set by _import_main_elements.
# Alternatively, if _import_main_elements can be prevented or its imports mocked, that's cleaner.

@patch('client_widget.MAIN_MODULE_CONFIG', mock_config_for_client_widget)
@patch('client_widget.MAIN_MODULE_DATABASE_NAME', 'fake_db_path')
@patch('client_widget.MAIN_MODULE_PRODUCT_DIALOG') # Mock the ProductDialog class
@patch('client_widget.db_manager') # Mock the db_manager module used by ClientWidget
class TestClientWidgetAddProduct(unittest.TestCase):

    def setUp(self):
        self.mock_client_info = {
            'client_id': 'client123',
            'client_name': 'Test Client',
            'project_id': 'project456', # Assuming project_id might be used
            'base_folder_path': '/fake/client/folder',
            # Add other fields ClientWidget constructor or setup_ui might need
            'status_id': 'status_active',
            'category': 'TestCategory',
            'selected_languages': 'fr,en',
        }

        self.mock_notification_manager = MagicMock()

        # Instantiate ClientWidget
        # We need to ensure all heavy UI setup that's not relevant to the test
        # is either mocked or doesn't break the test.
        # ClientWidget's __init__ calls setup_ui(), which creates many UI elements.
        # For focused testing of add_product/load_products, we might not need full UI.
        # However, these methods interact with self.products_table.

        # Patching methods that might be problematic during setup_ui if not needed for these tests
        with patch.object(ClientWidget, 'setup_ui', MagicMock(return_value=None)) as mock_setup_ui, \
             patch.object(ClientWidget, 'load_statuses', MagicMock(return_value=None)), \
             patch.object(ClientWidget, 'populate_details_layout', MagicMock(return_value=None)), \
             patch.object(ClientWidget, 'load_contacts', MagicMock(return_value=None)), \
             patch.object(ClientWidget, 'populate_doc_table', MagicMock(return_value=None)), \
             patch.object(ClientWidget, 'load_document_notes_filters', MagicMock(return_value=None)), \
             patch.object(ClientWidget, 'load_document_notes_table', MagicMock(return_value=None)), \
             patch.object(ClientWidget, 'load_products_for_dimension_tab', MagicMock(return_value=None)), \
             patch.object(ClientWidget, 'update_sav_tab_visibility', MagicMock(return_value=None)), \
             patch.object(ClientWidget, 'load_assigned_vendors_personnel', MagicMock(return_value=None)), \
             patch.object(ClientWidget, 'load_assigned_technicians', MagicMock(return_value=None)), \
             patch.object(ClientWidget, 'load_assigned_transporters', MagicMock(return_value=None)), \
             patch.object(ClientWidget, 'load_assigned_freight_forwarders', MagicMock(return_value=None)):

            self.widget = ClientWidget(
                client_info=self.mock_client_info,
                config=mock_config_for_client_widget, # Use the globally mocked one
                app_root_dir='/fake_app_root_dir',    # Or get from mock_config
                notification_manager=self.mock_notification_manager
            )
            # Now, after instance creation with a mocked setup_ui, manually create critical components.
            # Or, allow setup_ui to run but mock its problematic parts.
            # For this test, we need self.products_table and self.product_lang_filter_combo
            # Let's assume setup_ui was run (by removing the patch for it for a moment)
            # and only specific UI elements are mocked if they cause issues.
            # The above patch of setup_ui is very broad. Let's try to be more specific.

        # Minimal re-setup for products_table related things
        # This is tricky because setup_ui does a LOT.
        # A better approach if ClientWidget is hard to instantiate in tests:
        # Refactor logic from ClientWidget into non-GUI classes/functions.
        # For now, we'll try to mock parts of setup_ui or its callees.

        # Let's assume self.widget is created. We need to mock self.products_table
        self.widget.products_table = MagicMock()
        self.widget.product_lang_filter_combo = MagicMock() # Used by load_products
        self.widget.products_empty_label = MagicMock() # Used by load_products

    def test_add_product_single_valid_product(self, mock_db_manager, MockProductDialog):
        """Test adding a single valid product."""
        # Configure ProductDialog mock
        mock_dialog_instance = MockProductDialog.return_value
        mock_dialog_instance.exec_.return_value = QDialog.Accepted
        mock_dialog_instance.get_data.return_value = [
            {'product_id': 'prod1', 'name': 'Product 1', 'quantity': '2', 'unit_price': '10.50'}
        ]

        # Configure db_manager mocks
        mock_db_manager.add_product_to_client_or_project.return_value = 1 # Simulate successful DB add (returns link_id)
        mock_db_manager.get_products_for_client_or_project.return_value = [
            {'client_project_product_id': 1, 'product_id': 'prod1', 'product_name': 'Product 1',
             'quantity': 2.0, 'unit_price_override': 10.50, 'base_unit_price': 10.0, # assume base is 10
             'total_price_calculated': 21.0, 'language_code': 'fr'} # Match expected data for load_products
        ]

        # Patch QMessageBox for this test
        with patch('client_widget.QMessageBox') as mock_qmessagebox:
            self.widget.add_product()

        # Assertions
        MockProductDialog.assert_called_once_with(self.mock_client_info['client_id'], ANY, parent=self.widget)

        expected_payload = {
            'client_id': self.mock_client_info['client_id'],
            'product_id': 'prod1',
            'quantity': 2.0,
            'unit_price_override': 10.50,
            'project_id': self.mock_client_info['project_id']
        }
        mock_db_manager.add_product_to_client_or_project.assert_called_once_with(expected_payload)

        # Check that load_products was called (implicitly by checking get_products_for_client_or_project)
        mock_db_manager.get_products_for_client_or_project.assert_called_once_with(self.mock_client_info['client_id'], project_id=None)

        # Check if products_table was populated (simplified check)
        self.widget.products_table.setRowCount.assert_called_with(0) # Cleared first
        self.widget.products_table.insertRow.assert_called_once() # One product added
        self.widget.products_table.setItem.assert_any_call(0, 1, ANY) # Check if name column was set for row 0

        mock_qmessagebox.information.assert_called_once() # Success message
        mock_qmessagebox.warning.assert_not_called() # No warnings for data issues


    def test_add_product_multiple_products_one_invalid_data(self, mock_db_manager, MockProductDialog):
        """Test adding multiple products, one with invalid quantity."""
        mock_dialog_instance = MockProductDialog.return_value
        mock_dialog_instance.exec_.return_value = QDialog.Accepted
        mock_dialog_instance.get_data.return_value = [
            {'product_id': 'prod1', 'name': 'Product 1', 'quantity': '2', 'unit_price': '10.00'},
            {'product_id': 'prod2', 'name': 'Product 2', 'quantity': 'invalid_qty', 'unit_price': '20.00'}, # Invalid
            {'product_id': 'prod3', 'name': 'Product 3', 'quantity': '3', 'unit_price': '5.00'}
        ]

        # Simulate DB calls
        # db.add only called for valid products
        mock_db_manager.add_product_to_client_or_project.side_effect = [1, 2] # Link IDs for prod1, prod3

        # db.get returns only successfully added products
        mock_db_manager.get_products_for_client_or_project.return_value = [
            {'client_project_product_id': 1, 'product_id': 'prod1', 'product_name': 'Product 1', 'quantity': 2.0, 'unit_price_override': 10.00, 'total_price_calculated': 20.0, 'language_code': 'fr'},
            {'client_project_product_id': 2, 'product_id': 'prod3', 'product_name': 'Product 3', 'quantity': 3.0, 'unit_price_override': 5.00, 'total_price_calculated': 15.0, 'language_code': 'fr'}
        ]

        with patch('client_widget.QMessageBox') as mock_qmessagebox:
            self.widget.add_product()

        # Assertions
        self.assertEqual(mock_db_manager.add_product_to_client_or_project.call_count, 2)
        calls_to_db_add = [
            call({'client_id': 'client123', 'product_id': 'prod1', 'quantity': 2.0, 'unit_price_override': 10.0, 'project_id': 'project456'}),
            call({'client_id': 'client123', 'product_id': 'prod3', 'quantity': 3.0, 'unit_price_override': 5.0, 'project_id': 'project456'})
        ]
        mock_db_manager.add_product_to_client_or_project.assert_has_calls(calls_to_db_add, any_order=False)

        mock_qmessagebox.warning.assert_called_once() # For the invalid product
        # Check the title of the warning
        args, _ = mock_qmessagebox.warning.call_args
        self.assertEqual(args[1], self.widget.tr("Données Produit Invalides ou Manquantes"))


        # Check that load_products was called
        mock_db_manager.get_products_for_client_or_project.assert_called_once_with(self.mock_client_info['client_id'], project_id=None)

        # Check table population
        self.assertEqual(self.widget.products_table.insertRow.call_count, 2) # Prod1 and Prod3


    def test_add_product_db_failure(self, mock_db_manager, MockProductDialog):
        """Test scenario where adding a product to DB fails."""
        mock_dialog_instance = MockProductDialog.return_value
        mock_dialog_instance.exec_.return_value = QDialog.Accepted
        mock_dialog_instance.get_data.return_value = [
            {'product_id': 'prod1', 'name': 'Product 1', 'quantity': '1', 'unit_price': '10.00'}
        ]

        mock_db_manager.add_product_to_client_or_project.return_value = None # Simulate DB failure
        mock_db_manager.get_products_for_client_or_project.return_value = [] # No products after failed add

        with patch('client_widget.QMessageBox') as mock_qmessagebox:
            self.widget.add_product()

        mock_db_manager.add_product_to_client_or_project.assert_called_once()
        mock_qmessagebox.warning.assert_any_call(self.widget, self.widget.tr("Erreur Base de Données"), ANY)

        # load_products is still called
        mock_db_manager.get_products_for_client_or_project.assert_called_once()
        self.widget.products_table.insertRow.assert_not_called() # No product should be added to table

    # TODO: Add more tests for load_products directly if needed, e.g. different language filters, empty data from DB etc.
    # For now, load_products is indirectly tested via add_product.

if __name__ == '__main__':
    unittest.main()
