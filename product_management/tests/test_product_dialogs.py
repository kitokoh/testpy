import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import time # For unique naming

# Add project root to sys.path to allow imports from main project
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt5.QtWidgets import QApplication, QDialog
from product_management.list_dialog import ProductListDialog # Updated import
import db as db_manager # aliased as db_manager in product_list_dialog
# Specific CRUD functions from product_management.crud
from product_management.crud import (
    add_product as pm_add_product,
    get_product_by_id as pm_get_product_by_id,
    delete_product as pm_delete_product,
    update_product_price as pm_update_product_price,
    get_products as pm_get_products
)
import html_to_pdf_util

# Ensure a QApplication instance exists for widget testing, but only one.
# It's often better to manage this per test class or even per test method if tests interfere.
# For simplicity here, we'll try a global one, but it can be problematic.
# A better approach for larger test suites is a base test class that handles QApplication.
app = None

def setUpModule():
    """Initialize database and QApplication for the test module."""
    global app
    print("Setting up module: Initializing database...")
    db_manager.DATABASE_NAME = "test_app_data.db" # Use a test database
    if os.path.exists(db_manager.DATABASE_NAME):
        os.remove(db_manager.DATABASE_NAME)
        print(f"Removed existing test database: {db_manager.DATABASE_NAME}")
    db_manager.initialize_database()
    print(f"Test database '{db_manager.DATABASE_NAME}' initialized.")

    # QApplication needed for QDialog instantiation
    # Check if an instance already exists (e.g. if run in an environment that pre-creates one)
    if QApplication.instance():
        app = QApplication.instance()
        print("QApplication instance already exists.")
    else:
        app = QApplication(sys.argv)
        print("QApplication instance created for tests.")


def tearDownModule():
    """Clean up resources after all tests in the module have run."""
    print(f"Tearing down module: Removing test database '{db_manager.DATABASE_NAME}'...")
    if os.path.exists(db_manager.DATABASE_NAME):
        os.remove(db_manager.DATABASE_NAME)
        print(f"Test database '{db_manager.DATABASE_NAME}' removed.")
    # app.quit() # Not typically needed if app is managed correctly or not event-looped

class TestProductList(unittest.TestCase):

    def setUp(self):
        """Set up for each test method."""
        # Ensure the database is clean before each test, or manage data specifically per test.
        # For these tests, we'll add and remove data within each test for isolation.
        # We ensure tables exist via setUpModule's initialize_database.
        self.products_to_cleanup = [] # Keep track of product_ids to delete

    def tearDown(self):
        """Clean up after each test method."""
        for prod_id in self.products_to_cleanup:
            try:
                pm_delete_product({'product_id': prod_id}) # Assuming delete_product expects a dict or product_id directly
            except Exception as e:
                print(f"Error cleaning up product_id {prod_id}: {e}")
        self.products_to_cleanup.clear()

    def _add_test_product(self, name_suffix, lang, price=10.0, desc="Test Desc"):
        unique_name = f"TestProd_{name_suffix}_{int(time.time_ns())}"
        # add_product from product_management.crud returns a dict {'success': True/False, 'id': new_id}
        result = pm_add_product({
            'product_name': unique_name,
            'description': desc,
            'language_code': lang,
            'base_unit_price': price,
            'category': 'TestCat',
            'unit_of_measure': 'unit'
        })
        self.assertTrue(result.get('success'), f"Failed to add product {unique_name}: {result.get('error')}")
        product_id = result.get('id')
        self.assertIsNotNone(product_id, f"add_product did not return an ID for {unique_name}")
        self.products_to_cleanup.append(product_id)
        # Return the full product dict as would be returned by get_product_by_id for convenience
        return pm_get_product_by_id(product_id)


    def test_fetch_products(self):
        print("\nRunning test_fetch_products...")
        prod1_en = self._add_test_product("P1", "en", 10.99)
        prod2_en = self._add_test_product("P2", "en", 20.50)
        prod3_fr = self._add_test_product("P3", "fr", 5.00)

        all_products = pm_get_products() # Using aliased import
        # Check if all added products are in the fetched list
        # Note: get_products might return other products if DB is not perfectly clean
        # So, we check if our specific products are present.
        product_ids_fetched = [p['product_id'] for p in all_products]
        self.assertIn(prod1_en['product_id'], product_ids_fetched)
        self.assertIn(prod2_en['product_id'], product_ids_fetched)
        self.assertIn(prod3_fr['product_id'], product_ids_fetched)
        print(f"Fetched {len(all_products)} products total.")

        en_products = pm_get_products(language_code='en') # Using aliased import
        en_product_ids_fetched = [p['product_id'] for p in en_products]
        self.assertIn(prod1_en['product_id'], en_product_ids_fetched, "English product 1 not found")
        self.assertIn(prod2_en['product_id'], en_product_ids_fetched, "English product 2 not found")
        self.assertNotIn(prod3_fr['product_id'], en_product_ids_fetched, "French product found in English list")
        print(f"Fetched {len(en_products)} English products.")

        fr_products = pm_get_products(language_code='fr') # Using aliased import
        fr_product_ids_fetched = [p['product_id'] for p in fr_products]
        self.assertIn(prod3_fr['product_id'], fr_product_ids_fetched, "French product not found")
        self.assertNotIn(prod1_en['product_id'], fr_product_ids_fetched, "English product 1 found in French list")
        print(f"Fetched {len(fr_products)} French products.")
        print("test_fetch_products PASSED.")


    def test_update_product_price(self):
        print("\nRunning test_update_product_price...")
        product = self._add_test_product("PriceUpdate", "en", 15.00)
        new_price = 18.75

        update_result = pm_update_product_price(product['product_id'], new_price) # Using aliased
        self.assertTrue(update_result.get('success'), f"Failed to update product price: {update_result.get('error')}")

        updated_product = pm_get_product_by_id(product['product_id']) # Using aliased
        self.assertIsNotNone(updated_product, "Failed to fetch updated product")
        self.assertEqual(updated_product['base_unit_price'], new_price, "Product price was not updated correctly")
        print(f"Product ID {product['product_id']} price updated to {updated_product['base_unit_price']}.")
        print("test_update_product_price PASSED.")

    def test_product_list_dialog_loads_data(self):
        print("\nRunning test_product_list_dialog_loads_data...")
        # Add some products that the dialog should load
        prod_a = self._add_test_product("DialA", "en", 1.0)
        prod_b = self._add_test_product("DialB", "en", 2.0)

        dialog = ProductListDialog() # Parent is None for test

        # The dialog's __init__ calls load_products_to_table() (which defaults to lang=None)
        # So it should load all active products initially.
        # We need to ensure our test products are among them.
        # A more precise test would be to count rows IF the DB was guaranteed clean.
        # For now, check if table has at least the number of products we added.
        # Or, iterate through table and check for our product names.

        # Let's count based on "All Languages" which load_products_to_table defaults to
        all_db_products = pm_get_products(language_code=None) # Using aliased
        expected_rows = len(all_db_products)

        self.assertEqual(dialog.product_table.rowCount(), expected_rows,
                         f"Dialog table row count ({dialog.product_table.rowCount()}) "
                         f"does not match expected product count ({expected_rows}) for 'All Languages'.")

        # Test language filter change
        dialog.language_combo.setCurrentText("English") # This should trigger load_products_to_table('en')

        # Wait for signals if necessary, though direct call should be synchronous.
        # QApplication.processEvents() # Might be needed if signals are queued across threads

        en_db_products = pm_get_products(language_code='en') # Using aliased
        expected_en_rows = len(en_db_products)
        self.assertEqual(dialog.product_table.rowCount(), expected_en_rows,
                        f"Dialog table row count for English ({dialog.product_table.rowCount()}) "
                        f"does not match expected ({expected_en_rows}).")

        dialog.close() # Close the dialog
        print("test_product_list_dialog_loads_data PASSED.")


    @patch('product_management.list_dialog.QFileDialog.getSaveFileName') # Updated patch target
    @patch('product_management.list_dialog.html_to_pdf_util.convert_html_to_pdf') # Updated patch target
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_pdf_export_creates_file(self, mock_file_open, mock_convert_to_pdf, mock_get_save_file_name):
        print("\nRunning test_pdf_export_creates_file...")
        # Setup mocks
        dummy_pdf_path = "dummy_path/test_product_list.pdf"
        mock_get_save_file_name.return_value = (dummy_pdf_path, None)
        mock_convert_to_pdf.return_value = b'%PDF-1.4 dummy content'

        # Add a product to be exported
        prod_export = self._add_test_product("ExportProd", "en", 55.55)

        dialog = ProductListDialog()
        dialog.language_combo.setCurrentText("English") # Ensure a language is selected with products

        # Call the export function
        dialog.export_pdf_button.click() # Simulate button click

        # Assertions
        mock_get_save_file_name.assert_called_once()
        # render_html_template is called internally by export_pdf_placeholder
        # convert_html_to_pdf should be called with rendered HTML
        mock_convert_to_pdf.assert_called_once()

        # Check that open was called with the dummy file path and 'wb' mode
        mock_file_open.assert_called_once_with(dummy_pdf_path, "wb")
        # Check that write was called with the dummy PDF bytes
        mock_file_open().write.assert_called_once_with(b'%PDF-1.4 dummy content')

        dialog.close()
        print("test_pdf_export_creates_file PASSED.")

    @patch('product_management.list_dialog.ProductListDialog.apply_filters_and_reload') # Updated patch target
    @patch('product_management.list_dialog.ProductEditDialog') # Updated patch target
    def test_add_product_button_opens_dialog(self, MockProductEditDialog, mock_apply_filters_and_reload):
        print("\nRunning test_add_product_button_opens_dialog...")
        dialog = ProductListDialog()

        # Configure the mock dialog instance
        mock_edit_dialog_instance = MockProductEditDialog.return_value
        mock_edit_dialog_instance.exec_.return_value = QDialog.Accepted # Simulate "OK" clicked

        # Simulate Add Product button click
        dialog.add_product_button.click()

        MockProductEditDialog.assert_called_once_with(product_id=None, parent=dialog)
        mock_edit_dialog_instance.exec_.assert_called_once()
        mock_apply_filters_and_reload.assert_called_once()

        dialog.close()
        print("test_add_product_button_opens_dialog PASSED.")

    @patch('product_management.list_dialog.ProductListDialog.apply_filters_and_reload') # Updated patch target
    @patch('product_management.list_dialog.ProductEditDialog') # Updated patch target
    def test_edit_product_opens_dialog(self, MockProductEditDialog, mock_apply_filters_and_reload):
        print("\nRunning test_edit_product_opens_dialog...")
        # Add a product to be edited
        test_product = self._add_test_product("EditTest", "en", price=30.0)
        test_product_id = test_product['product_id']

        dialog = ProductListDialog() # This will load products

        # Select the product in the table
        # Assuming it's the first product if DB is clean or products are sorted predictably
        # For more robustness, iterate and find by name/ID if needed.
        # Here, we add one product, then reload the dialog, so it should be row 0.
        # We need to reload the dialog or ensure it loads this specific product.
        # Re-instantiating dialog ensures it loads the product added.

        # Find the row for the test product
        found_row = -1
        for r in range(dialog.product_table.rowCount()):
            item = dialog.product_table.item(r, 0) # ID column
            if item and item.text() == str(test_product_id):
                found_row = r
                break
        self.assertNotEqual(found_row, -1, f"Test product ID {test_product_id} not found in table.")
        dialog.product_table.setCurrentCell(found_row, 1) # Select name column of the found row

        self.assertTrue(dialog.edit_product_button.isEnabled(), "Edit button should be enabled after selection.")

        # Configure the mock dialog instance for button click
        mock_edit_dialog_instance_btn = MockProductEditDialog.return_value
        mock_edit_dialog_instance_btn.exec_.return_value = QDialog.Accepted

        # Test 1: Edit button click
        dialog.edit_product_button.click()
        MockProductEditDialog.assert_called_with(product_id=test_product_id, parent=dialog)
        mock_edit_dialog_instance_btn.exec_.assert_called_once()
        mock_apply_filters_and_reload.assert_called_once()

        # Reset mocks for double-click test
        MockProductEditDialog.reset_mock()
        mock_apply_filters_and_reload.reset_mock()
        # Re-configure mock instance for double-click
        mock_edit_dialog_instance_dbl = MockProductEditDialog.return_value
        mock_edit_dialog_instance_dbl.exec_.return_value = QDialog.Accepted

        # Test 2: Double-click
        # Ensure the correct item is selected for double click.
        # The selection should still be on found_row from previous setCurrentCell.
        item_to_double_click = dialog.product_table.item(found_row, 1) # Name item
        self.assertIsNotNone(item_to_double_click, "Item to double click not found.")

        dialog.product_table.itemDoubleClicked.emit(item_to_double_click)

        MockProductEditDialog.assert_called_with(product_id=test_product_id, parent=dialog)
        mock_edit_dialog_instance_dbl.exec_.assert_called_once()
        mock_apply_filters_and_reload.assert_called_once()

        dialog.close()
        print("test_edit_product_opens_dialog PASSED.")

    @patch('product_management.list_dialog.ProductListDialog.apply_filters_and_reload') # Updated patch target
    @patch('product_management.list_dialog.products_crud_instance.delete_product') # Updated patch target
    @patch('product_management.list_dialog.QMessageBox.question') # Updated patch target
    def test_delete_product_button(self, mock_qmessagebox_question, mock_crud_delete_product, mock_apply_filters_and_reload):
        print("\nRunning test_delete_product_button...")
        # Add a product to be deleted
        test_product = self._add_test_product("DeleteTest", "en", price=40.0)
        test_product_id = test_product['product_id']
        test_product_name = test_product['product_name']

        dialog = ProductListDialog()

        # Find and select the product in the table
        found_row = -1
        for r in range(dialog.product_table.rowCount()):
            item_id_col = dialog.product_table.item(r, 0) # ID column
            if item_id_col and item_id_col.text() == str(test_product_id):
                found_row = r
                break
        self.assertNotEqual(found_row, -1, f"Test product ID {test_product_id} not found in table for deletion.")
        dialog.product_table.setCurrentCell(found_row, 1) # Select the name column

        self.assertTrue(dialog.delete_product_button.isEnabled(), "Delete button should be enabled after selection.")

        # Test 1: Confirm Delete
        mock_qmessagebox_question.return_value = QMessageBox.Yes
        mock_crud_delete_product.return_value = {'success': True}

        dialog.delete_product_button.click()

        mock_qmessagebox_question.assert_called_once()
        # Check that the question dialog shows the correct product name and ID
        args, _ = mock_qmessagebox_question.call_args
        self.assertIn(test_product_name, args[1]) # args[1] is the message string
        self.assertIn(str(test_product_id), args[1])

        mock_crud_delete_product.assert_called_once_with(product_id=test_product_id)
        mock_apply_filters_and_reload.assert_called_once()

        # Reset mocks for Test 2
        mock_qmessagebox_question.reset_mock()
        mock_crud_delete_product.reset_mock()
        mock_apply_filters_and_reload.reset_mock()

        # Test 2: Cancel Delete
        mock_qmessagebox_question.return_value = QMessageBox.No
        # Ensure selection is still valid for button to be clickable
        dialog.product_table.setCurrentCell(found_row, 1)

        dialog.delete_product_button.click()

        mock_qmessagebox_question.assert_called_once()
        mock_crud_delete_product.assert_not_called()
        mock_apply_filters_and_reload.assert_not_called()

        dialog.close()
        print("test_delete_product_button PASSED.")


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
