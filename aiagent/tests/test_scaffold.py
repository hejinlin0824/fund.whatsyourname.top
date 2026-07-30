from django.test import TestCase
from django.apps import apps


class ScaffoldTest(TestCase):
    def test_app_installed(self):
        self.assertTrue(apps.is_installed("aiagent"))
