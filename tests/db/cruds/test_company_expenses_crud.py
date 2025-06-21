import unittest
import sqlite3
import os
import sys
from datetime import datetime, date

# Add project root to sys.path to allow imports from db, utils etc.
# This is often handled by test runners or conftest.py, but added here for explicitness
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now import after path adjustment
from db.cruds.company_expenses_crud import (
    add_company_facture, get_company_facture_by_id, update_company_facture, soft_delete_company_facture, get_all_company_factures,
    add_company_expense, get_company_expense_by_id, update_company_expense, soft_delete_company_expense, get_all_company_expenses,
    link_facture_to_expense, unlink_facture_from_expense
)
import db.init_schema  # To initialize schema in memory
from db.connection import get_db_connection # To override for in-memory testing

# Store the original get_db_connection function
original_get_db_connection = db.connection.get_db_connection
original_db_path = None
if hasattr(db.init_schema, 'config') and hasattr(db.init_schema.config, 'DATABASE_PATH'):
    original_db_path = db.init_schema.config.DATABASE_PATH


def get_in_memory_db_connection():
    """Returns an in-memory SQLite connection."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row # Important for accessing columns by name
    return conn

class TestCompanyExpensesCRUD(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Override the database path and connection function for testing
        if original_db_path: # Ensure config was loaded
            db.init_schema.config.DATABASE_PATH = ":memory:"
        db.connection.get_db_connection = get_in_memory_db_connection

        # Initialize the schema in the in-memory database
        # We need a connection to pass to initialize_database if it expects one,
        # or it should use the overridden get_db_connection internally.
        # The current init_schema.initialize_database creates its own connection using config.DATABASE_PATH
        db.init_schema.initialize_database()


    @classmethod
    def tearDownClass(cls):
        # Restore original settings
        if original_db_path:
             db.init_schema.config.DATABASE_PATH = original_db_path
        db.connection.get_db_connection = original_get_db_connection

    def setUp(self):
        # Each test method will get a fresh connection and cursor if needed,
        # but the database is shared and persists within the class due to setUpClass.
        # For true test isolation, re-initialize DB per test or clean tables.
        # For simplicity here, we'll clean up relevant tables.
        conn = get_in_memory_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM company_expenses")
        cursor.execute("DELETE FROM company_factures")
        # If Users table is used for created_by_user_id, ensure a test user exists or handle FKs.
        # For now, assuming created_by_user_id can be NULL or a test string.
        # Example test user (if Users table is part of in-memory schema):
        try:
            cursor.execute("INSERT OR IGNORE INTO Users (user_id, username, password_hash, salt, email, role) VALUES (?, ?, ?, ?, ?, ?)",
                           ('testuser123', 'testuser', 'hash', 'salt', 'test@example.com', 'user'))
        except sqlite3.Error as e:
            # Users table might not exist if init_schema was partial or failed.
            # This is fine if created_by_user_id is not strictly enforced in tests for now.
            print(f"Note: Could not insert test user, possibly Users table not fully initialized: {e}")

        conn.commit()
        conn.close()

    def test_add_and_get_company_facture(self):
        facture_id = add_company_facture(
            original_file_name="test_invoice.pdf",
            stored_file_path="/path/to/test_invoice.pdf",
            file_mime_type="application/pdf",
            extraction_status="pending_extraction"
        )
        self.assertIsNotNone(facture_id)

        retrieved_facture = get_company_facture_by_id(facture_id)
        self.assertIsNotNone(retrieved_facture)
        self.assertEqual(retrieved_facture["original_file_name"], "test_invoice.pdf")
        self.assertEqual(retrieved_facture["extraction_status"], "pending_extraction")

    def test_update_company_facture(self):
        facture_id = add_company_facture("update_me.pdf", "/path/updatable.pdf")
        self.assertIsNotNone(facture_id)

        updated = update_company_facture(
            facture_id=facture_id,
            original_file_name="updated_name.pdf",
            extraction_status="data_extracted"
        )
        self.assertTrue(updated)

        retrieved = get_company_facture_by_id(facture_id)
        self.assertEqual(retrieved["original_file_name"], "updated_name.pdf")
        self.assertEqual(retrieved["extraction_status"], "data_extracted")

    def test_soft_delete_company_facture(self):
        facture_id = add_company_facture("to_delete.pdf", "/path/to_delete.pdf")
        self.assertIsNotNone(facture_id)

        deleted = soft_delete_company_facture(facture_id)
        self.assertTrue(deleted)

        retrieved = get_company_facture_by_id(facture_id)
        self.assertIsNone(retrieved) # Should not be found by default getter

        # Verify is_deleted flag if we had a getter for deleted items
        # For now, this check is implicit.

    def test_get_all_company_factures(self):
        add_company_facture("facture1.pdf", "/path/f1.pdf", extraction_status="pending")
        add_company_facture("facture2.pdf", "/path/f2.pdf", extraction_status="done")

        all_factures = get_all_company_factures()
        self.assertEqual(len(all_factures), 2)

        pending_factures = get_all_company_factures(extraction_status="pending")
        self.assertEqual(len(pending_factures), 1)
        self.assertEqual(pending_factures[0]["original_file_name"], "facture1.pdf")

    def test_add_and_get_company_expense(self):
        expense_id = add_company_expense(
            expense_date="2023-11-01",
            amount=100.50,
            currency="USD",
            recipient_name="Test Vendor",
            description="Office supplies",
            created_by_user_id="testuser123"
        )
        self.assertIsNotNone(expense_id)

        retrieved = get_company_expense_by_id(expense_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["recipient_name"], "Test Vendor")
        self.assertEqual(retrieved["amount"], 100.50)

    def test_update_company_expense(self):
        expense_id = add_company_expense("2023-11-01", 50.0, "EUR", "Old Supplier")
        self.assertIsNotNone(expense_id)

        updated = update_company_expense(
            expense_id=expense_id,
            recipient_name="New Supplier",
            amount=75.25
        )
        self.assertTrue(updated)
        retrieved = get_company_expense_by_id(expense_id)
        self.assertEqual(retrieved["recipient_name"], "New Supplier")
        self.assertEqual(retrieved["amount"], 75.25)

    def test_soft_delete_company_expense(self):
        expense_id = add_company_expense("2023-11-01", 20.0, "CAD", "Temp Service")
        self.assertIsNotNone(expense_id)

        deleted = soft_delete_company_expense(expense_id)
        self.assertTrue(deleted)
        retrieved = get_company_expense_by_id(expense_id)
        self.assertIsNone(retrieved)

    def test_get_all_company_expenses_with_filters(self):
        add_company_expense("2023-10-15", 100.0, "USD", "Vendor A", "Office Food")
        add_company_expense("2023-10-20", 200.0, "USD", "Vendor B", "Software License")
        add_company_expense("2023-11-05", 150.0, "EUR", "Vendor A", "Travel Costs")

        all_exp = get_all_company_expenses()
        self.assertEqual(len(all_exp), 3)

        usd_expenses = get_all_company_expenses(currency="USD")
        self.assertEqual(len(usd_expenses), 2)

        vendor_a_expenses = get_all_company_expenses(recipient_name="Vendor A")
        self.assertEqual(len(vendor_a_expenses), 2)

        oct_expenses = get_all_company_expenses(date_from="2023-10-01", date_to="2023-10-31")
        self.assertEqual(len(oct_expenses), 2)

        food_expenses = get_all_company_expenses(description_keywords="Food")
        self.assertEqual(len(food_expenses), 1)
        self.assertEqual(food_expenses[0]["recipient_name"], "Vendor A")

    def test_link_and_unlink_facture_to_expense(self):
        facture_id = add_company_facture("linkable.pdf", "/path/linkable.pdf")
        self.assertIsNotNone(facture_id)
        expense_id = add_company_expense("2023-11-01", 300.0, "USD", "Service Co")
        self.assertIsNotNone(expense_id)

        # Link
        linked = link_facture_to_expense(expense_id, facture_id)
        self.assertTrue(linked)
        retrieved_exp = get_company_expense_by_id(expense_id)
        self.assertEqual(retrieved_exp["facture_id"], facture_id)

        # Unlink
        unlinked = unlink_facture_from_expense(expense_id)
        self.assertTrue(unlinked)
        retrieved_exp_unlinked = get_company_expense_by_id(expense_id)
        self.assertIsNone(retrieved_exp_unlinked["facture_id"])

    def test_update_expense_clear_facture_id(self):
        facture_id = add_company_facture("clearable_link.pdf", "/path/clearable.pdf")
        self.assertIsNotNone(facture_id)
        expense_id = add_company_expense("2023-11-02", 400.0, "GBP", "Consultant", facture_id=facture_id)
        self.assertIsNotNone(expense_id)

        retrieved_exp = get_company_expense_by_id(expense_id)
        self.assertEqual(retrieved_exp["facture_id"], facture_id)

        # Update expense, explicitly setting facture_id to None (or 0 which crud handles as None)
        updated = update_company_expense(expense_id=expense_id, facture_id=None) # Test with None
        self.assertTrue(updated)
        retrieved_exp_updated = get_company_expense_by_id(expense_id)
        self.assertIsNone(retrieved_exp_updated["facture_id"], "Facture ID should be None after update")

        # Re-link and then update with 0
        link_facture_to_expense(expense_id, facture_id)
        updated_with_zero = update_company_expense(expense_id=expense_id, facture_id=0)
        self.assertTrue(updated_with_zero)
        retrieved_exp_updated_zero = get_company_expense_by_id(expense_id)
        self.assertIsNone(retrieved_exp_updated_zero["facture_id"], "Facture ID should be None after update with 0")


if __name__ == '__main__':
    unittest.main()
