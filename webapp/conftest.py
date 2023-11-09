# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from django.core.cache import cache
from django.contrib.auth.models import Group


# Load the socorro/tests/conftest.py file so webapp tests can use those pytest fixtures
pytest_plugins = ["socorro.tests.conftest"]


def pytest_runtest_setup(item):
    # Clear the cache before every test; this reduces inter-test rate-limiting
    cache.clear()


class UserHelper:
    def __init__(self, django_user_model):
        self._django_user_model = django_user_model

    def create_user(self, username="example", password="pwd"):
        user = self._django_user_model.objects.create_user(
            username=username, password=password
        )
        return user

    def create_protected_user(self, username="example", password="pwd"):
        user = self.create_user(username=username, password=password)
        group = Group.objects.get(name="Hackers")
        user.groups.add(group)
        assert user.has_perm("crashstats.view_pii")
        assert user.has_perm("crashstats.view_rawdump")
        return user

    def create_protected_plus_user(self, username="example", password="pwd"):
        user = self.create_user(username=username, password=password)
        group = Group.objects.get(name="Hackers Plus")
        user.groups.add(group)
        assert user.has_perm("crashstats.view_pii")
        assert user.has_perm("crashstats.view_rawdump")
        assert user.has_perm("crashstats.run_custom_queries")
        return user


@pytest.fixture
def user_helper(django_user_model):
    return UserHelper(django_user_model)
