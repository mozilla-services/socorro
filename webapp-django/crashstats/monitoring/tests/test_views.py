# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import json

import pytest
import requests

from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import smart_str

from crashstats import productlib
from crashstats.cron import MAX_ONGOING
from crashstats.cron.models import Job as CronJob
from crashstats.monitoring.views import HeartbeatException
from crashstats.supersearch.models import SuperSearch
from socorro.lib import revision_data


class TestViews:
    def test_index(self, client):
        response = client.get(reverse("monitoring:index"))
        assert response.status_code == 200

        assert reverse("monitoring:cron_status") in smart_str(response.content)


class TestCrontabberStatusViews:
    def test_cron_status_ok(self, client, db):
        recently = timezone.now()
        CronJob.objects.create(
            app_name="job1", error_count=0, depends_on="", last_run=recently
        )

        response = client.get(reverse("monitoring:cron_status"))
        assert response.status_code == 200
        assert json.loads(response.content) == {"status": "ALLGOOD"}

    def test_cron_status_trouble(self, client, db):
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

        response = client.get(reverse("monitoring:cron_status"))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "Broken"
        assert data["broken"] == ["job1"]

    def test_cron_status_not_run_for_a_while(self, client, db):
        some_time_ago = timezone.now() - datetime.timedelta(minutes=MAX_ONGOING)
        CronJob.objects.create(
            app_name="job1", error_count=0, depends_on="", last_run=some_time_ago
        )
        CronJob.objects.create(
            app_name="job2", error_count=0, depends_on="job1", last_run=some_time_ago
        )

        response = client.get(reverse("monitoring:cron_status"))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "Stale"
        assert data["last_run"] == some_time_ago.isoformat()

    def test_cron_status_never_run(self, client, db):
        response = client.get(reverse("monitoring:cron_status"))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "Stale"


class TestDockerflowHeartbeatViews:
    def test_dockerflow_lbheartbeat(self, client, db, django_assert_num_queries):
        # Verify __lbheartbeat__ works
        with django_assert_num_queries(0):
            response = client.get(
                reverse("monitoring:dockerflow_lbheartbeat"), {"elb": "true"}
            )
            assert response.status_code == 200
            assert json.loads(response.content)["ok"] is True

    def test_heartbeat(self, client, db, monkeypatch):
        searches = []

        def mocked_supersearch_get(*args, **kwargs):
            searches.append(kwargs)
            assert kwargs["product"] == productlib.get_default_product().name
            assert kwargs["_results_number"] == 1
            assert kwargs["_columns"] == ["uuid"]
            return {
                "hits": [{"uuid": "12345"}],
                "facets": [],
                "total": 30002,
                "errors": [],
            }

        monkeypatch.setattr(SuperSearch, "get", mocked_supersearch_get)

        def mocked_requests_get(url, **params):
            return HttpResponse()

        monkeypatch.setattr(requests, "get", mocked_requests_get)

        # Verify the __heartbeat__ endpoint
        response = client.get(reverse("monitoring:dockerflow_heartbeat"))
        assert response.status_code == 200
        assert json.loads(response.content)["ok"] is True
        assert len(searches) == 1

    def test_supersearch_errors(self, client, db, monkeypatch):
        searches = []

        def mocked_supersearch_get(*args, **kwargs):
            searches.append(kwargs)
            assert kwargs["product"] == productlib.get_default_product().name
            assert kwargs["_results_number"] == 1
            assert kwargs["_columns"] == ["uuid"]
            return {
                "hits": [{"uuid": "12345"}],
                "facets": [],
                "total": 320,
                "errors": ["bad"],
            }

        monkeypatch.setattr(SuperSearch, "get", mocked_supersearch_get)
        with pytest.raises(HeartbeatException):
            client.get(reverse("monitoring:dockerflow_heartbeat"))


class TestDockerflowVersionView:
    def test_version_no_file(self, client, settings, tmpdir, monkeypatch):
        """Test with no version.json file"""
        # The tmpdir definitely doesn't have a version.json in it, so we use
        # that
        monkeypatch.setattr(revision_data, "VERSION_DATA_PATH", str(tmpdir))

        resp = client.get(reverse("monitoring:dockerflow_version"))
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/json"
        assert smart_str(resp.content) == "{}"

    def test_version_with_file(self, client, settings, tmpdir, monkeypatch):
        """Test with a version.json file"""
        text = '{"commit": "d6ac5a5d2acf99751b91b2a3ca651d99af6b9db3"}'

        # Create the version.json file in the tmpdir
        version_json = tmpdir / "version.json"
        version_json.write(text)

        monkeypatch.setattr(revision_data, "VERSION_DATA_PATH", str(tmpdir))

        resp = client.get(reverse("monitoring:dockerflow_version"))
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/json"
        assert smart_str(resp.content) == text


class TestBroken:
    def test_broken(self, client):
        with pytest.raises(Exception):
            client.get(reverse("monitoring:broken"))
