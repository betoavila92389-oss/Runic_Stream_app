import unittest
from downloader import ExtractorThread, DownloaderThread

class TestDownloader(unittest.TestCase):
    def test_purify_url_youtube_standard(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        purified = ExtractorThread(url).url
        self.assertEqual(purified, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_purify_url_youtube_short(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        purified = ExtractorThread(url).url
        self.assertEqual(purified, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_purify_url_youtube_music(self):
        url = "https://music.youtube.com/watch?v=dQw4w9WgXcQ&feature=share"
        purified = ExtractorThread(url).url
        self.assertEqual(purified, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_purify_url_with_extra_params(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=RDdQw4w9WgXcQ&start_radio=1"
        purified = ExtractorThread(url).url
        self.assertEqual(purified, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_purify_url_invalid(self):
        url = "https://google.com"
        purified = ExtractorThread(url).url
        self.assertEqual(purified, "https://google.com")

    def test_extractor_thread_none_info(self):
        from unittest.mock import MagicMock, patch
        import yt_dlp
        
        with patch('yt_dlp.YoutubeDL') as mock_ydl:
            # Configure the mock to return None when extract_info is called
            instance = mock_ydl.return_value.__enter__.return_value
            instance.extract_info.return_value = None
            
            thread = ExtractorThread("https://example.com")
            
            # Use a list to capture signals
            error_msg = []
            thread.error.connect(lambda msg: error_msg.append(msg))
            
            # Run the thread logic (calling run() directly for testing)
            thread.run()
            
            self.assertTrue(len(error_msg) > 0)
            self.assertIn("No se pudo extraer", error_msg[0])

if __name__ == "__main__":
    unittest.main()
