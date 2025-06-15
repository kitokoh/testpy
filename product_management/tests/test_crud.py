import unittest
import sqlite3
import sys
import os
from datetime import datetime
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from product_management.crud import ProductsCRUD # Updated import
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
                product_name TEXT NOT NULL UNIQUE,
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
            'base_unit_price': 19.99,
            'category': 'Category A',
            'description': 'Description for product 1'
        }
        self.product_data2 = {
            'product_name': 'Test Product 2',
            'base_unit_price': 29.99,
            'category': 'Category B'
        }
        self.product_data3 = {
            'product_name': 'Test Product 3',
            'base_unit_price': 39.99,
            'category': 'Category A'
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
        self.assertEqual(db_product['is_deleted'], 0)

    def test_add_product_missing_required_field(self):
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
    def test_add_or_update_product_dimension(self):
        product_id = self._add_product_get_id(self.product_data1)
        dim_data = {'dim_A': 10, 'dim_B': 20, 'technical_image_path': 'path/to/image.png'}

        # Add
        res_add = self.products_crud.add_or_update_product_dimension(product_id, dim_data, conn=self.conn)
        self.assertTrue(res_add['success'])
        self.assertEqual(res_add['operation'], 'inserted')

        db_dim = self.products_crud.get_product_dimension(product_id, conn=self.conn)
        self.assertIsNotNone(db_dim)
        self.assertEqual(db_dim['dim_A'], 10)

        # Update
        dim_data_update = {'dim_A': 12, 'dim_C': 30}
        res_update = self.products_crud.add_or_update_product_dimension(product_id, dim_data_update, conn=self.conn)
        self.assertTrue(res_update['success'])
        self.assertEqual(res_update['operation'], 'updated')

        db_dim_updated = self.products_crud.get_product_dimension(product_id, conn=self.conn)
        self.assertEqual(db_dim_updated['dim_A'], 12)
        self.assertEqual(db_dim_updated['dim_B'], 20) # Should persist
        self.assertEqual(db_dim_updated['dim_C'], 30)

    def test_get_product_dimension_for_soft_deleted_product(self):
        product_id = self._add_product_get_id(self.product_data1)
        dim_data = {'dim_A': 5}
        self.products_crud.add_or_update_product_dimension(product_id, dim_data, conn=self.conn)

        self.products_crud.delete_product(product_id, conn=self.conn) # Soft delete product

        self.assertIsNone(self.products_crud.get_product_dimension(product_id, conn=self.conn)) # Default no
        dim = self.products_crud.get_product_dimension(product_id, conn=self.conn, include_deleted_product=True)
        self.assertIsNotNone(dim)
        self.assertEqual(dim['dim_A'], 5)

    # --- ProductEquivalencies Tests ---
    def test_add_product_equivalence(self):
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

if __name__ == '__main__':
    unittest.main()
