import unittest
import sqlite3
from datetime import datetime, timezone, timedelta
import uuid
import os
import sys

# Add project root to sys.path to allow imports from db.cruds
# This assumes the tests are run from the project root or tests directory.
# Adjust if your test runner handles paths differently.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db.cruds.company_assets_crud import CompanyAssetsCRUD

class TestCompanyAssetsCRUD(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        # Minimal schema for CompanyAssets table, matching the one in init_schema.py
        self.cursor.execute("""
            CREATE TABLE CompanyAssets (
                asset_id TEXT PRIMARY KEY,
                asset_name TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                serial_number TEXT UNIQUE,
                description TEXT,
                purchase_date DATE,
                purchase_value REAL,
                current_status TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TIMESTAMP
            )
        """)
        # Add required indexes if their absence could affect test logic (e.g., unique constraints beyond just serial_number)
        # For CompanyAssets, serial_number UNIQUE is the main one defined in the table DDL.
        self.conn.commit()
        # Instantiate the CRUD class for testing, it will use its default db_path unless one is provided
        # For these unit tests, we explicitly pass the connection to each method.
        self.assets_crud = CompanyAssetsCRUD()
        # Note: The CompanyAssetsCRUD instance itself doesn't store the conn.
        # We must pass self.conn to each method call.

    def tearDown(self):
        self.conn.close()

    def _create_sample_asset_data(self, **kwargs):
        """Helper to create sample asset data, allowing overrides."""
        data = {
            "asset_name": "Test Laptop",
            "asset_type": "Electronics",
            "serial_number": f"SN{uuid.uuid4().hex[:10]}", # Ensure unique serial for most tests
            "current_status": "In Stock",
            "description": "A standard test laptop.",
            "purchase_date": "2023-01-15",
            "purchase_value": 1200.50,
            "notes": "Initial stock entry."
        }
        data.update(kwargs)
        return data

    def test_add_asset_success(self):
        asset_data = self._create_sample_asset_data()
        asset_id = self.assets_crud.add_asset(asset_data, conn=self.conn)

        self.assertIsNotNone(asset_id)
        self.assertIsInstance(asset_id, str)

        fetched = self.assets_crud.get_asset_by_id(asset_id, conn=self.conn)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched['asset_name'], asset_data['asset_name'])
        self.assertEqual(fetched['serial_number'], asset_data['serial_number'])
        self.assertEqual(fetched['is_deleted'], 0)
        self.assertIsNotNone(fetched['created_at'])
        self.assertIsNotNone(fetched['updated_at'])
        self.assertEqual(fetched['created_at'], fetched['updated_at']) # On creation, they should be same

    def test_add_asset_required_fields(self):
        # Missing asset_name
        asset_data_no_name = {"asset_type": "Type", "current_status": "Status"}
        asset_id_no_name = self.assets_crud.add_asset(asset_data_no_name, conn=self.conn)
        self.assertIsNone(asset_id_no_name, "Asset creation should fail if asset_name is missing.")

        # Missing asset_type
        asset_data_no_type = {"asset_name": "Name", "current_status": "Status"}
        asset_id_no_type = self.assets_crud.add_asset(asset_data_no_type, conn=self.conn)
        self.assertIsNone(asset_id_no_type, "Asset creation should fail if asset_type is missing.")

        # Missing current_status
        asset_data_no_status = {"asset_name": "Name", "asset_type": "Type"}
        asset_id_no_status = self.assets_crud.add_asset(asset_data_no_status, conn=self.conn)
        self.assertIsNone(asset_id_no_status, "Asset creation should fail if current_status is missing.")

    def test_add_asset_unique_serial_number(self):
        common_serial = f"SN-UNIQUE-{uuid.uuid4().hex[:6]}"
        asset_data1 = self._create_sample_asset_data(serial_number=common_serial)
        asset_id1 = self.assets_crud.add_asset(asset_data1, conn=self.conn)
        self.assertIsNotNone(asset_id1)

        asset_data2 = self._create_sample_asset_data(serial_number=common_serial, asset_name="Another Laptop")
        # Expecting add_asset to return None or raise IntegrityError if serial is duplicate.
        # The current CRUD implementation catches IntegrityError and returns None.
        asset_id2 = self.assets_crud.add_asset(asset_data2, conn=self.conn)
        self.assertIsNone(asset_id2, "Asset creation should fail due to duplicate serial number.")

    def test_get_asset_by_id_existing(self):
        asset_data = self._create_sample_asset_data()
        asset_id = self.assets_crud.add_asset(asset_data, conn=self.conn)

        fetched = self.assets_crud.get_asset_by_id(asset_id, conn=self.conn)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched['asset_id'], asset_id)
        self.assertEqual(fetched['asset_name'], asset_data['asset_name'])

    def test_get_asset_by_id_non_existent(self):
        non_existent_id = str(uuid.uuid4())
        fetched = self.assets_crud.get_asset_by_id(non_existent_id, conn=self.conn)
        self.assertIsNone(fetched)

    def test_get_asset_by_id_soft_deleted(self):
        asset_data = self._create_sample_asset_data()
        asset_id = self.assets_crud.add_asset(asset_data, conn=self.conn)
        self.assets_crud.delete_asset(asset_id, conn=self.conn) # Soft delete

        # Test include_deleted=False (default)
        fetched_not_deleted = self.assets_crud.get_asset_by_id(asset_id, conn=self.conn)
        self.assertIsNone(fetched_not_deleted, "Should not return soft-deleted asset by default.")

        # Test include_deleted=True
        fetched_deleted = self.assets_crud.get_asset_by_id(asset_id, include_deleted=True, conn=self.conn)
        self.assertIsNotNone(fetched_deleted)
        self.assertEqual(fetched_deleted['asset_id'], asset_id)
        self.assertEqual(fetched_deleted['is_deleted'], 1)

    def test_get_assets_basic(self):
        asset_data1 = self._create_sample_asset_data(asset_name="Laptop A")
        asset_data2 = self._create_sample_asset_data(asset_name="Laptop B", serial_number="SN-B")
        self.assets_crud.add_asset(asset_data1, conn=self.conn)
        self.assets_crud.add_asset(asset_data2, conn=self.conn)

        all_assets = self.assets_crud.get_assets(conn=self.conn)
        self.assertEqual(len(all_assets), 2)

    def test_get_assets_filtering(self):
        asset_data_laptop = self._create_sample_asset_data(asset_type="Laptop", current_status="In Use", serial_number="SN-LAP")
        asset_data_monitor = self._create_sample_asset_data(asset_type="Monitor", current_status="In Stock", serial_number="SN-MON")
        self.assets_crud.add_asset(asset_data_laptop, conn=self.conn)
        self.assets_crud.add_asset(asset_data_monitor, conn=self.conn)

        # Filter by asset_type
        laptops = self.assets_crud.get_assets(filters={"asset_type": "Laptop"}, conn=self.conn)
        self.assertEqual(len(laptops), 1)
        self.assertEqual(laptops[0]['asset_name'], asset_data_laptop['asset_name'])

        # Filter by current_status
        in_stock_assets = self.assets_crud.get_assets(filters={"current_status": "In Stock"}, conn=self.conn)
        self.assertEqual(len(in_stock_assets), 1)
        self.assertEqual(in_stock_assets[0]['asset_name'], asset_data_monitor['asset_name'])

        # Filter by serial_number
        specific_sn_asset = self.assets_crud.get_assets(filters={"serial_number": "SN-LAP"}, conn=self.conn)
        self.assertEqual(len(specific_sn_asset), 1)
        self.assertEqual(specific_sn_asset[0]['asset_name'], asset_data_laptop['asset_name'])

    def test_get_assets_include_deleted(self):
        asset_data1 = self._create_sample_asset_data(asset_name="Active Asset")
        asset_id1 = self.assets_crud.add_asset(asset_data1, conn=self.conn)

        asset_data2 = self._create_sample_asset_data(asset_name="Deleted Asset", serial_number="SN-DEL")
        asset_id2 = self.assets_crud.add_asset(asset_data2, conn=self.conn)
        self.assets_crud.delete_asset(asset_id2, conn=self.conn) # Soft delete

        # Default (include_deleted=False)
        active_assets = self.assets_crud.get_assets(conn=self.conn)
        self.assertEqual(len(active_assets), 1)
        self.assertEqual(active_assets[0]['asset_id'], asset_id1)

        # include_deleted=True
        all_assets_including_deleted = self.assets_crud.get_assets(include_deleted=True, conn=self.conn)
        self.assertEqual(len(all_assets_including_deleted), 2)

    def test_get_assets_pagination(self):
        for i in range(5):
            self.assets_crud.add_asset(self._create_sample_asset_data(asset_name=f"Asset {i}", serial_number=f"SN-PAG{i}"), conn=self.conn)

        # Limit
        limited_assets = self.assets_crud.get_assets(limit=2, conn=self.conn)
        self.assertEqual(len(limited_assets), 2)

        # Offset
        offset_assets = self.assets_crud.get_assets(limit=2, offset=2, conn=self.conn) # Assets 2, 3 (0-indexed)
        self.assertEqual(len(offset_assets), 2)
        # Names depend on default ordering (created_at DESC in CRUD)
        # So, Asset 2 and Asset 1 if 0,1,2,3,4 were added in order.
        self.assertTrue(any(a['asset_name'] == "Asset 2" for a in offset_assets))
        self.assertTrue(any(a['asset_name'] == "Asset 1" for a in offset_assets))


    def test_update_asset_success(self):
        asset_data = self._create_sample_asset_data()
        asset_id = self.assets_crud.add_asset(asset_data, conn=self.conn)

        original_asset = self.assets_crud.get_asset_by_id(asset_id, conn=self.conn)
        original_updated_at = datetime.fromisoformat(original_asset['updated_at'].replace('Z', '+00:00'))


        # Make sure there's a slight delay for updated_at to change meaningfully
        # In a real scenario, this might not be needed if operations are slower,
        # but for fast in-memory tests, it can be.
        # However, the CRUD sets updated_at to a new `now`, so it should differ.
        # If tests run extremely fast, time resolution might be an issue.
        # Forcing a small delay or ensuring the test logic doesn't rely on microsecond differences.

        update_payload = {"asset_name": "Updated Laptop Name", "current_status": "In Repair"}
        updated = self.assets_crud.update_asset(asset_id, update_payload, conn=self.conn)
        self.assertTrue(updated)

        fetched_updated = self.assets_crud.get_asset_by_id(asset_id, conn=self.conn)
        self.assertEqual(fetched_updated['asset_name'], "Updated Laptop Name")
        self.assertEqual(fetched_updated['current_status'], "In Repair")

        new_updated_at = datetime.fromisoformat(fetched_updated['updated_at'].replace('Z', '+00:00'))
        self.assertGreater(new_updated_at, original_updated_at, "updated_at should be more recent after update.")


    def test_update_asset_non_existent(self):
        non_existent_id = str(uuid.uuid4())
        updated = self.assets_crud.update_asset(non_existent_id, {"asset_name": "No Such Asset"}, conn=self.conn)
        self.assertFalse(updated)

    def test_update_asset_soft_delete(self):
        asset_data = self._create_sample_asset_data()
        asset_id = self.assets_crud.add_asset(asset_data, conn=self.conn)

        update_payload = {"is_deleted": 1} # deleted_at should be set by CRUD
        updated = self.assets_crud.update_asset(asset_id, update_payload, conn=self.conn)
        self.assertTrue(updated)

        fetched_deleted = self.assets_crud.get_asset_by_id(asset_id, include_deleted=True, conn=self.conn)
        self.assertEqual(fetched_deleted['is_deleted'], 1)
        self.assertIsNotNone(fetched_deleted['deleted_at'])

    def test_update_asset_restore_soft_deleted(self):
        asset_data = self._create_sample_asset_data()
        asset_id = self.assets_crud.add_asset(asset_data, conn=self.conn)
        self.assets_crud.update_asset(asset_id, {"is_deleted": 1}, conn=self.conn) # Soft delete

        update_payload = {"is_deleted": 0, "current_status": "Restored from Deletion"} # deleted_at should be set to None by CRUD
        updated = self.assets_crud.update_asset(asset_id, update_payload, conn=self.conn)
        self.assertTrue(updated)

        fetched_restored = self.assets_crud.get_asset_by_id(asset_id, conn=self.conn)
        self.assertIsNotNone(fetched_restored)
        self.assertEqual(fetched_restored['is_deleted'], 0)
        self.assertIsNone(fetched_restored['deleted_at'])
        self.assertEqual(fetched_restored['current_status'], "Restored from Deletion")

    def test_delete_asset_success(self): # Tests soft delete specifically
        asset_data = self._create_sample_asset_data()
        asset_id = self.assets_crud.add_asset(asset_data, conn=self.conn)

        deleted = self.assets_crud.delete_asset(asset_id, conn=self.conn)
        self.assertTrue(deleted)

        fetched_soft_deleted = self.assets_crud.get_asset_by_id(asset_id, include_deleted=True, conn=self.conn)
        self.assertIsNotNone(fetched_soft_deleted)
        self.assertEqual(fetched_soft_deleted['is_deleted'], 1)
        self.assertIsNotNone(fetched_soft_deleted['deleted_at'])

        # Verify it's not returned by default get
        fetched_active = self.assets_crud.get_asset_by_id(asset_id, conn=self.conn)
        self.assertIsNone(fetched_active)

    def test_delete_asset_non_existent(self):
        non_existent_id = str(uuid.uuid4())
        deleted = self.assets_crud.delete_asset(non_existent_id, conn=self.conn)
        self.assertFalse(deleted)

if __name__ == '__main__':
    unittest.main()
