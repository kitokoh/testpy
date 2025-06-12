import unittest
import os
import shutil
import json
import sys

# Ensure the media_manager package can be imported
# This might be necessary if running tests from the 'tests' directory directly
# or if the project root isn't automatically in PYTHONPATH for the test runner.
# For `python -m unittest discover tests` from project root, this might not be strictly needed
# but doesn't hurt.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from media_manager import operations, models

class TestMediaManager(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        self.media_library_path = operations.MEDIA_LIBRARY_FILE # Use the constant from operations
        self.media_files_dir = operations.MEDIA_FILES_DIR # Use the constant
        self.test_download_dir = 'test_downloads_temp' # Use a distinct name for test downloads

        # Store original media library if it exists
        self.original_media_library_content = None
        if os.path.exists(self.media_library_path):
            with open(self.media_library_path, 'r') as f:
                self.original_media_library_content = f.read()

        # Clean up and create directories
        if os.path.exists(self.media_library_path):
            os.remove(self.media_library_path)

        if os.path.exists(self.media_files_dir):
            shutil.rmtree(self.media_files_dir)
        os.makedirs(self.media_files_dir, exist_ok=True)

        if os.path.exists(self.test_download_dir):
            shutil.rmtree(self.test_download_dir)
        os.makedirs(self.test_download_dir, exist_ok=True)

        # Create dummy source files
        self.dummy_video_path = "dummy_video.mp4"
        self.dummy_image_path = "dummy_image.jpg"
        open(self.dummy_video_path, 'w').close() # Create empty file
        open(self.dummy_image_path, 'w').close() # Create empty file

    def tearDown(self):
        """Clean up test environment after each test."""
        if os.path.exists(self.media_library_path):
            os.remove(self.media_library_path)

        if os.path.exists(self.media_files_dir):
            shutil.rmtree(self.media_files_dir)

        if os.path.exists(self.test_download_dir):
            shutil.rmtree(self.test_download_dir)

        # Remove dummy source files
        if os.path.exists(self.dummy_video_path):
            os.remove(self.dummy_video_path)
        if os.path.exists(self.dummy_image_path):
            os.remove(self.dummy_image_path)

        # Restore original media library if it was stored
        if self.original_media_library_content:
            with open(self.media_library_path, 'w') as f:
                f.write(self.original_media_library_content)
        elif os.path.exists(self.media_library_path): # If no original, but file created during test
             os.remove(self.media_library_path)


    def test_models_to_dict_from_dict(self):
        """Test serialization and deserialization of media models."""
        video = models.VideoItem("v1", "Video 1", "Desc v1", "Cat A", "media_files/v1.mp4")
        image = models.ImageItem("i1", "Image 1", "Desc i1", "Cat B", "media_files/i1.jpg")
        link = models.LinkItem("l1", "Link 1", "Desc l1", "Cat A", "http://example.com/link1")

        video_dict = video.to_dict()
        image_dict = image.to_dict()
        link_dict = link.to_dict()

        self.assertEqual(video, models.MediaItem.from_dict(video_dict))
        self.assertEqual(image, models.MediaItem.from_dict(image_dict))
        self.assertEqual(link, models.MediaItem.from_dict(link_dict))

        # Test with a generic dict that should become a base MediaItem (if from_dict supports it)
        # or raise ValueError if strict about known types.
        # Current from_dict logic will raise ValueError for unknown type if specific fields are missing.
        generic_dict_ok = {"id": "g1", "title": "Generic", "description": "Desc", "category": "Generic", "type": "unknown_type"}
        # The from_dict will create a base MediaItem if all base fields are present.
        generic_item = models.MediaItem.from_dict(generic_dict_ok)
        self.assertIsInstance(generic_item, models.MediaItem)
        self.assertEqual(generic_item.item_type, "unknown_type")


        malformed_dict = {"id": "m1", "title": "Malformed"} # Missing type and other fields
        with self.assertRaises(ValueError): # Expecting ValueError due to unknown/malformed type
            models.MediaItem.from_dict(malformed_dict)


    def test_add_media(self):
        """Test adding video, image, and link items."""
        # Test adding a video
        video_item = operations.add_video("Test Video", "A test video.", "Tutorials", self.dummy_video_path)
        self.assertIsInstance(video_item, models.VideoItem)
        self.assertTrue(os.path.exists(video_item.filepath))
        self.assertTrue(video_item.filepath.startswith(self.media_files_dir))

        # Test adding an image
        image_item = operations.add_image("Test Image", "A test image.", "Nature", self.dummy_image_path)
        self.assertIsInstance(image_item, models.ImageItem)
        self.assertTrue(os.path.exists(image_item.filepath))
        self.assertTrue(image_item.filepath.startswith(self.media_files_dir))

        # Test adding a link
        link_item = operations.add_link("Test Link", "A test link.", "News", "http://example.com")
        self.assertIsInstance(link_item, models.LinkItem)

        # Verify media_library.json
        library = operations._load_media_library()
        self.assertEqual(len(library), 3)

        # Check if items are in the library by checking one property (e.g. title)
        titles_in_library = [item['title'] for item in library]
        self.assertIn("Test Video", titles_in_library)
        self.assertIn("Test Image", titles_in_library)
        self.assertIn("Test Link", titles_in_library)

        # Test adding media with non-existent source file
        with self.assertRaises(FileNotFoundError):
            operations.add_video("No File Video", "Desc", "Category", "non_existent_video.mp4")
        with self.assertRaises(FileNotFoundError):
            operations.add_image("No File Image", "Desc", "Category", "non_existent_image.jpg")

    # Placeholder for further tests - will be implemented in subsequent steps
    def test_list_media(self):
        # Add sample data
        v1 = operations.add_video("Video Alpha", "Description video alpha", "CategoryX", self.dummy_video_path)
        i1 = operations.add_image("Image Beta", "Description image beta", "CategoryY", self.dummy_image_path)
        l1 = operations.add_link("Link Gamma", "Description link gamma", "CategoryX", "http://gamma.com")
        v2 = operations.add_video("Video Delta", "Description video delta", "CategoryY", self.dummy_video_path)

        # Test list_media() with no filters
        all_items = operations.list_media()
        self.assertEqual(len(all_items), 4)
        self.assertIn(v1, all_items)
        self.assertIn(i1, all_items)
        self.assertIn(l1, all_items)
        self.assertIn(v2, all_items)

        # Test list_media(filter_category='CategoryX') - case-insensitive check
        cat_x_items = operations.list_media(filter_category='categoryx')
        self.assertEqual(len(cat_x_items), 2)
        self.assertIn(v1, cat_x_items)
        self.assertIn(l1, cat_x_items)

        # Test list_media(filter_type='video')
        video_items = operations.list_media(filter_type='video')
        self.assertEqual(len(video_items), 2)
        self.assertIn(v1, video_items)
        self.assertIn(v2, video_items)

        # Test list_media(filter_category='CategoryY', filter_type='image')
        cat_y_image_items = operations.list_media(filter_category='CategoryY', filter_type='image')
        self.assertEqual(len(cat_y_image_items), 1)
        self.assertIn(i1, cat_y_image_items)

        # Test with non-matching filters
        no_match_items = operations.list_media(filter_category='NoMatch')
        self.assertEqual(len(no_match_items), 0)

        no_match_type_items = operations.list_media(filter_type='NoSuchType')
        self.assertEqual(len(no_match_type_items), 0)


    def test_search_media(self):
        # Add sample data
        v1 = operations.add_video("Exploring Space", "A documentary about space exploration.", "Documentary", self.dummy_video_path)
        i1 = operations.add_image("Mountain Sunrise", "Sunrise over the mountains.", "Nature", self.dummy_image_path)
        l1 = operations.add_link("Tech News", "Latest news in technology and space.", "News", "http://technews.com")
        v2 = operations.add_video("Deep Sea", "Mysteries of the deep sea.", "Documentary", self.dummy_video_path)

        # Test search by title (exact, partial, case-insensitive)
        self.assertIn(v1, operations.search_media("Exploring Space"))
        self.assertIn(v1, operations.search_media("space")) # Partial, in title and description of l1
        self.assertIn(l1, operations.search_media("space"))
        self.assertEqual(len(operations.search_media("space")), 2) # v1 (title), l1 (description)

        self.assertIn(v1, operations.search_media("EXPLORING")) # Case-insensitive

        # Test search by description
        self.assertIn(i1, operations.search_media("sunrise over the mountains"))
        self.assertIn(v2, operations.search_media("deep sea"))

        # Test search returning multiple items
        doc_items = operations.search_media("documentary") # Matches v1 title and description, v2 description
        self.assertIn(v1, doc_items)
        # v2's title is "Deep Sea", description is "Mysteries of the deep sea."
        # "documentary" is in v1's category, but search is title/desc.
        # The word "documentary" is in v1's description: "A documentary about space exploration."
        # Let's adjust:
        v1_new = operations.add_video("Exploring Space", "A great documentary about space.", "Documentary", self.dummy_video_path) # v1.id will change
        # Need to reload or use the new item. For simplicity, let's assume items are re-added if test setup is per method
        # Or, let's make descriptions more distinct for search_media test setup
        # Resetting library for this specific test might be cleaner if add_video modifies global state in a way that persists across calls within a single test method run.
        # For now, assuming operations._load_media_library() is called by search_media()

        # Let's restart items for search for clarity
        operations._save_media_library([]) # Clear library for this test section
        v_search1 = operations.add_video("Alpha Adventures", "Journey to the alpha point.", "Adventure", self.dummy_video_path)
        i_search1 = operations.add_image("Beta Landscapes", "The beta fields.", "Nature", self.dummy_image_path)
        l_search1 = operations.add_link("Gamma Tech", "All about gamma technology.", "Tech", "http://gamma.com")

        self.assertIn(v_search1, operations.search_media("alpha"))
        self.assertIn(i_search1, operations.search_media("beta"))
        self.assertIn(l_search1, operations.search_media("gamma"))

        # Test search returning no items
        self.assertEqual(len(operations.search_media("OmegaNotFound")), 0)

        # Test search with empty query
        self.assertEqual(len(operations.search_media("")), 0)
        self.assertEqual(len(operations.search_media("   ")), 0)

        # Test item uniqueness (query in title and description)
        v_uniq = operations.add_video("Unique Test", "A unique test case.", "Test", self.dummy_video_path)
        results_uniq = operations.search_media("unique")
        self.assertEqual(len(results_uniq), 1)
        self.assertIn(v_uniq, results_uniq)


    def test_get_media_items_by_ids(self):
        # Add sample data
        v1 = operations.add_video("Video One", "Desc One", "Cat1", self.dummy_video_path)
        i1 = operations.add_image("Image One", "Desc Two", "Cat2", self.dummy_image_path)
        l1 = operations.add_link("Link One", "Desc Three", "Cat1", "http://link.com")

        # Test with a list of these IDs
        ids_to_get = [v1.id, l1.id]
        items_by_id = operations.get_media_items_by_ids(ids_to_get)
        self.assertEqual(len(items_by_id), 2)
        self.assertIn(v1, items_by_id)
        self.assertIn(l1, items_by_id)
        self.assertNotIn(i1, items_by_id)

        # Test with a mix of valid and invalid IDs
        mixed_ids = [v1.id, "invalid_id_123", i1.id]
        mixed_items = operations.get_media_items_by_ids(mixed_ids)
        self.assertEqual(len(mixed_items), 2)
        self.assertIn(v1, mixed_items)
        self.assertIn(i1, mixed_items)

        # Test with an empty list of IDs
        self.assertEqual(len(operations.get_media_items_by_ids([])), 0)

        # Test with only invalid IDs
        self.assertEqual(len(operations.get_media_items_by_ids(["invalid1", "invalid2"])), 0)


    def test_download_selected_media(self):
        # Add a video, an image, and a link
        v1 = operations.add_video("Download Vid", "Vid to download", "Downloads", self.dummy_video_path)
        i1 = operations.add_image("Download Img", "Img to download", "Downloads", self.dummy_image_path)
        l1 = operations.add_link("Download Link", "Link to save", "Downloads", "http://download.example.com")

        media_ids_to_download = [v1.id, i1.id, l1.id, "invalid_id_for_download"]

        downloaded_files = operations.download_selected_media(media_ids_to_download, self.test_download_dir)

        self.assertEqual(len(downloaded_files), 3) # Video, Image, and links.txt

        # Assert video/image files are copied
        expected_video_filename = os.path.basename(v1.filepath)
        expected_image_filename = os.path.basename(i1.filepath)
        self.assertTrue(os.path.exists(os.path.join(self.test_download_dir, expected_video_filename)))
        self.assertTrue(os.path.exists(os.path.join(self.test_download_dir, expected_image_filename)))

        # Assert that downloaded_links.txt is created and contains the link info
        links_file_path = os.path.join(self.test_download_dir, "downloaded_links.txt")
        self.assertTrue(os.path.exists(links_file_path))

        with open(links_file_path, 'r') as f:
            links_content = f.read()
        self.assertIn(l1.title, links_content)
        self.assertIn(l1.url, links_content)

        # Check returned paths
        self.assertIn(os.path.join(self.test_download_dir, expected_video_filename), downloaded_files)
        self.assertIn(os.path.join(self.test_download_dir, expected_image_filename), downloaded_files)
        self.assertIn(links_file_path, downloaded_files)

        # Test with no valid IDs
        no_valid_ids_downloads = operations.download_selected_media(["invalid1", "invalid2"], self.test_download_dir)
        self.assertEqual(len(no_valid_ids_downloads), 0)
        # Ensure no new link file or it's empty if it was created by a previous call in a shared test_download_dir state (tearDown should handle this)

    def test_placeholder_sharing_functions(self):
        """Test placeholder sharing functions for correct output messages."""
        v1 = operations.add_video("Share Vid", "Vid to share", "Sharing", self.dummy_video_path)
        ids_to_share = [v1.id]

        email_recipient = "test@example.com"
        whatsapp_recipient = "+1234567890"

        email_status = operations.share_media_by_email(ids_to_share, email_recipient)
        self.assertIn(email_recipient, email_status)
        self.assertIn(str(len(ids_to_share)), email_status)
        self.assertIn("Email functionality is not fully implemented", self.get_printed_output(operations.share_media_by_email, ids_to_share, email_recipient))


        whatsapp_status = operations.share_media_by_whatsapp(ids_to_share, whatsapp_recipient)
        self.assertIn(whatsapp_recipient, whatsapp_status)
        self.assertIn(str(len(ids_to_share)), whatsapp_status)
        self.assertIn("WhatsApp functionality is not fully implemented", self.get_printed_output(operations.share_media_by_whatsapp, ids_to_share, whatsapp_recipient))

    # Helper to capture print output for testing placeholder functions
    def get_printed_output(self, func, *args, **kwargs):
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            func(*args, **kwargs)
        return f.getvalue()


if __name__ == '__main__':
    unittest.main()
