import unittest
import os
import shutil
import json
import sys
import sqlite3
import asyncio

from PIL import Image
import cv2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from media_manager import operations, models
import db
from config import MEDIA_FILES_BASE_PATH, DEFAULT_DOWNLOAD_PATH, DATABASE_PATH, APP_ROOT_DIR

class TestMediaManager(unittest.TestCase):
    test_user_id_1 = None
    test_user_id_2 = None
    THUMBNAIL_SUBDIR = operations.THUMBNAIL_DIR_NAME

    @classmethod
    def setUpClass(cls):
        db.DATABASE_NAME = os.path.basename(DATABASE_PATH)
        db.initialize_database()

        conn_setup = db.get_db_connection()
        conn_setup.execute("PRAGMA foreign_keys = ON;")

        user1_data = {'username': 'test_uploader_1', 'password': 'password1', 'full_name': 'Test Uploader One', 'email': 'uploader1@test.com', 'role': 'user'}
        user2_data = {'username': 'test_uploader_2', 'password': 'password2', 'full_name': 'Test Uploader Two', 'email': 'uploader2@test.com', 'role': 'user'}

        existing_user1 = db.get_user_by_username(user1_data['username'])
        if existing_user1: db.delete_user(existing_user1['user_id'])

        existing_user2 = db.get_user_by_username(user2_data['username'])
        if existing_user2: db.delete_user(existing_user2['user_id'])

        cls.test_user_id_1 = db.add_user(user1_data)
        cls.test_user_id_2 = db.add_user(user2_data)

        if not cls.test_user_id_1 or not cls.test_user_id_2:
            if not cls.test_user_id_1:
                u1 = db.get_user_by_username(user1_data['username'])
                if u1: cls.test_user_id_1 = u1['user_id']
            if not cls.test_user_id_2:
                u2 = db.get_user_by_username(user2_data['username'])
                if u2: cls.test_user_id_2 = u2['user_id']
            if not cls.test_user_id_1 or not cls.test_user_id_2:
                 raise Exception("Failed to create or retrieve test users for MediaManager tests.")
        conn_setup.close()

    @classmethod
    def tearDownClass(cls):
        if cls.test_user_id_1:
            db.delete_user(cls.test_user_id_1)
        if cls.test_user_id_2:
            db.delete_user(cls.test_user_id_2)

    def setUp(self):
        self.media_files_base_path_config = MEDIA_FILES_BASE_PATH
        self.thumbnails_path = os.path.join(self.media_files_base_path_config, self.THUMBNAIL_SUBDIR)
        self.test_download_dir = os.path.join(APP_ROOT_DIR, 'test_media_downloads_temp')

        self.conn = db.get_db_connection()
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.cursor = self.conn.cursor()
        self.cursor.execute("DELETE FROM MediaItemTags")
        self.cursor.execute("DELETE FROM Tags")
        self.cursor.execute("DELETE FROM MediaItems")
        self.conn.commit()

        for path in [self.media_files_base_path_config, self.thumbnails_path, self.test_download_dir]:
            if os.path.exists(path):
                shutil.rmtree(path, ignore_errors=True)
            os.makedirs(path, exist_ok=True)

        self.dummy_image_path = "dummy_image.png"
        try:
            img = Image.new('RGB', (60, 30), color = 'red')
            img.save(self.dummy_image_path)
        except Exception as e:
            print(f"Warning: Could not create dummy PNG image for tests: {e}")
            open(self.dummy_image_path, 'w').close()

        self.dummy_video_path = "dummy_video.mp4"
        open(self.dummy_video_path, 'w').close()


    def tearDown(self):
        try:
            self.cursor.execute("DELETE FROM MediaItemTags")
            self.cursor.execute("DELETE FROM Tags")
            self.cursor.execute("DELETE FROM MediaItems")
            self.conn.commit()
        except sqlite3.Error as e: print(f"Error cleaning tables in tearDown: {e}")
        finally:
            if self.conn: self.conn.close()

        for path in [self.media_files_base_path_config, self.test_download_dir]:
             if os.path.exists(path): shutil.rmtree(path, ignore_errors=True)

        if os.path.exists(self.dummy_video_path): os.remove(self.dummy_video_path)
        if os.path.exists(self.dummy_image_path): os.remove(self.dummy_image_path)

    def test_models_to_dict_from_dict(self):
        video_metadata = {"duration": "10:00", "resolution": "1080p"}
        video = models.VideoItem(id="v1", title="Video 1", description="Desc v1", filepath=os.path.join("v1.mp4"), tags=["tag1", "tag2"], thumbnail_path=".thumbnails/v1.jpg", metadata=video_metadata)
        video_dict = video.to_dict()
        self.assertEqual(video_dict['metadata'], video_metadata)
        reconstructed_video = models.MediaItem.from_dict(video_dict)
        self.assertEqual(video, reconstructed_video)
        self.assertEqual(reconstructed_video.metadata, video_metadata)

        # Test with metadata_json string as input (simulating DB row)
        video_dict_from_db_row = {
            'id': "v1db", 'title': "Video DB", 'description': "Desc DB", 'type': "video",
            'filepath': "v1db.mp4", 'tags': ["db", "test"],
            'thumbnail_path': ".thumbnails/v1db.jpg",
            'metadata_json': json.dumps(video_metadata) # metadata as JSON string
        }
        reconstructed_from_db_row = models.MediaItem.from_dict(video_dict_from_db_row)
        self.assertIsInstance(reconstructed_from_db_row, models.VideoItem)
        self.assertEqual(reconstructed_from_db_row.metadata, video_metadata)


    async def test_add_media(self):
        sample_metadata = {"source": "test_camera", "quality": "high"}
        video_item_obj = await operations.add_video("Async Test Video", "A test video for DB.", self.dummy_video_path, uploader_user_id=self.test_user_id_1, tags=["tutorial", "testing"], metadata=sample_metadata)
        self.assertIsInstance(video_item_obj, models.VideoItem)
        # Check user-provided metadata and some auto-extracted (if dummy file allows)
        self.assertEqual(video_item_obj.metadata.get("source"), "test_camera")
        self.assertTrue("width" in video_item_obj.metadata) # Auto-extracted

        self.cursor.execute("SELECT metadata_json FROM MediaItems WHERE media_item_id = ?", (video_item_obj.id,))
        video_row = self.cursor.fetchone()
        self.assertIsNotNone(video_row)
        db_metadata = json.loads(video_row['metadata_json'])
        self.assertEqual(db_metadata.get("source"), "test_camera")
        self.assertTrue("width" in db_metadata)

        # Test image metadata
        image_metadata = {"user_caption": "A beautiful test image"}
        image_item_obj = await operations.add_image("Async Test Image", "A test image for DB.", self.dummy_image_path, uploader_user_id=self.test_user_id_1, tags=["nature", "testing"], metadata=image_metadata)
        self.assertEqual(image_item_obj.metadata.get("user_caption"), "A beautiful test image")
        self.assertTrue("width" in image_item_obj.metadata) # Auto-extracted from dummy PNG
        self.assertTrue("height" in image_item_obj.metadata)
        self.assertEqual(image_item_obj.metadata.get("format"), "PNG") # Dummy is PNG

        self.cursor.execute("SELECT metadata_json FROM MediaItems WHERE media_item_id = ?", (image_item_obj.id,))
        image_db_meta_json = self.cursor.fetchone()['metadata_json']
        image_db_metadata = json.loads(image_db_meta_json)
        self.assertEqual(image_db_metadata.get("user_caption"), "A beautiful test image")
        self.assertTrue("format" in image_db_metadata)


        # ... (rest of add_media assertions for file paths, other fields)
        self.assertTrue(os.path.exists(os.path.join(MEDIA_FILES_BASE_PATH, video_item_obj.filepath)))
        self.assertTrue(video_item_obj.filepath.startswith(video_item_obj.id))
        if video_item_obj.thumbnail_path:
             self.assertTrue(os.path.exists(os.path.join(MEDIA_FILES_BASE_PATH, video_item_obj.thumbnail_path)))


    async def test_list_media(self):
        meta1 = {"key1": "val1", "source": "list_test_cam1"}
        meta2 = {"key2": "val2", "source": "list_test_cam2"}
        v1 = await operations.add_video("Video Alpha", "Desc video alpha", self.dummy_video_path, uploader_user_id=self.test_user_id_1, tags=["catX", "videoTag"], metadata=meta1)
        i1 = await operations.add_image("Image Beta", "Desc image beta", self.dummy_image_path, uploader_user_id=self.test_user_id_2, tags=["catY", "imageTag"], metadata=meta2)

        all_items = operations.list_media()
        self.assertEqual(len(all_items), 2)
        item_v1_listed = next(i for i in all_items if i.id == v1.id)
        self.assertListEqual(sorted(item_v1_listed.tags), sorted(["catx", "videotag"]))
        self.assertIsNotNone(item_v1_listed.thumbnail_path)
        self.assertTrue("width" in item_v1_listed.metadata) # Auto-extracted
        self.assertEqual(item_v1_listed.metadata.get("source"), "list_test_cam1") # User-provided

        item_i1_listed = next(i for i in all_items if i.id == i1.id)
        self.assertTrue("format" in item_i1_listed.metadata) # Auto-extracted
        self.assertEqual(item_i1_listed.metadata.get("source"), "list_test_cam2") # User-provided
        # ... (rest of list_media assertions)


    async def test_search_media(self):
        meta_search = {"priority": "high", "project_code": "XYZ"}
        v_s1_u1 = await operations.add_video("Alpha Search User1", "Journey to alpha point.", self.dummy_video_path, uploader_user_id=self.test_user_id_1, tags=["adventureS"], metadata=meta_search)
        results = operations.search_media(query="Alpha Search User1")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, v_s1_u1.id)
        self.assertListEqual(sorted(results[0].tags), sorted(["adventures"]))
        self.assertIsNotNone(results[0].thumbnail_path)
        self.assertEqual(results[0].metadata.get("project_code"), "XYZ")
        self.assertTrue("width" in results[0].metadata)
        # ... (rest of search_media tests)


    async def test_get_media_items_by_ids(self):
        meta_get = {"format": "landscape", "camera_model": "Nikon Z6"}
        v1 = await operations.add_video("Video One DB Get", "Desc One", self.dummy_video_path, uploader_user_id=self.test_user_id_1, tags=["cat1get", "vidGet"], metadata=meta_get)
        items = operations.get_media_items_by_ids([v1.id])
        self.assertEqual(len(items), 1)
        self.assertListEqual(sorted(items[0].tags), sorted(["cat1get", "vidget"]))
        self.assertIsNotNone(items[0].thumbnail_path)
        self.assertEqual(items[0].metadata.get("camera_model"), "Nikon Z6")
        self.assertTrue("width" in items[0].metadata)


    async def test_download_selected_media(self):
        meta_dl = {"project": "Project X"}
        v1 = await operations.add_video("Download Vid Async", "Vid to download", self.dummy_video_path, uploader_user_id=self.test_user_id_1, tags=["download", "videoAsync"], metadata=meta_dl)
        l1 = operations.add_link("Download Link Async", "Link to save", "http://download-async.example.com", uploader_user_id=self.test_user_id_1, tags=["download", "linkAsync"], metadata={"source": "web"})
        # ... (rest of download test setup)
        media_ids_to_download = [v1.id, l1.id]
        downloaded_files = await operations.download_selected_media(media_ids_to_download, self.test_download_dir)
        # ... (assertions for files)
        links_file_path = os.path.join(self.test_download_dir, "downloaded_links.txt")
        with open(links_file_path, 'r') as f:
            content = f.read()
            self.assertIn("Tags: download, linkasync", content)
            self.assertIn(f"Metadata: {json.dumps({'source': 'web'})}", content)


    async def test_placeholder_sharing_functions(self):
        meta_share = {"audience": "public"}
        v1 = await operations.add_video("Share Vid Async", "Vid to share DB", self.dummy_video_path, uploader_user_id=self.test_user_id_1, tags=["shareAsync"], metadata=meta_share)
        # ... (rest of placeholder tests)
        email_output = self.get_printed_output(operations.share_media_by_email, [v1.id], "test@example.com")
        self.assertIn("shareasync", email_output)
        self.assertIn(json.dumps(meta_share), email_output)


    def _add_media_with_timestamps(self, title: str, item_type:str, created_at_iso: str, updated_at_iso: str, filepath: str | None = None, url: str | None = None, uploader_user_id=None, tags: List[str] | None = None, thumbnail_path: str | None = None, metadata: Dict[str,Any] | None = None) -> str:
        item_id = operations._generate_id()
        db_filepath = filepath
        metadata_json_str = json.dumps(metadata) if metadata else None
        self.cursor.execute(
            """INSERT INTO MediaItems (media_item_id, title, description, item_type, filepath, url, uploader_user_id, created_at, updated_at, thumbnail_path, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (item_id, title, f"Description for {title}", item_type,
             db_filepath, url, uploader_user_id, created_at_iso, updated_at_iso, thumbnail_path, metadata_json_str)
        )
        if tags:
            for tag_name in tags:
                tag_id = operations._get_or_create_tag_id(tag_name, self.cursor)
                self.cursor.execute("INSERT INTO MediaItemTags (media_item_id, tag_id) VALUES (?,?)", (item_id, tag_id))
        self.conn.commit()
        return item_id

    async def test_search_media_by_date(self):
        meta_date_search = {"event": "New Year"}
        id1 = self._add_media_with_timestamps("Created Early Date", "link", "2023-01-01T10:00:00Z", "2023-01-05T10:00:00Z", uploader_user_id=self.test_user_id_1, url="http://early.date.com", tags=["dated"], metadata=meta_date_search)
        results = operations.search_media(created_after="2023-01-01T09:00:00Z", filter_by_uploader_id=self.test_user_id_1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, id1)
        self.assertListEqual(sorted(results[0].tags), ["dated"])
        self.assertIsNone(results[0].thumbnail_path)
        self.assertEqual(results[0].metadata, meta_date_search)

    def get_printed_output(self, func, *args, **kwargs):
        import io
        from contextlib import redirect_stdout
        f = io.StringIO()
        with redirect_stdout(f):
            func(*args, **kwargs)
        return f.getvalue()

if __name__ == '__main__':
    unittest.main()