# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from io import StringIO

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.utils import timezone


class TestHackerEmailsCommand:
    """Test hackeremails command."""

    def test_no_users(self, db):
        buffer = StringIO()
        call_command("hackeremails", stdout=buffer)
        assert "No users." in buffer.getvalue()

    def test_print_users(self, db):
        hackers_group = Group.objects.get(name="Hackers")

        bob = User.objects.create(username="bob", email="bob@mozilla.com")
        bob.last_login = timezone.now()
        bob.groups.add(hackers_group)
        bob.save()

        assert hackers_group.user_set.count() == 1

        buffer = StringIO()
        call_command("hackeremails", stdout=buffer)
        assert "bob@mozilla.com" in buffer.getvalue()
