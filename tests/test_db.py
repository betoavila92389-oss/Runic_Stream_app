import unittest
import os
import sqlite3
from db import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_runic_stream.db"
        self.db_manager = DatabaseManager(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_init_db(self):
        self.assertTrue(os.path.exists(self.db_path))
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='media_library'")
            self.assertIsNotNone(cursor.fetchone())

    def test_add_media(self):
        media_id = self.db_manager.add_media("Test Song", "audio", "/path/to/song.mp3", "http://example.com", "320k")
        self.assertIsInstance(media_id, int)
        
        media = self.db_manager.get_all_media("audio")
        self.assertEqual(len(media), 1)
        self.assertEqual(media[0]['title'], "Test Song")

    def test_get_media_by_url(self):
        url = "http://example.com/video"
        self.db_manager.add_media("Test Video", "video", "/path/to/video.mp4", url, "1080p")
        
        results = self.db_manager.get_media_by_url(url)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Test Video")

    def test_sync_library(self):
        # Add a record with a non-existent file
        self.db_manager.add_media("Missing File", "audio", "/non/existent/path.mp3")
        
        # Add a record with an existing file (using the test file itself)
        self.db_manager.add_media("Existing File", "audio", __file__)
        
        deleted_count = self.db_manager.sync_library()
        self.assertEqual(deleted_count, 1)
        
        all_media = self.db_manager.get_all_media()
        self.assertEqual(len(all_media), 1)
        self.assertEqual(all_media[0]['title'], "Existing File")

    def test_delete_media(self):
        # Create a dummy file to delete
        dummy_file = "dummy_media.mp3"
        with open(dummy_file, "w") as f:
            f.write("dummy content")
        
        media_id = self.db_manager.add_media("Dummy", "audio", dummy_file)
        
        result = self.db_manager.delete_media(media_id)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(dummy_file))
        
        all_media = self.db_manager.get_all_media()
        self.assertEqual(len(all_media), 0)

if __name__ == "__main__":
    unittest.main()
