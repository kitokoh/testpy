import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import sys
import os
from datetime import datetime

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox, QInputDialog, QFileDialog
from PyQt5.QtCore import Qt

from product_management.edit_dialog import ProductEditDialog, SUPPORTED_LANGUAGES
from db.cruds import products_crud
from db.cruds import product_media_links_crud
from media_manager import operations as media_ops # For mocking add_image
from config import MEDIA_FILES_BASE_PATH # For _browse_technical_image path logic

# Ensure a QApplication instance exists.
app = QApplication.instance() if QApplication.instance() else QApplication(sys.argv)

class TestProductEditDialog(unittest.TestCase):

    def setUp(self):
        """Set up for each test method."""
        # self.app = QApplication.instance() if QApplication.instance() else QApplication(sys.argv)
        pass # QApplication is managed globally for now.

    @patch('product_management.edit_dialog.products_crud.get_product_by_id')
    @patch('product_management.edit_dialog.products_crud.get_product_dimension')
    @patch('product_management.edit_dialog.products_crud.get_all_product_equivalencies')
    def test_load_new_product_data(self, mock_get_equivalencies, mock_get_dimension, mock_get_product):
        """Test dialog state when product_id is None (new product)."""
        print("\nRunning test_load_new_product_data...")
        dialog = ProductEditDialog(product_id=None)

        self.assertEqual(dialog.windowTitle(), dialog.tr("Add New Product"))
        self.assertTrue(dialog.name_edit.text() == "")
        self.assertTrue(dialog.language_code_combo.isVisible())
        self.assertFalse(dialog.language_code_edit is not None and dialog.language_code_edit.isVisible())

        # Sections for existing products should be disabled
        self.assertFalse(dialog.gallery_group.isEnabled())
        self.assertFalse(dialog.tech_specs_group.isEnabled())
        self.assertFalse(dialog.equivalencies_group.isEnabled())

        mock_get_product.assert_not_called()
        mock_get_dimension.assert_not_called()
        mock_get_equivalencies.assert_not_called()
        dialog.close()

    @patch('product_management.edit_dialog.products_crud.get_product_by_id')
    @patch('product_management.edit_dialog.products_crud.get_product_dimension')
    @patch('product_management.edit_dialog.products_crud.get_all_product_equivalencies') # Mock this
    @patch('product_management.edit_dialog.media_ops.add_image') # For _populate_image_gallery if it calls it
    def test_load_existing_product_data(self, mock_media_add_image, mock_get_all_eq, mock_get_dim, mock_get_prod_by_id):
        print("\nRunning test_load_existing_product_data...")
        product_id = 1
        sample_product = {
            'product_id': product_id, 'product_name': 'Test Existing', 'description': 'Desc',
            'category': 'Cat', 'language_code': 'fr', 'base_unit_price': 12.34,
            'unit_of_measure': 'kg', 'weight': 1.2, 'dimensions': '10x10x10',
            'is_active': True, 'media_links': [{'media_filepath': 'test.jpg', 'media_title': 'Test Image'}]
        }
        sample_dimensions = {'dim_A': 1, 'dim_B': 2, 'technical_image_path': 'tech/img.png'}
        # Sample equivalencies: product_id_a, product_id_b, equivalence_id
        # get_all_product_equivalencies returns list of these link dicts.
        # load_product_data then fetches details for the "other" product.
        sample_eq_links = [{'equivalence_id': 10, 'product_id_a': product_id, 'product_id_b': 2}]
        sample_eq_prod_details = {'product_id': 2, 'product_name': 'Equivalent Prod', 'language_code': 'en'}

        mock_get_prod_by_id.side_effect = lambda pid, conn=None: sample_product if pid == product_id else (sample_eq_prod_details if pid == 2 else None)
        mock_get_dim.return_value = sample_dimensions
        mock_get_all_eq.return_value = sample_eq_links

        dialog = ProductEditDialog(product_id=product_id)

        mock_get_prod_by_id.assert_any_call(product_id, conn=None) # Initial load
        mock_get_prod_by_id.assert_any_call(2, conn=None) # Load for equivalent product details
        mock_get_dim.assert_called_once_with(product_id)
        mock_get_all_eq.assert_called_once_with(product_id_filter=product_id)

        self.assertEqual(dialog.name_edit.text(), sample_product['product_name'])
        self.assertEqual(dialog.language_code_edit.text(), sample_product['language_code'])
        self.assertEqual(dialog.dim_A_edit.text(), str(sample_dimensions['dim_A']))
        self.assertEqual(dialog.tech_image_path_edit.text(), sample_dimensions['technical_image_path'])
        self.assertTrue(dialog.gallery_group.isEnabled())
        self.assertTrue(dialog.tech_specs_group.isEnabled())
        self.assertTrue(dialog.equivalencies_group.isEnabled())
        self.assertTrue(dialog.equivalencies_list.count() > 0)
        self.assertIn(sample_eq_prod_details['product_name'], dialog.equivalencies_list.item(0).text())
        dialog.close()

    @patch('product_management.edit_dialog.QMessageBox.warning')
    @patch('product_management.edit_dialog.products_crud.add_product')
    @patch('product_management.edit_dialog.products_crud.add_or_update_product_dimension')
    def test_save_new_product(self, mock_add_or_update_dim, mock_add_prod, mock_msg_warn):
        print("\nRunning test_save_new_product...")
        dialog = ProductEditDialog(product_id=None)

        # Simulate filling UI
        dialog.name_edit.setText("New Product XYZ")
        dialog.description_edit.setPlainText("New Description")
        dialog.category_edit.setText("NewCat")
        # language_code_combo is used for new products
        lang_idx_to_select = 1 # e.g., French 'fr'
        dialog.language_code_combo.setCurrentIndex(lang_idx_to_select)
        selected_lang_code = SUPPORTED_LANGUAGES[lang_idx_to_select][1]
        dialog.price_edit.setText("99.99")
        dialog.dim_A_edit.setText("100")
        dialog.tech_image_path_edit.setText("new_tech_img.png") # Usually set by browse

        mock_add_prod.return_value = {'success': True, 'id': 500} # Simulate successful add
        mock_add_or_update_dim.return_value = {'success': True}

        with patch.object(dialog, 'accept', MagicMock()) as mock_accept, \
             patch.object(dialog, 'load_product_data', MagicMock()) as mock_load_data, \
             patch.object(QMessageBox, 'information', MagicMock()) as mock_msg_info:

            dialog._save_changes()

            expected_product_data = {
                'product_name': "New Product XYZ", 'description': "New Description",
                'category': "NewCat", 'language_code': selected_lang_code,
                'base_unit_price': 99.99, 'unit_of_measure': '', # Assuming empty if not filled
                'weight': None, 'dimensions': '', 'is_active': True
            }
            mock_add_prod.assert_called_once_with(product_data=expected_product_data)

            self.assertEqual(dialog.product_id, 500) # Check if product_id was updated in dialog

            expected_dim_data = {
                'dim_A': "100", 'dim_B': None, 'dim_C': None, 'dim_D': None, 'dim_E': None,
                'dim_F': None, 'dim_G': None, 'dim_H': None, 'dim_I': None, 'dim_J': None,
                'technical_image_path': "new_tech_img.png"
            }
            mock_add_or_update_dim.assert_called_once_with(500, expected_dim_data)

            mock_load_data.assert_called_once() # Should reload data after new product save
            mock_msg_info.assert_called() # Info message on success
            # mock_accept should NOT be called for new product, dialog stays open
            mock_accept.assert_not_called()
        dialog.close()


    @patch('product_management.edit_dialog.QMessageBox.warning')
    @patch('product_management.edit_dialog.products_crud.update_product')
    @patch('product_management.edit_dialog.products_crud.add_or_update_product_dimension')
    def test_save_existing_product(self, mock_add_or_update_dim, mock_update_prod, mock_msg_warn):
        print("\nRunning test_save_existing_product...")
        product_id = 1
        # First, load some data as if product exists
        with patch('product_management.edit_dialog.products_crud.get_product_by_id') as mock_get_init_prod, \
             patch('product_management.edit_dialog.products_crud.get_product_dimension') as mock_get_init_dim, \
             patch('product_management.edit_dialog.products_crud.get_all_product_equivalencies') as mock_get_init_eq:
            mock_get_init_prod.return_value = {'product_id': product_id, 'product_name': 'Old Name', 'language_code': 'en', 'base_unit_price': 10.0}
            mock_get_init_dim.return_value = {'dim_A': '5'}
            mock_get_init_eq.return_value = []
            dialog = ProductEditDialog(product_id=product_id)

        # Simulate UI changes
        dialog.name_edit.setText("Updated Name")
        dialog.price_edit.setText("12.50")
        dialog.dim_A_edit.setText("7")

        mock_update_prod.return_value = {'success': True}
        mock_add_or_update_dim.return_value = {'success': True}

        with patch.object(dialog, 'accept', MagicMock()) as mock_accept, \
             patch.object(QMessageBox, 'information', MagicMock()) as mock_msg_info:
            dialog._save_changes()

            expected_product_data = {
                'product_name': "Updated Name", 'description': '', 'category': '',
                'language_code': 'en', # From initial load, read-only
                'base_unit_price': 12.50, 'unit_of_measure': '', 'weight': None,
                'dimensions': '', 'is_active': True # Assuming default if not changed
            }
            mock_update_prod.assert_called_once_with(product_id=product_id, data=unittest.mock.ANY)
            # Check specific fields in the data passed to update_product
            args, kwargs = mock_update_prod.call_args
            self.assertEqual(kwargs['data']['product_name'], expected_product_data['product_name'])
            self.assertEqual(kwargs['data']['base_unit_price'], expected_product_data['base_unit_price'])


            expected_dim_data = {'dim_A': "7", # Changed
                                 # Other dims would be None if their QLineEdit is empty
                                 'dim_B': None, 'dim_C': None, 'dim_D': None, 'dim_E': None,
                                 'dim_F': None, 'dim_G': None, 'dim_H': None, 'dim_I': None, 'dim_J': None,
                                 'technical_image_path': None}
            mock_add_or_update_dim.assert_called_once_with(product_id, expected_dim_data)

            mock_msg_info.assert_called() # Info message on success
            mock_accept.assert_called_once() # Dialog should close on successful update
        dialog.close()

    @patch('product_management.edit_dialog.QInputDialog.getInt')
    @patch('product_management.edit_dialog.products_crud.add_product_equivalence')
    @patch('product_management.edit_dialog.products_crud.get_product_by_id') # For checking target product
    @patch('product_management.edit_dialog.products_crud.get_all_product_equivalencies') # For checking existing links
    @patch('product_management.edit_dialog.QMessageBox.information')
    @patch('product_management.edit_dialog.QMessageBox.warning')
    def test_add_product_equivalence(self, mock_msg_warn, mock_msg_info, mock_get_all_eq_check, mock_get_prod_check, mock_add_eq, mock_get_int):
        print("\nRunning test_add_product_equivalence...")
        # Setup: Dialog with an existing product_id
        with patch('product_management.edit_dialog.products_crud.get_product_by_id', return_value={'product_id': 1, 'product_name': 'Main'}):
            dialog = ProductEditDialog(product_id=1)

        mock_get_int.return_value = (2, True) # Simulate user entering Product ID 2 and clicking OK
        mock_get_prod_check.return_value = {'product_id': 2, 'name': 'TargetProd'} # Target product exists
        mock_get_all_eq_check.return_value = [] # No pre-existing equivalencies
        mock_add_eq.return_value = {'success': True, 'id': 123} # Successful link

        with patch.object(dialog, 'load_product_data', MagicMock()) as mock_load_data:
            dialog._add_product_equivalence()
            mock_get_int.assert_called_once()
            mock_get_prod_check.assert_called_once_with(2)
            mock_get_all_eq_check.assert_called_once_with(product_id_filter=1)
            mock_add_eq.assert_called_once_with(1, 2)
            mock_load_data.assert_called_once() # Ensure data is reloaded
            mock_msg_info.assert_called_once_with(dialog, dialog.tr("Success"), dialog.tr("Product equivalence added successfully."))

        # Test adding self as equivalent
        mock_get_int.return_value = (1, True) # Product links to itself
        dialog._add_product_equivalence()
        mock_msg_warn.assert_called_with(dialog, dialog.tr("Invalid ID"), dialog.tr("Cannot link a product to itself."))

        dialog.close()

    @patch('product_management.edit_dialog.QMessageBox.question')
    @patch('product_management.edit_dialog.products_crud.remove_product_equivalence')
    def test_remove_product_equivalence(self, mock_remove_eq, mock_msg_question):
        print("\nRunning test_remove_product_equivalence...")
        # Setup
        with patch('product_management.edit_dialog.products_crud.get_product_by_id', return_value={'product_id': 1, 'name': 'Main'}):
            dialog = ProductEditDialog(product_id=1)

        # Populate list widget with a dummy item
        item = MagicMock()
        item.data.return_value = {"equivalent_product_id": 2, "equivalence_id": 123}
        item.text.return_value = "Equivalent Product (eq) - ID: 2" # For message box
        dialog.equivalencies_list.addItem(item) # Add item directly for test
        dialog.equivalencies_list.setCurrentItem(item) # Select it

        mock_msg_question.return_value = QMessageBox.Yes # Confirm removal
        mock_remove_eq.return_value = {'success': True}

        with patch.object(dialog, 'load_product_data', MagicMock()) as mock_load_data, \
             patch.object(QMessageBox, 'information', MagicMock()) as mock_msg_info:
            dialog._remove_product_equivalence()
            mock_msg_question.assert_called_once()
            mock_remove_eq.assert_called_once_with(123)
            mock_load_data.assert_called_once()
            mock_msg_info.assert_called_with(dialog, dialog.tr("Success"), dialog.tr("Equivalence removed successfully."))
        dialog.close()

    @patch('product_management.edit_dialog.QFileDialog.getOpenFileName')
    def test_browse_technical_image(self, mock_get_open_file_name):
        print("\nRunning test_browse_technical_image...")
        with patch('product_management.edit_dialog.products_crud.get_product_by_id', return_value={'product_id': 1, 'name': 'Main'}):
            dialog = ProductEditDialog(product_id=1) # Needs product_id to enable button generally

        test_file_path = os.path.join(MEDIA_FILES_BASE_PATH, "schematics", "test_image.png")
        # Ensure schematics subfolder exists for relpath to work as expected if MEDIA_FILES_BASE_PATH is root for it
        expected_relative_path = os.path.join("schematics", "test_image.png")

        mock_get_open_file_name.return_value = (test_file_path, "Images (*.png *.jpg *.jpeg *.bmp *.gif)")

        dialog._browse_technical_image()

        mock_get_open_file_name.assert_called_once()
        # Path stored should be relative if under MEDIA_FILES_BASE_PATH
        # On Windows, os.path.normpath might be needed for consistent separator
        self.assertEqual(os.path.normpath(dialog.tech_image_path_edit.text()), os.path.normpath(expected_relative_path))

        # Test with file outside MEDIA_FILES_BASE_PATH (e.g. different root)
        # On Windows, relpath throws ValueError if paths are on different drives.
        # On POSIX, it will produce '..' paths.
        if os.name == 'nt': # Simulate different drive for Windows
            # This part of the test is tricky to make cross-platform robustly for "outside media base"
            # Let's assume for now if relpath fails or gives '..', it's handled as absolute.
             pass # Skip different drive test on windows for simplicity in unit test.
        else:
            another_path = "/another/root/image.png"
            mock_get_open_file_name.return_value = (another_path, "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
            with patch('product_management.edit_dialog.QMessageBox.warning') as mock_path_warn:
                 dialog._browse_technical_image()
                 self.assertEqual(dialog.tech_image_path_edit.text(), another_path)
                 mock_path_warn.assert_called()


        dialog.close()

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
