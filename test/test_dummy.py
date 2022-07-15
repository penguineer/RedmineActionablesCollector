""" Dummy Unit test """

import tornado.testing
from tornado.web import Application


class TestDummy(tornado.testing.AsyncHTTPTestCase):
    def get_app(self) -> Application:
        pass

    def test_dummy(self):
        return
