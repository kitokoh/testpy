import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import csv

# Ensure QApplication is created before any QWidgets
from PyQt5.QtWidgets import QApplication, QDialog
# QApplication.instance() needs to be called before SettingsPage import if it's not already done in a global setup
app = QApplication.instance() if QApplication.instance() else QApplication([])

# Assuming settings_page.py is in the parent directory or sys.path is configured
# For this environment, we'll assume it can be found.
# If settings_page.py is in the root and tests is a subdir, this might need adjustment
# e.g., by adding parent dir to sys.path in a test runner or conftest.py
try:
    from settings_page import SettingsPage, ImportInstructionsDialog
except ModuleNotFoundError:
    # This is a common issue in test environments if PYTHONPATH isn't set up.
    # For now, we'll proceed assuming it's resolvable by the execution environment.
    # A real test suite would have a proper way to handle this (e.g., tox, nox, or a project structure that supports it).
    print("ERROR: Could not import SettingsPage. Ensure the module is in PYTHONPATH.")
    # Fallback for the agent to proceed, though tests won't run without the actual module.
    class SettingsPage: pass
    class ImportInstructionsDialog: pass


# Mock products_crud_instance globally for this test file
# This mock will be active before SettingsPage attempts to import it if done right
mock_products_crud_instance = MagicMock()

# This is a bit tricky. If settings_page.py does `from db.cruds.products_crud import products_crud_instance`,
# we need to patch it *there*. If it gets it from `db_manager.products_crud_instance`, we mock `db_manager`.
# The prompt mentioned `from db.cruds.products_crud import products_crud_instance` was added to settings_page.py
# So, we need to patch 'settings_page.products_crud_instance'.

@patch('settings_page.products_crud_instance', new=mock_products_crud_instance)
class TestSettingsPageDataManagement(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Ensures QApplication exists for all tests in this class
        # cls.app = QApplication.instance() if QApplication.instance() else QApplication([])
        pass # app is created globally now

    def setUp(self):
        # Reset mocks for each test
        mock_products_crud_instance.reset_mock()

        # Mock necessary parts for SettingsPage instantiation
        self.mock_main_config = {}
        self.mock_app_root_dir = "/fake/app/root"
        self.mock_current_user_id = "test_user"

        # Patch QFileDialog and QMessageBox for all tests in this class
        # These patches will be active for the duration of each test method
        self.patch_qfiledialog = patch('settings_page.QFileDialog')
        self.mock_qfiledialog = self.patch_qfiledialog.start()

        self.patch_qmessagebox = patch('settings_page.QMessageBox')
        self.mock_qmessagebox = self.patch_qmessagebox.start()

        # Patch the custom ImportInstructionsDialog
        self.patch_import_instructions_dialog = patch('settings_page.ImportInstructionsDialog')
        self.mock_import_instructions_dialog_class = self.patch_import_instructions_dialog.start()
        # Configure the mocked class's instance's exec_ method
        self.mock_import_instructions_dialog_instance = MagicMock()
        self.mock_import_instructions_dialog_class.return_value = self.mock_import_instructions_dialog_instance
        self.mock_import_instructions_dialog_instance.exec_.return_value = QDialog.Accepted # Default for most tests

        # Create an instance of SettingsPage
        # This needs to be done *after* 'settings_page.products_crud_instance' is patched if SettingsPage imports it at module level.
        # The class-level patch should handle this.
        self.settings_page = SettingsPage(
            main_config=self.mock_main_config,
            app_root_dir=self.mock_app_root_dir,
            current_user_id=self.mock_current_user_id
        )
        # It's good practice to ensure the settings page has the buttons (they are created in _setup_data_management_tab)
        # For these unit tests, we are calling _handle_import/export_products directly, so buttons aren't strictly needed
        # but if we were simulating clicks, we would need them.

    def tearDown(self):
        self.patch_qfiledialog.stop()
        self.patch_qmessagebox.stop()
        self.patch_import_instructions_dialog.stop()

    # --- Tests for Product Export ---
    def test_export_products_successful(self):
        sample_products = [
            MagicMock(product_id='p1', product_name='Product 1', product_code='P001', description='Desc 1', category='Cat A',
                      language_code='en', base_unit_price=10.99, unit_of_measure='pcs', weight=0.5,
                      dimensions='10x5x2', is_active=True, is_deleted=False),
            MagicMock(product_id='p2', product_name='Product 2', product_code='P002', description='Desc 2', category='Cat B',
                      language_code='fr', base_unit_price=19.99, unit_of_measure='kg', weight=1.2,
                      dimensions='20x10x5', is_active=False, is_deleted=True),
        ]
        mock_products_crud_instance.get_all_products.return_value = sample_products

        dummy_filepath = "/fake/path/export.csv"
        self.mock_qfiledialog.getSaveFileName.return_value = (dummy_filepath, "CSV Files (*.csv)")

        # Mock open to capture what's written to the CSV
        mock_csv_open = mock_open()
        with patch('builtins.open', mock_csv_open):
            self.settings_page._handle_export_products()

        mock_products_crud_instance.get_all_products.assert_called_once_with(include_deleted=True, limit=None, offset=0)
        self.mock_qfiledialog.getSaveFileName.assert_called_once()

        # Verify CSV content
        mock_csv_open.assert_called_once_with(dummy_filepath, 'w', newline='', encoding='utf-8')

        # Get all write calls and join them to reconstruct the CSV content
        written_content = "".join(call.args[0] for call in mock_csv_open().write.call_args_list)

        reader = csv.reader(written_content.splitlines())
        header = next(reader)
        self.assertEqual(header, ["product_id", "product_name", "product_code", "description", "category",
                                  "language_code", "base_unit_price", "unit_of_measure", "weight",
                                  "dimensions", "is_active", "is_deleted"])

        row1 = next(reader)
        self.assertEqual(row1, ['p1', 'Product 1', 'P001', 'Desc 1', 'Cat A', 'en', '10.99', 'pcs', '0.5', '10x5x2', 'True', 'False'])
        row2 = next(reader)
        self.assertEqual(row2, ['p2', 'Product 2', 'P002', 'Desc 2', 'Cat B', 'fr', '19.99', 'kg', '1.2', '20x10x5', 'False', 'True'])

        self.mock_qmessagebox.information.assert_called_once_with(
            self.settings_page,
            self.settings_page.tr("Export Successful"),
            self.settings_page.tr("Products exported successfully to: {0}").format(dummy_filepath)
        )

    def test_export_products_no_data(self):
        mock_products_crud_instance.get_all_products.return_value = []

        self.settings_page._handle_export_products()

        mock_products_crud_instance.get_all_products.assert_called_once_with(include_deleted=True, limit=None, offset=0)
        self.mock_qfiledialog.getSaveFileName.assert_not_called() # Should not ask for filename if no data
        self.mock_qmessagebox.information.assert_called_once_with(
            self.settings_page,
            self.settings_page.tr("No Products"),
            self.settings_page.tr("There are no products to export.")
        )

    def test_export_products_crud_error_on_get(self):
        mock_products_crud_instance.get_all_products.side_effect = Exception("DB Read Error")

        self.settings_page._handle_export_products()

        mock_products_crud_instance.get_all_products.assert_called_once_with(include_deleted=True, limit=None, offset=0)
        self.mock_qfiledialog.getSaveFileName.assert_not_called()
        self.mock_qmessagebox.critical.assert_called_once_with(
            self.settings_page,
            self.settings_page.tr("Database Error"),
            self.settings_page.tr("Failed to retrieve products from the database: {0}").format("DB Read Error")
        )

    def test_export_products_file_dialog_cancel(self):
        sample_products = [MagicMock(product_id='p1', product_name='Product 1')] # Minimal data
        mock_products_crud_instance.get_all_products.return_value = sample_products

        self.mock_qfiledialog.getSaveFileName.return_value = ("", "") # User cancels dialog

        # Mock open to ensure it's not called
        mock_csv_open = mock_open()
        with patch('builtins.open', mock_csv_open):
            self.settings_page._handle_export_products()

        mock_products_crud_instance.get_all_products.assert_called_once()
        self.mock_qfiledialog.getSaveFileName.assert_called_once()
        mock_csv_open.assert_not_called() # File should not be opened
        self.mock_qmessagebox.information.assert_not_called() # No success/failure message related to file write

    def test_export_products_io_error_on_write(self):
        sample_products = [MagicMock(product_id='p1', product_name='Product 1')]
        mock_products_crud_instance.get_all_products.return_value = sample_products

        dummy_filepath = "/fake/path/export.csv"
        self.mock_qfiledialog.getSaveFileName.return_value = (dummy_filepath, "CSV Files (*.csv)")

        # Mock open to raise IOError
        with patch('builtins.open', mock_open() as m_open):
            m_open.side_effect = IOError("Disk full")
            self.settings_page._handle_export_products()

        self.mock_qmessagebox.critical.assert_called_once_with(
            self.settings_page,
            self.settings_page.tr("Export Error"),
            self.settings_page.tr("Failed to write to file: {0}\nError: {1}").format(dummy_filepath, "Disk full")
        )

    # --- Tests for Product Import ---
    def test_import_products_successful(self):
        csv_content = (
            "product_id,product_name,product_code,description,category,language_code,base_unit_price,unit_of_measure,weight,dimensions,is_active,is_deleted\n"
            "ignore_me,ProdImport1,PI001,DescImport1,CatImpA,en,15.99,pcs,0.6,12x6x3,True,False\n"
            "ignore_me_too,ProdImport2,PI002,DescImport2,CatImpB,fr,25.50,kg,1.5,22x11x6,FALSE,TRUE" # Test mixed case boolean
        )

        self.mock_qfiledialog.getOpenFileName.return_value = ("/fake/import.csv", "CSV Files (*.csv)")
        mock_products_crud_instance.add_product.return_value = {'success': True, 'id': MagicMock()} # Simulate successful add

        with patch('builtins.open', mock_open(read_data=csv_content)):
            self.settings_page._handle_import_products()

        self.mock_import_instructions_dialog_instance.exec_.assert_called_once()
        self.mock_qfiledialog.getOpenFileName.assert_called_once()

        self.assertEqual(mock_products_crud_instance.add_product.call_count, 2)

        # Check first call's data
        call_args_1 = mock_products_crud_instance.add_product.call_args_list[0][0][0]
        self.assertEqual(call_args_1['product_name'], "ProdImport1")
        self.assertEqual(call_args_1['product_code'], "PI001")
        self.assertEqual(call_args_1['base_unit_price'], 15.99)
        self.assertTrue(call_args_1['is_active'])
        self.assertFalse(call_args_1['is_deleted'])

        # Check second call's data
        call_args_2 = mock_products_crud_instance.add_product.call_args_list[1][0][0]
        self.assertEqual(call_args_2['product_name'], "ProdImport2")
        self.assertEqual(call_args_2['product_code'], "PI002")
        self.assertEqual(call_args_2['base_unit_price'], 25.50)
        self.assertFalse(call_args_2['is_active'])
        self.assertTrue(call_args_2['is_deleted'])

        self.mock_qmessagebox.information.assert_called_once_with(
            self.settings_page,
            self.settings_page.tr("Import Successful"),
            self.settings_page.tr("Import complete.\nSuccessfully imported: {0} products.\nFailed to import: {1} products.").format(2, 0)
        )

    def test_import_products_instructions_dialog_cancel(self):
        self.mock_import_instructions_dialog_instance.exec_.return_value = QDialog.Rejected # Simulate user cancelling instructions

        self.settings_page._handle_import_products()

        self.mock_import_instructions_dialog_instance.exec_.assert_called_once()
        self.mock_qfiledialog.getOpenFileName.assert_not_called()
        mock_products_crud_instance.add_product.assert_not_called()
        self.mock_qmessagebox.information.assert_not_called()

    def test_import_products_file_dialog_cancel(self):
        self.mock_qfiledialog.getOpenFileName.return_value = ("", "") # User cancels file dialog

        self.settings_page._handle_import_products()

        self.mock_import_instructions_dialog_instance.exec_.assert_called_once()
        self.mock_qfiledialog.getOpenFileName.assert_called_once()
        mock_products_crud_instance.add_product.assert_not_called()
        self.mock_qmessagebox.information.assert_not_called() # No summary if no file selected

    def test_import_products_invalid_header(self):
        csv_content = "bad_header,column2\nval1,val2"
        self.mock_qfiledialog.getOpenFileName.return_value = ("/fake/bad_header.csv", "CSV Files (*.csv)")

        with patch('builtins.open', mock_open(read_data=csv_content)):
            self.settings_page._handle_import_products()

        self.mock_qmessagebox.critical.assert_called_once_with(
            self.settings_page,
            self.settings_page.tr("Invalid CSV Format"),
            self.settings_page.tr("The CSV file is missing one or more required headers (product_name, product_code, base_unit_price) or is not a valid CSV.")
        )
        mock_products_crud_instance.add_product.assert_not_called()

    def test_import_products_some_invalid_rows(self):
        csv_content = (
            "product_name,product_code,base_unit_price,is_active\n" # Minimal valid header
            "Prod1,P001,10.00,True\n" # Valid
            ",P002,20.00,True\n" # Missing name
            "Prod3,,30.00,False\n" # Missing code
            "Prod4,P004,not_a_price,True\n" # Invalid price
            "Prod5,P005,50.00\n" # Valid, is_active defaults
        )
        self.mock_qfiledialog.getOpenFileName.return_value = ("/fake/mixed.csv", "CSV Files (*.csv)")
        mock_products_crud_instance.add_product.return_value = {'success': True, 'id': MagicMock()}

        with patch('builtins.open', mock_open(read_data=csv_content)):
            self.settings_page._handle_import_products()

        self.assertEqual(mock_products_crud_instance.add_product.call_count, 2) # Prod1 and Prod5

        # Check that Prod1 was processed correctly
        args_prod1 = mock_products_crud_instance.add_product.call_args_list[0][0][0]
        self.assertEqual(args_prod1['product_name'], "Prod1")
        self.assertEqual(args_prod1['base_unit_price'], 10.0)
        self.assertTrue(args_prod1['is_active'])

        # Check that Prod5 was processed correctly
        args_prod5 = mock_products_crud_instance.add_product.call_args_list[1][0][0]
        self.assertEqual(args_prod5['product_name'], "Prod5")
        self.assertEqual(args_prod5['base_unit_price'], 50.0)
        self.assertTrue(args_prod5['is_active']) # Default for is_active

        self.mock_qmessagebox.warning.assert_called_once()
        # Check the message content (simplified check)
        args, _ = self.mock_qmessagebox.warning.call_args
        self.assertIn(self.settings_page.tr("Import complete.\nSuccessfully imported: {0} products.\nFailed to import: {1} products.").format(2, 3), args[1])
        self.assertIn(self.settings_page.tr("Line {0}: Missing required field 'product_name'.").format(3), args[1]) # Line 3 in CSV (row index 1 + 2)
        self.assertIn(self.settings_page.tr("Line {0}: Missing required field 'product_code' for product '{1}'.").format(4, "Prod3"), args[1])
        self.assertIn(self.settings_page.tr("Line {0}: Invalid format for 'base_unit_price' (must be a number) for product '{1}'.").format(5, "Prod4"), args[1])


    def test_import_products_crud_add_fails(self):
        csv_content = "product_name,product_code,base_unit_price\nProdFail,PF001,99.99"
        self.mock_qfiledialog.getOpenFileName.return_value = ("/fake/fail_add.csv", "CSV Files (*.csv)")
        mock_products_crud_instance.add_product.side_effect = Exception("DB Unique Constraint Failed")

        with patch('builtins.open', mock_open(read_data=csv_content)):
            self.settings_page._handle_import_products()

        mock_products_crud_instance.add_product.assert_called_once()
        self.mock_qmessagebox.warning.assert_called_once()
        args, _ = self.mock_qmessagebox.warning.call_args
        self.assertIn(self.settings_page.tr("Import complete.\nSuccessfully imported: {0} products.\nFailed to import: {1} products.").format(0, 1), args[1])
        self.assertIn(self.settings_page.tr("Line {0}: Error importing product '{1}': {2}").format(2, "ProdFail", "DB Unique Constraint Failed"), args[1])


    def test_import_products_file_not_found(self):
        self.mock_qfiledialog.getOpenFileName.return_value = ("/fake/nonexistent.csv", "CSV Files (*.csv)")

        with patch('builtins.open', mock_open()) as m_open:
            m_open.side_effect = FileNotFoundError("File does not exist")
            self.settings_page._handle_import_products()

        self.mock_qmessagebox.critical.assert_called_once_with(
            self.settings_page,
            self.settings_page.tr("Error"),
            self.settings_page.tr("The selected file was not found: {0}").format("/fake/nonexistent.csv")
        )

if __name__ == '__main__':
    unittest.main()
