import unittest
import sqlite3
import sys
import os

# Add the parent directory of 'db' to sys.path to allow direct import of 'db.cruds.generic_crud'
# This assumes 'tests' is a sibling of 'app' or 'db' is directly under 'app'
# tests/db/test_generic_crud.py -> tests/ -> app_root /
# sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# Correcting path assumption: if 'tests' is top-level, and cruds are in 'db/cruds'
# This structure assumes 'app' is the root and this file is 'app/tests/db/test_generic_crud.py'
# Or, if the tool runs from the repo root:
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from db.cruds.generic_crud import GenericCRUD

class TestGenericCRUD(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        # Create a dummy table for testing
        self.cursor.execute("""
            CREATE TABLE TestItems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value REAL
            )
        """)
        self.conn.commit()
        self.generic_crud = GenericCRUD()

        # Add some initial data
        self.cursor.execute("INSERT INTO TestItems (name, value) VALUES (?, ?)", ('item1', 10.5))
        self.cursor.execute("INSERT INTO TestItems (name, value) VALUES (?, ?)", ('item2', 20.0))
        self.conn.commit()
        self.item1_id = 1
        self.item2_id = 2


    def tearDown(self):
        self.conn.close()

    def test_get_by_id_exists(self):
        item = self.generic_crud.get_by_id('TestItems', 'id', self.item1_id, conn=self.conn)
        self.assertIsNotNone(item)
        self.assertEqual(item['name'], 'item1')

    def test_get_by_id_not_exists(self):
        item = self.generic_crud.get_by_id('TestItems', 'id', 999, conn=self.conn)
        self.assertIsNone(item)

    def test_delete_by_id_exists(self):
        result = self.generic_crud.delete_by_id('TestItems', 'id', self.item1_id, conn=self.conn)
        self.assertTrue(result)
        # Verify it's actually deleted
        item = self.generic_crud.get_by_id('TestItems', 'id', self.item1_id, conn=self.conn)
        self.assertIsNone(item)

    def test_delete_by_id_not_exists(self):
        result = self.generic_crud.delete_by_id('TestItems', 'id', 999, conn=self.conn)
        self.assertFalse(result)

    def test_exists_by_id_exists(self):
        result = self.generic_crud.exists_by_id('TestItems', 'id', self.item1_id, conn=self.conn)
        self.assertTrue(result)

    def test_exists_by_id_not_exists(self):
        result = self.generic_crud.exists_by_id('TestItems', 'id', 999, conn=self.conn)
        self.assertFalse(result)

    def test_get_all_has_items(self):
        items = self.generic_crud.get_all('TestItems', conn=self.conn)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['name'], 'item1')

    def test_get_all_empty_table(self):
        # Clear the table first
        self.cursor.execute("DELETE FROM TestItems")
        self.conn.commit()
        items = self.generic_crud.get_all('TestItems', conn=self.conn)
        self.assertEqual(len(items), 0)

    def test_get_all_order_by(self):
        # Add another item to make ordering more obvious
        self.cursor.execute("INSERT INTO TestItems (name, value) VALUES (?, ?)", ('item0', 5.0))
        self.conn.commit()

        items_asc = self.generic_crud.get_all('TestItems', conn=self.conn, order_by='name ASC')
        self.assertEqual(len(items_asc), 3)
        self.assertEqual(items_asc[0]['name'], 'item0')
        self.assertEqual(items_asc[1]['name'], 'item1')
        self.assertEqual(items_asc[2]['name'], 'item2')

        items_desc = self.generic_crud.get_all('TestItems', conn=self.conn, order_by='value DESC')
        self.assertEqual(len(items_desc), 3)
        self.assertEqual(items_desc[0]['name'], 'item2') # value 20.0
        self.assertEqual(items_desc[1]['name'], 'item1') # value 10.5
        self.assertEqual(items_desc[2]['name'], 'item0') # value 5.0

if __name__ == '__main__':
    unittest.main()
