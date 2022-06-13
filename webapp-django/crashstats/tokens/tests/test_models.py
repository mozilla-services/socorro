# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime

from django.utils import timezone
from django.contrib.auth.models import User, Permission, Group
from django.conf import settings

from crashstats.crashstats.tests.testbase import DjangoTestCase
from crashstats.tokens import models


class TestModels(DjangoTestCase):
    def test_create_token(self):
        bob = User.objects.create(username="bob")
        token = models.Token.objects.create(user=bob, notes="Some notes")
        assert len(token.key) == 32

        now = timezone.now()
        future = now + datetime.timedelta(days=settings.TOKENS_DEFAULT_EXPIRATION_DAYS)
        assert token.expires.strftime("%Y%m%d%H%M") == future.strftime("%Y%m%d%H%M")

        # using __repr__ shouldn't reveal the key
        assert token.key not in repr(token)

    def test_token_manager(self):
        bob = User.objects.create(username="bob")
        models.Token.objects.create(user=bob, notes="Second one")

        now = timezone.now()
        models.Token.objects.create(user=bob, notes="First one", expires=now)
        assert models.Token.objects.all().count() == 2
        assert models.Token.objects.active().count() == 1

    def test_is_expired(self):
        bob = User.objects.create(username="bob")
        token = models.Token.objects.create(user=bob, notes="Some notes")
        assert not token.is_expired
        now = timezone.now()
        yesterday = now - datetime.timedelta(days=1)
        token.expires = yesterday
        token.save()
        assert token.is_expired

    def test_api_token_losing_permissions(self):
        bob = User.objects.create(username="bob")
        permission = Permission.objects.get(codename="view_pii")
        permission2 = Permission.objects.get(codename="view_exploitability")
        group = Group.objects.create(name="VIP")
        group.permissions.add(permission)
        group.permissions.add(permission2)
        bob.groups.add(group)

        token = models.Token.objects.create(user=bob, notes="Some notes")
        token.permissions.add(permission)
        token.permissions.add(permission2)

        # change the group's permissions
        group.permissions.remove(permission)

        # reload the token
        token = models.Token.objects.get(id=token.id)
        assert permission not in token.permissions.all()
        # it should still have this one though
        assert permission2 in token.permissions.all()
