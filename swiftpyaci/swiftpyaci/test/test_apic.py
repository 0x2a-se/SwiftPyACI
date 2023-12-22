import unittest
from unittest.mock import patch
import swiftpyaci

# class APICTestCase(unittest.TestCase):
#     @patch(
#         "requests.sessions.Session.post",
#         return_value=Response(),
#     )
#     def test_get(self, *_):
#         api = pynetbox.api(host, **def_kwargs)
#         self.assertTrue(api)

#     @patch(
#         "requests.sessions.Session.post",
#         return_value=Response(),
#     )
#     def test_sanitize_url(self, *_):
#         api = pynetbox.api("http://localhost:8000/", **def_kwargs)
#         self.assertTrue(api)
#         self.assertEqual(api.base_url, "http://localhost:8000/api")