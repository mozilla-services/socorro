# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
import requests_mock

from django.urls import reverse

from crashstats.crashstats.tests.test_views import BaseTestViews


class SiteAdminTestViews(BaseTestViews):
    def _login(self, is_superuser=True):
        user = super()._login(username="lonnen", email="lonnen@example.com")
        user.is_superuser = is_superuser
        user.is_staff = is_superuser
        user.save()
        return user


class TestCrashMeNow(SiteAdminTestViews):
    def test_view(self):
        url = reverse("siteadmin:crash_me_now")
        response = self.client.get(url)
        assert response.status_code == 302

        self._login()
        with pytest.raises(ZeroDivisionError):
            self.client.get(url)


class TestSiteStatus(SiteAdminTestViews):
    @requests_mock.Mocker()
    def test_page_load(self, req_mock):
        """Basic test to make sure the page loads at all"""
        req_mock.get("http://localhost:8000/__version__", json={"foo": "bar"})

        url = reverse("siteadmin:site_status")
        response = self.client.get(url)
        assert response.status_code == 302

        self._login()
        response = self.client.get(url)
        assert response.status_code == 200


class TestAnalyzeModelFetches(SiteAdminTestViews):
    def test_analyze_model_fetches(self):
        """Basic test to make sure the page loads at all"""
        url = reverse("siteadmin:analyze_model_fetches")
        response = self.client.get(url)
        assert response.status_code == 302

        self._login()
        response = self.client.get(url)
        assert response.status_code == 200
