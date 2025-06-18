import unittest
import sqlite3
from datetime import datetime, timezone
import uuid
import json
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db.cruds.asset_media_links_crud import AssetMediaLinksCRUD
from db.cruds.company_assets_crud import CompanyAssetsCRUD

class TestAssetMediaLinksCRUD(unittest.TestCase):

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        # Create CompanyAssets table
        self.cursor.execute("""
            CREATE TABLE CompanyAssets (
                asset_id TEXT PRIMARY KEY, asset_name TEXT NOT NULL, asset_type TEXT NOT NULL,
                serial_number TEXT UNIQUE, description TEXT, purchase_date DATE,
                purchase_value REAL, current_status TEXT NOT NULL, notes TEXT,
                created_at TIMESTAMP, updated_at TIMESTAMP,
                is_deleted INTEGER DEFAULT 0, deleted_at TIMESTAMP
            )
        """)
        # Create MediaItems table
        self.cursor.execute("""
            CREATE TABLE MediaItems (
                media_item_id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT,
                item_type TEXT NOT NULL, filepath TEXT, url TEXT,
                uploader_user_id TEXT, thumbnail_path TEXT, metadata_json TEXT,
                created_at TIMESTAMP, updated_at TIMESTAMP
            )
        """)
        # Create AssetMediaLinks table
        self.cursor.execute("""
            CREATE TABLE AssetMediaLinks (
                link_id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_id TEXT NOT NULL,
                media_item_id TEXT NOT NULL,
                display_order INTEGER DEFAULT 0,
                alt_text TEXT,
                created_at TIMESTAMP,
                FOREIGN KEY (asset_id) REFERENCES CompanyAssets (asset_id) ON DELETE CASCADE,
                FOREIGN KEY (media_item_id) REFERENCES MediaItems (media_item_id) ON DELETE CASCADE,
                UNIQUE (asset_id, media_item_id),
                UNIQUE (asset_id, display_order)
            )
        """)
        self.conn.commit()

        self.media_links_crud = AssetMediaLinksCRUD()
        self.assets_crud = CompanyAssetsCRUD()

        # Add sample asset
        self.sample_asset_id = self.assets_crud.add_asset({
            "asset_name": "Test Asset for Media", "asset_type": "Equipment",
            "current_status": "In Use", "serial_number": f"SN-MEDIA-{uuid.uuid4().hex[:4]}"
        }, conn=self.conn)
        self.assertIsNotNone(self.sample_asset_id, "Setup: Failed to create sample asset")


        # Add sample media items (direct insert for simplicity)
        now_iso = datetime.now(timezone.utc).isoformat()
        self.sample_media_item_id_1 = str(uuid.uuid4())
        self.cursor.execute(
            "INSERT INTO MediaItems (media_item_id, title, item_type, uploader_user_id, created_at, updated_at, thumbnail_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.sample_media_item_id_1, "Test Media 1 (Image)", "image", "user1", now_iso, now_iso, "/thumb/img1.jpg")
        )
        self.sample_media_item_id_2 = str(uuid.uuid4())
        self.cursor.execute(
            "INSERT INTO MediaItems (media_item_id, title, item_type, uploader_user_id, created_at, updated_at, thumbnail_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.sample_media_item_id_2, "Test Media 2 (Video)", "video", "user2", now_iso, now_iso, "/thumb/vid2.jpg")
        )
        self.sample_media_item_id_3 = str(uuid.uuid4()) # Unlinked media item
        self.cursor.execute(
            "INSERT INTO MediaItems (media_item_id, title, item_type, uploader_user_id, created_at, updated_at, thumbnail_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.sample_media_item_id_3, "Test Media 3 (Doc)", "document", "user3", now_iso, now_iso, "/thumb/doc3.jpg")
        )
        self.conn.commit()


    def tearDown(self):
        self.conn.close()

    def test_link_media_to_asset_success(self):
        link_id = self.media_links_crud.link_media_to_asset(
            self.sample_asset_id, self.sample_media_item_id_1, 0, "Alt text 1", conn=self.conn
        )
        self.assertIsNotNone(link_id)

        fetched = self.media_links_crud.get_media_link_by_link_id(link_id, conn=self.conn)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched['asset_id'], self.sample_asset_id)
        self.assertEqual(fetched['media_item_id'], self.sample_media_item_id_1)
        self.assertEqual(fetched['display_order'], 0)
        self.assertEqual(fetched['alt_text'], "Alt text 1")
        self.assertIsNotNone(fetched['created_at'])

    def test_link_media_to_asset_fk_constraints(self):
        # Non-existent asset_id
        link_id_bad_asset = self.media_links_crud.link_media_to_asset(
            str(uuid.uuid4()), self.sample_media_item_id_1, conn=self.conn
        )
        self.assertIsNone(link_id_bad_asset, "Linking should fail with non-existent asset_id.")

        # Non-existent media_item_id
        link_id_bad_media = self.media_links_crud.link_media_to_asset(
            self.sample_asset_id, str(uuid.uuid4()), conn=self.conn
        )
        self.assertIsNone(link_id_bad_media, "Linking should fail with non-existent media_item_id.")

    def test_link_media_to_asset_unique_constraints(self):
        # Link 1 (asset_id, media_item_id)
        self.media_links_crud.link_media_to_asset(
            self.sample_asset_id, self.sample_media_item_id_1, 0, conn=self.conn
        )
        # Attempt duplicate (asset_id, media_item_id)
        link_id_dup_pair = self.media_links_crud.link_media_to_asset(
            self.sample_asset_id, self.sample_media_item_id_1, 1, conn=self.conn # Different display_order
        )
        self.assertIsNone(link_id_dup_pair, "Linking should fail for duplicate (asset_id, media_item_id) pair.")

        # Link 2 (asset_id, display_order) - using a different media item
        self.media_links_crud.link_media_to_asset(
             self.sample_asset_id, self.sample_media_item_id_2, 0, conn=self.conn # Same display_order as first link, but different media
        )
        # This should fail because (asset_id, display_order) must be unique.
        # The previous link was (sample_asset_id, sample_media_item_id_1, 0)
        # This new link is (sample_asset_id, sample_media_item_id_2, 0)
        # The unique constraint on (asset_id, display_order) should catch this.
        link_id_dup_order = self.media_links_crud.link_media_to_asset(
            self.sample_asset_id, self.sample_media_item_id_2, 0, conn=self.conn
        )
        self.assertIsNone(link_id_dup_order, "Linking should fail for duplicate (asset_id, display_order) pair.")


    def test_get_media_links_for_asset(self):
        self.media_links_crud.link_media_to_asset(self.sample_asset_id, self.sample_media_item_id_2, 1, "Video", conn=self.conn)
        self.media_links_crud.link_media_to_asset(self.sample_asset_id, self.sample_media_item_id_1, 0, "Image", conn=self.conn)

        links = self.media_links_crud.get_media_links_for_asset(self.sample_asset_id, conn=self.conn)
        self.assertEqual(len(links), 2)
        # Check order (display_order ASC)
        self.assertEqual(links[0]['media_item_id'], self.sample_media_item_id_1)
        self.assertEqual(links[0]['display_order'], 0)
        self.assertEqual(links[0]['media_title'], "Test Media 1 (Image)") # Check joined data
        self.assertEqual(links[0]['media_item_type'], "image")
        self.assertEqual(links[0]['media_thumbnail_path'], "/thumb/img1.jpg")

        self.assertEqual(links[1]['media_item_id'], self.sample_media_item_id_2)
        self.assertEqual(links[1]['display_order'], 1)
        self.assertEqual(links[1]['media_title'], "Test Media 2 (Video)")
        self.assertEqual(links[1]['media_item_type'], "video")


    def test_get_media_links_for_asset_no_links(self):
        new_asset_id_no_links = self.assets_crud.add_asset(
            {"asset_name": "No Media Asset", "asset_type": "Fixture", "current_status": "Installed", "serial_number": f"SN-NOLINK-{uuid.uuid4().hex[:4]}"}, conn=self.conn
        )
        links = self.media_links_crud.get_media_links_for_asset(new_asset_id_no_links, conn=self.conn)
        self.assertEqual(len(links), 0)

    def test_get_media_link_by_ids(self):
        self.media_links_crud.link_media_to_asset(self.sample_asset_id, self.sample_media_item_id_1, conn=self.conn)
        link = self.media_links_crud.get_media_link_by_ids(self.sample_asset_id, self.sample_media_item_id_1, conn=self.conn)
        self.assertIsNotNone(link)
        self.assertEqual(link['asset_id'], self.sample_asset_id)
        self.assertEqual(link['media_item_id'], self.sample_media_item_id_1)

    def test_get_media_link_by_link_id(self):
        link_id = self.media_links_crud.link_media_to_asset(self.sample_asset_id, self.sample_media_item_id_1, conn=self.conn)
        link = self.media_links_crud.get_media_link_by_link_id(link_id, conn=self.conn)
        self.assertIsNotNone(link)
        self.assertEqual(link['link_id'], link_id)

    def test_update_media_link(self):
        link_id = self.media_links_crud.link_media_to_asset(self.sample_asset_id, self.sample_media_item_id_1, 0, "Old Alt", conn=self.conn)

        updated = self.media_links_crud.update_media_link(link_id, display_order=5, alt_text="New Alt", conn=self.conn)
        self.assertTrue(updated)

        fetched = self.media_links_crud.get_media_link_by_link_id(link_id, conn=self.conn)
        self.assertEqual(fetched['display_order'], 5)
        self.assertEqual(fetched['alt_text'], "New Alt")

    def test_update_media_link_non_existent(self):
        updated = self.media_links_crud.update_media_link(99999, display_order=1, conn=self.conn)
        self.assertFalse(updated)

    def test_update_media_link_unique_display_order_conflict(self):
        link_id_1 = self.media_links_crud.link_media_to_asset(self.sample_asset_id, self.sample_media_item_id_1, 0, conn=self.conn)
        link_id_2 = self.media_links_crud.link_media_to_asset(self.sample_asset_id, self.sample_media_item_id_2, 1, conn=self.conn)

        # Try to update link_id_2's display_order to 0, which is already used by link_id_1 for this asset
        with self.assertRaises(sqlite3.IntegrityError): # CRUD's update uses generic self.update which might raise this
             self.media_links_crud.update_media_link(link_id_2, display_order=0, conn=self.conn)

        # Verify it wasn't updated
        link2_data = self.media_links_crud.get_media_link_by_link_id(link_id_2, conn=self.conn)
        self.assertEqual(link2_data['display_order'], 1, "Display order should not have changed on conflict.")


    def test_unlink_media_from_asset(self): # By link_id
        link_id = self.media_links_crud.link_media_to_asset(self.sample_asset_id, self.sample_media_item_id_1, conn=self.conn)
        self.assertIsNotNone(self.media_links_crud.get_media_link_by_link_id(link_id, conn=self.conn))

        unlinked = self.media_links_crud.unlink_media_from_asset(link_id, conn=self.conn)
        self.assertTrue(unlinked)
        self.assertIsNone(self.media_links_crud.get_media_link_by_link_id(link_id, conn=self.conn))

    def test_unlink_media_by_ids(self):
        self.media_links_crud.link_media_to_asset(self.sample_asset_id, self.sample_media_item_id_1, conn=self.conn)
        self.assertIsNotNone(self.media_links_crud.get_media_link_by_ids(self.sample_asset_id, self.sample_media_item_id_1, conn=self.conn))

        unlinked = self.media_links_crud.unlink_media_by_ids(self.sample_asset_id, self.sample_media_item_id_1, conn=self.conn)
        self.assertTrue(unlinked)
        self.assertIsNone(self.media_links_crud.get_media_link_by_ids(self.sample_asset_id, self.sample_media_item_id_1, conn=self.conn))

    def test_unlink_all_media_from_asset(self):
        self.media_links_crud.link_media_to_asset(self.sample_asset_id, self.sample_media_item_id_1, 0, conn=self.conn)
        self.media_links_crud.link_media_to_asset(self.sample_asset_id, self.sample_media_item_id_2, 1, conn=self.conn)

        self.assertEqual(len(self.media_links_crud.get_media_links_for_asset(self.sample_asset_id, conn=self.conn)), 2)

        unlinked_all = self.media_links_crud.unlink_all_media_from_asset(self.sample_asset_id, conn=self.conn)
        self.assertTrue(unlinked_all)
        self.assertEqual(len(self.media_links_crud.get_media_links_for_asset(self.sample_asset_id, conn=self.conn)), 0)

    def test_update_asset_media_display_orders(self):
        self.media_links_crud.link_media_to_asset(self.sample_asset_id, self.sample_media_item_id_1, 0, conn=self.conn)
        self.media_links_crud.link_media_to_asset(self.sample_asset_id, self.sample_media_item_id_2, 1, conn=self.conn)
        self.media_links_crud.link_media_to_asset(self.sample_asset_id, self.sample_media_item_id_3, 2, conn=self.conn)

        new_order = [self.sample_media_item_id_3, self.sample_media_item_id_1, self.sample_media_item_id_2]
        updated = self.media_links_crud.update_asset_media_display_orders(self.sample_asset_id, new_order, conn=self.conn)
        self.assertTrue(updated)

        links = self.media_links_crud.get_media_links_for_asset(self.sample_asset_id, conn=self.conn) # Already ordered by display_order
        self.assertEqual(len(links), 3)
        self.assertEqual(links[0]['media_item_id'], self.sample_media_item_id_3)
        self.assertEqual(links[0]['display_order'], 0)
        self.assertEqual(links[1]['media_item_id'], self.sample_media_item_id_1)
        self.assertEqual(links[1]['display_order'], 1)
        self.assertEqual(links[2]['media_item_id'], self.sample_media_item_id_2)
        self.assertEqual(links[2]['display_order'], 2)

if __name__ == '__main__':
    unittest.main()
