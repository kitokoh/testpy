import unittest
import sqlite3
import uuid
import os
import sys

# Add project root to sys.path to allow importing project modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db.cruds import experience_crud
from db.init_schema import initialize_database # To create schema in memory

# Mock get_db_connection to use the in-memory database for tests
def get_test_db_connection():
    conn = sqlite3.connect(':memory:')
    # Need to initialize schema for each connection if using :memory:
    # We will call initialize_database with this connection in setUp
    return conn

# Monkey patch the original get_db_connection used by the CRUDs
experience_crud.get_db_connection = get_test_db_connection


class TestExperienceCRUD(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Set up an in-memory SQLite database and initialize the schema once for the class.
        This is more efficient than doing it for each test method if tests are independent.
        However, for strict test isolation, setUp could be used.
        For this CRUD, operations are fairly independent, so setUpClass is acceptable.
        """
        cls.conn = sqlite3.connect(':memory:')
        # Temporarily override the config.DATABASE_PATH for initialize_database
        # This is a bit of a hack. A better way would be to pass the connection
        # directly to initialize_database if it supported it, or use a test-specific config.
        original_db_path = None
        if 'config' in sys.modules:
            original_db_path = sys.modules['config'].DATABASE_PATH
            sys.modules['config'].DATABASE_PATH = ':memory:' # This won't work as expected if config is already loaded
                                                          # and DATABASE_PATH is read at import time.
                                                          # Forcing initialize_database to use our connection is better.

        # A more direct way to ensure initialize_database uses our connection:
        # We need to make initialize_database use cls.conn.
        # The initialize_database function in the provided example directly uses config.DATABASE_PATH.
        # We will patch its internal connect call for the duration of schema init.

        original_sqlite_connect = sqlite3.connect
        def mock_sqlite_connect(db_path, *args, **kwargs):
            if db_path == ':memory:' or (hasattr(sys.modules.get('config'), 'DATABASE_PATH') and db_path == sys.modules['config'].DATABASE_PATH):
                return cls.conn # Return the class-level connection
            return original_sqlite_connect(db_path, *args, **kwargs)

        sqlite3.connect = mock_sqlite_connect

        # The initialize_database function in the provided context uses config.DATABASE_PATH
        # We need to make sure it uses our in-memory connection.
        # The crud functions themselves are patched to use get_test_db_connection which returns a new :memory: db
        # This means each CRUD call in tests gets its own fresh :memory: db.
        # For setUpClass, we create one common :memory: db and initialize schema.
        # Then, for each test, the CRUD functions will use their *own* :memory: db.
        # This is not ideal. CRUDs should take a connection object.
        #
        # Workaround: We will use a single connection for all tests in this class
        # and pass it explicitly to CRUD functions.
        # The monkey patch of experience_crud.get_db_connection will be ignored by passing conn.

        initialize_database() # This will now use cls.conn due to the patch
        sqlite3.connect = original_sqlite_connect # Restore original connect

        if original_db_path and 'config' in sys.modules:
             sys.modules['config'].DATABASE_PATH = original_db_path


    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def setUp(self):
        """
        For each test, we ensure tables are clean.
        Since setUpClass initializes the schema, we can delete data from tables here.
        Or, if tests truly need to be independent down to the connection level,
        each test would establish its own :memory: connection and init schema.
        Given the current structure, we'll use the class connection and clean tables.
        """
        self.conn.execute("DELETE FROM ExperienceTags")
        self.conn.execute("DELETE FROM ExperienceMedia")
        self.conn.execute("DELETE FROM ExperienceRelatedEntities")
        self.conn.execute("DELETE FROM Experiences")
        self.conn.execute("DELETE FROM Tags")
        self.conn.execute("DELETE FROM MediaItems")
        self.conn.execute("DELETE FROM Users") # If user_id FK is relevant
        self.conn.commit()

        # Create a dummy user for FK constraints if necessary
        self.test_user_id = str(uuid.uuid4())
        try:
            self.conn.execute(
                "INSERT OR IGIGNORE INTO Users (user_id, username, password_hash, salt, email, role) VALUES (?, ?, ?, ?, ?, ?)",
                (self.test_user_id, 'testuser', 'hash', 'salt', 'test@example.com', 'user')
            )
            self.conn.commit()
        except sqlite3.IntegrityError: # User might already exist if tests are run multiple times or setup changes
            pass


    def test_add_and_get_experience(self):
        experience_data = {
            "title": "Test Experience 1",
            "description": "A description for test experience 1.",
            "experience_date": "2024-01-15",
            "type": "TestType",
            "user_id": self.test_user_id
        }
        exp_id = experience_crud.add_experience(experience_data, conn=self.conn)
        self.assertIsNotNone(exp_id)

        retrieved_exp = experience_crud.get_experience_by_id(exp_id, conn=self.conn)
        self.assertIsNotNone(retrieved_exp)
        self.assertEqual(retrieved_exp["title"], experience_data["title"])
        self.assertEqual(retrieved_exp["description"], experience_data["description"])
        self.assertEqual(retrieved_exp["experience_date"], experience_data["experience_date"])
        self.assertEqual(retrieved_exp["type"], experience_data["type"])
        self.assertEqual(retrieved_exp["user_id"], self.test_user_id)

    def test_get_all_experiences(self):
        exps_data = [
            {"title": "Exp A", "type": "Type1", "user_id": self.test_user_id, "experience_date": "2024-01-01"},
            {"title": "Exp B", "type": "Type2", "user_id": self.test_user_id, "experience_date": "2024-01-02"},
            {"title": "Exp C", "type": "Type1", "user_id": self.test_user_id, "experience_date": "2024-01-03"},
        ]
        for data in exps_data:
            experience_crud.add_experience(data, conn=self.conn)

        all_exps = experience_crud.get_all_experiences(conn=self.conn)
        self.assertEqual(len(all_exps), 3)

        # Test with filter
        filtered_exps = experience_crud.get_all_experiences(filters={"type": "Type1"}, conn=self.conn)
        self.assertEqual(len(filtered_exps), 2)
        for exp in filtered_exps:
            self.assertEqual(exp["type"], "Type1")

    def test_update_experience(self):
        initial_data = {"title": "Initial Title", "description": "Initial Desc", "type": "Initial", "user_id": self.test_user_id}
        exp_id = experience_crud.add_experience(initial_data, conn=self.conn)
        self.assertIsNotNone(exp_id)

        update_data = {"title": "Updated Title", "description": "Updated Desc"}
        updated = experience_crud.update_experience(exp_id, update_data, conn=self.conn)
        self.assertTrue(updated)

        retrieved_exp = experience_crud.get_experience_by_id(exp_id, conn=self.conn)
        self.assertEqual(retrieved_exp["title"], "Updated Title")
        self.assertEqual(retrieved_exp["description"], "Updated Desc")
        self.assertEqual(retrieved_exp["type"], "Initial") # Type should remain unchanged

    def test_delete_experience(self):
        exp_data = {"title": "To Be Deleted", "type": "DeleteTest", "user_id": self.test_user_id}
        exp_id = experience_crud.add_experience(exp_data, conn=self.conn)
        self.assertIsNotNone(exp_id)

        deleted = experience_crud.delete_experience(exp_id, conn=self.conn)
        self.assertTrue(deleted)

        retrieved_exp = experience_crud.get_experience_by_id(exp_id, conn=self.conn)
        self.assertIsNone(retrieved_exp)

    def test_add_and_get_related_entities(self):
        exp_id = experience_crud.add_experience({"title": "Related Entity Test Exp", "user_id": self.test_user_id}, conn=self.conn)
        self.assertIsNotNone(exp_id)

        entity_type = "Client"
        entity_id_val = "client_xyz"
        link_id = experience_crud.add_experience_related_entity(exp_id, entity_type, entity_id_val, conn=self.conn)
        self.assertIsNotNone(link_id)

        related_entities = experience_crud.get_related_entities_for_experience(exp_id, conn=self.conn)
        self.assertEqual(len(related_entities), 1)
        self.assertEqual(related_entities[0]["entity_type"], entity_type)
        self.assertEqual(related_entities[0]["entity_id"], entity_id_val)
        self.assertEqual(related_entities[0]["experience_related_entity_id"], link_id)


    def test_remove_related_entity(self):
        exp_id = experience_crud.add_experience({"title": "Remove Related Test", "user_id": self.test_user_id}, conn=self.conn)
        link_id = experience_crud.add_experience_related_entity(exp_id, "Project", "proj_123", conn=self.conn)
        self.assertIsNotNone(link_id)

        removed = experience_crud.remove_experience_related_entity(link_id, conn=self.conn)
        self.assertTrue(removed)

        related_entities = experience_crud.get_related_entities_for_experience(exp_id, conn=self.conn)
        self.assertEqual(len(related_entities), 0)

        # Test remove all
        experience_crud.add_experience_related_entity(exp_id, "Asset", "asset_001", conn=self.conn)
        experience_crud.add_experience_related_entity(exp_id, "Asset", "asset_002", conn=self.conn)
        removed_all = experience_crud.remove_all_related_entities_for_experience(exp_id, conn=self.conn)
        self.assertTrue(removed_all)
        related_entities_after_all_removed = experience_crud.get_related_entities_for_experience(exp_id, conn=self.conn)
        self.assertEqual(len(related_entities_after_all_removed), 0)


    def test_add_and_get_experience_media(self):
        exp_id = experience_crud.add_experience({"title": "Media Test Exp", "user_id": self.test_user_id}, conn=self.conn)
        self.assertIsNotNone(exp_id)

        # Create a dummy media item for FK constraint
        media_item_id_val = str(uuid.uuid4())
        self.conn.execute("INSERT INTO MediaItems (media_item_id, title, item_type) VALUES (?, ?, ?)",
                          (media_item_id_val, "Test Media Item", "image"))
        self.conn.commit()

        link_id = experience_crud.add_experience_media(exp_id, media_item_id_val, conn=self.conn)
        self.assertIsNotNone(link_id)

        linked_media = experience_crud.get_media_for_experience(exp_id, conn=self.conn)
        self.assertEqual(len(linked_media), 1)
        self.assertEqual(linked_media[0]["media_item_id"], media_item_id_val)
        self.assertEqual(linked_media[0]["experience_media_id"], link_id)

        # Test remove
        removed = experience_crud.remove_experience_media(link_id, conn=self.conn)
        self.assertTrue(removed)
        linked_media_after_remove = experience_crud.get_media_for_experience(exp_id, conn=self.conn)
        self.assertEqual(len(linked_media_after_remove), 0)

        # Test remove all
        experience_crud.add_experience_media(exp_id, media_item_id_val, conn=self.conn) # Re-add one
        # Add another dummy media item
        media_item_id_val2 = str(uuid.uuid4())
        self.conn.execute("INSERT INTO MediaItems (media_item_id, title, item_type) VALUES (?, ?, ?)",
                          (media_item_id_val2, "Test Media Item 2", "video"))
        experience_crud.add_experience_media(exp_id, media_item_id_val2, conn=self.conn)

        removed_all = experience_crud.remove_all_media_for_experience(exp_id, conn=self.conn)
        self.assertTrue(removed_all)
        linked_media_after_all_removed = experience_crud.get_media_for_experience(exp_id, conn=self.conn)
        self.assertEqual(len(linked_media_after_all_removed), 0)


    def test_add_and_get_experience_tags(self):
        exp_id = experience_crud.add_experience({"title": "Tag Test Exp", "user_id": self.test_user_id}, conn=self.conn)
        self.assertIsNotNone(exp_id)

        # Create a dummy tag for FK constraint
        tag_name = "TestTagForExperience"
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO Tags (tag_name) VALUES (?)", (tag_name,))
        tag_id_val = cursor.lastrowid
        self.conn.commit()
        self.assertIsNotNone(tag_id_val)

        link_id = experience_crud.add_experience_tag(exp_id, tag_id_val, conn=self.conn)
        self.assertIsNotNone(link_id)

        linked_tags = experience_crud.get_tags_for_experience(exp_id, conn=self.conn)
        self.assertEqual(len(linked_tags), 1)
        self.assertEqual(linked_tags[0]["tag_id"], tag_id_val)
        self.assertEqual(linked_tags[0]["tag_name"], tag_name)
        self.assertEqual(linked_tags[0]["experience_tag_id"], link_id)

        # Test remove
        removed = experience_crud.remove_experience_tag_link(exp_id, tag_id_val, conn=self.conn)
        self.assertTrue(removed)
        linked_tags_after_remove = experience_crud.get_tags_for_experience(exp_id, conn=self.conn)
        self.assertEqual(len(linked_tags_after_remove), 0)

        # Test remove all
        experience_crud.add_experience_tag(exp_id, tag_id_val, conn=self.conn) # Re-add one
        # Add another dummy tag
        tag_name2 = "AnotherTestTag"
        cursor.execute("INSERT INTO Tags (tag_name) VALUES (?)", (tag_name2,))
        tag_id_val2 = cursor.lastrowid
        self.conn.commit()
        experience_crud.add_experience_tag(exp_id, tag_id_val2, conn=self.conn)

        removed_all = experience_crud.remove_all_tags_for_experience(exp_id, conn=self.conn)
        self.assertTrue(removed_all)
        linked_tags_after_all_removed = experience_crud.get_tags_for_experience(exp_id, conn=self.conn)
        self.assertEqual(len(linked_tags_after_all_removed), 0)


if __name__ == '__main__':
    unittest.main()
