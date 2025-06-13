import unittest
import sqlite3
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from db.cruds.clients_crud import ClientsCRUD

class TestClientsCRUD(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        self.cursor.execute("""
            CREATE TABLE Clients (
                client_id TEXT PRIMARY KEY,
                client_name TEXT NOT NULL,
                company_name TEXT,
                primary_need_description TEXT,
                project_identifier TEXT,
                country_id TEXT,
                city_id TEXT,
                default_base_folder_path TEXT,
                status_id TEXT,
                selected_languages TEXT,
                price REAL,
                notes TEXT,
                category TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                created_by_user_id TEXT NOT NULL,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT
            )
        """)
        # Minimal other tables for basic foreign key linkage if complex queries are tested
        # For now, focusing on Clients table logic
        self.cursor.execute("CREATE TABLE ClientNotes (note_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT, note_text TEXT, user_id TEXT, timestamp TEXT)")
        self.conn.commit()

        self.clients_crud = ClientsCRUD()

        # Sample data
        self.user_id1 = "user_test_1"
        self.client_data1 = {
            'client_name': 'Test Client 1',
            'created_by_user_id': self.user_id1,
            'price': 100.50,
            'company_name': 'Test Company A',
            'category': 'Test Category'
        }
        self.client_data2 = {
            'client_name': 'Test Client 2',
            'created_by_user_id': 'user_test_2',
            'price': 200.75
        }


    def tearDown(self):
        self.conn.close()

    def test_add_client_success(self):
        result = self.clients_crud.add_client(self.client_data1, conn=self.conn)
        self.assertTrue(result['success'])
        self.assertIsNotNone(result.get('client_id'))
        client_id = result['client_id']

        # Verify in DB
        db_client = self.cursor.execute("SELECT * FROM Clients WHERE client_id = ?", (client_id,)).fetchone()
        self.assertIsNotNone(db_client)
        self.assertEqual(db_client['client_name'], self.client_data1['client_name'])
        self.assertEqual(db_client['is_deleted'], 0)

    def test_add_client_missing_required_field(self):
        invalid_data = self.client_data1.copy()
        del invalid_data['client_name']
        result = self.clients_crud.add_client(invalid_data, conn=self.conn)
        self.assertFalse(result['success'])
        self.assertIn("Missing required field: client_name", result['error'])

    def test_add_client_invalid_price_type(self):
        invalid_data = self.client_data1.copy()
        invalid_data['price'] = "not_a_number"
        result = self.clients_crud.add_client(invalid_data, conn=self.conn)
        self.assertFalse(result['success'])
        self.assertIn("Invalid data type for price", result['error'])

    def test_get_client_by_id_exists(self):
        add_result = self.clients_crud.add_client(self.client_data1, conn=self.conn)
        client_id = add_result['client_id']

        client = self.clients_crud.get_client_by_id(client_id, conn=self.conn)
        self.assertIsNotNone(client)
        self.assertEqual(client['client_name'], self.client_data1['client_name'])

    def test_get_client_by_id_not_exists(self):
        client = self.clients_crud.get_client_by_id("non_existent_id", conn=self.conn)
        self.assertIsNone(client)

    def test_soft_delete_client(self):
        add_result = self.clients_crud.add_client(self.client_data1, conn=self.conn)
        client_id = add_result['client_id']

        delete_result = self.clients_crud.delete_client(client_id, conn=self.conn)
        self.assertTrue(delete_result['success'])

        # Verify soft delete in DB
        db_client = self.cursor.execute("SELECT * FROM Clients WHERE client_id = ?", (client_id,)).fetchone()
        self.assertIsNotNone(db_client)
        self.assertEqual(db_client['is_deleted'], 1)
        self.assertIsNotNone(db_client['deleted_at'])

        # Verify getter excludes soft-deleted by default
        client = self.clients_crud.get_client_by_id(client_id, conn=self.conn)
        self.assertIsNone(client)

        # Verify getter includes soft-deleted when asked
        client_incl_deleted = self.clients_crud.get_client_by_id(client_id, conn=self.conn, include_deleted=True)
        self.assertIsNotNone(client_incl_deleted)
        self.assertEqual(client_incl_deleted['client_name'], self.client_data1['client_name'])

    def test_delete_non_existent_client(self):
        delete_result = self.clients_crud.delete_client("non_existent_id", conn=self.conn)
        self.assertFalse(delete_result['success'])
        self.assertIn("not found or already deleted", delete_result['error'])


    def test_get_all_clients(self):
        self.clients_crud.add_client(self.client_data1, conn=self.conn)
        self.clients_crud.add_client(self.client_data2, conn=self.conn)

        all_clients = self.clients_crud.get_all_clients(conn=self.conn)
        self.assertEqual(len(all_clients), 2)

        # Test pagination
        paginated_clients = self.clients_crud.get_all_clients(conn=self.conn, limit=1, offset=0)
        self.assertEqual(len(paginated_clients), 1)
        # Names are ordered, client_data1 and client_data2 names might need to be specific for predictable order
        # For now, just checking length.

        # Test soft delete filtering
        client1_id = self.cursor.execute("SELECT client_id FROM Clients WHERE client_name = ?", (self.client_data1['client_name'],)).fetchone()['client_id']
        self.clients_crud.delete_client(client1_id, conn=self.conn)

        all_active_clients = self.clients_crud.get_all_clients(conn=self.conn)
        self.assertEqual(len(all_active_clients), 1)
        self.assertEqual(all_active_clients[0]['client_name'], self.client_data2['client_name'])

        all_clients_incl_deleted = self.clients_crud.get_all_clients(conn=self.conn, include_deleted=True)
        self.assertEqual(len(all_clients_incl_deleted), 2)

    def test_get_all_clients_empty(self):
        clients = self.clients_crud.get_all_clients(conn=self.conn)
        self.assertEqual(len(clients), 0)

    def test_update_client_success(self):
        add_result = self.clients_crud.add_client(self.client_data1, conn=self.conn)
        client_id = add_result['client_id']

        update_data = {'client_name': 'Updated Name', 'price': 150.00}
        update_result = self.clients_crud.update_client(client_id, update_data, conn=self.conn)
        self.assertTrue(update_result['success'])
        self.assertEqual(update_result['updated_count'], 1)

        updated_db_client = self.clients_crud.get_client_by_id(client_id, conn=self.conn)
        self.assertEqual(updated_db_client['client_name'], 'Updated Name')
        self.assertEqual(updated_db_client['price'], 150.00)

    def test_update_client_non_existent(self):
        update_result = self.clients_crud.update_client("non_existent_id", {'client_name': 'New Name'}, conn=self.conn)
        # The current update_client might return success: True, updated_count: 0 if no error,
        # or success: False depending on implementation if ID is checked first.
        # Based on current implementation, it will execute UPDATE and get 0 rowcount.
        self.assertTrue(update_result['success']) # No SQL error
        self.assertEqual(update_result['updated_count'], 0) # No rows updated

    def test_update_client_invalid_data_type(self):
        add_result = self.clients_crud.add_client(self.client_data1, conn=self.conn)
        client_id = add_result['client_id']

        update_data = {'price': 'not_a_valid_price'}
        update_result = self.clients_crud.update_client(client_id, update_data, conn=self.conn)
        self.assertFalse(update_result['success'])
        self.assertIn("Invalid data type for price", update_result['error'])

    def test_add_client_note(self):
        add_client_res = self.clients_crud.add_client(self.client_data1, conn=self.conn)
        client_id = add_client_res['client_id']

        note_text = "This is a test note."
        add_note_res = self.clients_crud.add_client_note(client_id, note_text, self.user_id1, conn=self.conn)
        self.assertTrue(add_note_res['success'])
        self.assertIsNotNone(add_note_res['note_id'])

        notes = self.clients_crud.get_client_notes(client_id, conn=self.conn)
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]['note_text'], note_text)
        self.assertEqual(notes[0]['user_id'], self.user_id1)

    def test_get_client_notes_no_notes(self):
        add_client_res = self.clients_crud.add_client(self.client_data1, conn=self.conn)
        client_id = add_client_res['client_id']
        notes = self.clients_crud.get_client_notes(client_id, conn=self.conn)
        self.assertEqual(len(notes), 0)

    # Placeholder for get_all_clients_with_details - requires more setup for joined tables
    # def test_get_all_clients_with_details(self):
    #     # This would require setting up Countries, Cities, StatusSettings tables and data
    #     pass

if __name__ == '__main__':
    unittest.main()
