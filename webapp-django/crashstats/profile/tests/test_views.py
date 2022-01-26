# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pyquery

from django.urls import reverse
from django.utils.encoding import smart_str

from crashstats.crashstats.signals import PERMISSIONS
from crashstats.crashstats.tests.test_views import BaseTestViews


class TestViews(BaseTestViews):
    def test_profile(self):
        url = reverse("profile:profile")

        # Test that the user must be logged in.
        response = self.client.get(url, follow=False)
        assert response.status_code == 302
        assert response.url == reverse("crashstats:login") + "?next=%s" % url

        # Now log in for the remaining tests.
        user = self._login()

        # Check email is there.
        response = self.client.get(url)
        assert response.status_code == 200
        assert "test@example.com" in smart_str(response.content)

        # Make some permissions.
        self._create_group_with_permission("view_pii", "Group A")
        group_b = self._create_group_with_permission("view_exploitability", "Group B")
        user.groups.add(group_b)
        assert not user.has_perm("crashstats.view_pii")
        assert user.has_perm("crashstats.view_exploitability")

        # Test permissions.
        response = self.client.get(url)
        assert PERMISSIONS["view_pii"] in smart_str(response.content)
        assert PERMISSIONS["view_exploitability"] in smart_str(response.content)
        doc = pyquery.PyQuery(response.content)
        for row in doc("table.permissions tbody tr"):
            cells = []
            for td in doc("td", row):
                cells.append(td.text.strip())
            if cells[0] == PERMISSIONS["view_pii"]:
                assert cells[1] == "No"
            elif cells[0] == PERMISSIONS["view_exploitability"]:
                assert cells[1] == "Yes!"

        # If the user ceases to be active, this page should redirect instead
        user.is_active = False
        user.save()
        response = self.client.get(url, follow=False)
        assert response.status_code == 302
        assert response.url == reverse("crashstats:login") + "?next=%s" % url

    def test_homepage_profile_footer(self):
        """This test isn't specifically for the profile page, because
        it ultimately tests the crashstats_base.html template. But
        that template has a link to the profile page."""
        url = reverse("crashstats:product_home", args=("WaterWolf",))
        response = self.client.get(url)
        assert response.status_code == 200
        profile_url = reverse("profile:profile")
        assert profile_url not in smart_str(response.content)

        # Render again when logged in
        user = self._login()
        response = self.client.get(url)
        assert response.status_code == 200
        assert profile_url in smart_str(response.content)

        # Render again when no longer an active user
        user.is_active = False
        user.save()
        response = self.client.get(url)
        assert response.status_code == 200
        assert profile_url not in smart_str(response.content)
