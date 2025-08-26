import tornado.web
from tornado.testing import AsyncHTTPTestCase
from app import make_app  # adjust import as needed

class TestCORSHeaders(AsyncHTTPTestCase):
    def get_app(self):
        return make_app()

    def test_cors_headers_present(self):
        response = self.fetch('/v0/redmine/actionables', method='OPTIONS')
        self.assertEqual(response.code, 204)
        self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), '*')
        self.assertIn('x-requested-with', response.headers.get('Access-Control-Allow-Headers', ''))
        self.assertIn('content-type', response.headers.get('Access-Control-Allow-Headers', ''))
        self.assertIn('OPTIONS', response.headers.get('Access-Control-Allow-Methods', ''))
