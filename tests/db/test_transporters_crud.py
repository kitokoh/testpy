import unittest
import os
import sys
import sqlite3

# Adjust path to import from root project directory
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db.cruds.transporters_crud import (
    add_transporter, get_transporter_by_id, get_all_transporters,
    update_transporter, delete_transporter
)
from db.utils import get_db_connection # Used by CRUDs, not directly in test usually
from db.init_schema import initialize_database

# Mock config for testing if config is imported by db.init_schema or db.utils
# This is to ensure DATABASE_PATH is controlled during tests.
class MockConfig:
    DATABASE_PATH = os.path.join(project_root, "test_app_data.db")
    DEFAULT_ADMIN_USERNAME = "test_admin"
    DEFAULT_ADMIN_PASSWORD = "test_password"

# Apply the mock config at the module level for db.init_schema
# This is a common pattern if the modules it uses (like config.py) are at the root
# and are imported when db.init_schema is loaded.
# We need to ensure that when db.init_schema (or its imports) try to import 'config',
# they get our mock.
sys.modules['config'] = MockConfig


class TestTransportersCrud(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Set up the database once for the entire test class.
        This involves ensuring a clean test database file is used.
        """
        # Ensure any old test database is removed
        if os.path.exists(MockConfig.DATABASE_PATH):
            os.remove(MockConfig.DATABASE_PATH)

        # Initialize the database schema
        # initialize_database() will use the MockConfig.DATABASE_PATH
        initialize_database()

    @classmethod
    def tearDownClass(cls):
        """
        Clean up by removing the test database file after all tests are run.
        """
        if os.path.exists(MockConfig.DATABASE_PATH):
            os.remove(MockConfig.DATABASE_PATH)

    def setUp(self):
        """
        Prepare for each test. This typically means ensuring tables are clean.
        Since initialize_database() in setUpClass creates the schema,
        we'll delete all rows from Transporters table for test isolation.
        """
        conn = None
        try:
            conn = sqlite3.connect(MockConfig.DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Transporters")
            # Add other DELETES if there are foreign key relations from Transporters
            # or if other tables are dirtied by transporter actions.
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error in setUp, cleaning Transporters table: {e}")
            # Depending on severity, you might want to raise or handle differently
        finally:
            if conn:
                conn.close()

    def test_add_and_get_transporter_with_location_and_cargo(self):
        """Test adding a transporter with all fields and retrieving it."""
        data = {
            "name": "Test Transporter 1",
            "contact_person": "John Doe",
            "phone": "123-456-7890",
            "email": "john.doe@example.com",
            "address": "123 Test St",
            "service_area": "Local",
            "notes": "Test notes",
            "latitude": 45.123,
            "longitude": -75.456,
            "current_cargo": "Electronics"
        }
        transporter_id = add_transporter(data)
        self.assertIsNotNone(transporter_id, "add_transporter should return an ID.")

        retrieved = get_transporter_by_id(transporter_id)
        self.assertIsNotNone(retrieved, "get_transporter_by_id should retrieve data.")
        self.assertEqual(retrieved['name'], data['name'])
        self.assertEqual(retrieved['latitude'], data['latitude'])
        self.assertEqual(retrieved['longitude'], data['longitude'])
        self.assertEqual(retrieved['current_cargo'], data['current_cargo'])
        self.assertEqual(retrieved['contact_person'], data['contact_person'])

    def test_add_transporter_minimal_data(self):
        """Test adding a transporter with only mandatory fields (name) and null for others."""
        data = {"name": "Minimal Transporter"}
        transporter_id = add_transporter(data)
        self.assertIsNotNone(transporter_id)

        retrieved = get_transporter_by_id(transporter_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['name'], data['name'])
        self.assertIsNone(retrieved['latitude'])
        self.assertIsNone(retrieved['longitude'])
        self.assertIsNone(retrieved['current_cargo'])
        self.assertIsNone(retrieved['contact_person']) # Assuming contact_person is not mandatory

    def test_update_transporter_location_and_cargo(self):
        """Test updating a transporter's location, cargo, and other fields."""
        initial_data = {
            "name": "Old Transporter Name",
            "latitude": 10.0,
            "longitude": 20.0,
            "current_cargo": "Initial Goods"
        }
        transporter_id = add_transporter(initial_data)
        self.assertIsNotNone(transporter_id)

        updated_data = {
            "name": "New Transporter Name",
            "latitude": 12.34,
            "longitude": 56.78,
            "current_cargo": "Updated Cargo",
            "phone": "987-654-3210" # Also update another field
        }
        success = update_transporter(transporter_id, updated_data)
        self.assertTrue(success, "update_transporter should return True on success.")

        retrieved = get_transporter_by_id(transporter_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['name'], updated_data['name'])
        self.assertEqual(retrieved['latitude'], updated_data['latitude'])
        self.assertEqual(retrieved['longitude'], updated_data['longitude'])
        self.assertEqual(retrieved['current_cargo'], updated_data['current_cargo'])
        self.assertEqual(retrieved['phone'], updated_data['phone'])
        # Check that fields not in updated_data but present in initial_data are still there (or None if not set)
        self.assertIsNone(retrieved['address']) # Assuming address was not in initial_data

    def test_get_all_transporters_includes_new_fields(self):
        """Test that get_all_transporters retrieves new fields correctly."""
        data1 = {
            "name": "Transporter Alpha",
            "latitude": 33.3,
            "longitude": 44.4,
            "current_cargo": "Cargo A"
        }
        data2 = {
            "name": "Transporter Beta", # No location/cargo
            "contact_person": "Jane Smith"
        }
        data3 = {
            "name": "Transporter Gamma",
            "latitude": 55.5,
            "longitude": 66.6,
            "current_cargo": None # Explicitly None cargo
        }
        add_transporter(data1)
        add_transporter(data2)
        add_transporter(data3)

        all_transporters = get_all_transporters()
        self.assertEqual(len(all_transporters), 3, "Should retrieve all three transporters.")

        found_alpha = False
        found_beta = False
        found_gamma = False

        for t in all_transporters:
            if t['name'] == "Transporter Alpha":
                found_alpha = True
                self.assertEqual(t['latitude'], data1['latitude'])
                self.assertEqual(t['longitude'], data1['longitude'])
                self.assertEqual(t['current_cargo'], data1['current_cargo'])
            elif t['name'] == "Transporter Beta":
                found_beta = True
                self.assertIsNone(t['latitude'])
                self.assertIsNone(t['longitude'])
                self.assertIsNone(t['current_cargo'])
                self.assertEqual(t['contact_person'], data2['contact_person'])
            elif t['name'] == "Transporter Gamma":
                found_gamma = True
                self.assertEqual(t['latitude'], data3['latitude'])
                self.assertEqual(t['longitude'], data3['longitude'])
                self.assertIsNone(t['current_cargo']) # current_cargo was None

        self.assertTrue(found_alpha, "Transporter Alpha not found in get_all_transporters result.")
        self.assertTrue(found_beta, "Transporter Beta not found in get_all_transporters result.")
        self.assertTrue(found_gamma, "Transporter Gamma not found in get_all_transporters result.")

    def test_delete_transporter(self):
        """Test deleting a transporter."""
        data = {"name": "To Be Deleted"}
        transporter_id = add_transporter(data)
        self.assertIsNotNone(transporter_id)

        retrieved_before_delete = get_transporter_by_id(transporter_id)
        self.assertIsNotNone(retrieved_before_delete, "Transporter should exist before deletion.")

        success = delete_transporter(transporter_id)
        self.assertTrue(success, "delete_transporter should return True on success.")

        retrieved_after_delete = get_transporter_by_id(transporter_id)
        self.assertIsNone(retrieved_after_delete, "Transporter should not exist after deletion.")

    def test_update_non_existent_transporter(self):
        """Test updating a non-existent transporter."""
        non_existent_id = "abc-123-def-456" # Assuming UUID format, but any non-existent ID
        updated_data = {"name": "Attempt Update"}
        success = update_transporter(non_existent_id, updated_data)
        self.assertFalse(success, "Updating a non-existent transporter should return False.")

    def test_get_non_existent_transporter(self):
        """Test getting a non-existent transporter by ID."""
        non_existent_id = "xyz-789-uvw-012"
        retrieved = get_transporter_by_id(non_existent_id)
        self.assertIsNone(retrieved, "Getting a non-existent transporter should return None.")

if __name__ == '__main__':
    unittest.main()
