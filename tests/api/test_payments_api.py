import unittest
import os
import sys
import uuid
from datetime import datetime, date, timedelta
import json # For loading response data

from fastapi.testclient import TestClient

# Adjust path to import from the app's root directory
APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(APP_ROOT)

from api.main import app # The FastAPI application
from db import init_schema
from db import db_config
from api import models # For Pydantic models if needed for request construction hints

# Hold the original DATABASE_PATH
ORIGINAL_DB_PATH_API_TEST = None # Use a unique name to avoid clashes if run in same session as other tests

def setUpModule():
    """Override DATABASE_PATH for testing and initialize in-memory DB for API tests."""
    global ORIGINAL_DB_PATH_API_TEST
    ORIGINAL_DB_PATH_API_TEST = db_config.DATABASE_PATH
    db_config.DATABASE_PATH = ":memory:"
    # print(f"TestPaymentsAPI: Using DB at {db_config.DATABASE_PATH}")
    init_schema.initialize_database()

def tearDownModule():
    """Restore original DATABASE_PATH for API tests."""
    global ORIGINAL_DB_PATH_API_TEST
    if ORIGINAL_DB_PATH_API_TEST:
        db_config.DATABASE_PATH = ORIGINAL_DB_PATH_API_TEST
    # print(f"TestPaymentsAPI: Restored DB path to {db_config.DATABASE_PATH}")

class TestPaymentsAPI(unittest.TestCase):

    client = None # TestClient instance

    @classmethod
    def setUpClass(cls):
        # initialize_database called in setUpModule
        cls.client = TestClient(app)

        # Mock data setup - direct SQL for simplicity and control in test setup
        # These should match dependencies for creating invoices
        cls.client_id_1 = str(uuid.uuid4())
        cls.client_id_2 = str(uuid.uuid4())
        cls.project_id_1 = str(uuid.uuid4()) # For client_id_1
        cls.project_id_2 = str(uuid.uuid4()) # For client_id_2
        cls.user_id_manager = cls._add_mock_user("api_manager_user")
        cls.status_id_project = cls._add_mock_status_setting("API Project Planning", "Project")

        cls._add_mock_client_db(cls.client_id_1, "API Test Client 1", "APITC1")
        cls._add_mock_client_db(cls.client_id_2, "API Test Client 2", "APITC2")
        cls._add_mock_project_db(cls.project_id_1, cls.client_id_1, "API Test Project 1", cls.status_id_project, cls.user_id_manager)
        cls._add_mock_project_db(cls.project_id_2, cls.client_id_2, "API Test Project 2", cls.status_id_project, cls.user_id_manager)

    @staticmethod
    def _execute_sql_for_setup(sql, params=()):
        # Helper for setting up data directly in DB, bypassing CRUDs for test setup speed/isolation
        # Note: This means tests rely on schema structure; if schema changes, these might too.
        # invoices_crud uses its own connection management, so this is fine for setup.
        conn = sqlite3.connect(db_config.DATABASE_PATH) # Connects to the :memory: db
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        last_row_id = cursor.lastrowid
        conn.close()
        return last_row_id

    @classmethod
    def _add_mock_client_db(cls, client_id, client_name, project_identifier):
        cls._execute_sql_for_setup(
            "INSERT OR IGNORE INTO Clients (client_id, client_name, project_identifier, default_base_folder_path) VALUES (?, ?, ?, ?)",
            (client_id, client_name, project_identifier, f"/tmp/api_{project_identifier}")
        )

    @classmethod
    def _add_mock_user(cls, username):
        user_id = str(uuid.uuid4())
        cls._execute_sql_for_setup(
            "INSERT OR IGNORE INTO Users (user_id, username, password_hash, email, role) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, "api_hashed_password", f"{username}_api@example.com", "member")
        )
        return user_id

    @classmethod
    def _add_mock_status_setting(cls, status_name, status_type):
        return cls._execute_sql_for_setup(
            "INSERT OR IGNORE INTO StatusSettings (status_name, status_type) VALUES (?, ?)",
            (status_name, status_type)
        )

    @classmethod
    def _add_mock_project_db(cls, project_id, client_id, project_name, status_id, manager_id):
        cls._execute_sql_for_setup(
            "INSERT OR IGNORE INTO Projects (project_id, client_id, project_name, status_id, manager_team_member_id) VALUES (?, ?, ?, ?, ?)",
            (project_id, client_id, project_name, status_id, manager_id)
        )

    def _create_sample_invoice_payload(self, client_id, project_id=None, suffix=""):
        return {
            "client_id": client_id,
            "project_id": project_id,
            "invoice_number": f"API-INV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}{suffix}",
            "issue_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
            "total_amount": 150.75 + (float(len(suffix)) if suffix else 0.0), # Ensure some variation
            "currency": "EUR",
            "payment_status": "unpaid",
            "notes": f"API test invoice notes {suffix}"
        }

    def test_create_and_get_invoice(self):
        invoice_payload = self._create_sample_invoice_payload(self.client_id_1, self.project_id_1, "CG")

        # Create
        response = self.client.post("/api/v1/payments/invoices/", json=invoice_payload)
        self.assertEqual(response.status_code, 201, response.text) # Changed to 201 as per API design
        created_invoice_data = response.json()

        self.assertIn("invoice_id", created_invoice_data)
        self.assertEqual(created_invoice_data["client_id"], invoice_payload["client_id"])
        self.assertEqual(created_invoice_data["invoice_number"], invoice_payload["invoice_number"])
        self.assertEqual(created_invoice_data["total_amount"], invoice_payload["total_amount"])
        # Dates are returned as strings by API, match with payload strings
        self.assertEqual(created_invoice_data["issue_date"], invoice_payload["issue_date"])

        invoice_id = created_invoice_data["invoice_id"]

        # Get
        response_get = self.client.get(f"/api/v1/payments/invoices/{invoice_id}")
        self.assertEqual(response_get.status_code, 200, response_get.text)
        retrieved_invoice_data = response_get.json()
        self.assertEqual(retrieved_invoice_data["invoice_id"], invoice_id)
        self.assertEqual(retrieved_invoice_data["invoice_number"], invoice_payload["invoice_number"])

    def test_create_invoice_invalid_data(self):
        invalid_payload = {"total_amount": 100.0} # Missing client_id, invoice_number, etc.
        response = self.client.post("/api/v1/payments/invoices/", json=invalid_payload)
        self.assertEqual(response.status_code, 422, response.text) # Unprocessable Entity

    def test_get_invoice_not_found(self):
        non_existent_id = str(uuid.uuid4())
        response = self.client.get(f"/api/v1/payments/invoices/{non_existent_id}")
        self.assertEqual(response.status_code, 404, response.text)

    def test_update_invoice(self):
        # First, create an invoice
        original_payload = self._create_sample_invoice_payload(self.client_id_1, self.project_id_1, "UP")
        response_create = self.client.post("/api/v1/payments/invoices/", json=original_payload)
        self.assertEqual(response_create.status_code, 201)
        invoice_id = response_create.json()["invoice_id"]

        update_data = {
            "payment_status": "paid",
            "payment_date": date.today().isoformat(),
            "notes": "Updated via API test"
        }
        response_update = self.client.put(f"/api/v1/payments/invoices/{invoice_id}", json=update_data)
        self.assertEqual(response_update.status_code, 200, response_update.text)
        updated_invoice_data = response_update.json()

        self.assertEqual(updated_invoice_data["payment_status"], update_data["payment_status"])
        self.assertEqual(updated_invoice_data["payment_date"], update_data["payment_date"])
        self.assertEqual(updated_invoice_data["notes"], update_data["notes"])
        # Check original fields that shouldn't change
        self.assertEqual(updated_invoice_data["invoice_number"], original_payload["invoice_number"])

        # Fetch again to confirm persistence
        response_get = self.client.get(f"/api/v1/payments/invoices/{invoice_id}")
        self.assertEqual(response_get.status_code, 200)
        fetched_data = response_get.json()
        self.assertEqual(fetched_data["payment_status"], update_data["payment_status"])

    def test_update_invoice_not_found(self):
        non_existent_id = str(uuid.uuid4())
        update_data = {"payment_status": "paid"}
        response = self.client.put(f"/api/v1/payments/invoices/{non_existent_id}", json=update_data)
        self.assertEqual(response.status_code, 404, response.text) # API should return 404 if trying to update non-existent

    def test_delete_invoice(self):
        # Create an invoice to delete
        payload = self._create_sample_invoice_payload(self.client_id_1, suffix="DEL")
        response_create = self.client.post("/api/v1/payments/invoices/", json=payload)
        self.assertEqual(response_create.status_code, 201)
        invoice_id = response_create.json()["invoice_id"]

        # Delete
        response_delete = self.client.delete(f"/api/v1/payments/invoices/{invoice_id}")
        self.assertEqual(response_delete.status_code, 204, response_delete.text)

        # Try to get it again
        response_get = self.client.get(f"/api/v1/payments/invoices/{invoice_id}")
        self.assertEqual(response_get.status_code, 404, response_get.text)

    def test_delete_invoice_not_found(self):
        non_existent_id = str(uuid.uuid4())
        response = self.client.delete(f"/api/v1/payments/invoices/{non_existent_id}")
        self.assertEqual(response.status_code, 404, response.text) # API should return 404

    def test_list_invoices(self):
        # Create a few invoices
        self.client.post("/api/v1/payments/invoices/", json=self._create_sample_invoice_payload(self.client_id_1, self.project_id_1, "L1"))
        self.client.post("/api/v1/payments/invoices/", json=self._create_sample_invoice_payload(self.client_id_2, self.project_id_2, "L2"))
        payload_l3 = self._create_sample_invoice_payload(self.client_id_1, self.project_id_1, "L3")
        payload_l3["payment_status"] = "paid"
        payload_l3["issue_date"] = "2023-01-01"
        self.client.post("/api/v1/payments/invoices/", json=payload_l3)


        # Basic list
        response = self.client.get("/api/v1/payments/invoices/")
        self.assertEqual(response.status_code, 200)
        invoices = response.json()
        self.assertTrue(len(invoices) >= 3)

        # Filter by payment_status
        response_paid = self.client.get("/api/v1/payments/invoices/?payment_status=paid")
        self.assertEqual(response_paid.status_code, 200)
        paid_invoices = response_paid.json()
        self.assertTrue(len(paid_invoices) >= 1)
        for inv in paid_invoices:
            self.assertEqual(inv["payment_status"], "paid")

        # Filter by client_id
        response_client = self.client.get(f"/api/v1/payments/invoices/?client_id={self.client_id_1}")
        self.assertEqual(response_client.status_code, 200)
        client_invoices = response_client.json()
        self.assertTrue(len(client_invoices) >= 2) # L1 and L3
        for inv in client_invoices:
            self.assertEqual(inv["client_id"], self.client_id_1)

        # Pagination (limit=1, offset=1)
        response_page = self.client.get("/api/v1/payments/invoices/?limit=1&offset=1&sort_by=issue_date_asc") # Ensure consistent order
        self.assertEqual(response_page.status_code, 200)
        paginated_invoices = response_page.json()
        self.assertEqual(len(paginated_invoices), 1)

        # Sorting (example: issue_date_desc)
        response_sort = self.client.get("/api/v1/payments/invoices/?sort_by=issue_date_desc")
        self.assertEqual(response_sort.status_code, 200)
        sorted_invoices = response_sort.json()
        # Check if dates are in descending order (if more than 1)
        if len(sorted_invoices) > 1:
            self.assertTrue(sorted_invoices[0]["issue_date"] >= sorted_invoices[1]["issue_date"])

    def test_list_invoices_by_client_id_endpoint(self):
        # Create specific invoices for this test
        test_client_id = str(uuid.uuid4())
        self._add_mock_client_db(test_client_id, "Client Endpoint Test", "CET")

        self.client.post("/api/v1/payments/invoices/", json=self._create_sample_invoice_payload(test_client_id, suffix="CE1"))
        self.client.post("/api/v1/payments/invoices/", json=self._create_sample_invoice_payload(test_client_id, suffix="CE2"))
        # Invoice for another client
        self.client.post("/api/v1/payments/invoices/", json=self._create_sample_invoice_payload(self.client_id_1, suffix="CEOther"))

        response = self.client.get(f"/api/v1/payments/invoices/client/{test_client_id}")
        self.assertEqual(response.status_code, 200, response.text)
        client_invoices = response.json()
        self.assertEqual(len(client_invoices), 2)
        for inv in client_invoices:
            self.assertEqual(inv["client_id"], test_client_id)

    def test_list_invoices_by_project_id_endpoint(self):
        test_project_id = str(uuid.uuid4())
        # Need a client for this project
        client_for_project_test = str(uuid.uuid4())
        self._add_mock_client_db(client_for_project_test, "Client For Project Endpoint Test", "CFPET")
        self._add_mock_project_db(test_project_id, client_for_project_test, "Project Endpoint Test", self.status_id_project, self.user_id_manager)

        self.client.post("/api/v1/payments/invoices/", json=self._create_sample_invoice_payload(client_for_project_test, test_project_id, suffix="PE1"))
        self.client.post("/api/v1/payments/invoices/", json=self._create_sample_invoice_payload(client_for_project_test, test_project_id, suffix="PE2"))
        # Invoice for another project
        self.client.post("/api/v1/payments/invoices/", json=self._create_sample_invoice_payload(self.client_id_1, self.project_id_1, suffix="PEOther"))

        response = self.client.get(f"/api/v1/payments/invoices/project/{test_project_id}")
        self.assertEqual(response.status_code, 200, response.text)
        project_invoices = response.json()
        self.assertEqual(len(project_invoices), 2)
        for inv in project_invoices:
            self.assertEqual(inv["project_id"], test_project_id)

if __name__ == '__main__':
    # Need to import sqlite3 for _execute_sql_for_setup
    import sqlite3
    unittest.main()
```
