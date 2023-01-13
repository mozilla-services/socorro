# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import inspect
from unittest import mock

from django.contrib.auth.models import User
import django.test

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


class DjangoTestCase(django.test.TestCase):
    def setUp(self):
        super().setUp()

        # These are all the classes who have an implementation
        # (e.g. a class that belongs to socorro.external.something.something)
        # They all need to be mocked.
        self._mockeries = {}

        for klass in classes_with_implementation:
            self._mockeries[klass] = klass.implementation
            klass.implementation = mock.MagicMock()
            # The class name is used by the internal caching that guards
            # for repeated calls with the same parameter.
            # If we don't do this the cache key will always have the
            # string 'MagicMock' in it no matter which class it came from.
            klass.implementation().__class__.__name__ = klass.__name__

    def undo_implementation_mock(self, klass):
        """Undoes a single implementation mock."""
        klass.implementation = self._mockeries[klass]

    def tearDown(self):
        for klass in classes_with_implementation:
            klass.implementation = self._mockeries[klass]
        super().tearDown()

    def _login(self, email="test@example.com", username="test", password="secret"):
        User.objects.create_user(username, email, password)
        assert self.client.login(username=username, password=password)
        # Do this so that the last_login gets set and saved
        return User.objects.get(username=username)

    def _logout(self):
        self.client.logout()
