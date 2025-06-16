import unittest
import sqlite3
import uuid
from datetime import datetime, date, timedelta
import os
import sys

# Adjust path to import from the app's root directory
# Assuming this test file is in /app/tests/db/ and db_config.py is in /app/
# and cruds are in /app/db/cruds/ and init_schema is in /app/db/
APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(APP_ROOT)

from db.cruds import invoices_crud
from db import init_schema # To initialize the database schema
from db import db_config # To override DATABASE_PATH for tests

# Hold the original DATABASE_PATH
ORIGINAL_DB_PATH = None

def setUpModule():
    """Override DATABASE_PATH for testing and initialize in-memory DB."""
    global ORIGINAL_DB_PATH
    ORIGINAL_DB_PATH = db_config.DATABASE_PATH
    db_config.DATABASE_PATH = ":memory:"
    # print(f"TestInvoicesCrud: Using DB at {db_config.DATABASE_PATH}")
    # No need to connect here, initialize_database will handle it.
    init_schema.initialize_database() # Create schema in the in-memory DB

def tearDownModule():
    """Restore original DATABASE_PATH and clean up."""
    global ORIGINAL_DB_PATH
    if ORIGINAL_DB_PATH:
        db_config.DATABASE_PATH = ORIGINAL_DB_PATH
    # print(f"TestInvoicesCrud: Restored DB path to {db_config.DATABASE_PATH}")
    # In-memory database is automatically discarded. If file DB, os.remove here.


class TestInvoicesCrud(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Set up mock data needed for invoice tests (clients, projects).
        This runs once for the entire test class.
        """
        # initialize_database is now called in setUpModule
        # cls.conn = sqlite3.connect(db_config.DATABASE_PATH) # Use shared connection for setup
        # cls.conn.row_factory = sqlite3.Row
        # init_schema.initialize_database() # Ensures tables are created using the overridden path

        # Add common mock data
        cls.client_id_1 = str(uuid.uuid4())
        cls.client_id_2 = str(uuid.uuid4())
        cls.project_id_1 = str(uuid.uuid4()) # Associated with client_id_1
        cls.project_id_2 = str(uuid.uuid4()) # Associated with client_id_2
        cls.project_id_3 = str(uuid.uuid4()) # Associated with client_id_1, different project

        cls._add_mock_client(cls.client_id_1, "Test Client 1", "TC1")
        cls._add_mock_client(cls.client_id_2, "Test Client 2", "TC2")

        # Projects require status_id, manager_team_member_id (user_id)
        # For simplicity, we'll add a dummy status and user first
        cls.status_id_project = cls._add_mock_status_setting("Planning", "Project")
        cls.user_id_manager = cls._add_mock_user("manager_user")

        cls._add_mock_project(cls.project_id_1, cls.client_id_1, "Test Project 1", cls.status_id_project, cls.user_id_manager)
        cls._add_mock_project(cls.project_id_2, cls.client_id_2, "Test Project 2", cls.status_id_project, cls.user_id_manager)
        cls._add_mock_project(cls.project_id_3, cls.client_id_1, "Test Project 3", cls.status_id_project, cls.user_id_manager)

    @classmethod
    def tearDownClass(cls):
        # cls.conn.close() # Close shared connection
        pass # In-memory DB is auto-cleaned

    @staticmethod
    def _execute_sql(sql, params=()):
        conn = sqlite3.connect(db_config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        last_row_id = cursor.lastrowid
        conn.close()
        return last_row_id

    @classmethod
    def _add_mock_client(cls, client_id, client_name, project_identifier):
        # A simplified version; real one might need more fields from Clients table
        cls._execute_sql(
            "INSERT OR IGNORE INTO Clients (client_id, client_name, project_identifier, default_base_folder_path) VALUES (?, ?, ?, ?)",
            (client_id, client_name, project_identifier, f"/tmp/{project_identifier}")
        )

    @classmethod
    def _add_mock_user(cls, username):
        user_id = str(uuid.uuid4())
        # Simplified user insert
        cls._execute_sql(
            "INSERT OR IGNORE INTO Users (user_id, username, password_hash, email, role) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, "hashed_password", f"{username}@example.com", "member")
        )
        return user_id

    @classmethod
    def _add_mock_status_setting(cls, status_name, status_type):
        # Simplified status insert
        return cls._execute_sql(
            "INSERT OR IGNORE INTO StatusSettings (status_name, status_type) VALUES (?, ?)",
            (status_name, status_type)
        )

    @classmethod
    def _add_mock_project(cls, project_id, client_id, project_name, status_id, manager_id):
        # Simplified project insert
        cls._execute_sql(
            "INSERT OR IGNORE INTO Projects (project_id, client_id, project_name, status_id, manager_team_member_id) VALUES (?, ?, ?, ?, ?)",
            (project_id, client_id, project_name, status_id, manager_id)
        )

    def _create_sample_invoice_data(self, client_id, project_id=None, suffix=""):
        return {
            'client_id': client_id,
            'project_id': project_id,
            'invoice_number': f"INV-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}{suffix}",
            'issue_date': date.today().isoformat(),
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'total_amount': 100.0 + float(suffix) if suffix else 100.0,
            'currency': 'USD',
            'payment_status': 'unpaid',
            'notes': f'Test invoice notes {suffix}'
        }

    def test_add_and_get_invoice(self):
        invoice_data = self._create_sample_invoice_data(self.client_id_1, self.project_id_1, "AG")

        invoice_id = invoices_crud.add_invoice(invoice_data)
        self.assertIsNotNone(invoice_id)

        retrieved_invoice = invoices_crud.get_invoice_by_id(invoice_id)
        self.assertIsNotNone(retrieved_invoice)
        self.assertEqual(retrieved_invoice['invoice_id'], invoice_id)
        self.assertEqual(retrieved_invoice['client_id'], invoice_data['client_id'])
        self.assertEqual(retrieved_invoice['project_id'], invoice_data['project_id'])
        self.assertEqual(retrieved_invoice['invoice_number'], invoice_data['invoice_number'])
        self.assertEqual(retrieved_invoice['issue_date'], invoice_data['issue_date'])
        self.assertEqual(retrieved_invoice['due_date'], invoice_data['due_date'])
        self.assertEqual(retrieved_invoice['total_amount'], invoice_data['total_amount'])
        self.assertEqual(retrieved_invoice['currency'], invoice_data['currency'])
        self.assertEqual(retrieved_invoice['payment_status'], invoice_data['payment_status'])
        self.assertEqual(retrieved_invoice['notes'], invoice_data['notes'])
        self.assertIsNotNone(retrieved_invoice['created_at'])
        self.assertIsNotNone(retrieved_invoice['updated_at'])

    def test_get_invoice_not_found(self):
        non_existent_id = str(uuid.uuid4())
        retrieved_invoice = invoices_crud.get_invoice_by_id(non_existent_id)
        self.assertIsNone(retrieved_invoice)

    def test_update_invoice(self):
        invoice_data_orig = self._create_sample_invoice_data(self.client_id_1, suffix="UP")
        invoice_id = invoices_crud.add_invoice(invoice_data_orig)
        self.assertIsNotNone(invoice_id)

        original_invoice = invoices_crud.get_invoice_by_id(invoice_id)
        original_updated_at = original_invoice['updated_at']

        update_payload = {
            'payment_status': 'paid',
            'payment_date': date.today().isoformat(),
            'notes': 'Updated notes for payment.',
            'total_amount': 150.25
        }

        # Allow a small delay to ensure updated_at changes
        # time.sleep(0.001) # Not strictly necessary with SQLite's CURRENT_TIMESTAMP precision if changes are quick

        success = invoices_crud.update_invoice(invoice_id, update_payload)
        self.assertTrue(success)

        updated_invoice = invoices_crud.get_invoice_by_id(invoice_id)
        self.assertIsNotNone(updated_invoice)
        self.assertEqual(updated_invoice['payment_status'], update_payload['payment_status'])
        self.assertEqual(updated_invoice['payment_date'], update_payload['payment_date'])
        self.assertEqual(updated_invoice['notes'], update_payload['notes'])
        self.assertEqual(updated_invoice['total_amount'], update_payload['total_amount'])
        self.assertNotEqual(updated_invoice['updated_at'], original_updated_at)
        # Check other fields remain unchanged
        self.assertEqual(updated_invoice['invoice_number'], invoice_data_orig['invoice_number'])

    def test_update_invoice_not_found(self):
        non_existent_id = str(uuid.uuid4())
        update_payload = {'payment_status': 'paid'}
        success = invoices_crud.update_invoice(non_existent_id, update_payload)
        self.assertFalse(success)

    def test_delete_invoice(self):
        invoice_data = self._create_sample_invoice_data(self.client_id_1, suffix="DEL")
        invoice_id = invoices_crud.add_invoice(invoice_data)
        self.assertIsNotNone(invoice_id)

        success = invoices_crud.delete_invoice(invoice_id)
        self.assertTrue(success)

        deleted_invoice = invoices_crud.get_invoice_by_id(invoice_id)
        self.assertIsNone(deleted_invoice)

    def test_delete_invoice_not_found(self):
        non_existent_id = str(uuid.uuid4())
        success = invoices_crud.delete_invoice(non_existent_id)
        self.assertFalse(success)

    def test_get_invoices_by_client_id(self):
        # Clear previous test data or use unique client
        client_specific_id = str(uuid.uuid4())
        self._add_mock_client(client_specific_id, "Client For List Test", "CFLT")

        inv1_data = self._create_sample_invoice_data(client_specific_id, suffix="C1")
        inv2_data = self._create_sample_invoice_data(client_specific_id, suffix="C2")
        # Invoice for another client
        other_client_inv_data = self._create_sample_invoice_data(self.client_id_2, suffix="C3")

        invoices_crud.add_invoice(inv1_data)
        invoices_crud.add_invoice(inv2_data)
        invoices_crud.add_invoice(other_client_inv_data)

        client_invoices = invoices_crud.get_invoices_by_client_id(client_specific_id)
        self.assertEqual(len(client_invoices), 2)
        for inv in client_invoices:
            self.assertEqual(inv['client_id'], client_specific_id)

        # Check invoice numbers to be sure
        retrieved_inv_numbers = sorted([inv['invoice_number'] for inv in client_invoices])
        expected_inv_numbers = sorted([inv1_data['invoice_number'], inv2_data['invoice_number']])
        self.assertListEqual(retrieved_inv_numbers, expected_inv_numbers)

    def test_get_invoices_by_project_id(self):
        project_specific_id = str(uuid.uuid4())
        client_for_project_test = str(uuid.uuid4())
        self._add_mock_client(client_for_project_test, "Client Project Test", "CPT")
        self._add_mock_project(project_specific_id, client_for_project_test, "Project For List Test", self.status_id_project, self.user_id_manager)

        inv1_data = self._create_sample_invoice_data(client_for_project_test, project_specific_id, suffix="P1")
        inv2_data = self._create_sample_invoice_data(client_for_project_test, project_specific_id, suffix="P2")
        # Invoice for another project (or no project)
        other_project_inv_data = self._create_sample_invoice_data(client_for_project_test, self.project_id_1, suffix="P3")


        invoices_crud.add_invoice(inv1_data)
        invoices_crud.add_invoice(inv2_data)
        invoices_crud.add_invoice(other_project_inv_data)

        project_invoices = invoices_crud.get_invoices_by_project_id(project_specific_id)
        self.assertEqual(len(project_invoices), 2)
        for inv in project_invoices:
            self.assertEqual(inv['project_id'], project_specific_id)

        retrieved_inv_numbers = sorted([inv['invoice_number'] for inv in project_invoices])
        expected_inv_numbers = sorted([inv1_data['invoice_number'], inv2_data['invoice_number']])
        self.assertListEqual(retrieved_inv_numbers, expected_inv_numbers)

    def test_list_all_invoices_no_filters(self):
        # Consider cleaning up invoices table or ensure unique data for this test
        # For simplicity, assume previous tests don't interfere significantly or we add enough new ones
        inv1 = invoices_crud.add_invoice(self._create_sample_invoice_data(self.client_id_1, suffix="LNF1"))
        inv2 = invoices_crud.add_invoice(self._create_sample_invoice_data(self.client_id_2, suffix="LNF2"))

        all_invoices = invoices_crud.list_all_invoices()
        self.assertTrue(len(all_invoices) >= 2) # Check if at least the two added are present

        # Check if our specific invoices are in the list
        found_inv1 = any(inv['invoice_id'] == inv1 for inv in all_invoices)
        found_inv2 = any(inv['invoice_id'] == inv2 for inv in all_invoices)
        self.assertTrue(found_inv1)
        self.assertTrue(found_inv2)

    def test_list_all_invoices_with_filters(self):
        client_filter_id = str(uuid.uuid4())
        self._add_mock_client(client_filter_id, "Client List Filter Test", "CLFT")

        inv_paid_data = self._create_sample_invoice_data(client_filter_id, suffix="LFPa")
        inv_paid_data['payment_status'] = 'paid'
        inv_paid_data['issue_date'] = '2023-01-15'
        inv_paid = invoices_crud.add_invoice(inv_paid_data)

        inv_unpaid_data = self._create_sample_invoice_data(client_filter_id, suffix="LFUPa")
        inv_unpaid_data['payment_status'] = 'unpaid'
        inv_unpaid_data['issue_date'] = '2023-02-10'
        inv_unpaid = invoices_crud.add_invoice(inv_unpaid_data)

        inv_other_client_data = self._create_sample_invoice_data(self.client_id_1, suffix="LFOther")
        inv_other_client_data['payment_status'] = 'paid'
        inv_other_client_data['issue_date'] = '2023-01-20'
        invoices_crud.add_invoice(inv_other_client_data)

        # Test filter by payment_status
        paid_invoices = invoices_crud.list_all_invoices(filters={'payment_status': 'paid'})
        self.assertTrue(len(paid_invoices) >= 1)
        self.assertTrue(any(i['invoice_id'] == inv_paid for i in paid_invoices))
        self.assertFalse(any(i['invoice_id'] == inv_unpaid for i in paid_invoices))

        # Test filter by client_id
        client_filtered_invoices = invoices_crud.list_all_invoices(filters={'client_id': client_filter_id})
        self.assertEqual(len(client_filtered_invoices), 2)
        self.assertTrue(any(i['invoice_id'] == inv_paid for i in client_filtered_invoices))
        self.assertTrue(any(i['invoice_id'] == inv_unpaid for i in client_filtered_invoices))

        # Test filter by issue_date_start and issue_date_end
        date_filtered_invoices = invoices_crud.list_all_invoices(filters={'issue_date_start': '2023-01-01', 'issue_date_end': '2023-01-31'})
        self.assertTrue(len(date_filtered_invoices) >= 1) # At least inv_paid and inv_other_client
        self.assertTrue(any(i['invoice_id'] == inv_paid for i in date_filtered_invoices))
        self.assertFalse(any(i['invoice_id'] == inv_unpaid for i in date_filtered_invoices)) # inv_unpaid is in Feb

    def test_list_all_invoices_sorting(self):
        # Add invoices with varying issue_date and total_amount
        # Ensure unique invoice numbers by using suffix
        inv_s1_data = self._create_sample_invoice_data(self.client_id_1, suffix="LS1")
        inv_s1_data['issue_date'] = '2023-03-10'
        inv_s1_data['total_amount'] = 200.0
        inv_s1 = invoices_crud.add_invoice(inv_s1_data)

        inv_s2_data = self._create_sample_invoice_data(self.client_id_1, suffix="LS2")
        inv_s2_data['issue_date'] = '2023-01-15' # Earlier
        inv_s2_data['total_amount'] = 50.0    # Smaller
        inv_s2 = invoices_crud.add_invoice(inv_s2_data)

        inv_s3_data = self._create_sample_invoice_data(self.client_id_1, suffix="LS3")
        inv_s3_data['issue_date'] = '2023-02-20' # Middle
        inv_s3_data['total_amount'] = 300.0   # Larger
        inv_s3 = invoices_crud.add_invoice(inv_s3_data)

        # Test sorting by issue_date_asc
        sorted_invoices_date_asc = invoices_crud.list_all_invoices(sort_by="issue_date_asc", filters={'client_id': self.client_id_1})
        # Filter to only our test items for assertion, if DB is shared.
        test_inv_ids = {inv_s1, inv_s2, inv_s3}
        relevant_invoices = [inv for inv in sorted_invoices_date_asc if inv['invoice_id'] in test_inv_ids]
        if len(relevant_invoices) >=3: # Only assert if we found our items
            self.assertEqual(relevant_invoices[0]['invoice_id'], inv_s2) # 2023-01-15
            self.assertEqual(relevant_invoices[1]['invoice_id'], inv_s3) # 2023-02-20
            self.assertEqual(relevant_invoices[2]['invoice_id'], inv_s1) # 2023-03-10

        # Test sorting by total_amount_desc
        sorted_invoices_amount_desc = invoices_crud.list_all_invoices(sort_by="total_amount_desc", filters={'client_id': self.client_id_1})
        relevant_invoices_amount = [inv for inv in sorted_invoices_amount_desc if inv['invoice_id'] in test_inv_ids]
        if len(relevant_invoices_amount) >= 3:
            self.assertEqual(relevant_invoices_amount[0]['invoice_id'], inv_s3) # 300.0
            self.assertEqual(relevant_invoices_amount[1]['invoice_id'], inv_s1) # 200.0
            self.assertEqual(relevant_invoices_amount[2]['invoice_id'], inv_s2) # 50.0

    def test_list_all_invoices_pagination(self):
        client_page_id = str(uuid.uuid4())
        self._add_mock_client(client_page_id, "Client Pagination Test", "CPGT")

        # Add 5 invoices for this client
        invoice_ids = []
        for i in range(5):
            data = self._create_sample_invoice_data(client_page_id, suffix=f"LP{i}")
            data['issue_date'] = (date(2023, 1, 1) + timedelta(days=i)).isoformat() # Ensure order
            invoice_ids.append(invoices_crud.add_invoice(data))

        # Get all for this client sorted by issue_date_asc to have a predictable order
        all_client_invoices = invoices_crud.list_all_invoices(filters={'client_id': client_page_id}, sort_by="issue_date_asc")
        self.assertEqual(len(all_client_invoices), 5)

        # limit=2, offset=0
        page1 = invoices_crud.list_all_invoices(filters={'client_id': client_page_id}, sort_by="issue_date_asc", limit=2, offset=0)
        self.assertEqual(len(page1), 2)
        self.assertEqual(page1[0]['invoice_id'], all_client_invoices[0]['invoice_id'])
        self.assertEqual(page1[1]['invoice_id'], all_client_invoices[1]['invoice_id'])

        # limit=2, offset=2
        page2 = invoices_crud.list_all_invoices(filters={'client_id': client_page_id}, sort_by="issue_date_asc", limit=2, offset=2)
        self.assertEqual(len(page2), 2)
        self.assertEqual(page2[0]['invoice_id'], all_client_invoices[2]['invoice_id'])
        self.assertEqual(page2[1]['invoice_id'], all_client_invoices[3]['invoice_id'])

        # limit=2, offset=4
        page3 = invoices_crud.list_all_invoices(filters={'client_id': client_page_id}, sort_by="issue_date_asc", limit=2, offset=4)
        self.assertEqual(len(page3), 1)
        self.assertEqual(page3[0]['invoice_id'], all_client_invoices[4]['invoice_id'])

        # limit=5, offset=0 (get all)
        page_all = invoices_crud.list_all_invoices(filters={'client_id': client_page_id}, sort_by="issue_date_asc", limit=5, offset=0)
        self.assertEqual(len(page_all), 5)

        # Offset beyond items
        page_none = invoices_crud.list_all_invoices(filters={'client_id': client_page_id}, sort_by="issue_date_asc", limit=2, offset=10)
        self.assertEqual(len(page_none), 0)


if __name__ == '__main__':
    unittest.main()

```
