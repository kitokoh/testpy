import unittest
import sqlite3
import uuid
from datetime import datetime, date, timedelta

# Ensure this path is correct based on the project structure.
# If tests/ is at the same level as db/, this should work.
from db.cruds.recruitment_job_openings_crud import add_job_opening

class TestMinimalRecruitmentJobOpeningsCRUD(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()

        cursor.execute("CREATE TABLE Users (user_id TEXT PRIMARY KEY, username TEXT, email TEXT, role TEXT)")
        self.test_user_id = str(uuid.uuid4())
        cursor.execute("INSERT INTO Users (user_id, username, email, role) VALUES (?, ?, ?, ?)",
                       (self.test_user_id, 'testuser', 'user@example.com', 'admin'))

        cursor.execute("CREATE TABLE StatusSettings (status_id INTEGER PRIMARY KEY AUTOINCREMENT, status_name TEXT, status_type TEXT)")
        cursor.execute("INSERT INTO StatusSettings (status_name, status_type) VALUES (?, ?)", ('Open', 'JobOpening'))
        self.test_status_id_open = cursor.lastrowid

        cursor.execute("""
            CREATE TABLE JobOpenings (
                job_opening_id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT,
                status_id INTEGER, department_id INTEGER, created_by_user_id TEXT,
                created_at TIMESTAMP, updated_at TIMESTAMP, closing_date DATE,
                FOREIGN KEY (status_id) REFERENCES StatusSettings (status_id),
                FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id)
            )
        """)
        self.conn.commit()

    def tearDown(self):
        if self.conn:
            self.conn.close()

    def test_simple_add(self):
        job_data = {
            'title': 'Minimal Test Job',
            'status_id': self.test_status_id_open,
            'created_by_user_id': self.test_user_id,
            'closing_date': (datetime.now().date() + timedelta(days=1)).isoformat()
        }
        new_id = add_job_opening(job_data, conn=self.conn)
        self.assertIsNotNone(new_id)
        self.assertTrue(isinstance(new_id, str))

# No if __name__ == '__main__' block
```
