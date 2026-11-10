import unittest
import json
from app import app

class SecurityTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_info_rejects_empty_url(self):
        res = self.client.post("/api/info", json={"url": ""})
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.get_json())

    def test_info_rejects_command_injection_flags(self):
        res = self.client.post("/api/info", json={"url": "--version"})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)
        self.assertIn("YouTube", data["error"])

    def test_info_rejects_non_youtube_urls(self):
        bad_urls = [
            "http://169.254.169.254/latest/meta-data/",
            "http://localhost:8080/secret",
            "https://attacker.com/exploit",
            "file:///etc/passwd",
            "ftp://example.com/test",
            "https://youtube.com.attacker.com/watch?v=123",
        ]
        for url in bad_urls:
            with self.subTest(url=url):
                res = self.client.post("/api/info", json={"url": url})
                self.assertEqual(res.status_code, 400)
                self.assertIn("error", res.get_json())

    def test_start_download_rejects_command_injection_and_non_youtube(self):
        res = self.client.post("/api/start-download", json={
            "url": "--help",
            "start": 0,
            "end": 10,
            "format": "mp4"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("YouTube", res.get_json()["error"])

    def test_start_download_rejects_invalid_format(self):
        res = self.client.post("/api/start-download", json={
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "start": 0,
            "end": 10,
            "format": "exe"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("format", res.get_json()["error"].lower())

    def test_start_download_accepts_valid_youtube_url(self):
        from unittest.mock import patch
        with patch("threading.Thread") as mock_thread:
            res = self.client.post("/api/start-download", json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "start": 0,
                "end": 10,
                "format": "mp4"
            })
            # Should queue job and return 200 with job_id without spawning live subprocess
            self.assertEqual(res.status_code, 200)
            self.assertIn("job_id", res.get_json())
            mock_thread.assert_called()

if __name__ == "__main__":
    unittest.main()
