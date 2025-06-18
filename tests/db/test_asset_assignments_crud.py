import unittest
import sqlite3
from datetime import datetime, timezone, timedelta
import uuid
import os
import sys

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db.cruds.asset_assignments_crud import AssetAssignmentsCRUD
from db.cruds.company_assets_crud import CompanyAssetsCRUD
# We will use direct SQL for CompanyPersonnel to avoid pulling in its full dependencies for this test.

class TestAssetAssignmentsCRUD(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        # Create CompanyAssets table (minimal version from CompanyAssetsCRUD tests)
        self.cursor.execute("""
            CREATE TABLE CompanyAssets (
                asset_id TEXT PRIMARY KEY, asset_name TEXT NOT NULL, asset_type TEXT NOT NULL,
                serial_number TEXT UNIQUE, description TEXT, purchase_date DATE,
                purchase_value REAL, current_status TEXT NOT NULL, notes TEXT,
                created_at TIMESTAMP, updated_at TIMESTAMP,
                is_deleted INTEGER DEFAULT 0, deleted_at TIMESTAMP
            )
        """)

        # Create CompanyPersonnel table (minimal version for FK)
        # Assuming company_id is just a TEXT field for simplicity here, not necessarily FK to a Companies table for this test scope.
        self.cursor.execute("""
            CREATE TABLE CompanyPersonnel (
                personnel_id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                phone TEXT,
                email TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create AssetAssignments table
        self.cursor.execute("""
            CREATE TABLE AssetAssignments (
                assignment_id TEXT PRIMARY KEY,
                asset_id TEXT NOT NULL,
                personnel_id INTEGER NOT NULL,
                assignment_date TIMESTAMP NOT NULL,
                expected_return_date TIMESTAMP,
                actual_return_date TIMESTAMP,
                assignment_status TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (asset_id) REFERENCES CompanyAssets (asset_id) ON DELETE CASCADE,
                FOREIGN KEY (personnel_id) REFERENCES CompanyPersonnel (personnel_id) ON DELETE RESTRICT
            )
        """)
        self.conn.commit()

        self.assignments_crud = AssetAssignmentsCRUD()
        self.assets_crud = CompanyAssetsCRUD() # To add sample assets for FK

        # Add sample asset
        self.sample_asset_id = self.assets_crud.add_asset({
            "asset_name": "Test Asset for Assignment", "asset_type": "Tool",
            "current_status": "In Stock", "serial_number": f"SN-ASSET-{uuid.uuid4().hex[:6]}"
        }, conn=self.conn)
        self.assertIsNotNone(self.sample_asset_id, "Setup failed: Could not create sample asset.")

        # Add sample personnel using direct SQL
        now_iso = datetime.now(timezone.utc).isoformat()
        self.cursor.execute(
            "INSERT INTO CompanyPersonnel (company_id, name, role, email, created_at) VALUES (?, ?, ?, ?, ?)",
            ("COMP-XYZ", "Test Assignee", "Technician", f"assignee.{uuid.uuid4().hex[:6]}@example.com", now_iso)
        )
        self.sample_personnel_id = self.cursor.lastrowid
        self.conn.commit()
        self.assertIsNotNone(self.sample_personnel_id, "Setup failed: Could not create sample personnel.")


    def tearDown(self):
        self.conn.close()

    def _create_sample_assignment_data(self, **kwargs):
        data = {
            "asset_id": self.sample_asset_id,
            "personnel_id": self.sample_personnel_id,
            "assignment_date": datetime.now(timezone.utc).isoformat(),
            "assignment_status": "Assigned",
            "expected_return_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "notes": "Standard assignment for testing."
        }
        data.update(kwargs)
        return data

    def test_add_assignment_success(self):
        assignment_data = self._create_sample_assignment_data()
        assignment_id = self.assignments_crud.add_assignment(assignment_data, conn=self.conn)

        self.assertIsNotNone(assignment_id)
        self.assertIsInstance(assignment_id, str)

        fetched = self.assignments_crud.get_assignment_by_id(assignment_id, conn=self.conn)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched['asset_id'], self.sample_asset_id)
        self.assertEqual(fetched['personnel_id'], self.sample_personnel_id)
        self.assertEqual(fetched['assignment_status'], assignment_data['assignment_status'])
        self.assertIsNotNone(fetched['created_at'])
        self.assertIsNotNone(fetched['updated_at'])
        self.assertEqual(fetched['created_at'], fetched['updated_at'])

    def test_add_assignment_required_fields(self):
        minimal_data = {"asset_id": self.sample_asset_id, "personnel_id": self.sample_personnel_id,
                        "assignment_date": datetime.now(timezone.utc).isoformat(), "assignment_status": "Status"}

        for field in minimal_data.keys():
            data_copy = minimal_data.copy()
            del data_copy[field]
            assign_id = self.assignments_crud.add_assignment(data_copy, conn=self.conn)
            self.assertIsNone(assign_id, f"Assignment creation should fail if '{field}' is missing.")

    def test_add_assignment_fk_constraints(self):
        # Non-existent asset_id
        data_bad_asset = self._create_sample_assignment_data(asset_id=str(uuid.uuid4()))
        assign_id_bad_asset = self.assignments_crud.add_assignment(data_bad_asset, conn=self.conn)
        self.assertIsNone(assign_id_bad_asset, "Assignment should fail with non-existent asset_id.")

        # Non-existent personnel_id
        # Max personnel_id + some large number to ensure it's non-existent
        non_existent_personnel_id = self.sample_personnel_id + 1000
        data_bad_personnel = self._create_sample_assignment_data(personnel_id=non_existent_personnel_id)
        assign_id_bad_personnel = self.assignments_crud.add_assignment(data_bad_personnel, conn=self.conn)
        self.assertIsNone(assign_id_bad_personnel, "Assignment should fail with non-existent personnel_id.")

    def test_get_assignment_by_id_existing(self):
        assignment_data = self._create_sample_assignment_data()
        assignment_id = self.assignments_crud.add_assignment(assignment_data, conn=self.conn)

        fetched = self.assignments_crud.get_assignment_by_id(assignment_id, conn=self.conn)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched['assignment_id'], assignment_id)

    def test_get_assignment_by_id_non_existent(self):
        non_existent_id = str(uuid.uuid4())
        fetched = self.assignments_crud.get_assignment_by_id(non_existent_id, conn=self.conn)
        self.assertIsNone(fetched)

    def test_get_assignments_for_asset(self):
        assign_data1 = self._create_sample_assignment_data(notes="First assignment for asset")
        self.assignments_crud.add_assignment(assign_data1, conn=self.conn)

        # Create another asset and assign it to ensure we only get assignments for the target asset
        other_asset_id = self.assets_crud.add_asset(self._create_sample_asset_data(asset_name="Other Asset", serial_number="SN-OTHER"), conn=self.conn)
        self.assignments_crud.add_assignment(self._create_sample_assignment_data(asset_id=other_asset_id, notes="Assignment for other asset"), conn=self.conn)

        asset_assignments = self.assignments_crud.get_assignments_for_asset(self.sample_asset_id, conn=self.conn)
        self.assertEqual(len(asset_assignments), 1)
        self.assertEqual(asset_assignments[0]['notes'], "First assignment for asset")

        # Test with status filter
        self.assignments_crud.add_assignment(self._create_sample_assignment_data(assignment_status="Returned", notes="Returned item"), conn=self.conn)

        active_for_asset = self.assignments_crud.get_assignments_for_asset(self.sample_asset_id, filters={"assignment_status": "Assigned"}, conn=self.conn)
        self.assertEqual(len(active_for_asset), 1) # Only the first one with "Assigned" status
        self.assertEqual(active_for_asset[0]['notes'], "First assignment for asset")


    def test_get_assignments_for_asset_no_assignments(self):
        new_asset_id_no_assign = self.assets_crud.add_asset(self._create_sample_asset_data(asset_name="Unassigned Asset", serial_number="SN-UNASSIGN"), conn=self.conn)
        assignments = self.assignments_crud.get_assignments_for_asset(new_asset_id_no_assign, conn=self.conn)
        self.assertEqual(len(assignments), 0)

    def test_get_assignments_for_personnel(self):
        assign_data1 = self._create_sample_assignment_data(notes="First assignment for personnel")
        self.assignments_crud.add_assignment(assign_data1, conn=self.conn)

        # Create another personnel and assign to them
        self.cursor.execute("INSERT INTO CompanyPersonnel (company_id, name, role, email) VALUES (?, ?, ?, ?)",
                            ("COMP-XYZ", "Other Employee", "Manager", f"other.{uuid.uuid4().hex[:6]}@example.com"))
        other_personnel_id = self.cursor.lastrowid
        self.conn.commit()
        self.assignments_crud.add_assignment(self._create_sample_assignment_data(personnel_id=other_personnel_id, notes="Assignment for other personnel"), conn=self.conn)

        personnel_assignments = self.assignments_crud.get_assignments_for_personnel(self.sample_personnel_id, conn=self.conn)
        self.assertEqual(len(personnel_assignments), 1)
        self.assertEqual(personnel_assignments[0]['notes'], "First assignment for personnel")

        # Test with status filter
        self.assignments_crud.add_assignment(self._create_sample_assignment_data(assignment_status="Pending", notes="Pending item for personnel"), conn=self.conn)

        assigned_for_personnel = self.assignments_crud.get_assignments_for_personnel(self.sample_personnel_id, filters={"assignment_status": "Assigned"}, conn=self.conn)
        self.assertEqual(len(assigned_for_personnel), 1)
        self.assertEqual(assigned_for_personnel[0]['notes'], "First assignment for personnel")


    def test_get_assignments_for_personnel_no_assignments(self):
        self.cursor.execute("INSERT INTO CompanyPersonnel (company_id, name, role, email) VALUES (?, ?, ?, ?)",
                            ("COMP-XYZ", "Unassigned Employee", "Intern", f"unassigned.{uuid.uuid4().hex[:6]}@example.com"))
        new_personnel_id_no_assign = self.cursor.lastrowid
        self.conn.commit()
        assignments = self.assignments_crud.get_assignments_for_personnel(new_personnel_id_no_assign, conn=self.conn)
        self.assertEqual(len(assignments), 0)

    def test_get_all_assignments(self):
        self.assignments_crud.add_assignment(self._create_sample_assignment_data(notes="All Assign 1"), conn=self.conn)
        self.assignments_crud.add_assignment(self._create_sample_assignment_data(notes="All Assign 2", asset_id=self.sample_asset_id, personnel_id=self.sample_personnel_id, assignment_status="Returned"), conn=self.conn)

        all_assign = self.assignments_crud.get_all_assignments(conn=self.conn)
        self.assertEqual(len(all_assign), 2)

        # Test with filters
        returned_assign = self.assignments_crud.get_all_assignments(filters={"assignment_status": "Returned"}, conn=self.conn)
        self.assertEqual(len(returned_assign), 1)
        self.assertEqual(returned_assign[0]['notes'], "All Assign 2")

        # Test pagination
        self.assignments_crud.add_assignment(self._create_sample_assignment_data(notes="All Assign 3"), conn=self.conn)
        paginated = self.assignments_crud.get_all_assignments(limit=2, offset=1, conn=self.conn) # Default order is created_at DESC
        self.assertEqual(len(paginated), 2)
        # Check based on insertion order and default DESC order by created_at
        # If 1,2,3 added, order is 3,2,1. Offset 1, limit 2 -> items 2,1
        self.assertTrue(any(a['notes'] == "All Assign 2" for a in paginated))
        self.assertTrue(any(a['notes'] == "All Assign 1" for a in paginated))


    def test_update_assignment_success(self):
        assignment_id = self.assignments_crud.add_assignment(self._create_sample_assignment_data(), conn=self.conn)
        original_assignment = self.assignments_crud.get_assignment_by_id(assignment_id, conn=self.conn)
        original_updated_at = datetime.fromisoformat(original_assignment['updated_at'].replace('Z', '+00:00'))

        update_payload = {
            "assignment_status": "Returned",
            "actual_return_date": datetime.now(timezone.utc).isoformat(),
            "notes": "Asset returned by user."
        }
        updated = self.assignments_crud.update_assignment(assignment_id, update_payload, conn=self.conn)
        self.assertTrue(updated)

        fetched_updated = self.assignments_crud.get_assignment_by_id(assignment_id, conn=self.conn)
        self.assertEqual(fetched_updated['assignment_status'], "Returned")
        self.assertEqual(fetched_updated['notes'], "Asset returned by user.")
        self.assertIsNotNone(fetched_updated['actual_return_date'])

        new_updated_at = datetime.fromisoformat(fetched_updated['updated_at'].replace('Z', '+00:00'))
        self.assertGreater(new_updated_at, original_updated_at)

    def test_update_assignment_non_existent(self):
        non_existent_id = str(uuid.uuid4())
        updated = self.assignments_crud.update_assignment(non_existent_id, {"notes": "No such assignment"}, conn=self.conn)
        self.assertFalse(updated)

    def test_delete_assignment_success(self): # Hard delete
        assignment_id = self.assignments_crud.add_assignment(self._create_sample_assignment_data(), conn=self.conn)
        self.assertIsNotNone(self.assignments_crud.get_assignment_by_id(assignment_id, conn=self.conn), "Assignment should exist before delete.")

        deleted = self.assignments_crud.delete_assignment(assignment_id, conn=self.conn)
        self.assertTrue(deleted)

        fetched_after_delete = self.assignments_crud.get_assignment_by_id(assignment_id, conn=self.conn)
        self.assertIsNone(fetched_after_delete, "Assignment should be hard deleted.")

    def test_delete_assignment_non_existent(self):
        non_existent_id = str(uuid.uuid4())
        deleted = self.assignments_crud.delete_assignment(non_existent_id, conn=self.conn)
        self.assertFalse(deleted)

if __name__ == '__main__':
    unittest.main()
