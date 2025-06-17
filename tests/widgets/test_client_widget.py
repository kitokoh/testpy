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

        # Check if products_table was populated
        self.widget.products_table.setRowCount.assert_called_with(0) # Cleared first
        self.widget.products_table.insertRow.assert_called_once_with(0) # Row 0 for the first product

        # Verify setItem calls for the single product
        # Expected data from mock_db_manager.get_products_for_client_or_project
        # {'client_project_product_id': 1, 'product_id': 'prod1', 'product_name': 'Product 1',
        #  'quantity': 2.0, 'unit_price_override': 10.50, 'base_unit_price': 10.0,
        #  'total_price_calculated': 21.0, 'language_code': 'fr',
        #  'product_description': '', 'weight': None, 'dimensions': None } # Assuming defaults if not in mock

        # Helper to get text from QTableWidgetItem mock calls
        def get_item_text_from_call(call_obj):
            # setItem(row, col, QTableWidgetItem_instance)
            # QTableWidgetItem_instance is call_obj[0][2]
            # QTableWidgetItem is instantiated with text: QTableWidgetItem("text")
            # The mock for QTableWidgetItem needs to capture this text or have a text() method.
            # For simplicity, if QTableWidgetItem is not deeply mocked, we assume its string representation
            # or a 'text' attribute holds the value if it were a custom mock.
            # Given QTableWidgetItem is a real class, its instance will have .text()
            qt_item = call_obj[0][2]
            return qt_item.text()

        # Expected calls for row 0
        # Column indices: ID=0(hidden), Name=1, Desc=2, Weight=3, Dims=4, Qty=5, UnitPrice=6, TotalPrice=7
        # Data from mock: 'product_name': 'Product 1', 'quantity': 2.0, unit_price_override (or base for effective): 10.50, total_price_calculated: 21.0
        # description, weight, dimensions might be missing or default from prod_link_data.get
        # Let's assume product_description, weight, dimensions are part of the mock return from get_products_for_client_or_project
        # For example:
        mock_product_data_for_table = {
            'client_project_product_id': 1, 'product_name': 'Product 1', 'product_description': 'Desc 1',
            'weight': 0.5, 'dimensions': '10x5x2', 'quantity': 2.0,
            'unit_price_override': 10.50, 'base_unit_price': 10.0, 'total_price_calculated': 21.0
        }
        # Update the mock return to include these for a more complete test
        mock_db_manager.get_products_for_client_or_project.return_value = [mock_product_data_for_table]

        # Re-run add_product with the updated mock if necessary, or ensure this mock is set before add_product call.
        # The current structure sets it before, which is fine.

        # Check specific cells
        # We need to iterate through call_args_list of setItem
        # This is more robust than assert_has_calls with ANY for the item.

        # Get all calls to setItem
        set_item_calls = self.widget.products_table.setItem.call_args_list

        # Expected values for row 0
        expected_row_0_texts = {
            0: str(mock_product_data_for_table['client_project_product_id']), # ID
            1: mock_product_data_for_table['product_name'],                   # Name
            2: mock_product_data_for_table['product_description'],            # Description
            3: f"{mock_product_data_for_table['weight']} kg",                 # Weight
            4: mock_product_data_for_table['dimensions'],                     # Dimensions
            5: str(mock_product_data_for_table['quantity']),                  # Qty
            6: f"{mock_product_data_for_table['unit_price_override']:.2f}",   # Unit Price (effective)
            7: f"€ {mock_product_data_for_table['total_price_calculated']:.2f}"# Total Price
        }

        actual_row_0_items = {}
        for call_args in set_item_calls:
            args = call_args[0] # (row, col, QTableWidgetItem_instance)
            if args[0] == 0: # Filter for row 0
                actual_row_0_items[args[1]] = args[2].text() # Store text by col_idx

        for col_idx, expected_text in expected_row_0_texts.items():
            self.assertEqual(actual_row_0_items.get(col_idx), expected_text, f"Mismatch in row 0, col {col_idx}")

        mock_qmessagebox.information.assert_called_once()
        mock_qmessagebox.warning.assert_not_called()



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

        # Check table population for 2 valid products
        self.widget.products_table.setRowCount.assert_called_with(0)
        self.assertEqual(self.widget.products_table.insertRow.call_count, 2) # Prod1 and Prod3
        self.widget.products_table.insertRow.assert_any_call(0) # For Prod1
        self.widget.products_table.insertRow.assert_any_call(1) # For Prod3

        # Verify setItem calls for the two valid products
        # Prod1 data (from mock_dialog_instance.get_data)
        prod1_data_for_table = {
            'client_project_product_id': 1, 'product_name': 'Product 1', 'product_description': '',
            'weight': None, 'dimensions': 'N/A', 'quantity': 2.0,
            'unit_price_override': 10.00, 'base_unit_price': 10.00, # Assuming base matches if override is same
            'total_price_calculated': 20.0
        }
        # Prod3 data
        prod3_data_for_table = {
            'client_project_product_id': 2, 'product_name': 'Product 3', 'product_description': '',
            'weight': None, 'dimensions': 'N/A', 'quantity': 3.0,
            'unit_price_override': 5.00, 'base_unit_price': 5.00,
            'total_price_calculated': 15.0
        }

        # Update the mock return to include these details if they are used by setItem
        # The current mock for get_products_for_client_or_project is already structured this way.

        set_item_calls = self.widget.products_table.setItem.call_args_list

        # Check Prod1 (row 0)
        expected_row_0_texts = {
            0: str(prod1_data_for_table['client_project_product_id']),
            1: prod1_data_for_table['product_name'],
            # Add more columns if their data is explicitly set and verifiable
            5: str(prod1_data_for_table['quantity']),
            6: f"{prod1_data_for_table['unit_price_override']:.2f}",
            7: f"€ {prod1_data_for_table['total_price_calculated']:.2f}"
        }
        actual_row_0_items = {args[0][1]: args[0][2].text() for args in set_item_calls if args[0][0] == 0}
        for col_idx, expected_text in expected_row_0_texts.items():
            self.assertEqual(actual_row_0_items.get(col_idx), expected_text, f"Mismatch in Prod1, row 0, col {col_idx}")

        # Check Prod3 (row 1)
        expected_row_1_texts = {
            0: str(prod3_data_for_table['client_project_product_id']),
            1: prod3_data_for_table['product_name'],
            5: str(prod3_data_for_table['quantity']),
            6: f"{prod3_data_for_table['unit_price_override']:.2f}",
            7: f"€ {prod3_data_for_table['total_price_calculated']:.2f}"
        }
        actual_row_1_items = {args[0][1]: args[0][2].text() for args in set_item_calls if args[0][0] == 1}
        for col_idx, expected_text in expected_row_1_texts.items():
            self.assertEqual(actual_row_1_items.get(col_idx), expected_text, f"Mismatch in Prod3, row 1, col {col_idx}")



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
