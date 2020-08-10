# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import json
from unittest import mock

import pytest

from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import smart_text

from crashstats import productlib
from crashstats.crashstats.tests.test_views import BaseTestViews, Response
from crashstats.cron import MAX_ONGOING
from crashstats.cron.models import Job as CronJob
from crashstats.monitoring.views import assert_supersearch_no_errors
from crashstats.supersearch.models import SuperSearch


class TestViews(BaseTestViews):
    def test_index(self):
        url = reverse("monitoring:index")
        response = self.client.get(url)
        assert response.status_code == 200

        assert reverse("monitoring:cron_status") in smart_text(response.content)


class TestCrontabberStatusViews(BaseTestViews):
    def test_cron_status_ok(self):
        recently = timezone.now()
        CronJob.objects.create(
            app_name="job1", error_count=0, depends_on="", last_run=recently
        )

        url = reverse("monitoring:cron_status")
        response = self.client.get(url)
        assert response.status_code == 200
        assert json.loads(response.content) == {"status": "ALLGOOD"}

    def test_cron_status_trouble(self):
        recently = timezone.now()
        CronJob.objects.create(
            app_name="job1", error_count=1, depends_on="", last_run=recently
        )
        CronJob.objects.create(
            app_name="job2", error_count=0, depends_on="job1", last_run=recently
        )
        CronJob.objects.create(
            app_name="job3", error_count=0, depends_on="job2", last_run=recently
        )
        CronJob.objects.create(
            app_name="job1b", error_count=0, depends_on="", last_run=recently
        )

        url = reverse("monitoring:cron_status")
        response = self.client.get(url)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "Broken"
        assert data["broken"] == ["job1"]

    def test_cron_status_not_run_for_a_while(self):
        some_time_ago = timezone.now() - datetime.timedelta(minutes=MAX_ONGOING)
        CronJob.objects.create(
            app_name="job1", error_count=0, depends_on="", last_run=some_time_ago
        )
        CronJob.objects.create(
            app_name="job2", error_count=0, depends_on="job1", last_run=some_time_ago
        )

        url = reverse("monitoring:cron_status")
        response = self.client.get(url)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "Stale"
        assert data["last_run"] == some_time_ago.isoformat()

    def test_cron_status_never_run(self):
        url = reverse("monitoring:cron_status")
        response = self.client.get(url)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "Stale"


class TestDockerflowHeartbeatViews(BaseTestViews):
    def test_dockerflow_lbheartbeat(self):
        # Verify __lbheartbeat__ works
        url = reverse("monitoring:dockerflow_lbheartbeat")
        response = self.client.get(url, {"elb": "true"})
        assert response.status_code == 200
        assert json.loads(response.content)["ok"] is True

        # Verify it doesn't run ay db queries
        self.assertNumQueries(0, self.client.get, url)

    @mock.patch("requests.get")
    @mock.patch("crashstats.monitoring.views.elasticsearch")
    def test_heartbeat(self, mocked_elasticsearch, rget):
        searches = []

        def mocked_supersearch_get(**params):
            searches.append(params)
            assert params["product"] == [productlib.get_default_product().name]
            assert params["_results_number"] == 1
            assert params["_columns"] == ["uuid"]
            return {
                "hits": [{"uuid": "12345"}],
                "facets": [],
                "total": 30002,
                "errors": [],
            }

        SuperSearch.implementation().get.side_effect = mocked_supersearch_get

        def mocked_requests_get(url, **params):
            return Response(True)

        rget.side_effect = mocked_requests_get

        # Verify the __heartbeat__ endpoint
        url = reverse("monitoring:dockerflow_heartbeat")
        response = self.client.get(url)
        assert response.status_code == 200
        assert json.loads(response.content)["ok"] is True
        assert len(searches) == 1

    def test_assert_supersearch_errors(self):
        searches = []

        def mocked_supersearch_get(**params):
            searches.append(params)
            assert params["product"] == [productlib.get_default_product().name]
            assert params["_results_number"] == 1
            assert params["_columns"] == ["uuid"]
            return {
                "hits": [{"uuid": "12345"}],
                "facets": [],
                "total": 320,
                "errors": ["bad"],
            }

        SuperSearch.implementation().get.side_effect = mocked_supersearch_get
        with pytest.raises(AssertionError):
            assert_supersearch_no_errors()

        assert len(searches) == 1


class TestDockerflowVersionView:
    def test_version_no_file(self, client, settings, tmpdir):
        """Test with no version.json file"""
        # The tmpdir definitely doesn't have a version.json in it, so we use
        # that
        settings.SOCORRO_ROOT = str(tmpdir)

        resp = client.get(reverse("monitoring:dockerflow_version"))
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/json"
        assert smart_text(resp.content) == "{}"

    def test_version_with_file(self, client, settings, tmpdir):
        """Test with a version.json file"""
        text = '{"commit": "d6ac5a5d2acf99751b91b2a3ca651d99af6b9db3"}'

        # Create the version.json file in the tmpdir
        version_json = tmpdir.join("version.json")
        version_json.write(text)

        settings.SOCORRO_ROOT = str(tmpdir)

        resp = client.get(reverse("monitoring:dockerflow_version"))
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/json"
        assert smart_text(resp.content) == text
