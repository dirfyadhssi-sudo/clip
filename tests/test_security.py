import unittest
from app import app

class TestSecurity(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_static_files_not_exposed(self):
        """Ensure sensitive root files are not served via static routes."""
        self.assertEqual(self.client.get("/cookies.txt").status_code, 404)
        self.assertEqual(self.client.get("/./cookies.txt").status_code, 404)
        self.assertEqual(self.client.get("/app.py").status_code, 404)
        self.assertEqual(self.client.get("/./app.py").status_code, 404)
        self.assertEqual(self.client.get("/.git/config").status_code, 404)
        self.assertEqual(self.client.get("/./.git/config").status_code, 404)

    def test_index_route_serves_html(self):
        """Ensure the home route still serves the application interface."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"ClipSnap", response.data)

if __name__ == "__main__":
    unittest.main()
