import unittest
import sqlite3
import sys
import os
from datetime import datetime
import time # For slight delay in timestamp checks

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from db.cruds.users_crud import UsersCRUD

class TestUsersCRUD(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        self.cursor.execute("""
            CREATE TABLE Users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                full_name TEXT,
                email TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT
            )
        """)
        self.conn.commit()

        self.users_crud = UsersCRUD()

        self.user_data1 = {
            'username': 'testuser1',
            'password': 'Password123!',
            'email': 'test1@example.com',
            'role': 'user',
            'full_name': 'Test User One'
        }
        self.user_data2 = {
            'username': 'testuser2',
            'password': 'AnotherPassword321!',
            'email': 'test2@example.com',
            'role': 'admin',
            'full_name': 'Test User Two'
        }

    def tearDown(self):
        self.conn.close()

    def _add_user_get_id(self, user_data):
        res = self.users_crud.add_user(user_data, conn=self.conn)
        self.assertTrue(res['success'], f"Failed to add user: {res.get('error')}")
        self.assertIsNotNone(res.get('id'))
        return res['id']

    def test_add_user_success(self):
        res = self.users_crud.add_user(self.user_data1, conn=self.conn)
        self.assertTrue(res['success'])
        user_id = res['id']

        db_user = self.cursor.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,)).fetchone()
        self.assertIsNotNone(db_user)
        self.assertEqual(db_user['username'], self.user_data1['username'])
        self.assertNotEqual(db_user['password_hash'], self.user_data1['password'])
        self.assertTrue(len(db_user['salt']) > 0)
        self.assertEqual(db_user['is_deleted'], 0)

    def test_add_user_username_exists(self):
        self._add_user_get_id(self.user_data1)
        invalid_data = self.user_data2.copy()
        invalid_data['username'] = self.user_data1['username']
        res = self.users_crud.add_user(invalid_data, conn=self.conn)
        self.assertFalse(res['success'])
        self.assertIn("Username already exists", res['error'])

    def test_add_user_email_exists(self):
        self._add_user_get_id(self.user_data1)
        invalid_data = self.user_data2.copy()
        invalid_data['email'] = self.user_data1['email']
        res = self.users_crud.add_user(invalid_data, conn=self.conn)
        self.assertFalse(res['success'])
        self.assertIn("Email already exists", res['error'])

    def test_add_user_missing_fields(self):
        res = self.users_crud.add_user({'username': 'u', 'password': 'p', 'role': 'r'}, conn=self.conn) # Missing email
        self.assertFalse(res['success'])
        self.assertIn("Missing required field: email", res['error'])

    def test_add_user_invalid_email(self):
        invalid_data = self.user_data1.copy()
        invalid_data['email'] = "not-an-email"
        res = self.users_crud.add_user(invalid_data, conn=self.conn)
        self.assertFalse(res['success'])
        self.assertIn("Invalid email format", res['error'])

    def test_add_user_weak_password(self):
        invalid_data = self.user_data1.copy()
        invalid_data['password'] = "short"
        res = self.users_crud.add_user(invalid_data, conn=self.conn)
        self.assertFalse(res['success'])
        self.assertIn("Password must be at least 8 characters long", res['error'])

    def test_get_user_by_id(self):
        user_id = self._add_user_get_id(self.user_data1)
        user = self.users_crud.get_user_by_id(user_id, conn=self.conn)
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], self.user_data1['username'])
        # By default, get_by_id from GenericCRUD returns all fields.
        # For UsersCRUD, we might want to refine this or have specific methods.
        self.assertIn('password_hash', user)
        self.assertIn('salt', user)

    def test_get_user_by_username_masks_sensitive_data(self):
        self._add_user_get_id(self.user_data1)
        user = self.users_crud.get_user_by_username(self.user_data1['username'], conn=self.conn)
        self.assertIsNotNone(user)
        self.assertNotIn('password_hash', user)
        self.assertNotIn('salt', user)

    def test_soft_delete_user(self):
        user_id = self._add_user_get_id(self.user_data1)
        res = self.users_crud.delete_user(user_id, conn=self.conn)
        self.assertTrue(res['success'])

        db_user = self.cursor.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,)).fetchone()
        self.assertEqual(db_user['is_deleted'], 1)
        self.assertEqual(db_user['is_active'], 0)
        self.assertIsNotNone(db_user['deleted_at'])

        self.assertIsNone(self.users_crud.get_user_by_id(user_id, conn=self.conn))
        self.assertIsNotNone(self.users_crud.get_user_by_id(user_id, conn=self.conn, include_deleted=True))

    def test_verify_user_password_correct(self):
        user_id = self._add_user_get_id(self.user_data1)
        db_user_before_login = dict(self.cursor.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,)).fetchone())

        # Ensure slight time difference for last_login_at
        time.sleep(0.01)

        verified_user = self.users_crud.verify_user_password(self.user_data1['username'], self.user_data1['password'], conn=self.conn)
        self.assertIsNotNone(verified_user)
        self.assertEqual(verified_user['username'], self.user_data1['username'])
        self.assertNotIn('password_hash', verified_user)
        self.assertNotIn('salt', verified_user)

        db_user_after_login = dict(self.cursor.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,)).fetchone())
        self.assertIsNotNone(db_user_after_login['last_login_at'])
        if db_user_before_login.get('last_login_at'):
             self.assertNotEqual(db_user_before_login['last_login_at'], db_user_after_login['last_login_at'])


    def test_verify_user_password_incorrect(self):
        self._add_user_get_id(self.user_data1)
        verified_user = self.users_crud.verify_user_password(self.user_data1['username'], "WrongPassword!", conn=self.conn)
        self.assertIsNone(verified_user)

    def test_verify_user_password_inactive_user(self):
        user_id = self._add_user_get_id(self.user_data1)
        self.users_crud.update_user(user_id, {'is_active': 0}, conn=self.conn)
        verified_user = self.users_crud.verify_user_password(self.user_data1['username'], self.user_data1['password'], conn=self.conn)
        self.assertIsNone(verified_user)

    def test_verify_user_password_soft_deleted_user(self):
        user_id = self._add_user_get_id(self.user_data1)
        self.users_crud.delete_user(user_id, conn=self.conn) # Soft deletes and deactivates
        verified_user = self.users_crud.verify_user_password(self.user_data1['username'], self.user_data1['password'], conn=self.conn)
        self.assertIsNone(verified_user)

    def test_update_user_password(self):
        user_id = self._add_user_get_id(self.user_data1)
        original_user = dict(self.cursor.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,)).fetchone())

        new_password = "NewSecurePassword456$"
        update_res = self.users_crud.update_user(user_id, {'password': new_password}, conn=self.conn)
        self.assertTrue(update_res['success'])

        updated_user = dict(self.cursor.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,)).fetchone())
        self.assertNotEqual(original_user['password_hash'], updated_user['password_hash'])
        self.assertNotEqual(original_user['salt'], updated_user['salt'])

        # Verify login with new password
        verified_user = self.users_crud.verify_user_password(self.user_data1['username'], new_password, conn=self.conn)
        self.assertIsNotNone(verified_user)

        # Verify login with old password fails
        verified_user_old_pass = self.users_crud.verify_user_password(self.user_data1['username'], self.user_data1['password'], conn=self.conn)
        self.assertIsNone(verified_user_old_pass)

    def test_get_all_users(self):
        self._add_user_get_id(self.user_data1)
        self._add_user_get_id(self.user_data2)

        all_users = self.users_crud.get_all_users(conn=self.conn)
        self.assertEqual(len(all_users), 2)
        for user in all_users: # Check masking
            self.assertNotIn('password_hash', user)
            self.assertNotIn('salt', user)

        # Test pagination
        paginated_users = self.users_crud.get_all_users(conn=self.conn, limit=1, offset=0)
        self.assertEqual(len(paginated_users), 1)
        # Assuming order by username: testuser1, testuser2
        self.assertEqual(paginated_users[0]['username'], self.user_data1['username'])


        # Test soft delete filtering
        user1_id = self.cursor.execute("SELECT user_id FROM Users WHERE username = ?", (self.user_data1['username'],)).fetchone()['user_id']
        self.users_crud.delete_user(user1_id, conn=self.conn)

        active_users = self.users_crud.get_all_users(conn=self.conn)
        self.assertEqual(len(active_users), 1)
        self.assertEqual(active_users[0]['username'], self.user_data2['username'])

        all_users_incl_deleted = self.users_crud.get_all_users(conn=self.conn, include_deleted=True)
        self.assertEqual(len(all_users_incl_deleted), 2)

if __name__ == '__main__':
    unittest.main()
