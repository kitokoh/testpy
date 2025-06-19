import unittest
import sys
import os
import sqlite3 # For specific error checking if needed, though current db.py handles it

# Add project root to sys.path to allow importing 'db'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import db as db_manager # For add_user, get_user_by_id etc. from db/__init__
from db import init_schema # For initialize_database

class TestAuth(unittest.TestCase):

    def setUp(self):
        """
        Initialize the database before each test.
        This ensures that tables are created.
        For auth tests, we primarily interact with the Users table.
        Consider clearing Users table or using unique data for each test.
        """
        # Using a separate test database might be safer in the long run,
        # but for now, we use the main one and clean up.
        # Ensure DATABASE_NAME in db.py is either a test-specific DB or handle cleanup carefully.
        # For this exercise, we assume db_manager.initialize_database() sets up the necessary tables
        # and we will manually add/delete users for each test to maintain independence.
        init_schema.initialize_database() # Correctly call initialize_database
        # It's good practice to ensure the Users table is clean before auth tests,
        # but db.py doesn't have a 'delete_all_users' function.
        # We will rely on specific user deletion in each test.

    def tearDown(self):
        """
        Clean up after tests if necessary.
        For example, delete the test database file if a separate one was used.
        Or, ensure all test users are deleted.
        """
        # If using a dedicated test database file, os.remove(db_manager.DATABASE_NAME) could go here.
        # For now, cleanup is handled within tests.
        pass

    def test_successful_registration(self):
        """Test that a new user can be added successfully."""
        user_data = {
            'username': 'testuser_succ_reg',
            'email': 'succ_reg@example.com',
            'password': 'password123',
            'full_name': 'Test User Success',
            'role': 'member'
        }
        user_id = db_manager.add_user(user_data)
        self.assertIsNotNone(user_id, "add_user should return a user_id on successful registration.")

        # Optional: Fetch and verify
        fetched_user = db_manager.get_user_by_id(user_id)
        self.assertIsNotNone(fetched_user)
        self.assertEqual(fetched_user['username'], user_data['username'])
        self.assertEqual(fetched_user['email'], user_data['email'])

        # Cleanup
        if user_id:
            deleted = db_manager.delete_user(user_id)
            self.assertTrue(deleted, "Failed to delete user after successful registration test.")

    def test_registration_existing_username(self):
        """Test that registration fails if the username already exists."""
        user_data1 = {
            'username': 'existinguser',
            'email': 'email1@example.com',
            'password': 'password123',
            'full_name': 'Existing User',
            'role': 'member'
        }
        user_id1 = db_manager.add_user(user_data1)
        self.assertIsNotNone(user_id1, "Setup: Failed to add initial user for existing username test.")

        user_data2 = {
            'username': 'existinguser', # Same username
            'email': 'email2@example.com', # Different email
            'password': 'password456',
            'full_name': 'Another User',
            'role': 'member'
        }
        user_id2 = db_manager.add_user(user_data2)
        self.assertIsNone(user_id2, "add_user should return None when username already exists.")

        # Cleanup
        if user_id1:
            deleted = db_manager.delete_user(user_id1)
            self.assertTrue(deleted, "Failed to delete user after existing username test.")

    def test_registration_existing_email(self):
        """Test that registration fails if the email already exists."""
        user_data1 = {
            'username': 'user_email_test1',
            'email': 'existingemail@example.com',
            'password': 'password123',
            'full_name': 'User Email Test',
            'role': 'member'
        }
        user_id1 = db_manager.add_user(user_data1)
        self.assertIsNotNone(user_id1, "Setup: Failed to add initial user for existing email test.")

        user_data2 = {
            'username': 'user_email_test2', # Different username
            'email': 'existingemail@example.com', # Same email
            'password': 'password456',
            'full_name': 'Another User Email Test',
            'role': 'member'
        }
        user_id2 = db_manager.add_user(user_data2)
        self.assertIsNone(user_id2, "add_user should return None when email already exists.")

        # Cleanup
        if user_id1:
            deleted = db_manager.delete_user(user_id1)
            self.assertTrue(deleted, "Failed to delete user after existing email test.")

    def test_successful_login(self):
        """Test that a user can log in with correct credentials."""
        username = 'logintestuser'
        password = 'loginpassword'
        user_data = {
            'username': username,
            'email': 'login@example.com',
            'password': password,
            'full_name': 'Login Test User',
            'role': 'member'
        }
        user_id = db_manager.add_user(user_data)
        self.assertIsNotNone(user_id, "Setup: Failed to add user for successful login test.")

        verified_user = db_manager.verify_user_password(username, password)
        self.assertIsNotNone(verified_user, "verify_user_password should return user data for correct credentials.")
        self.assertEqual(verified_user['username'], username)

        # Cleanup
        if user_id:
            deleted = db_manager.delete_user(user_id)
            self.assertTrue(deleted, "Failed to delete user after successful login test.")

    def test_login_incorrect_password(self):
        """Test that login fails with an incorrect password."""
        username = 'incorrectpasstest'
        correct_password = 'correctpassword'
        incorrect_password = 'wrongpassword'
        user_data = {
            'username': username,
            'email': 'incorrectpass@example.com',
            'password': correct_password,
            'full_name': 'Incorrect Pass Test User',
            'role': 'member'
        }
        user_id = db_manager.add_user(user_data)
        self.assertIsNotNone(user_id, "Setup: Failed to add user for incorrect password test.")

        verified_user = db_manager.verify_user_password(username, incorrect_password)
        self.assertIsNone(verified_user, "verify_user_password should return None for incorrect password.")

        # Cleanup
        if user_id:
            deleted = db_manager.delete_user(user_id)
            self.assertTrue(deleted, "Failed to delete user after incorrect password test.")

    def test_login_non_existent_username(self):
        """Test that login fails with a non-existent username."""
        verified_user = db_manager.verify_user_password('iamnotauser', 'anypassword')
        self.assertIsNone(verified_user, "verify_user_password should return None for a non-existent username.")

    def test_get_user_by_email(self):
        """Test fetching a user by email."""
        email_to_find = 'findme@example.com'
        user_data = {
            'username': 'findbyemailuser',
            'email': email_to_find,
            'password': 'password123',
            'full_name': 'Find By Email User',
            'role': 'member'
        }
        user_id = db_manager.add_user(user_data)
        self.assertIsNotNone(user_id, "Setup: Failed to add user for get_user_by_email test.")

        fetched_user = db_manager.get_user_by_email(email_to_find)
        self.assertIsNotNone(fetched_user, "get_user_by_email should return user data for an existing email.")
        self.assertEqual(fetched_user['username'], user_data['username'])
        self.assertEqual(fetched_user['user_id'], user_id)

        # Test with non-existent email
        fetched_non_existent = db_manager.get_user_by_email('noexist@example.com')
        self.assertIsNone(fetched_non_existent, "get_user_by_email should return None for a non-existent email.")

        # Cleanup
        if user_id:
            deleted = db_manager.delete_user(user_id)
            self.assertTrue(deleted, "Failed to delete user after get_user_by_email test.")


if __name__ == '__main__':
    unittest.main()
