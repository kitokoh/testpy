import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import time # For unique naming

# Add project root to sys.path to allow imports from main project
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')) # Adjusted path for new location
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtGui import QIcon # For new column tests if icons were used
from product_management.list_dialog import ProductListDialog
from product_management.edit_dialog import ProductEditDialog # For mocking add/edit calls
from db.cruds.products_crud import products_crud_instance # Direct import
import html_to_pdf_util # Assuming this is still a top-level or correctly pathed import

# Ensure a QApplication instance exists for widget testing, but only one.
# It's often better to manage this per test class or even per test method if tests interfere.
# For simplicity here, we'll try a global one, but it can be problematic.
# A better approach for larger test suites is a base test class that handles QApplication.
app = QApplication.instance() if QApplication.instance() else QApplication(sys.argv)

# Old setUpModule and tearDownModule are removed as each test now uses an in-memory DB.

class TestProductList(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # This method is called once before any tests in the class are run.
        # Setup database connection using products_crud_instance's internal connection manager
        # This assumes products_crud_instance uses a similar mechanism to db_manager for DB init.
        # If products_crud_instance uses a global connection, this might conflict.
        # For now, we assume products_crud_instance can work with a test DB.

        # To ensure ProductsCRUD (and its instance) uses the test DB, we might need to
        # patch its _manage_conn decorator or its DB connection logic if it's hardcoded.
        # A simpler way for now if ProductsCRUD uses db_manager internally and db_manager is
        # already configured for test_app_data.db by setUpModule.
        # Let's assume products_crud_instance will pick up the test DB settings from db_manager
        # or that its methods accept a 'conn' parameter we can use.
        # The methods in ProductsCRUD (like get_all_products) do accept 'conn'.
        # We will pass the test connection from self.conn to these methods.
        pass

    @classmethod
    def tearDownClass(cls):
        # Called once after all tests in the class have run
        pass

    def setUp(self):
        """Set up for each test method."""
        # Create a new in-memory SQLite database for each test to ensure isolation
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row # To access columns by name
        # Create schema (simplified, focusing on what ProductListDialog needs)
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE Products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL, description TEXT, category TEXT,
                language_code TEXT, base_unit_price REAL, unit_of_measure TEXT,
                weight REAL, dimensions TEXT, is_active INTEGER DEFAULT 1,
                created_at TEXT, updated_at TEXT,
                is_deleted INTEGER DEFAULT 0, deleted_at TEXT
            )""")
        cursor.execute("""
            CREATE TABLE ProductDimensions (
                product_id INTEGER PRIMARY KEY, dim_A REAL, technical_image_path TEXT,
                FOREIGN KEY (product_id) REFERENCES Products(product_id)
            )""")
        cursor.execute("""
            CREATE TABLE ProductEquivalencies (
                equivalence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id_a INTEGER, product_id_b INTEGER,
                FOREIGN KEY (product_id_a) REFERENCES Products(product_id),
                FOREIGN KEY (product_id_b) REFERENCES Products(product_id)
            )""")
        self.conn.commit()
        self.products_to_cleanup = [] # This line is removed as it's not used with in-memory DB per test


    def tearDown(self):
        """Clean up after each test method."""
        self.conn.close() # Close the in-memory database


    def _add_test_product_to_db(self, name_suffix, lang, price=10.0, desc="Test Desc", category="TestCat"): # This helper is good
        """Directly adds a product to the test DB and returns its ID."""
        unique_name = f"TestProd_{name_suffix}_{int(time.time_ns())}"
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO Products (product_name, description, language_code, base_unit_price, category, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (unique_name, desc, lang, price, category, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
        self.conn.commit()
        product_id = cursor.lastrowid
        self.assertIsNotNone(product_id, f"Failed to add product {unique_name} to in-memory DB")

        return {
            'product_id': product_id, 'product_name': unique_name, 'description': desc,
            'language_code': lang, 'base_unit_price': price, 'category': category
        }

    # Old tests like test_fetch_products, test_update_product_price,
    # test_product_list_dialog_loads_data (old version), test_pdf_export_creates_file (old version)
    # are removed as they used the module-level DB and different mocking/assertion strategies.
    # The new tests test_product_list_dialog_loads_data_with_new_columns and
    # test_pdf_export_with_new_columns are more focused on UI and mocked data.

    @patch('product_management.list_dialog.products_crud_instance.get_product_dimension')
    @patch('product_management.list_dialog.products_crud_instance.get_equivalent_products')
    @patch('product_management.list_dialog.products_crud_instance.get_all_products')
    def test_product_list_dialog_loads_data_with_new_columns(self, mock_get_all_products, mock_get_equivalent_products, mock_get_product_dimension): # This is a new, enhanced test
        print("\nRunning test_product_list_dialog_loads_data_with_new_columns...")

        # Setup mock return values
        prod1_data = {'product_id': 1, 'product_name': 'Prod1', 'description': 'Desc1', 'base_unit_price': 10.0, 'language_code': 'en'}
        prod2_data = {'product_id': 2, 'product_name': 'Prod2', 'description': 'Desc2', 'base_unit_price': 20.0, 'language_code': 'fr'}
        mock_get_all_products.return_value = [prod1_data, prod2_data]

        # Mock for Prod1
        mock_get_product_dimension.side_effect = lambda product_id, conn=None: {'technical_image_path': 'path.jpg'} if product_id == 1 else None
        mock_get_equivalent_products.side_effect = lambda product_id, include_deleted=False, conn=None: [{'product_id': 101}] if product_id == 1 else []

        dialog = ProductListDialog() # This will call load_products_to_table

        # Verify table structure
        self.assertEqual(dialog.product_table.columnCount(), 7)
        headers = [dialog.product_table.horizontalHeaderItem(i).text() for i in range(dialog.product_table.columnCount())]
        self.assertIn("Language", headers)
        self.assertIn("Tech Specs", headers)
        self.assertIn("Translations", headers)

        # Verify data for Prod1 (row 0)
        self.assertEqual(dialog.product_table.item(0, 1).text(), 'Prod1') # Name
        self.assertEqual(dialog.product_table.item(0, 4).text(), 'en')    # Language
        self.assertEqual(dialog.product_table.item(0, 5).text(), dialog.tr("Yes")) # Tech Specs
        self.assertEqual(dialog.product_table.item(0, 6).text(), "1")      # Translations count

        # Reset side_effect for Prod2 before it's processed if get_all_products was called again or if loop processes it
        # For this test, get_all_products is called once. We need to set up side_effects carefully.
        mock_get_product_dimension.side_effect = lambda product_id, conn=None: None if product_id == 2 else {'technical_image_path': 'path.jpg'}
        mock_get_equivalent_products.side_effect = lambda product_id, include_deleted=False, conn=None: [] if product_id == 2 else [{'product_id': 101}]

        # Manually call load_products_to_table again if needed, or ensure mocks are general enough.
        # The initial load_products_to_table already happened. To test Prod2, we'd need to ensure the mocks are set before that.
        # Let's refine the mock setup to handle calls for different product_ids within the single load_products_to_table call.

        def dim_side_effect(product_id, conn=None):
            if product_id == 1: return {'technical_image_path': 'path.jpg'}
            if product_id == 2: return None # Prod2 has no tech specs
            return None

        def equiv_side_effect(product_id, include_deleted=False, conn=None):
            if product_id == 1: return [{'product_id': 101, 'product_name': 'Equiv1'}] # Prod1 has 1 translation
            if product_id == 2: return [] # Prod2 has no translations
            return []

        mock_get_product_dimension.side_effect = dim_side_effect
        mock_get_equivalent_products.side_effect = equiv_side_effect

        # Re-call load_products_to_table after setting up more specific mocks
        dialog.load_products_to_table() # This uses the mocked products_crud_instance methods

        self.assertEqual(dialog.product_table.rowCount(), 2)
        # Prod1 assertions (already made, but good to re-verify if load was re-run)
        self.assertEqual(dialog.product_table.item(0, 1).text(), 'Prod1')
        self.assertEqual(dialog.product_table.item(0, 4).text(), 'en')
        self.assertEqual(dialog.product_table.item(0, 5).text(), dialog.tr("Yes"))
        self.assertEqual(dialog.product_table.item(0, 6).text(), "1")

        # Verify data for Prod2 (row 1)
        self.assertEqual(dialog.product_table.item(1, 1).text(), 'Prod2') # Name
        self.assertEqual(dialog.product_table.item(1, 4).text(), 'fr')    # Language
        self.assertEqual(dialog.product_table.item(1, 5).text(), dialog.tr("No"))  # Tech Specs
        self.assertEqual(dialog.product_table.item(1, 6).text(), dialog.tr("No")) # Translations

        dialog.close()
        print("test_product_list_dialog_loads_data_with_new_columns PASSED.")


    @patch('product_management.list_dialog.QFileDialog.getSaveFileName')
    @patch('product_management.list_dialog.html_to_pdf_util.convert_html_to_pdf')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    @patch('product_management.list_dialog.products_crud_instance') # Mock the instance
    def test_pdf_export_with_new_columns(self, mock_crud_instance, mock_file_open, mock_convert_to_pdf, mock_get_save_file_name):
        print("\nRunning test_pdf_export_with_new_columns...")

        dummy_pdf_path = "dummy_path/test_product_list_enhanced.pdf"
        mock_get_save_file_name.return_value = (dummy_pdf_path, None)
        mock_convert_to_pdf.return_value = b'%PDF-1.4 dummy content enhanced'

        prod1_pdf_data = {'product_id': 1, 'product_name': 'Prod1PDF', 'description': 'Desc1', 'base_unit_price': 10.0, 'language_code': 'en'}
        mock_crud_instance.get_all_products.return_value = [prod1_pdf_data]

        def dim_side_effect_pdf(product_id, conn=None):
            if product_id == 1: return {'dim_A': 'Value'} # Has some tech spec
            return None
        def equiv_side_effect_pdf(product_id, include_deleted=False, conn=None):
            if product_id == 1: return [{'product_id': 102}] # Has one translation
            return []

        mock_crud_instance.get_product_dimension.side_effect = dim_side_effect_pdf
        mock_crud_instance.get_equivalent_products.side_effect = equiv_side_effect_pdf

        dialog = ProductListDialog()
        dialog.export_pdf_button.click()

        mock_convert_to_pdf.assert_called_once()
        rendered_html_arg = mock_convert_to_pdf.call_args[0][0]

        self.assertIn("<th>Language</th>", rendered_html_arg)
        self.assertIn("<th>Tech Specs</th>", rendered_html_arg)
        self.assertIn("<th>Translations</th>", rendered_html_arg)
        self.assertIn(f"<td>{prod1_pdf_data['language_code']}</td>", rendered_html_arg)
        self.assertIn(f"<td>{dialog.tr('Yes')}</td>", rendered_html_arg) # For tech specs
        self.assertIn("<td>1</td>", rendered_html_arg) # For translations count

        mock_file_open.assert_called_once_with(dummy_pdf_path, "wb")
        mock_file_open().write.assert_called_once_with(b'%PDF-1.4 dummy content enhanced')

        dialog.close()
        print("test_pdf_export_with_new_columns PASSED.")


    @patch('product_management.list_dialog.ProductListDialog.apply_filters_and_reload')
    @patch('product_management.list_dialog.ProductEditDialog') # Path to ProductEditDialog for mocking
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

    @patch('product_list_dialog.ProductListDialog.apply_filters_and_reload')
    @patch('product_list_dialog.ProductEditDialog')
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

    @patch('product_list_dialog.ProductListDialog.apply_filters_and_reload')
    @patch('product_list_dialog.products_crud_instance.delete_product')
    @patch('product_list_dialog.QMessageBox.question')
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
