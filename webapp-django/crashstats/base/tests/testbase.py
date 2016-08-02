import inspect

import mock

import django.test
import django.utils.unittest
from django.contrib.auth.models import User

import crashstats.crashstats.models
import crashstats.supersearch.models


classes_with_implementation = []
for module in (crashstats.crashstats.models, crashstats.supersearch.models):
    for _, klass in inspect.getmembers(module, inspect.isclass):
        if issubclass(klass, crashstats.crashstats.models.SocorroMiddleware):
            # Remember, the default thing for SocorroMiddleware is
            # that it always has a class attribute called `implementation`
            # it's by default set to None.
            if klass.implementation:
                classes_with_implementation.append(klass)


class TestCase(django.utils.unittest.TestCase):

    def shortDescription(self):
        return None


class DjangoTestCase(django.test.TestCase):

    def setUp(self):
        super(DjangoTestCase, self).setUp()

        # These are all the classes who have an implementation
        # (e.g. a class that belongs to socorro.external.something.something)
        # They all need to be mocked.

        for klass in classes_with_implementation:
            klass.implementation = mock.MagicMock()
            # The class name is used by the internal caching that guards
            # for repeated calls with the same parameter.
            # If we don't do this the cache key will always have the
            # string 'MagicMock' in it no matter which class it came from.
            klass.implementation().__class__.__name__ = klass.__name__

    def shortDescription(self):
        return None

    def _login(self):
        user = User.objects.create_user('test', 'test@example.com', 'secret')
        assert self.client.login(username='test', password='secret')
        return user
