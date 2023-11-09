# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib.auth.models import User
import django.test


class DjangoTestCase(django.test.TestCase):
    def _login(self, email="test@example.com", username="test", password="secret"):
        User.objects.create_user(username, email, password)
        assert self.client.login(username=username, password=password)
        # Do this so that the last_login gets set and saved
        return User.objects.get(username=username)

    def _logout(self):
        self.client.logout()
