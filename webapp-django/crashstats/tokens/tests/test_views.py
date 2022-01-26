# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pyquery

from django.contrib.auth.models import User, Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.encoding import smart_str

from crashstats.crashstats.tests.test_views import BaseTestViews
from crashstats.tokens import models


class TestViews(BaseTestViews):
    def _login(self):
        user = User.objects.create_user("test", "test@example.com", "secret")
        assert self.client.login(username="test", password="secret")
        return user

    def _make_permission(self, name, codename=None):
        codename = codename or name.lower().replace(" ", "-")
        ct, __ = ContentType.objects.get_or_create(model="", app_label="crashstats")
        return Permission.objects.create(name=name, codename=codename, content_type=ct)

    def test_home_page(self):
        url = reverse("tokens:home")
        response = self.client.get(url, follow=False)
        assert response.url == reverse("crashstats:login") + "?next=%s" % url

        user = self._login()
        response = self.client.get(url)
        assert response.status_code == 200

        user.is_active = False
        user.save()
        response = self.client.get(url, follow=False)
        assert response.url == reverse("crashstats:login") + "?next=%s" % url

    def test_generate_new_token_form(self):
        url = reverse("tokens:home")
        user = self._login()
        response = self.client.get(url)
        assert response.status_code == 200
        # which choices you have depend in your owned permissions
        doc = pyquery.PyQuery(response.content)
        assert len(doc("#id_permissions")) == 0

        p1 = self._make_permission("Make a mess", "make-mess")
        p2 = self._make_permission("Clean Things", "cool-things")
        p3 = self._make_permission("Play with sticks", "play-with-sticks")
        group = Group.objects.create(name="Cool people")
        group.permissions.add(p1)
        group.permissions.add(p3)
        user.groups.add(group)

        assert user.has_perm("crashstats.%s" % p1.codename)
        assert not user.has_perm("crashstats.%s" % p2.codename)
        assert user.has_perm("crashstats.%s" % p3.codename)

        response = self.client.get(url)
        assert response.status_code == 200
        # which choices you have depend in your owned permissions
        doc = pyquery.PyQuery(response.content)
        assert len(doc("#id_permissions option")) == 2

    def test_generate_new_token(self):
        url = reverse("tokens:home")
        p1 = self._make_permission("Make a mess")
        p2 = self._make_permission("Clean Things")
        p3 = self._make_permission("Play with sticks")

        params = {"notes": " Some notes ", "permissions": [p1.pk, p3.pk]}
        response = self.client.post(url, params, follow=False)
        assert response.url == reverse("crashstats:login") + "?next=%s" % url

        # try again, but this time logged in
        user = self._login()
        response = self.client.post(url, {"notes": " Some notes "})
        assert response.status_code == 302
        (token,) = models.Token.objects.all()
        assert token.notes == "Some notes"
        assert token.permissions.all().count() == 0
        token.delete()

        # The 'notes' field can't been too long
        response = self.client.post(url, {"notes": "X" * 10000})
        assert response.status_code == 200
        assert "Text too long" in smart_str(response.content)

        group = Group.objects.create(name="Cool people")
        group.permissions.add(p1)
        group.permissions.add(p3)
        user.groups.add(group)

        response = self.client.post(
            url, {"notes": " Some notes ", "permissions": [p1.pk, p2.pk, p3.pk]}
        )
        # Because you tried to assign this token permissions you
        # don't have.
        assert response.status_code == 403

        response = self.client.post(
            url, {"notes": " Some notes ", "permissions": [p1.pk, p3.pk]}
        )
        assert response.status_code == 302
        (token,) = models.Token.objects.active().filter(user=user)
        assert set(token.permissions.all()) == {p1, p3}

        # this should be listed on the home page now
        response = self.client.get(url)
        assert response.status_code == 200
        assert 'data-key="' + smart_str(token.key) + '"' in smart_str(response.content)

    def test_delete_token(self):
        user = self._login()
        token1 = models.Token.objects.create(user=user, notes="Some note")
        other_user = User.objects.create(username="else")
        token_other_user = models.Token.objects.create(user=other_user)

        url = reverse("tokens:delete_token", args=(token1.pk,))
        # Just like a good logout endpoint, shouldn't be able to GET there.
        response = self.client.get(url)
        assert response.status_code == 405
        # It has to be post.
        response = self.client.post(url)
        assert response.status_code == 302
        assert not models.Token.objects.filter(notes="Some note")

        # but you can't delete someone elses
        url = reverse("tokens:delete_token", args=(token_other_user.pk,))
        response = self.client.post(url)
        assert response.status_code == 404
