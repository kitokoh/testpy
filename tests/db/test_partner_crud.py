import unittest
import sqlite3
import os
import uuid
from datetime import datetime, timedelta

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
        tables = ["PartnerCategoryLink", "PartnerContacts", "Partners", "PartnerCategories", "PartnerInteractions", "PartnerDocuments"] # Added PartnerInteractions
        for table in tables:
            # Check if table exists before trying to delete from it, as PartnerInteractions might not exist in older schema versions during transitional testing
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';")
            if cursor.fetchone():
                cursor.execute(f"DELETE FROM {table}")
        self.conn.commit()


    def tearDown(self):
        self.conn.close()

    # --- PartnerCategories Tests ---
    def test_add_get_partner_category(self):
        cat_id = db_manager.add_partner_category({"category_name": "Test Category", "description": "Desc"}, conn=self.conn) # Pass as dict
        self.assertIsNotNone(cat_id)
        cat = db_manager.get_partner_category_by_id(cat_id, conn=self.conn)
        self.assertEqual(cat['category_name'], "Test Category") # Corrected key
        cat_by_name = db_manager.get_partner_category_by_name("Test Category", conn=self.conn)
        self.assertEqual(cat_by_name['partner_category_id'], cat_id) # Corrected key

    def test_update_partner_category(self):
        cat_id = db_manager.add_partner_category({"category_name": "Old Name"}, conn=self.conn) # Pass as dict
        updated = db_manager.update_partner_category(cat_id, {"category_name": "New Name", "description": "New Desc"}, conn=self.conn) # Pass as dict
        self.assertTrue(updated)
        cat = db_manager.get_partner_category_by_id(cat_id, conn=self.conn)
        self.assertEqual(cat['category_name'], "New Name") # Corrected key
        self.assertEqual(cat['description'], "New Desc")

    def test_delete_partner_category(self):
        cat_id = db_manager.add_partner_category({"category_name": "To Delete"}, conn=self.conn) # Pass as dict
        deleted = db_manager.delete_partner_category(cat_id, conn=self.conn)
        self.assertTrue(deleted)
        self.assertIsNone(db_manager.get_partner_category_by_id(cat_id, conn=self.conn))

    def test_get_all_partner_categories(self):
        db_manager.add_partner_category({"category_name": "Cat 1"}, conn=self.conn) # Pass as dict
        db_manager.add_partner_category({"category_name": "Cat 2"}, conn=self.conn) # Pass as dict
        cats = db_manager.get_all_partner_categories(conn=self.conn)
        self.assertEqual(len(cats), 2)

    def test_partner_category_name_unique(self):
        db_manager.add_partner_category({"category_name": "Unique Cat"}, conn=self.conn) # Pass as dict
        cat_id_duplicate = db_manager.add_partner_category({"category_name": "Unique Cat"}, conn=self.conn) # Pass as dict
        # add_partner_category should return existing ID on conflict if designed that way, or None if strictly new
        # Assuming it returns None or raises error handled by _manage_conn for failed new insert due to unique
        # The current crud add_partner_category returns existing ID if name is found.
        self.assertIsNotNone(cat_id_duplicate) # It will return the ID of the existing one.

    # --- Partners Tests ---
    def test_add_get_partner(self):
        start_date = datetime.utcnow().strftime('%Y-%m-%d')
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
        start_date = datetime.utcnow().strftime('%Y-%m-%d')
        end_date = (datetime.utcnow() + timedelta(days=365)).strftime('%Y-%m-%d')
        partner_data = {
            "partner_name": "Test Partner Inc.", # Corrected key
            "email": "contact@partnerinc.com",
            "phone": "12345",
            "notes": "Good notes",
            "status": "Active",
            "website_url": "http://partner.example.com",
            "partner_type": "Supplier",
            "collaboration_start_date": start_date,
            "collaboration_end_date": end_date
        }
        partner_id = db_manager.add_partner(partner_data, conn=self.conn)
        self.assertIsNotNone(partner_id)
        try:
            uuid.UUID(partner_id) # Check if it's a valid UUID string
        except ValueError:
            self.fail("Partner ID is not a valid UUID string")

        partner = db_manager.get_partner_by_id(partner_id, conn=self.conn)
        self.assertEqual(partner['partner_name'], "Test Partner Inc.") # Corrected key
        self.assertEqual(partner['email'], "contact@partnerinc.com")
        self.assertEqual(partner['status'], "Active")
        self.assertEqual(partner['website_url'], "http://partner.example.com")
        self.assertEqual(partner['partner_type'], "Supplier")
        self.assertEqual(partner['collaboration_start_date'], start_date)
        self.assertEqual(partner['collaboration_end_date'], end_date)

        partner_by_email = db_manager.get_partner_by_email("contact@partnerinc.com", conn=self.conn)
        self.assertEqual(partner_by_email['partner_id'], partner_id)

    def test_update_partner(self):
        p_id = db_manager.add_partner({"partner_name": "Old Partner", "email": "old@p.com", "status": "Active"}, conn=self.conn) # Corrected key
        updated_data = {
            "partner_name": "New Partner",
            "phone": "555-0123",
            "status": "Inactive",
            "website_url": "http://new.example.com"
        }
        updated = db_manager.update_partner(p_id, updated_data, conn=self.conn)
        self.assertTrue(updated)
        partner = db_manager.get_partner_by_id(p_id, conn=self.conn)
        self.assertEqual(partner['partner_name'], "New Partner") # Corrected key
        self.assertEqual(partner['phone'], "555-0123")
        self.assertEqual(partner['status'], "Inactive")
        self.assertEqual(partner['website_url'], "http://new.example.com")

    def test_delete_partner(self):
        p_id = db_manager.add_partner({"partner_name": "Delete Me Partner", "email": "del@p.com"}, conn=self.conn) # Corrected key
        deleted = db_manager.delete_partner(p_id, conn=self.conn)
        self.assertTrue(deleted)
        self.assertIsNone(db_manager.get_partner_by_id(p_id, conn=self.conn))

    def test_partner_email_unique(self):
        db_manager.add_partner({"partner_name": "Partner A", "email": "unique@example.com"}, conn=self.conn) # Corrected key
        p_id_dup = db_manager.add_partner({"partner_name": "Partner B", "email": "unique@example.com"}, conn=self.conn) # Corrected key
        self.assertIsNone(p_id_dup) # add_partner returns None on integrity error for unique email

    # --- PartnerContacts Tests ---
    def _create_test_partner(self, name_suffix=""): # Added suffix for more unique test partners
        partner_name = f"Contact Test Partner {name_suffix} {uuid.uuid4()}"
        email = f"ctp-{uuid.uuid4()}@example.com"
        return db_manager.add_partner({"partner_name": partner_name, "email": email}, conn=self.conn)


    def test_add_get_partner_contact(self):
        partner_id = self._create_test_partner("contact_add_get")
        # Note: add_partner_contact in CRUD expects contact_data for central Contacts table
        # and link-specific data like is_primary, can_receive_documents.
        # The central_add_contact expects 'name' or 'displayName'.
        contact_payload = {
            "displayName": "John Doe", "email": "john@partner.com", "phone": "111",
            "position": "Sales", "is_primary": True # Example link-specific field
        }
        # add_partner_contact itself needs partner_id and the contact_payload.
        # The partner_id is passed as a separate argument to add_partner_contact.
        partner_contact_link_id = db_manager.add_partner_contact(partner_id, contact_payload, conn=self.conn)
        self.assertIsNotNone(partner_contact_link_id)

        # get_partner_contact_by_id retrieves the *linked* contact, including central details
        retrieved_linked_contact = db_manager.get_partner_contact_by_id(partner_contact_link_id, conn=self.conn)
        self.assertIsNotNone(retrieved_linked_contact)
        self.assertEqual(retrieved_linked_contact['displayName'], "John Doe")
        self.assertEqual(retrieved_linked_contact['partner_id'], partner_id)
        self.assertTrue(retrieved_linked_contact['is_primary'])


    def test_get_contacts_for_partner(self):
        partner_id = self._create_test_partner("get_contacts")
        db_manager.add_partner_contact(partner_id, {"displayName": "Jane", "email":"j@p.com"}, conn=self.conn)
        db_manager.add_partner_contact(partner_id, {"displayName": "Mike", "email":"m@p.com"}, conn=self.conn)
        contacts = db_manager.get_contacts_for_partner(partner_id, conn=self.conn)
        self.assertEqual(len(contacts), 2)

    def test_update_partner_contact(self):
        partner_id = self._create_test_partner("update_contact")
        # Add contact first
        contact_payload_initial = {"displayName": "Old Contact", "position": "Intern"}
        partner_contact_link_id = db_manager.add_partner_contact(partner_id, contact_payload_initial, conn=self.conn)
        self.assertIsNotNone(partner_contact_link_id)

        # Now update
        update_payload = {"displayName": "New Contact", "position": "Manager", "is_primary": True}
        updated = db_manager.update_partner_contact(partner_contact_link_id, update_payload, conn=self.conn)
        self.assertTrue(updated)

        retrieved_updated_contact = db_manager.get_partner_contact_by_id(partner_contact_link_id, conn=self.conn)
        self.assertEqual(retrieved_updated_contact['displayName'], "New Contact")
        self.assertEqual(retrieved_updated_contact['position'], "Manager")
        self.assertTrue(retrieved_updated_contact['is_primary'])


    def test_delete_partner_contact(self):
        partner_id = self._create_test_partner("delete_contact")
        partner_contact_link_id = db_manager.add_partner_contact(partner_id, {"displayName": "Delete Contact"}, conn=self.conn)
        deleted = db_manager.delete_partner_contact(partner_contact_link_id, conn=self.conn)
        self.assertTrue(deleted)
        self.assertIsNone(db_manager.get_partner_contact_by_id(partner_contact_link_id, conn=self.conn))

    def test_delete_contacts_for_partner(self):
        partner_id = self._create_test_partner("delete_all_contacts")
        db_manager.add_partner_contact(partner_id, {"displayName": "C1"}, conn=self.conn)
        db_manager.add_partner_contact(partner_id, {"displayName": "C2"}, conn=self.conn)
        deleted_all = db_manager.delete_contacts_for_partner(partner_id, conn=self.conn)
        self.assertTrue(deleted_all) # Assuming it returns True if successful
        contacts = db_manager.get_contacts_for_partner(partner_id, conn=self.conn)
        self.assertEqual(len(contacts), 0)

    # --- PartnerCategoryLink Tests ---
    def _create_test_category(self, name_suffix=""): # Added suffix for unique category names
        category_name = f"Link Test Cat {name_suffix} {uuid.uuid4()}"
        return db_manager.add_partner_category({"category_name": category_name}, conn=self.conn)


    def test_link_unlink_partner_to_category(self):
        partner_id = self._create_test_partner("link_cat")
        category_id = self._create_test_category("link_partner")

        linked = db_manager.link_partner_to_category(partner_id, category_id, conn=self.conn)
        self.assertTrue(linked)

        cats_for_partner = db_manager.get_categories_for_partner(partner_id, conn=self.conn)
        self.assertEqual(len(cats_for_partner), 1)
        self.assertEqual(cats_for_partner[0]['partner_category_id'], category_id) # Corrected key

        partners_in_cat = db_manager.get_partners_in_category(category_id, conn=self.conn)
        self.assertEqual(len(partners_in_cat), 1)
        self.assertEqual(partners_in_cat[0]['partner_id'], partner_id)

        # Test linking again (should be idempotent success, link_partner_to_category returns True if link exists or was created)
        linked_again = db_manager.link_partner_to_category(partner_id, category_id, conn=self.conn)
        self.assertTrue(linked_again) # Current CRUD returns True if exists


        unlinked = db_manager.unlink_partner_from_category(partner_id, category_id, conn=self.conn)
        self.assertTrue(unlinked)
        self.assertEqual(len(db_manager.get_categories_for_partner(partner_id, conn=self.conn)), 0)
        self.assertEqual(len(db_manager.get_partners_in_category(category_id, conn=self.conn)), 0)

    # --- PartnerInteractions Tests ---
    def test_add_get_partner_interaction(self):
        partner_id = self._create_test_partner("interaction_add_get")
        self.assertIsNotNone(partner_id, "Failed to create partner for interaction test")

        interaction_date = datetime.utcnow().strftime('%Y-%m-%d')
        interaction_data = {
            "partner_id": partner_id,
            "interaction_date": interaction_date,
            "interaction_type": "Call",
            "notes": "Discussed project milestones."
        }
        interaction_id = db_manager.add_partner_interaction(interaction_data, conn=self.conn)
        self.assertIsNotNone(interaction_id)
        try:
            uuid.UUID(interaction_id)
        except ValueError:
            self.fail("Interaction ID is not a valid UUID string")

        interactions = db_manager.get_interactions_for_partner(partner_id, conn=self.conn)
        self.assertEqual(len(interactions), 1)
        retrieved_interaction = interactions[0]
        self.assertEqual(retrieved_interaction['interaction_id'], interaction_id)
        self.assertEqual(retrieved_interaction['partner_id'], partner_id)
        self.assertEqual(retrieved_interaction['interaction_date'], interaction_date)
        self.assertEqual(retrieved_interaction['interaction_type'], "Call")
        self.assertEqual(retrieved_interaction['notes'], "Discussed project milestones.")
        self.assertIn('created_at', retrieved_interaction)
        self.assertIn('updated_at', retrieved_interaction)

    def test_update_partner_interaction(self):
        partner_id = self._create_test_partner("interaction_update")
        self.assertIsNotNone(partner_id)

        initial_date = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
        interaction_id = db_manager.add_partner_interaction({
            "partner_id": partner_id, "interaction_date": initial_date,
            "interaction_type": "Initial Meeting", "notes": "First contact."
        }, conn=self.conn)
        self.assertIsNotNone(interaction_id)

        updated_date = datetime.utcnow().strftime('%Y-%m-%d')
        update_data = {
            "interaction_date": updated_date,
            "interaction_type": "Follow-up Email",
            "notes": "Sent follow-up materials."
        }
        updated = db_manager.update_partner_interaction(interaction_id, update_data, conn=self.conn)
        self.assertTrue(updated)

        interactions = db_manager.get_interactions_for_partner(partner_id, conn=self.conn)
        self.assertEqual(len(interactions), 1)
        retrieved_interaction = interactions[0]
        self.assertEqual(retrieved_interaction['interaction_id'], interaction_id)
        self.assertEqual(retrieved_interaction['interaction_date'], updated_date)
        self.assertEqual(retrieved_interaction['interaction_type'], "Follow-up Email")
        self.assertEqual(retrieved_interaction['notes'], "Sent follow-up materials.")
        # Optionally, check if updated_at changed, though this requires careful handling of time precision
        # self.assertNotEqual(retrieved_interaction['created_at'], retrieved_interaction['updated_at'])


    def test_delete_partner_interaction(self):
        partner_id = self._create_test_partner("interaction_delete")
        self.assertIsNotNone(partner_id)

        interaction_id = db_manager.add_partner_interaction({
            "partner_id": partner_id, "interaction_date": datetime.utcnow().strftime('%Y-%m-%d'),
            "interaction_type": "Cleanup Test", "notes": "To be deleted."
        }, conn=self.conn)
        self.assertIsNotNone(interaction_id)

        deleted = db_manager.delete_partner_interaction(interaction_id, conn=self.conn)
        self.assertTrue(deleted)

        interactions = db_manager.get_interactions_for_partner(partner_id, conn=self.conn)
        self.assertEqual(len(interactions), 0)

        # Test deleting non-existent ID
        non_existent_id = str(uuid.uuid4())
        deleted_non_existent = db_manager.delete_partner_interaction(non_existent_id, conn=self.conn)
        self.assertFalse(deleted_non_existent)


    def test_get_interactions_for_partner_ordering(self):
        partner_id = self._create_test_partner("interaction_ordering")
        self.assertIsNotNone(partner_id)

        date_today = datetime.utcnow()
        date_yesterday = date_today - timedelta(days=1)
        date_day_before = date_today - timedelta(days=2)

        # Add interactions out of order by date and creation time
        interaction_id1 = db_manager.add_partner_interaction({
            "partner_id": partner_id, "interaction_date": date_yesterday.strftime('%Y-%m-%d'),
            "interaction_type": "Yesterday Call", "notes": "Note 1"
        }, conn=self.conn)
        # Simulate a slight delay for created_at difference
        interaction_id2 = db_manager.add_partner_interaction({
            "partner_id": partner_id, "interaction_date": date_day_before.strftime('%Y-%m-%d'),
            "interaction_type": "Day Before Meeting", "notes": "Note 2"
        }, conn=self.conn)
        interaction_id3 = db_manager.add_partner_interaction({ # Same date as id1, should be ordered by creation (id3 then id1)
            "partner_id": partner_id, "interaction_date": date_yesterday.strftime('%Y-%m-%d'),
            "interaction_type": "Yesterday Email", "notes": "Note 3"
        }, conn=self.conn)

        self.assertTrue(all([interaction_id1, interaction_id2, interaction_id3]))

        interactions = db_manager.get_interactions_for_partner(partner_id, conn=self.conn)
        self.assertEqual(len(interactions), 3)

        # Expected order: date_yesterday (id3), date_yesterday (id1), date_day_before (id2)
        # Because DESC date, then DESC created_at
        self.assertEqual(interactions[0]['interaction_id'], interaction_id3)
        self.assertEqual(interactions[0]['interaction_date'], date_yesterday.strftime('%Y-%m-%d'))

        self.assertEqual(interactions[1]['interaction_id'], interaction_id1)
        self.assertEqual(interactions[1]['interaction_date'], date_yesterday.strftime('%Y-%m-%d'))

        self.assertEqual(interactions[2]['interaction_id'], interaction_id2)
        self.assertEqual(interactions[2]['interaction_date'], date_day_before.strftime('%Y-%m-%d'))


if __name__ == '__main__':
    unittest.main()
