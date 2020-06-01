# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.urls import reverse
from django.utils.encoding import smart_text

from crashstats.crashstats.tests.test_views import BaseTestViews


class TestViews(BaseTestViews):
    def test_supersearch_home(self):
        url = reverse("documentation:supersearch_home")
        response = self.client.get(url)
        assert response.status_code == 200
        assert "What is Super Search?" in smart_text(response.content)

    def test_supersearch_examples(self):
        url = reverse("documentation:supersearch_examples")
        response = self.client.get(url)
        assert response.status_code == 200
        assert "Examples" in smart_text(response.content)

    def test_supersearch_api(self):
        url = reverse("documentation:supersearch_api")
        response = self.client.get(url)
        assert response.status_code == 200
        assert "_results_number" in smart_text(response.content)
        assert "_aggs.*" in smart_text(response.content)
        assert "signature" in smart_text(response.content)

    def test_memory_dump_access_redirect(self):
        """Verify memory_dump_access url redirects

        This is the old url to the data access policy. In order to keep those links
        working, we need it to redirect to the new url.

        """
        response = self.client.get("/documentation/memory_dump_access/")
        assert response.status_code == 302
        assert response.url == reverse("documentation:protected_data_access")
