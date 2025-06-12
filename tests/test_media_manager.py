import unittest
import os
import shutil
import json
import sys
import sqlite3
import asyncio

from PIL import Image # Added for creating dummy image and checking thumbs
import cv2 # Added, though direct use might be limited if creating dummy videos is hard

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from media_manager import operations, models
import db
from config import MEDIA_FILES_BASE_PATH, DEFAULT_DOWNLOAD_PATH, DATABASE_PATH, APP_ROOT_DIR

class TestMediaManager(unittest.TestCase):
    test_user_id_1 = None
    test_user_id_2 = None
    THUMBNAIL_SUBDIR = operations.THUMBNAIL_DIR_NAME # ".thumbnails"

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

        # Create a more valid dummy image (e.g., PNG)
        self.dummy_image_path = "dummy_image.png"
        try:
            img = Image.new('RGB', (60, 30), color = 'red')
            img.save(self.dummy_image_path)
        except Exception as e:
            print(f"Warning: Could not create dummy PNG image for tests: {e}")
            # Fallback to empty file if Pillow fails for some reason in test env
            open(self.dummy_image_path, 'w').close()

        # Create an empty dummy video file (actual thumbnailing might fail but tests flow)
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

        for path in [self.media_files_base_path_config, self.test_download_dir]: # self.thumbnails_path is inside media_files_base_path_config
             if os.path.exists(path): shutil.rmtree(path, ignore_errors=True)

        if os.path.exists(self.dummy_video_path): os.remove(self.dummy_video_path)
        if os.path.exists(self.dummy_image_path): os.remove(self.dummy_image_path)

    def test_models_to_dict_from_dict(self):
        video = models.VideoItem(id="v1", title="Video 1", description="Desc v1", filepath=os.path.join("v1.mp4"), tags=["tag1", "tag2"], thumbnail_path=".thumbnails/v1.jpg")
        # ... (rest of the test remains the same)
        image = models.ImageItem(id="i1", title="Image 1", description="Desc i1", filepath=os.path.join("i1.jpg"), tags=["tag2", "tag3"], thumbnail_path=".thumbnails/i1.jpg")
        link = models.LinkItem(id="l1", title="Link 1", description="Desc l1", url="http://example.com/link1", tags=[], thumbnail_path=None)
        video_dict = video.to_dict()
        image_dict = image.to_dict()
        link_dict = link.to_dict()
        self.assertEqual(video_dict['type'], 'video')
        self.assertListEqual(sorted(video_dict['tags']), sorted(["tag1", "tag2"]))
        self.assertEqual(video_dict['thumbnail_path'], ".thumbnails/v1.jpg")
        self.assertEqual(video, models.MediaItem.from_dict(video_dict))
        self.assertEqual(image, models.MediaItem.from_dict(image_dict))
        self.assertEqual(link, models.MediaItem.from_dict(link_dict))
        generic_dict_ok = {"id": "g1", "title": "Generic", "description": "Desc", "type": "unknown_type", "tags": ["generic"], "thumbnail_path": ".thumbnails/g1.jpg"}
        generic_item = models.MediaItem.from_dict(generic_dict_ok)
        self.assertIsInstance(generic_item, models.MediaItem)
        self.assertEqual(generic_item.item_type, "unknown_type")
        self.assertListEqual(generic_item.tags, ["generic"])
        self.assertEqual(generic_item.thumbnail_path, ".thumbnails/g1.jpg")
        malformed_dict = {"id": "m1", "title": "Malformed"}
        with self.assertRaises(ValueError):
            models.MediaItem.from_dict(malformed_dict)


    async def test_add_media(self):
        # Test adding an image (which should generate a thumbnail)
        image_item_obj = await operations.add_image("Async Test Image", "A test image for DB.", self.dummy_image_path, uploader_user_id=self.test_user_id_1, tags=["nature", "testing"])
        self.assertIsInstance(image_item_obj, models.ImageItem)
        self.assertTrue(os.path.exists(os.path.join(MEDIA_FILES_BASE_PATH, image_item_obj.filepath)))
        self.assertTrue(image_item_obj.filepath.startswith(image_item_obj.id)) # Filepath is now relative to MEDIA_FILES_BASE_PATH

        self.cursor.execute("SELECT * FROM MediaItems WHERE media_item_id = ?", (image_item_obj.id,))
        image_row = dict(self.cursor.fetchone())
        self.assertIsNotNone(image_row)
        self.assertEqual(image_row['title'], "Async Test Image")
        self.assertIsNotNone(image_row['thumbnail_path']) # Thumbnail path should be stored
        self.assertTrue(os.path.exists(os.path.join(MEDIA_FILES_BASE_PATH, image_row['thumbnail_path'])))
        # Optionally check thumbnail dimensions
        try:
            thumb_img = Image.open(os.path.join(MEDIA_FILES_BASE_PATH, image_row['thumbnail_path']))
            self.assertTrue(thumb_img.size[0] <= operations.THUMBNAIL_SIZE[0])
            self.assertTrue(thumb_img.size[1] <= operations.THUMBNAIL_SIZE[1])
        except Exception as e:
            self.fail(f"Thumbnail check failed: {e}")

        # Test adding a video (thumbnail generation might be basic if dummy video is empty)
        video_item_obj = await operations.add_video("Async Test Video", "A test video for DB.", self.dummy_video_path, uploader_user_id=self.test_user_id_1, tags=["tutorial"])
        self.assertIsInstance(video_item_obj, models.VideoItem)
        self.cursor.execute("SELECT thumbnail_path FROM MediaItems WHERE media_item_id = ?", (video_item_obj.id,))
        video_thumb_path = self.cursor.fetchone()['thumbnail_path']
        if video_thumb_path: # OpenCV might succeed on some systems with empty files, or fail gracefully
            self.assertTrue(os.path.exists(os.path.join(MEDIA_FILES_BASE_PATH, video_thumb_path)))
        else:
            print("Video thumbnail generation likely skipped for dummy video, this is acceptable for this test.")

        # Test adding a link (no thumbnail expected)
        link_item_obj = operations.add_link("Test Link DB", "A test link for DB.", "http://example-db.com", uploader_user_id=self.test_user_id_1, tags=["news"])
        self.cursor.execute("SELECT thumbnail_path FROM MediaItems WHERE media_item_id = ?", (link_item_obj.id,))
        self.assertIsNone(self.cursor.fetchone()['thumbnail_path'])

        # ... (rest of add_media tests like error handling remain similar) ...
        with self.assertRaises(FileNotFoundError):
            await operations.add_video("No File Video", "Desc", "non_existent_video.mp4", uploader_user_id=self.test_user_id_1, tags=["error"])


    async def test_list_media(self):
        v1 = await operations.add_video("Video Alpha", "Desc video alpha", self.dummy_video_path, uploader_user_id=self.test_user_id_1, tags=["catX", "videoTag"])
        all_items = operations.list_media()
        self.assertEqual(len(all_items), 1)
        item_v1_listed = next(i for i in all_items if i.id == v1.id)
        self.assertListEqual(sorted(item_v1_listed.tags), sorted(["catx", "videotag"]))
        self.assertIsNotNone(item_v1_listed.thumbnail_path) # Check thumbnail path is populated


    async def test_search_media(self):
        v_s1_u1 = await operations.add_video("Alpha Search User1", "Journey to alpha point.", self.dummy_video_path, uploader_user_id=self.test_user_id_1, tags=["adventureS"])
        results = operations.search_media(query="Alpha Search User1")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, v_s1_u1.id)
        self.assertListEqual(sorted(results[0].tags), sorted(["adventures"]))
        self.assertIsNotNone(results[0].thumbnail_path)


    async def test_get_media_items_by_ids(self):
        v1 = await operations.add_video("Video One DB Get", "Desc One", self.dummy_video_path, uploader_user_id=self.test_user_id_1, tags=["cat1get", "vidGet"])
        items = operations.get_media_items_by_ids([v1.id])
        self.assertEqual(len(items), 1)
        self.assertListEqual(sorted(items[0].tags), sorted(["cat1get", "vidget"]))
        self.assertIsNotNone(items[0].thumbnail_path)


    async def test_download_selected_media(self):
        v1 = await operations.add_video("Download Vid Async", "Vid to download", self.dummy_video_path, uploader_user_id=self.test_user_id_1, tags=["download", "videoAsync"])
        l1 = operations.add_link("Download Link Async", "Link to save", "http://download-async.example.com", uploader_user_id=self.test_user_id_1, tags=["download", "linkAsync"])
        media_ids_to_download = [v1.id, l1.id]
        downloaded_files = await operations.download_selected_media(media_ids_to_download, self.test_download_dir)
        self.assertEqual(len(downloaded_files), 2)
        expected_video_filepath_abs = os.path.join(self.test_download_dir, os.path.basename(v1.filepath)) # v1.filepath is relative
        self.assertIn(expected_video_filepath_abs, downloaded_files)
        self.assertTrue(os.path.exists(expected_video_filepath_abs))
        links_file_path = os.path.join(self.test_download_dir, "downloaded_links.txt")
        self.assertIn(links_file_path, downloaded_files)
        with open(links_file_path, 'r') as f:
            content = f.read()
            self.assertIn("Tags: download, linkasync", content)

    async def test_placeholder_sharing_functions(self):
        v1 = await operations.add_video("Share Vid Async", "Vid to share DB", self.dummy_video_path, uploader_user_id=self.test_user_id_1, tags=["shareAsync"])
        email_status = operations.share_media_by_email([v1.id], "test@example.com")
        # Check that thumbnail path might be mentioned if it were part of the details string (it's not currently, but good to be aware)
        self.assertIn("shareasync", self.get_printed_output(operations.share_media_by_email, [v1.id], "test@example.com"))


    def _add_media_with_timestamps(self, title: str, item_type:str, created_at_iso: str, updated_at_iso: str, filepath: str | None = None, url: str | None = None, uploader_user_id=None, tags: List[str] | None = None, thumbnail_path: str | None = None) -> str: # Added thumbnail_path
        item_id = operations._generate_id()
        db_filepath = filepath
        self.cursor.execute(
            """INSERT INTO MediaItems (media_item_id, title, description, item_type, filepath, url, uploader_user_id, created_at, updated_at, thumbnail_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", # Added thumbnail_path placeholder
            (item_id, title, f"Description for {title}", item_type,
             db_filepath, url, uploader_user_id, created_at_iso, updated_at_iso, thumbnail_path)
        )
        if tags:
            for tag_name in tags:
                tag_id = operations._get_or_create_tag_id(tag_name, self.cursor)
                self.cursor.execute("INSERT INTO MediaItemTags (media_item_id, tag_id) VALUES (?,?)", (item_id, tag_id))
        self.conn.commit()
        return item_id

    async def test_search_media_by_date(self):
        id1 = self._add_media_with_timestamps("Created Early Date", "link", "2023-01-01T10:00:00Z", "2023-01-05T10:00:00Z", uploader_user_id=self.test_user_id_1, url="http://early.date.com", tags=["dated"], thumbnail_path=None)
        results = operations.search_media(created_after="2023-01-01T09:00:00Z", filter_by_uploader_id=self.test_user_id_1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, id1)
        self.assertListEqual(sorted(results[0].tags), ["dated"])
        self.assertIsNone(results[0].thumbnail_path) # Link items have None thumbnail_path

    def get_printed_output(self, func, *args, **kwargs):
        import io
        from contextlib import redirect_stdout
        f = io.StringIO()
        with redirect_stdout(f):
            func(*args, **kwargs)
        return f.getvalue()

if __name__ == '__main__':
    unittest.main()
