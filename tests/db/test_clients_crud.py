import unittest
import sqlite3
import sys
import os
from datetime import datetime

import logging # For disabling logging during tests if needed
from unittest.mock import patch # For specific error simulation if possible

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import the instance for testing, and specific types if needed for isinstance checks etc.
from db.cruds.clients_crud import clients_crud_instance, ClientsCRUD

# Helper for date formatting consistent with the app
def format_datetime_for_db(dt_obj):
    return dt_obj.isoformat() + "Z"

class TestClientsCRUD(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Disable logging for most tests to keep output clean, can be enabled for debugging
        logging.disable(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET) # Re-enable logging

    def setUp(self):
        # Each test gets a fresh in-memory database
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
        self.cursor.execute("""
            CREATE TABLE StatusSettings (
                status_id TEXT PRIMARY KEY,
                status_name TEXT NOT NULL,
                status_type TEXT NOT NULL, -- e.g., 'Client', 'Project'
                color_hex TEXT,
                icon_name TEXT,
                is_default INTEGER DEFAULT 0,
                is_archival_status INTEGER DEFAULT 0, -- 0 for false, 1 for true
                display_order INTEGER
            )
        """)
        self.cursor.execute("CREATE TABLE ClientNotes (note_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT, note_text TEXT, user_id TEXT, timestamp TEXT)")
        self.conn.commit()

        # Use the global instance for tests, as it's what the application uses
        self.clients_crud = clients_crud_instance

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

    def _insert_client(self, client_id, created_at_dt, created_by_user_id="test_user", is_deleted=0, deleted_at_dt=None, status_id=None, client_name="Test Client"):
        created_at_iso = format_datetime_for_db(created_at_dt)
        deleted_at_iso = format_datetime_for_db(deleted_at_dt) if deleted_at_dt else None
        self.cursor.execute("""
            INSERT INTO Clients (client_id, client_name, created_at, updated_at, created_by_user_id, is_deleted, deleted_at, status_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (client_id, client_name, created_at_iso, created_at_iso, created_by_user_id, is_deleted, deleted_at_iso, status_id))
        self.conn.commit()

    def _insert_status_setting(self, status_id, status_name, status_type, is_archival_status):
        self.cursor.execute("""
            INSERT INTO StatusSettings (status_id, status_name, status_type, is_archival_status)
            VALUES (?, ?, ?, ?)
        """, (status_id, status_name, status_type, is_archival_status))
        self.conn.commit()

    # --- Tests for get_clients_count_created_between ---
    def test_get_clients_count_created_between_no_deleted(self):
        # Dates for test data
        date_2023_01_15 = datetime(2023, 1, 15, 12, 0, 0)
        date_2023_02_10 = datetime(2023, 2, 10, 12, 0, 0)
        date_2023_03_05 = datetime(2023, 3, 5, 12, 0, 0)

        # Insert clients
        self._insert_client("client1", date_2023_01_15) # Outside range (before)
        self._insert_client("client2", date_2023_02_10) # Inside range
        self._insert_client("client3", date_2023_02_10, is_deleted=1) # Inside range, but deleted
        self._insert_client("client4", date_2023_03_05) # Outside range (after)

        start_iso = format_datetime_for_db(datetime(2023, 2, 1, 0, 0, 0))
        end_iso = format_datetime_for_db(datetime(2023, 2, 28, 23, 59, 59))

        count = self.clients_crud.get_clients_count_created_between(start_iso, end_iso, conn=self.conn, include_deleted=False)
        self.assertEqual(count, 1) # Only client2

    def test_get_clients_count_created_between_with_deleted(self):
        date_2023_02_10 = datetime(2023, 2, 10, 12, 0, 0)
        self._insert_client("client2", date_2023_02_10)
        self._insert_client("client3", date_2023_02_10, is_deleted=1)

        start_iso = format_datetime_for_db(datetime(2023, 2, 1, 0, 0, 0))
        end_iso = format_datetime_for_db(datetime(2023, 2, 28, 23, 59, 59))

        count = self.clients_crud.get_clients_count_created_between(start_iso, end_iso, conn=self.conn, include_deleted=True)
        self.assertEqual(count, 2) # client2 and client3

    def test_get_clients_count_created_between_no_match(self):
        start_iso = format_datetime_for_db(datetime(2023, 4, 1, 0, 0, 0))
        end_iso = format_datetime_for_db(datetime(2023, 4, 30, 23, 59, 59))
        count = self.clients_crud.get_clients_count_created_between(start_iso, end_iso, conn=self.conn)
        self.assertEqual(count, 0)

    # --- Tests for get_total_clients_count_up_to_date ---
    def test_get_total_clients_count_up_to_date_basic(self):
        date_2023_01_10 = datetime(2023, 1, 10, 10, 0, 0)
        date_2023_02_15 = datetime(2023, 2, 15, 10, 0, 0)
        date_2023_03_20 = datetime(2023, 3, 20, 10, 0, 0) # Target date for count

        self._insert_client("c1", date_2023_01_10) # Included
        self._insert_client("c2", date_2023_02_15) # Included
        self._insert_client("c3", date_2023_02_15, is_deleted=1, deleted_at_dt=datetime(2023, 3, 1, 0, 0, 0)) # Deleted before target date, but deleted_at > target_date_param if param was just date
                                                                                                            # This tests the deleted_at > ? part of the query logic.
                                                                                                            # Query is created_at <= D AND (deleted_at > D OR deleted = 0)
                                                                                                            # So if deleted_at is 2023-03-01 and D is 2023-03-20, it's included.
        self._insert_client("c4", datetime(2023, 3, 21, 0, 0, 0)) # Created after target date

        # Client deleted *on* the target date (edge case for deleted_at > date_iso_end)
        self._insert_client("c5", date_2023_01_10, is_deleted=1, deleted_at_dt=date_2023_03_20) # Deleted on target date, should NOT be counted if query is strictly deleted_at > date_iso_end
                                                                                               # The query `deleted_at > ?` means if deleted_at is the same, it's not counted.

        date_iso_end = format_datetime_for_db(date_2023_03_20)
        count = self.clients_crud.get_total_clients_count_up_to_date(date_iso_end, conn=self.conn)
        # c1, c2, c3 are included. c5 is excluded because deleted_at is not > date_iso_end.
        self.assertEqual(count, 3)

    def test_get_total_clients_count_up_to_date_includes_deleted_after_target(self):
        # Client created before date_iso_end, deleted *after* date_iso_end
        self._insert_client("c1", datetime(2023,1,1,10,0,0), is_deleted=1, deleted_at_dt=datetime(2023,3,1,10,0,0))
        date_iso_end = format_datetime_for_db(datetime(2023,2,1,10,0,0)) # Count up to Feb 1st
        count = self.clients_crud.get_total_clients_count_up_to_date(date_iso_end, conn=self.conn)
        self.assertEqual(count, 1) # c1 should be counted

    def test_get_total_clients_count_up_to_date_excludes_deleted_before_target(self):
        # Client created before date_iso_end, deleted *before* date_iso_end
        self._insert_client("c1", datetime(2023,1,1,10,0,0), is_deleted=1, deleted_at_dt=datetime(2023,1,15,10,0,0))
        date_iso_end = format_datetime_for_db(datetime(2023,2,1,10,0,0)) # Count up to Feb 1st
        count = self.clients_crud.get_total_clients_count_up_to_date(date_iso_end, conn=self.conn)
        self.assertEqual(count, 0) # c1 should NOT be counted

    # --- Tests for get_active_clients_count_up_to_date ---
    def test_get_active_clients_count_up_to_date_basic(self):
        active_status_id = "status_active"
        archival_status_id = "status_archival"
        self._insert_status_setting(active_status_id, "Active", "Client", 0)
        self._insert_status_setting(archival_status_id, "Archived", "Client", 1)

        date_target = datetime(2023, 3, 15, 0, 0, 0)

        # Active client, created before date_target
        self._insert_client("active1", datetime(2023, 1, 1), status_id=active_status_id)
        # Active client, no status, created before date_target
        self._insert_client("active2", datetime(2023, 1, 5))
        # Archived client, created before date_target
        self._insert_client("archived1", datetime(2023, 1, 10), status_id=archival_status_id)
        # Active client, created after date_target
        self._insert_client("active_later", datetime(2023, 4, 1), status_id=active_status_id)
        # Active client, created before date_target, but soft-deleted before date_target
        self._insert_client("active_then_deleted", datetime(2023, 1, 15), status_id=active_status_id, is_deleted=1, deleted_at_dt=datetime(2023, 2, 1))
        # Active client, created before date_target, soft-deleted *after* date_target
        self._insert_client("active_deleted_later", datetime(2023, 1, 20), status_id=active_status_id, is_deleted=1, deleted_at_dt=datetime(2023, 4, 1))


        date_iso_end = format_datetime_for_db(date_target)
        count = self.clients_crud.get_active_clients_count_up_to_date(date_iso_end, conn=self.conn)
        # Expected: active1, active2, active_deleted_later (3 clients)
        self.assertEqual(count, 3)

    # It's hard to test specific SQL error paths without mocks for these integration-style tests.
    # The @_manage_conn decorator handles logging and returning default (0 for counts).
    # We can trust it or add a specific test that forces a connection issue if critical.

if __name__ == '__main__':
    unittest.main()
