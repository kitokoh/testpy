import unittest
import sqlite3
import os
import uuid
from datetime import datetime

# Temporarily adjust sys.path to import from the app's root for db.crud and db.schema
import sys
# Assuming this test file is in tests/db/test_partner_crud.py
# Adjust path to reach the application root (e.g., two levels up)
APP_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_ROOT_DIR not in sys.path:
    sys.path.insert(0, APP_ROOT_DIR)

# Now import application modules
try:
    from db import crud as db_manager, schema as db_schema, db_config
except ImportError as e:
    print(f"Failed to import db modules: {e}")
    print(f"Current sys.path: {sys.path}")
    # Fallback for cases where path adjustment might not be perfect in all execution contexts
    # This is a simplified attempt, real projects might need more robust test setup for imports
    if os.path.basename(APP_ROOT_DIR) == 'src' or os.path.basename(APP_ROOT_DIR) == 'app': # common project structures
         PARENT_OF_APP_ROOT = os.path.dirname(APP_ROOT_DIR)
         if PARENT_OF_APP_ROOT not in sys.path:
            sys.path.insert(0, PARENT_OF_APP_ROOT)
         from db import crud as db_manager, schema as db_schema, db_config


class TestPartnerCRUD(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Use a consistent in-memory database for all tests in this class
        # This speeds things up but requires careful test isolation if tests modify data
        # Alternatively, create a new in-memory DB for each test in setUp
        cls.db_path = ":memory:"
        cls.original_db_path = db_config.DATABASE_PATH
        db_config.DATABASE_PATH = cls.db_path

        # Initialize schema on this in-memory database
        # db_schema.initialize_database() # This creates its own connection
        # Instead, we need to get a connection and pass it, or ensure initialize_database uses the patched path
        conn = sqlite3.connect(cls.db_path)
        conn.row_factory = sqlite3.Row # Important for dict access
        # We need to manually execute schema creation using this connection
        # This is a simplified way; ideally, initialize_database would accept a conn or use the patched path
        # For now, let's assume initialize_database will pick up the patched db_config.DATABASE_PATH
        db_schema.initialize_database() # Call it once for the class
        conn.close()


    @classmethod
    def tearDownClass(cls):
        db_config.DATABASE_PATH = cls.original_db_path

    def setUp(self):
        # Each test gets a fresh connection to the class-level in-memory database
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        # Clean up tables before each test to ensure isolation (if not using per-test DB)
        # This is crucial if setUpClass initializes the DB once
        cursor = self.conn.cursor()
        tables = ["PartnerCategoryLink", "PartnerContacts", "Partners", "PartnerCategories"]
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
        self.conn.commit()


    def tearDown(self):
        self.conn.close()

    # --- PartnerCategories Tests ---
    def test_add_get_partner_category(self):
        cat_id = db_manager.add_partner_category("Test Category", "Desc", conn=self.conn)
        self.assertIsNotNone(cat_id)
        cat = db_manager.get_partner_category_by_id(cat_id, conn=self.conn)
        self.assertEqual(cat['name'], "Test Category")
        cat_by_name = db_manager.get_partner_category_by_name("Test Category", conn=self.conn)
        self.assertEqual(cat_by_name['category_id'], cat_id)

    def test_update_partner_category(self):
        cat_id = db_manager.add_partner_category("Old Name", conn=self.conn)
        updated = db_manager.update_partner_category(cat_id, "New Name", "New Desc", conn=self.conn)
        self.assertTrue(updated)
        cat = db_manager.get_partner_category_by_id(cat_id, conn=self.conn)
        self.assertEqual(cat['name'], "New Name")
        self.assertEqual(cat['description'], "New Desc")

    def test_delete_partner_category(self):
        cat_id = db_manager.add_partner_category("To Delete", conn=self.conn)
        deleted = db_manager.delete_partner_category(cat_id, conn=self.conn)
        self.assertTrue(deleted)
        self.assertIsNone(db_manager.get_partner_category_by_id(cat_id, conn=self.conn))

    def test_get_all_partner_categories(self):
        db_manager.add_partner_category("Cat 1", conn=self.conn)
        db_manager.add_partner_category("Cat 2", conn=self.conn)
        cats = db_manager.get_all_partner_categories(conn=self.conn)
        self.assertEqual(len(cats), 2)

    def test_partner_category_name_unique(self):
        db_manager.add_partner_category("Unique Cat", conn=self.conn)
        cat_id_duplicate = db_manager.add_partner_category("Unique Cat", conn=self.conn)
        # add_partner_category should return existing ID on conflict if designed that way, or None if strictly new
        # Assuming it returns None or raises error handled by _manage_conn for failed new insert due to unique
        # The current crud add_partner_category returns existing ID if name is found.
        self.assertIsNotNone(cat_id_duplicate) # It will return the ID of the existing one.

    # --- Partners Tests ---
    def test_add_get_partner(self):
        partner_data = {"name": "Test Partner Inc.", "email": "contact@partnerinc.com", "phone": "12345", "notes": "Good notes"}
        partner_id = db_manager.add_partner(partner_data, conn=self.conn)
        self.assertIsNotNone(partner_id)
        try:
            uuid.UUID(partner_id) # Check if it's a valid UUID string
        except ValueError:
            self.fail("Partner ID is not a valid UUID string")

        partner = db_manager.get_partner_by_id(partner_id, conn=self.conn)
        self.assertEqual(partner['name'], "Test Partner Inc.")
        self.assertEqual(partner['email'], "contact@partnerinc.com")
        partner_by_email = db_manager.get_partner_by_email("contact@partnerinc.com", conn=self.conn)
        self.assertEqual(partner_by_email['partner_id'], partner_id)

    def test_update_partner(self):
        p_id = db_manager.add_partner({"name": "Old Partner", "email": "old@p.com"}, conn=self.conn)
        updated = db_manager.update_partner(p_id, {"name": "New Partner", "phone": "555-0123"}, conn=self.conn)
        self.assertTrue(updated)
        partner = db_manager.get_partner_by_id(p_id, conn=self.conn)
        self.assertEqual(partner['name'], "New Partner")
        self.assertEqual(partner['phone'], "555-0123")

    def test_delete_partner(self):
        p_id = db_manager.add_partner({"name": "Delete Me Partner", "email": "del@p.com"}, conn=self.conn)
        deleted = db_manager.delete_partner(p_id, conn=self.conn)
        self.assertTrue(deleted)
        self.assertIsNone(db_manager.get_partner_by_id(p_id, conn=self.conn))

    def test_partner_email_unique(self):
        db_manager.add_partner({"name": "Partner A", "email": "unique@example.com"}, conn=self.conn)
        p_id_dup = db_manager.add_partner({"name": "Partner B", "email": "unique@example.com"}, conn=self.conn)
        self.assertIsNone(p_id_dup) # add_partner returns None on integrity error for unique email

    # --- PartnerContacts Tests ---
    def _create_test_partner(self):
        return db_manager.add_partner({"name": "Contact Test Partner", "email": f"ctp-{uuid.uuid4()}@example.com"}, conn=self.conn)

    def test_add_get_partner_contact(self):
        partner_id = self._create_test_partner()
        contact_data = {"partner_id": partner_id, "name": "John Doe", "email": "john@partner.com", "phone": "111", "role": "Sales"}
        contact_id = db_manager.add_partner_contact(contact_data, conn=self.conn)
        self.assertIsNotNone(contact_id)
        contact = db_manager.get_partner_contact_by_id(contact_id, conn=self.conn)
        self.assertEqual(contact['name'], "John Doe")
        self.assertEqual(contact['partner_id'], partner_id)

    def test_get_contacts_for_partner(self):
        partner_id = self._create_test_partner()
        db_manager.add_partner_contact({"partner_id": partner_id, "name": "Jane", "email":"j@p.com"}, conn=self.conn)
        db_manager.add_partner_contact({"partner_id": partner_id, "name": "Mike", "email":"m@p.com"}, conn=self.conn)
        contacts = db_manager.get_contacts_for_partner(partner_id, conn=self.conn)
        self.assertEqual(len(contacts), 2)

    def test_update_partner_contact(self):
        partner_id = self._create_test_partner()
        c_id = db_manager.add_partner_contact({"partner_id": partner_id, "name": "Old Contact"}, conn=self.conn)
        updated = db_manager.update_partner_contact(c_id, {"name": "New Contact", "role": "Manager"}, conn=self.conn)
        self.assertTrue(updated)
        contact = db_manager.get_partner_contact_by_id(c_id, conn=self.conn)
        self.assertEqual(contact['name'], "New Contact")
        self.assertEqual(contact['role'], "Manager")

    def test_delete_partner_contact(self):
        partner_id = self._create_test_partner()
        c_id = db_manager.add_partner_contact({"partner_id": partner_id, "name": "Delete Contact"}, conn=self.conn)
        deleted = db_manager.delete_partner_contact(c_id, conn=self.conn)
        self.assertTrue(deleted)
        self.assertIsNone(db_manager.get_partner_contact_by_id(c_id, conn=self.conn))

    def test_delete_contacts_for_partner(self):
        partner_id = self._create_test_partner()
        db_manager.add_partner_contact({"partner_id": partner_id, "name": "C1"}, conn=self.conn)
        db_manager.add_partner_contact({"partner_id": partner_id, "name": "C2"}, conn=self.conn)
        deleted_all = db_manager.delete_contacts_for_partner(partner_id, conn=self.conn)
        self.assertTrue(deleted_all) # Assuming it returns True if successful
        contacts = db_manager.get_contacts_for_partner(partner_id, conn=self.conn)
        self.assertEqual(len(contacts), 0)

    # --- PartnerCategoryLink Tests ---
    def _create_test_category(self):
        return db_manager.add_partner_category(f"Link Test Cat {uuid.uuid4()}", conn=self.conn)

    def test_link_unlink_partner_to_category(self):
        partner_id = self._create_test_partner()
        category_id = self._create_test_category()

        linked = db_manager.link_partner_to_category(partner_id, category_id, conn=self.conn)
        self.assertTrue(linked)

        cats_for_partner = db_manager.get_categories_for_partner(partner_id, conn=self.conn)
        self.assertEqual(len(cats_for_partner), 1)
        self.assertEqual(cats_for_partner[0]['category_id'], category_id)

        partners_in_cat = db_manager.get_partners_in_category(category_id, conn=self.conn)
        self.assertEqual(len(partners_in_cat), 1)
        self.assertEqual(partners_in_cat[0]['partner_id'], partner_id)

        # Test linking again (should not fail, might return False if already linked)
        linked_again = db_manager.link_partner_to_category(partner_id, category_id, conn=self.conn)
        # Depending on implementation, this might be True (if it's idempotent success) or False (if it means "no change")
        # The current crud.py link_partner_to_category returns False if link exists.
        self.assertFalse(linked_again)


        unlinked = db_manager.unlink_partner_from_category(partner_id, category_id, conn=self.conn)
        self.assertTrue(unlinked)
        self.assertEqual(len(db_manager.get_categories_for_partner(partner_id, conn=self.conn)), 0)
        self.assertEqual(len(db_manager.get_partners_in_category(category_id, conn=self.conn)), 0)

if __name__ == '__main__':
    unittest.main()
