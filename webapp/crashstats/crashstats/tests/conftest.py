# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import copy
import json
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache

from crashstats import libproduct
from crashstats.crashstats.signals import PERMISSIONS
from crashstats.crashstats.tests.testbase import DjangoTestCase
from crashstats.supersearch.libsupersearch import get_supersearch_fields


class Response:
    def __init__(self, content=None, status_code=200):
        self.raw = content
        if not isinstance(content, str):
            content = json.dumps(content)
        self.content = content.strip()
        self.status_code = status_code

    @property
    def text(self):
        # Similar to content but with the right encoding
        return str(self.content, "utf-8")

    def json(self):
        return self.raw


class ProductVersionsMixin:
    """Mixin for DjangoTestCase tests to create products and versions

    This creates products.

    This mocks the function that sets the versions in the response context
    and the versions dropdown in the navbar.

    The versions dropdown is generated by get_versions_for_product which does
    a Super Search. This lets you mock out that function to return default
    versions or specific versions.

    Usage::

        class TestViews(TestCase, ProductVersionsMixin):
            def test_something(self):
                # ...
                pass

            def test_something_else(self):
                self.set_product_versions(['64.0', '63.0', '62.0'])
                # ...
                pass

    """

    def setUp(self):
        super().setUp()
        cache.clear()

        # Hard-code products for testing
        libproduct._PRODUCTS = [
            libproduct.Product(
                name="WaterWolf",
                description="Test browser",
                home_page_sort=1,
                featured_versions=["auto"],
                in_buildhub=True,
                bug_links=[["WaterWolf", "create-waterwolf-bug"]],
                product_home_links=[["link", "http://example.com/"]],
            ),
            libproduct.Product(
                name="NightTrain",
                description="",
                home_page_sort=2,
                featured_versions=["auto"],
                in_buildhub=False,
                bug_links=[["NightTrain", "create-nighttrain-bug"]],
                product_home_links=[],
            ),
            libproduct.Product(
                name="SeaMonkey",
                description="",
                home_page_sort=3,
                featured_versions=["auto"],
                in_buildhub=False,
                bug_links=[["SeaMonkey", "create-seamonkey-bug"]],
                product_home_links=[],
            ),
        ]

        # Create product versions
        self.mock_gvfp_patcher = mock.patch(
            "crashstats.crashstats.utils.get_versions_for_product"
        )
        self.mock_gvfp = self.mock_gvfp_patcher.start()
        self.set_product_versions(["20.0", "19.1", "19.0", "18.0"])

    def tearDown(self):
        libproduct._PRODUCTS = []
        self.mock_gvfp_patcher.stop()
        super().tearDown()

    def set_product_versions(self, versions):
        self.mock_gvfp.return_value = versions


class SuperSearchFieldsMock:
    def setUp(self):
        super().setUp()

        def mocked_supersearchfields(**params):
            results = copy.deepcopy(get_supersearch_fields())
            # to be realistic we want to introduce some dupes that have a
            # different key but its `in_database_name` is one that is already
            # in the hardcoded list (the baseline)
            results["accessibility2"] = results["accessibility"]
            return results

        self.mock_ssf_get_patcher = mock.patch(
            "crashstats.supersearch.models.SuperSearchFields.get"
        )
        self.mock_ssf_fields_get = self.mock_ssf_get_patcher.start()
        self.mock_ssf_fields_get.side_effect = mocked_supersearchfields

    def tearDown(self):
        self.mock_ssf_get_patcher.stop()
        super().tearDown()


class BaseTestViews(ProductVersionsMixin, SuperSearchFieldsMock, DjangoTestCase):
    def setUp(self):
        super().setUp()

        # Tests assume and require a non-persistent cache backend
        assert "LocMemCache" in settings.CACHES["default"]["BACKEND"]

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def _add_permission(self, user, codename, group_name="Hackers"):
        group = self._create_group_with_permission(codename)
        user.groups.add(group)

    def _create_group_with_permission(self, permissions, group_name="Group"):
        if not isinstance(permissions, list):
            permissions = [permissions]
        appname = "crashstats"
        ct, _ = ContentType.objects.get_or_create(model="", app_label=appname)
        group, _ = Group.objects.get_or_create(name=group_name)

        for permission in permissions:
            obj, _ = Permission.objects.get_or_create(
                codename=permission, name=PERMISSIONS[permission], content_type=ct
            )
            group.permissions.add(obj)
        return group

    @staticmethod
    def only_certain_columns(hits, columns):
        """Return new list where dicts only have specified keys"""
        return [{k: x[k] for k in x if k in columns} for x in hits]
