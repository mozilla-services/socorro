import django.test
import django.utils.unittest


class TestCase(django.utils.unittest.TestCase):

    def shortDescription(self):
        return None


class DjangoTestCase(django.test.TestCase):

    def shortDescription(self):
        return None
