import unittest
from app import app, secs_to_hms

class TestClipSnap(unittest.TestCase):
    def test_secs_to_hms(self):
        self.assertEqual(secs_to_hms(0), "00:00:00")
        self.assertEqual(secs_to_hms(65), "00:01:05")
        self.assertEqual(secs_to_hms(3665), "01:01:05")

    def test_index_route(self):
        client = app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"ClipSnap", response.data)
        self.assertIn(b'aria-label="Waktu mulai jam"', response.data)
        self.assertIn(b'label for="urlInput"', response.data)

if __name__ == "__main__":
    unittest.main()
