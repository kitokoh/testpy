import unittest
import sqlite3
import sys
import os
from datetime import datetime
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from db.cruds.products_crud import ProductsCRUD
# Assuming product_media_links_crud is a module with functions.
# We will mock its behavior within ProductsCRUD for these tests.

class TestProductsCRUD(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        # --- Schema Definition ---
        self.cursor.execute("""
            CREATE TABLE Products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL, -- UNIQUE constraint removed for product_code tests, will be (name, lang) usually
                product_code TEXT UNIQUE, -- Added product_code
                description TEXT,
                category TEXT,
                language_code TEXT DEFAULT 'fr',
                base_unit_price REAL NOT NULL,
                unit_of_measure TEXT,
                weight REAL,
                dimensions TEXT, -- Simple text for now, could be JSON or link to ProductDimensions
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE ProductDimensions (
                product_id INTEGER PRIMARY KEY,
                dim_A REAL, dim_B REAL, dim_C REAL, dim_D REAL, dim_E REAL,
                dim_F REAL, dim_G REAL, dim_H REAL, dim_I REAL, dim_J REAL,
                technical_image_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES Products(product_id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE ProductEquivalencies (
                equivalence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id_a INTEGER NOT NULL,
                product_id_b INTEGER NOT NULL,
                FOREIGN KEY (product_id_a) REFERENCES Products(product_id),
                FOREIGN KEY (product_id_b) REFERENCES Products(product_id),
                UNIQUE (product_id_a, product_id_b)
            )
        """)
        # ProductMediaLinks is used by product_media_links_crud, not directly by ProductsCRUD tests here
        # as we mock the media_links_crud interaction.

        self.conn.commit()

        self.products_crud = ProductsCRUD()
        # Mock the media_links_crud module/object used by ProductsCRUD instance
        self.products_crud.media_links_crud = MagicMock()
        self.products_crud.media_links_crud.get_media_links_for_product = MagicMock(return_value=[])


        # Sample Data
        self.product_data1 = {
            'product_name': 'Test Product 1',
            'product_code': 'TP001',
            'base_unit_price': 19.99,
            'category': 'Category A',
            'description': 'Description for product 1',
            'language_code': 'en'
        }
        self.product_data2 = {
            'product_name': 'Test Product 2',
            'product_code': 'TP002',
            'base_unit_price': 29.99,
            'category': 'Category B',
            'language_code': 'en'
        }
        self.product_data3 = {
            'product_name': 'Test Product 3',
            'product_code': 'TP003',
            'base_unit_price': 39.99,
            'category': 'Category A',
            'language_code': 'fr'
        }

    def tearDown(self):
        self.conn.close()

    # --- Helper to add product and return ID ---
    def _add_product_get_id(self, product_data):
        res = self.products_crud.add_product(product_data, conn=self.conn)
        self.assertTrue(res['success'], f"Failed to add product: {res.get('error')}")
        self.assertIsNotNone(res.get('id'))
        return res['id']

    # --- Product Tests ---
    def test_add_product_success(self):
        res = self.products_crud.add_product(self.product_data1, conn=self.conn)
        self.assertTrue(res['success'])
        self.assertIsNotNone(res.get('id'))
        product_id = res['id']

        db_product = self.cursor.execute("SELECT * FROM Products WHERE product_id = ?", (product_id,)).fetchone()
        self.assertIsNotNone(db_product)
        self.assertEqual(db_product['product_name'], self.product_data1['product_name'])
        self.assertEqual(db_product['product_code'], self.product_data1['product_code']) # Verify product_code
        self.assertEqual(db_product['is_deleted'], 0)

    def test_add_product_missing_required_field_product_code(self):
        invalid_data = self.product_data1.copy()
        del invalid_data['product_code'] # Test missing product_code
        res = self.products_crud.add_product(invalid_data, conn=self.conn)
        self.assertFalse(res['success'])
        self.assertIn("Missing required field: product_code", res['error'])

    def test_add_product_missing_required_field_name(self): # Keep existing test for name
        invalid_data = self.product_data1.copy()
        del invalid_data['product_name']
        res = self.products_crud.add_product(invalid_data, conn=self.conn)
        self.assertFalse(res['success'])
        self.assertIn("Missing required field: product_name", res['error'])

    def test_add_product_invalid_price(self):
        invalid_data = self.product_data1.copy()
        invalid_data['base_unit_price'] = "not_a_price"
        res = self.products_crud.add_product(invalid_data, conn=self.conn)
        self.assertFalse(res['success'])
        self.assertIn("Invalid data type for base_unit_price", res['error'])

    def test_get_product_by_id_exists(self):
        product_id = self._add_product_get_id(self.product_data1)
        self.products_crud.media_links_crud.get_media_links_for_product.return_value = [{'link': 'dummy_link'}]

        product = self.products_crud.get_product_by_id(product_id, conn=self.conn)
        self.assertIsNotNone(product)
        self.assertEqual(product['product_name'], self.product_data1['product_name'])
        self.assertIn('media_links', product)
        self.assertEqual(len(product['media_links']), 1)
        self.products_crud.media_links_crud.get_media_links_for_product.assert_called_with(product_id=product_id, conn=self.conn)

    def test_get_product_by_id_not_exists(self):
        product = self.products_crud.get_product_by_id(999, conn=self.conn)
        self.assertIsNone(product)

    def test_soft_delete_product(self):
        product_id = self._add_product_get_id(self.product_data1)
        delete_res = self.products_crud.delete_product(product_id, conn=self.conn)
        self.assertTrue(delete_res['success'])

        db_product = self.cursor.execute("SELECT * FROM Products WHERE product_id = ?", (product_id,)).fetchone()
        self.assertEqual(db_product['is_deleted'], 1)
        self.assertEqual(db_product['is_active'], 0) # Check is_active is also set to 0
        self.assertIsNotNone(db_product['deleted_at'])

        # Check getters
        self.assertIsNone(self.products_crud.get_product_by_id(product_id, conn=self.conn))
        self.assertIsNotNone(self.products_crud.get_product_by_id(product_id, conn=self.conn, include_deleted=True))

    def test_get_all_products_pagination_and_soft_delete(self):
        p1_id = self._add_product_get_id(self.product_data1)
        self._add_product_get_id(self.product_data2)
        self._add_product_get_id(self.product_data3) # Total 3 products

        all_prod = self.products_crud.get_all_products(conn=self.conn)
        self.assertEqual(len(all_prod), 3)

        paginated = self.products_crud.get_all_products(conn=self.conn, limit=1, offset=1)
        self.assertEqual(len(paginated), 1)
        # Assuming order by name: Product 1, Product 2, Product 3
        self.assertEqual(paginated[0]['product_name'], self.product_data2['product_name'])


        self.products_crud.delete_product(p1_id, conn=self.conn) # Soft delete p1
        active_prod = self.products_crud.get_all_products(conn=self.conn)
        self.assertEqual(len(active_prod), 2)

        all_incl_deleted = self.products_crud.get_all_products(conn=self.conn, include_deleted=True)
        self.assertEqual(len(all_incl_deleted), 3)

    def test_update_product_price(self):
        product_id = self._add_product_get_id(self.product_data1)
        new_price = 25.99
        res = self.products_crud.update_product_price(product_id, new_price, conn=self.conn)
        self.assertTrue(res['success'])

        updated_prod = self.products_crud.get_product_by_id(product_id, conn=self.conn)
        self.assertEqual(updated_prod['base_unit_price'], new_price)

    # --- ProductDimensions Tests ---
    def test_add_product_dimension(self):
        product_id = self._add_product_get_id(self.product_data1)
        dim_data = {'dim_A': 10, 'dim_B': 20, 'technical_image_path': 'path/to/image.png'}

        # Using add_or_update_product_dimension for adding initially
        res_add = self.products_crud.add_or_update_product_dimension(product_id, dim_data, conn=self.conn)
        self.assertTrue(res_add['success'])
        self.assertEqual(res_add['operation'], 'inserted')

        db_dim = self.products_crud.get_product_dimension(product_id, conn=self.conn)
        self.assertIsNotNone(db_dim)
        self.assertEqual(db_dim['dim_A'], 10)
        self.assertEqual(db_dim['technical_image_path'], 'path/to/image.png')

    def test_get_product_dimension(self):
        product_id = self._add_product_get_id(self.product_data1)
        dim_data = {'dim_A': 15, 'dim_G': 70}
        self.products_crud.add_or_update_product_dimension(product_id, dim_data, conn=self.conn)

        retrieved_dim = self.products_crud.get_product_dimension(product_id, conn=self.conn)
        self.assertIsNotNone(retrieved_dim)
        self.assertEqual(retrieved_dim['dim_A'], 15)
        self.assertEqual(retrieved_dim['dim_G'], 70)
        self.assertIsNone(retrieved_dim.get('dim_B')) # Check un-set dimension

    def test_update_product_dimension(self):
        product_id = self._add_product_get_id(self.product_data1)
        initial_dim_data = {'dim_A': 5, 'dim_B': 10}
        self.products_crud.add_or_update_product_dimension(product_id, initial_dim_data, conn=self.conn)

        update_dim_data = {'dim_A': 7, 'technical_image_path': 'new/path.jpg'}
        # Using add_or_update_product_dimension for updating
        res_update = self.products_crud.add_or_update_product_dimension(product_id, update_dim_data, conn=self.conn)
        self.assertTrue(res_update['success'])
        self.assertEqual(res_update['operation'], 'updated')

        updated_db_dim = self.products_crud.get_product_dimension(product_id, conn=self.conn)
        self.assertEqual(updated_db_dim['dim_A'], 7) # Updated
        self.assertEqual(updated_db_dim['dim_B'], 10) # Original should persist
        self.assertEqual(updated_db_dim['technical_image_path'], 'new/path.jpg') # Newly added

    def test_add_or_update_product_dimension_new_and_update(self): # Renamed from task, as it's the same as add then update
        product_id = self._add_product_get_id(self.product_data1)
        dim_data_add = {'dim_A': 10, 'technical_image_path': 'path/to/image.png'}

        # Add
        res_add = self.products_crud.add_or_update_product_dimension(product_id, dim_data_add, conn=self.conn)
        self.assertTrue(res_add['success'])
        self.assertEqual(res_add['operation'], 'inserted')
        db_dim_after_add = self.products_crud.get_product_dimension(product_id, conn=self.conn)
        self.assertEqual(db_dim_after_add['dim_A'], 10)

        # Update
        dim_data_update = {'dim_A': 12, 'dim_J': 100}
        res_update = self.products_crud.add_or_update_product_dimension(product_id, dim_data_update, conn=self.conn)
        self.assertTrue(res_update['success'])
        self.assertEqual(res_update['operation'], 'updated')
        db_dim_after_update = self.products_crud.get_product_dimension(product_id, conn=self.conn)
        self.assertEqual(db_dim_after_update['dim_A'], 12)
        self.assertEqual(db_dim_after_update['dim_J'], 100)
        self.assertEqual(db_dim_after_update['technical_image_path'], 'path/to/image.png') # Persisted

    def test_get_product_dimension_non_existent(self):
        # Non-existent product ID
        retrieved_dim = self.products_crud.get_product_dimension(999, conn=self.conn)
        self.assertIsNone(retrieved_dim)

        # Product exists, but no dimensions
        product_id = self._add_product_get_id(self.product_data1)
        retrieved_dim_no_dims = self.products_crud.get_product_dimension(product_id, conn=self.conn)
        self.assertIsNone(retrieved_dim_no_dims)

    def test_delete_product_dimension(self):
        product_id = self._add_product_get_id(self.product_data1)
        dim_data = {'dim_A': 10}
        self.products_crud.add_or_update_product_dimension(product_id, dim_data, conn=self.conn)
        self.assertIsNotNone(self.products_crud.get_product_dimension(product_id, conn=self.conn))

        res_delete = self.products_crud.delete_product_dimension(product_id, conn=self.conn)
        self.assertTrue(res_delete['success'])
        self.assertIsNone(self.products_crud.get_product_dimension(product_id, conn=self.conn))

        # Test deleting non-existent dimension
        res_delete_non_existent = self.products_crud.delete_product_dimension(product_id + 1, conn=self.conn)
        self.assertTrue(res_delete_non_existent['success']) # Should still be success, nothing to delete
        self.assertEqual(res_delete_non_existent.get('message'), "No dimensions found for product ID, nothing to delete.")


    def test_add_dimensions_to_soft_deleted_product(self):
        product_id = self._add_product_get_id(self.product_data1)
        self.products_crud.delete_product(product_id, conn=self.conn) # Soft delete

        dim_data = {'dim_A': 10}
        res = self.products_crud.add_or_update_product_dimension(product_id, dim_data, conn=self.conn)
        self.assertFalse(res['success'])
        self.assertIn("Product not found or is deleted", res['error'])

    # The duplicated test_add_or_update_product_dimension_new_and_update (previously named test_add_or_update_product_dimension)
    # which was here, is now correctly removed by ensuring this SEARCH block targets the end of the
    # test_add_dimensions_to_soft_deleted_product method, and the REPLACE block starts with the corrected
    # test_get_product_dimension_for_soft_deleted_product.

    def test_get_product_dimension_for_soft_deleted_product(self): # Corrected
        product_id = self._add_product_get_id(self.product_data1)
        dim_data = {'dim_A': 5}
        self.products_crud.add_or_update_product_dimension(product_id, dim_data, conn=self.conn)

        self.products_crud.delete_product(product_id, conn=self.conn) # Soft delete product

        # get_product_dimension should implicitly not find dimensions for a soft-deleted product
        # as it likely joins on an active Products table.
        res_get = self.products_crud.get_product_dimension(product_id, conn=self.conn)
        self.assertIsNone(res_get, "Should not get dimensions for a soft-deleted product.")

    # --- ProductEquivalencies Tests ---
    def test_add_product_equivalence(self): # This test already exists and is mostly fine. Will add new ones after.
        p1_id = self._add_product_get_id(self.product_data1)
        p2_id = self._add_product_get_id(self.product_data2)

        res = self.products_crud.add_product_equivalence(p1_id, p2_id, conn=self.conn)
        self.assertTrue(res['success'])
        self.assertIsNotNone(res.get('id'))

        # Test adding again (should report success, already exists)
        res_again = self.products_crud.add_product_equivalence(p1_id, p2_id, conn=self.conn)
        self.assertTrue(res_again['success'])
        self.assertIn("already exists", res_again.get('message','').lower())


    def test_add_product_equivalence_with_soft_deleted_product(self):
        p1_id = self._add_product_get_id(self.product_data1)
        p2_id = self._add_product_get_id(self.product_data2)
        self.products_crud.delete_product(p2_id, conn=self.conn) # Soft delete p2

        res = self.products_crud.add_product_equivalence(p1_id, p2_id, conn=self.conn)
        self.assertFalse(res['success'])
        self.assertIn("not found or is deleted", res['error'])

    def test_get_equivalent_products(self):
        p1_id = self._add_product_get_id(self.product_data1)
        p2_id = self._add_product_get_id(self.product_data2)
        p3_id = self._add_product_get_id(self.product_data3) # p3 will be soft-deleted equivalent

        self.products_crud.add_product_equivalence(p1_id, p2_id, conn=self.conn)
        self.products_crud.add_product_equivalence(p1_id, p3_id, conn=self.conn)

        self.products_crud.delete_product(p3_id, conn=self.conn) # Soft delete p3

        equivalents_p1 = self.products_crud.get_equivalent_products(p1_id, conn=self.conn)
        self.assertEqual(len(equivalents_p1), 1)
        self.assertEqual(equivalents_p1[0]['product_id'], p2_id)

        equivalents_p1_incl_deleted = self.products_crud.get_equivalent_products(p1_id, conn=self.conn, include_deleted=True)
        self.assertEqual(len(equivalents_p1_incl_deleted), 2)
        # Order might vary, check for presence
        found_ids_incl_deleted = {eq['product_id'] for eq in equivalents_p1_incl_deleted}
        self.assertIn(p2_id, found_ids_incl_deleted)
        self.assertIn(p3_id, found_ids_incl_deleted)

    def test_get_equivalent_products_no_equivalencies(self):
        p1_id = self._add_product_get_id(self.product_data1)
        equivalents = self.products_crud.get_equivalent_products(p1_id, conn=self.conn)
        self.assertEqual(len(equivalents), 0)

    def test_get_all_product_equivalencies(self):
        p1_id = self._add_product_get_id(self.product_data1)
        p2_id = self._add_product_get_id(self.product_data2)
        p3_id = self._add_product_get_id(self.product_data3)
        res1 = self.products_crud.add_product_equivalence(p1_id, p2_id, conn=self.conn)
        res2 = self.products_crud.add_product_equivalence(p1_id, p3_id, conn=self.conn)

        all_eqs = self.products_crud.get_all_product_equivalencies(conn=self.conn)
        self.assertEqual(len(all_eqs), 2)
        eq_ids_retrieved = {eq['equivalence_id'] for eq in all_eqs}
        self.assertIn(res1['id'], eq_ids_retrieved)
        self.assertIn(res2['id'], eq_ids_retrieved)

        # Test with product_id_filter
        eqs_for_p1 = self.products_crud.get_all_product_equivalencies(conn=self.conn, product_id_filter=p1_id)
        self.assertEqual(len(eqs_for_p1), 2)

        eqs_for_p2 = self.products_crud.get_all_product_equivalencies(conn=self.conn, product_id_filter=p2_id)
        self.assertEqual(len(eqs_for_p2), 1)
        self.assertEqual(eqs_for_p2[0]['equivalence_id'], res1['id'])

        # Test with non-existent product_id_filter
        eqs_for_non_existent = self.products_crud.get_all_product_equivalencies(conn=self.conn, product_id_filter=999)
        self.assertEqual(len(eqs_for_non_existent), 0)

    def test_remove_product_equivalence_by_id(self):
        p1_id = self._add_product_get_id(self.product_data1)
        p2_id = self._add_product_get_id(self.product_data2)
        res_add = self.products_crud.add_product_equivalence(p1_id, p2_id, conn=self.conn)
        equivalence_id = res_add['id']

        res_remove = self.products_crud.remove_product_equivalence(equivalence_id, conn=self.conn)
        self.assertTrue(res_remove['success'])

        db_eq_after_remove = self.cursor.execute("SELECT * FROM ProductEquivalencies WHERE equivalence_id = ?", (equivalence_id,)).fetchone()
        self.assertIsNone(db_eq_after_remove)

        # Test removing non-existent equivalence
        res_remove_non_existent = self.products_crud.remove_product_equivalence(equivalence_id + 10, conn=self.conn)
        self.assertTrue(res_remove_non_existent['success']) # Should be success, nothing to delete.
        self.assertEqual(res_remove_non_existent.get('message'), "Equivalence link not found, nothing to delete.")

    # --- Tests for product_code ---

    def test_add_product_duplicate_product_code_fails(self):
        self._add_product_get_id(self.product_data1) # Add first product
        duplicate_code_data = self.product_data2.copy()
        duplicate_code_data['product_code'] = self.product_data1['product_code'] # Use same code

        res = self.products_crud.add_product(duplicate_code_data, conn=self.conn)
        self.assertFalse(res['success'])
        self.assertIn("Product name or other unique constraint violated", res['error']) # Error message might vary slightly based on DB
        # For SQLite, it's often "UNIQUE constraint failed: Products.product_code"

    def test_update_product_code(self):
        product_id = self._add_product_get_id(self.product_data1)
        new_code = "UPDATED_CODE_001"
        update_data = {'product_code': new_code}

        res = self.products_crud.update_product(product_id, update_data, conn=self.conn)
        self.assertTrue(res['success'])
        self.assertEqual(res.get('updated_count', 0), 1)

        updated_db_product = self.products_crud.get_product_by_id(product_id, conn=self.conn)
        self.assertEqual(updated_db_product['product_code'], new_code)

    def test_update_product_to_duplicate_product_code_fails(self):
        p1_id = self._add_product_get_id(self.product_data1) # Has TP001
        p2_id = self._add_product_get_id(self.product_data2) # Has TP002

        update_data = {'product_code': self.product_data1['product_code']} # Try to set p2's code to TP001
        res = self.products_crud.update_product(p2_id, update_data, conn=self.conn)
        self.assertFalse(res['success'])
        self.assertIn("UNIQUE constraint failed", res.get('error', '').upper()) # Check for UNIQUE constraint error

    def test_get_product_by_code(self):
        p1_id = self._add_product_get_id(self.product_data1)

        # Test fetching existing product
        fetched_product = self.products_crud.get_product_by_code(self.product_data1['product_code'], conn=self.conn)
        self.assertIsNotNone(fetched_product)
        self.assertEqual(fetched_product['product_id'], p1_id)
        self.assertEqual(fetched_product['product_name'], self.product_data1['product_name'])
        self.products_crud.media_links_crud.get_media_links_for_product.assert_called_with(product_id=p1_id, conn=self.conn)


        # Test fetching non-existing product code
        non_existent_product = self.products_crud.get_product_by_code("NON_EXISTENT_CODE", conn=self.conn)
        self.assertIsNone(non_existent_product)

    def test_get_product_by_code_include_deleted(self):
        p1_id = self._add_product_get_id(self.product_data1)
        self.products_crud.delete_product(p1_id, conn=self.conn) # Soft delete

        # Should not find without include_deleted=True
        fetched_product_not_deleted = self.products_crud.get_product_by_code(self.product_data1['product_code'], conn=self.conn)
        self.assertIsNone(fetched_product_not_deleted)

        # Should find with include_deleted=True
        fetched_product_deleted = self.products_crud.get_product_by_code(self.product_data1['product_code'], conn=self.conn, include_deleted=True)
        self.assertIsNotNone(fetched_product_deleted)
        self.assertEqual(fetched_product_deleted['product_id'], p1_id)
        self.assertEqual(fetched_product_deleted['is_deleted'], 1)

    def test_get_all_products_filter_by_product_code_like(self):
        self._add_product_get_id(self.product_data1) # TP001
        self._add_product_get_id(self.product_data2) # TP002
        self.products_crud.add_product({
            'product_name': 'Another Product Same Code Prefix',
            'product_code': 'TP001-Variant',
            'base_unit_price': 9.99,
            'language_code': 'en'
        }, conn=self.conn)

        # Test partial match
        filters_partial = {'product_code_like': 'TP001'}
        filtered_products_partial = self.products_crud.get_all_products(filters=filters_partial, conn=self.conn)
        self.assertEqual(len(filtered_products_partial), 2)
        product_codes_partial = {p['product_code'] for p in filtered_products_partial}
        self.assertIn('TP001', product_codes_partial)
        self.assertIn('TP001-Variant', product_codes_partial)

        # Test exact match (using LIKE but with full code)
        filters_exact = {'product_code_like': 'TP002'}
        filtered_products_exact = self.products_crud.get_all_products(filters=filters_exact, conn=self.conn)
        self.assertEqual(len(filtered_products_exact), 1)
        self.assertEqual(filtered_products_exact[0]['product_code'], 'TP002')

        # Test no match
        filters_no_match = {'product_code_like': 'XYZ'}
        filtered_products_no_match = self.products_crud.get_all_products(filters=filters_no_match, conn=self.conn)
        self.assertEqual(len(filtered_products_no_match), 0)


if __name__ == '__main__':
    unittest.main()
