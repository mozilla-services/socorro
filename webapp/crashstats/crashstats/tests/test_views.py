# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import copy
from io import StringIO
import json
import re
from unittest import mock

import requests_mock
import pyquery
from markus.testing import MetricsMock

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.cache import cache
from django.urls import reverse
from django.utils.encoding import smart_str
from django.test.client import RequestFactory
from django.test.utils import override_settings

from crashstats.crashstats import models
from crashstats.crashstats.tests.conftest import BaseTestViews, Response
from socorro import settings as socorro_settings
from socorro.external.boto.crashstorage import build_keys, dict_to_str
from socorro.lib.libdatetime import date_to_string
from socorro.lib.libooid import create_new_ooid, date_from_ooid
from socorro.lib.libsocorrodataschema import get_schema, validate_instance


RAW_CRASH_SCHEMA = get_schema("raw_crash.schema.yaml")
PROCESSED_CRASH_SCHEMA = get_schema("processed_crash.schema.yaml")


_SAMPLE_META = {
    "InstallTime": "1339289895",
    "Theme": "classic/1.0",
    "Version": "5.0a1",
    "Vendor": "Mozilla",
    "URL": "someaddress.com",
    "Comments": "this is a comment",
    "version": 2,
}


_SAMPLE_PROCESSED = {
    "addons_checked": None,
    "address": "0x8",
    "build": "20120609030536",
    "client_crash_date": "2022-06-11T06:08:40",
    "completed_datetime": "2022-06-11T06:08:50",
    "cpu_arch": "amd64",
    "cpu_info": "AuthenticAMD family 20 model 2 stepping 0 | 2 ",
    "crashing_thread": None,
    "date_processed": "2022-06-11T06:08:44",
    "hangid": None,
    "id": 383569625,
    "json_dump": {
        "status": "OK",
        "threads": [],
    },
    "last_crash": 371342,
    "os_name": "Mac OS X",
    "os_pretty_version": "OS X 10.11",
    "os_version": "10.6.8 10K549",
    "process_type": "parent",
    "product": "WaterWolf",
    "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
    "release_channel": "nightly",
    "ReleaseChannel": "nightly",
    "signature": "FakeSignature1",
    "success": True,
    "uptime": 14693,
    "uuid": "11cb72f5-eb28-41e1-a8e4-849982120611",
    "version": "5.0a1",
    # protected data
    "user_comments": "this is a comment",
}


def build_crash_data():
    crash_id = create_new_ooid()

    raw_crash = copy.deepcopy(_SAMPLE_META)
    processed_crash = copy.deepcopy(_SAMPLE_PROCESSED)
    processed_crash["uuid"] = crash_id
    processed_crash["date_processed"] = date_to_string(date_from_ooid(crash_id))
    return crash_id, raw_crash, processed_crash


def upload_crash_data(storage_helper, raw_crash, processed_crash):
    """Validate crash data and upload it to crash bucket"""
    crash_id = processed_crash["uuid"]
    bucket = storage_helper.get_crashstorage_bucket()

    validate_instance(raw_crash, RAW_CRASH_SCHEMA)
    raw_key = build_keys("raw_crash", crash_id)[0]
    storage_helper.upload(
        bucket_name=bucket, key=raw_key, data=dict_to_str(raw_crash).encode("utf-8")
    )

    validate_instance(processed_crash, PROCESSED_CRASH_SCHEMA)
    processed_key = build_keys("processed_crash", crash_id)[0]
    storage_helper.upload(
        bucket_name=bucket,
        key=processed_key,
        data=dict_to_str(processed_crash).encode("utf-8"),
    )


SAMPLE_SIGNATURE_SUMMARY = {
    "reports": {
        "products": [
            {
                "version_string": "33.0a2",
                "percentage": "57.542",
                "report_count": 103,
                "product_name": "Firefox",
            }
        ],
        "uptime": [{"category": "< 1 min", "percentage": "29.126", "report_count": 30}],
        "architecture": [
            {"category": "x86", "percentage": "100.000", "report_count": 103}
        ],
        "graphics": [
            {
                "report_count": 24,
                "adapter_name": None,
                "vendor_hex": "0x8086",
                "percentage": "23.301",
                "vendor_name": None,
                "adapter_hex": "0x0166",
            }
        ],
        "distinct_install": [
            {
                "crashes": 103,
                "version_string": "33.0a2",
                "product_name": "Firefox",
                "installations": 59,
            }
        ],
        "devices": [
            {
                "cpu_abi": "XXX",
                "manufacturer": "YYY",
                "model": "ZZZ",
                "version": "1.2.3",
                "report_count": 52311,
                "percentage": "48.440",
            }
        ],
        "os": [{"category": "Windows 8.1", "percentage": "55.340", "report_count": 57}],
        "process_type": [
            {"category": "Browser", "percentage": "100.000", "report_count": 103}
        ],
    }
}


class TestRobotsTxt:
    def test_robots_txt(self, settings, client):
        settings.ENGAGE_ROBOTS = True
        url = "/robots.txt"
        response = client.get(url)
        assert response.status_code == 200
        assert response["Content-Type"] == "text/plain"
        assert "Allow: /" in smart_str(response.content)

    @override_settings(ENGAGE_ROBOTS=False)
    def test_robots_txt_disengage(self, settings, client):
        settings.ENGAGE_ROBOTS = False
        url = "/robots.txt"
        response = client.get(url)
        assert response.status_code == 200
        assert response["Content-Type"] == "text/plain"
        assert "Disallow: /" in smart_str(response.content)


class TestFavicon:
    def test_favicon(self, client):
        response = client.get("/favicon.ico")
        assert response.status_code == 200
        # the content type is dependent on the OS
        expected = (
            "image/x-icon",  # most systems
            "image/vnd.microsoft.icon",  # jenkins for example
        )
        assert response["Content-Type"] in expected


class Test500:
    def test_html(self):
        root_urlconf = __import__(
            settings.ROOT_URLCONF, globals(), locals(), ["urls"], 0
        )
        # ...so that we can access the 'handler500' defined in there
        par, end = root_urlconf.handler500.rsplit(".", 1)
        # ...which is an importable reference to the real handler500 function
        views = __import__(par, globals(), locals(), [end], 0)
        # ...and finally we have the handler500 function at hand
        handler500 = getattr(views, end)

        # to make a mock call to the django view functions you need a request
        fake_request = RequestFactory().request(**{"wsgi.input": StringIO("")})

        # the reason for first causing an exception to be raised is because
        # the handler500 function is only called by django when an exception
        # has been raised which means sys.exc_info() is something.
        try:
            raise NameError("sloppy code")
        except NameError:
            # do this inside a frame that has a sys.exc_info()
            response = handler500(fake_request)
            assert response.status_code == 500
            assert "Internal Server Error" in smart_str(response.content)
            assert 'id="products_select"' not in smart_str(response.content)

    def test_json(self):
        root_urlconf = __import__(
            settings.ROOT_URLCONF, globals(), locals(), ["urls"], 0
        )
        par, end = root_urlconf.handler500.rsplit(".", 1)
        views = __import__(par, globals(), locals(), [end], 0)
        handler500 = getattr(views, end)

        fake_request = RequestFactory().request(**{"wsgi.input": StringIO("")})
        # This is what the utils.json_view decorator sets on views
        # that should eventually return JSON.
        fake_request._json_view = True

        try:
            raise NameError("sloppy code")
        except NameError:
            # do this inside a frame that has a sys.exc_info()
            response = handler500(fake_request)
            assert response.status_code == 500
            assert response["Content-Type"] == "application/json"
            result = json.loads(response.content)
            assert result["error"] == "Internal Server Error"
            assert result["path"] == "/"
            assert result["query_string"] is None


class Test404:
    def test_handler404(self, client):
        response = client.get("/fillbert/mcpicklepants")
        assert response.status_code == 404
        assert "The requested page could not be found." in smart_str(response.content)

    def test_handler404_json(self, client):
        # Just need any view that has the json_view decorator on it.
        url = reverse("api:model_wrapper", args=("Unknown",))
        response = client.get(url, {"foo": "bar"})
        assert response.status_code == 404
        assert response["Content-Type"] == "application/json"
        result = json.loads(response.content)
        assert result["error"] == "No service called 'Unknown'"


class TestContributeJson:
    def test_view(self, client):
        response = client.get("/contribute.json")
        assert response.status_code == 200
        assert json.loads(response.getvalue())
        assert response["Content-Type"] == "application/json"


class TestFaviconIco:
    def test_view(self, client):
        response = client.get("/favicon.ico")
        assert response.status_code == 200
        assert response["Content-Type"] == "image/vnd.microsoft.icon"


class Test_buginfo:
    def test_buginfo(self, client):
        with requests_mock.Mocker(real_http=False) as mock_requests:
            bugzilla_results = {
                "bugs": [
                    {
                        "id": 907277,
                        "status": "NEW",
                        "resolution": "",
                        "summary": "Some Summary",
                    },
                    {
                        "id": 1529342,
                        "status": "NEW",
                        "resolution": "",
                        "summary": "Other Summary",
                    },
                ]
            }
            mock_requests.get(
                (
                    "http://bugzilla.example.com/rest/bug?"
                    + "id=907277,1529342&include_fields=summary,status,id,resolution"
                ),
                text=json.dumps(bugzilla_results),
            )

            url = reverse("crashstats:buginfo")
            response = client.get(url)
            assert response.status_code == 400

            response = client.get(url, {"bug_ids": ""})
            assert response.status_code == 400

            response = client.get(url, {"bug_ids": " 907277, 1529342 "})
            assert response.status_code == 200

            struct = json.loads(response.content)
            assert struct["bugs"]
            assert struct["bugs"][0]["summary"] == "Some Summary"

    @mock.patch("requests.Session")
    def test_buginfo_with_caching(self, rsession, client):
        url = reverse("crashstats:buginfo")

        def mocked_get(url, **options):
            if "bug?id=987,654" in url:
                return Response(
                    {
                        "bugs": [
                            {
                                "id": "987",
                                "product": "allizom.org",
                                "summary": "Summary 1",
                            },
                            {
                                "id": "654",
                                "product": "mozilla.org",
                                "summary": "Summary 2",
                            },
                        ]
                    }
                )

            raise NotImplementedError(url)

        rsession().get.side_effect = mocked_get

        response = client.get(
            url, {"bug_ids": "987,654", "include_fields": "product,summary"}
        )
        assert response.status_code == 200
        struct = json.loads(response.content)

        assert struct["bugs"][0]["product"] == "allizom.org"
        assert struct["bugs"][0]["summary"] == "Summary 1"
        assert struct["bugs"][0]["id"] == "987"
        assert struct["bugs"][1]["product"] == "mozilla.org"
        assert struct["bugs"][1]["summary"] == "Summary 2"
        assert struct["bugs"][1]["id"] == "654"

        # expect to be able to find this in the cache now
        cache_key = "buginfo:987"
        assert cache.get(cache_key) == struct["bugs"][0]


class Test_quick_search:
    def test_quick_search(self, client):
        url = reverse("crashstats:quick_search")

        # Test with no parameter.
        response = client.get(url)
        assert response.status_code == 302
        target = reverse("supersearch:search")
        assert response["location"].endswith(target)

        # Test with a signature.
        response = client.get(url, {"query": "moz"})
        assert response.status_code == 302
        target = reverse("supersearch:search") + "?signature=~moz"
        assert response["location"].endswith(target)

        # Test with a crash_id.
        crash_id = "1234abcd-ef56-7890-ab12-abcdef130802"
        response = client.get(url, {"query": crash_id})
        assert response.status_code == 302
        target = reverse("crashstats:report_index", kwargs=dict(crash_id=crash_id))
        assert response["location"].endswith(target)

        # Test a simple search containing a crash id and spaces
        crash_id = "   1234abcd-ef56-7890-ab12-abcdef130802 "
        response = client.get(url, {"query": crash_id})
        assert response.status_code == 302
        assert response["location"].endswith(target)

    def test_quick_search_metrics(self, client):
        url = reverse("crashstats:quick_search")
        with MetricsMock() as metrics_mock:
            response = client.get(url)
        assert response.status_code == 302
        metrics_mock.assert_timing(
            "webapp.view.pageview",
            tags=[
                "ajax:false",
                "api:false",
                "path:/search/quick/",
                "status:302",
            ],
        )


class Test_report_index:
    def test_report_index(self, client, db, storage_helper, user_helper):
        json_dump = {
            "system_info": {
                "os": "Mac OS X",
                "os_ver": "10.6.8 10K549",
                "cpu_arch": "amd64",
                "cpu_info": "family 6 mod",
                "cpu_count": 1,
            },
        }

        crash_id, raw_crash, processed_crash = build_crash_data()
        processed_crash["json_dump"] = json_dump
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        models.BugAssociation.objects.create(bug_id=222222, signature="FakeSignature1")
        models.BugAssociation.objects.create(bug_id=333333, signature="FakeSignature1")
        models.BugAssociation.objects.create(
            bug_id=444444, signature="Other FakeSignature"
        )

        url = reverse("crashstats:report_index", args=(crash_id,))
        with MetricsMock() as metrics_mock:
            response = client.get(url)

        assert response.status_code == 200
        # which bug IDs appear is important and the order matters too
        content = smart_str(response.content)
        assert (
            -1
            == content.find("444444")
            < content.find("333333")
            < content.find("222222")
        )

        assert "FakeSignature1" in content
        assert crash_id in content

        # Verify the "AMD CPU bug" marker is there.
        assert "Possible AMD CPU bug related crash report" in content

        assert processed_crash["user_comments"] not in content
        assert raw_crash["URL"] not in content
        assert (
            "You need to be logged in and have access to protected data to see "
            "links to crash report data."
        ) in content

        # The pretty platform version should appear.
        assert "OS X 10.11" in content

        # the protected data will appear if we log in
        user = user_helper.create_protected_user()
        client.force_login(user)

        response = client.get(url)
        content = smart_str(response.content)
        assert processed_crash["user_comments"] in content
        assert raw_crash["URL"] in content
        assert response.status_code == 200

        # Ensure fields have their description in title.
        assert "No description for this field." in content
        # NOTE(willkg): This is the description of the "address" field. If we ever
        # change that we'll need to update this to another description that
        # shows up.
        assert "The address where the crashing thread crashed." in content

        if socorro_settings.CLOUD_PROVIDER == "AWS":
            metrics_mock.assert_timing(
                "webapp.view.pageview",
                tags=[
                    "ajax:false",
                    "api:false",
                    "path:/report/index/_crashid_crash_id_",
                    "status:200",
                ],
            )
        else:
            records = metrics_mock.filter_records(
                "timing", stat="socorro.webapp.view.pageview"
            )
            assert len(records) == 1
            record_tags = set(records[0].tags)
            expected_tags = {
                "ajax:false",
                "api:false",
                "path:/report/index/_crashid_crash_id_",
                "status:200",
            }

            assert expected_tags.issubset(record_tags)

        # If the user ceases to be active, these PII fields should disappear
        user.is_active = False
        user.save()
        response = client.get(url)
        assert response.status_code == 200
        content = smart_str(response.content)
        assert processed_crash["user_comments"] not in content
        assert raw_crash["URL"] not in content

    def test_raw_crash_unicode_key(self, client, db, storage_helper, user_helper):
        crash_id, raw_crash, processed_crash = build_crash_data()
        # NOTE(willkg): The collector doesn't remove non-ascii keys currently. At some
        # point, it probably should.
        raw_crash["Pr\u00e9nom"] = "Peter"
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        # Log in with protected data access to view all data
        user = user_helper.create_protected_user()
        client.force_login(user)

        url = reverse("crashstats:report_index", args=(crash_id,))
        response = client.get(url)
        assert response.status_code == 200
        assert "Pr\u00e9nom" in smart_str(response.content)

    def test_additional_raw_dump_links(self, client, db, storage_helper, user_helper):
        json_dump = {
            "system_info": {
                "os": "Mac OS X",
                "os_ver": "10.6.8 10K549",
                "cpu_arch": "amd64",
                "cpu_info": "family 6 mod",
                "cpu_count": 1,
            }
        }

        crash_id, raw_crash, processed_crash = build_crash_data()
        raw_crash["metadata"] = {
            "dump_checksums": {
                "upload_file_minidump": "xxx",
                "upload_file_minidump_foo": "xxx",
                "upload_file_minidump_bar": "xxx",
            },
        }
        processed_crash["json_dump"] = json_dump
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        # Expect these urls
        raw_crash_url = "%s?crash_id=%s" % (
            reverse("api:model_wrapper", kwargs={"model_name": "RawCrash"}),
            crash_id,
        )
        dump_url = "%s?crash_id=%s&amp;format=raw&amp;name=upload_file_minidump" % (
            reverse("api:model_wrapper", kwargs={"model_name": "RawCrash"}),
            crash_id,
        )

        # Request url as anonymous user--urls should not appear
        url = reverse("crashstats:report_index", args=(crash_id,))
        response = client.get(url)
        assert response.status_code == 200
        assert raw_crash_url not in smart_str(response.content)
        assert dump_url not in smart_str(response.content)

        # Log in as a user without protected data access--urls should not appear
        user = user_helper.create_user(username="user1")
        client.force_login(user)
        response = client.get(url)
        assert response.status_code == 200
        assert raw_crash_url not in smart_str(response.content)
        assert dump_url not in smart_str(response.content)
        client.logout()

        # Log in as a user with protected data access--urls should appear
        user = user_helper.create_protected_user(username="user2")
        client.force_login(user)
        response = client.get(url)
        assert response.status_code == 200
        assert raw_crash_url in smart_str(response.content)
        assert dump_url in smart_str(response.content)

        # Check that the other links are there
        foo_dump_url = (
            "%s?crash_id=%s&amp;format=raw&amp;name=upload_file_minidump_foo"
            % (
                reverse("api:model_wrapper", kwargs={"model_name": "RawCrash"}),
                crash_id,
            )
        )
        assert foo_dump_url in smart_str(response.content)
        bar_dump_url = (
            "%s?crash_id=%s&amp;format=raw&amp;name=upload_file_minidump_bar"
            % (
                reverse("api:model_wrapper", kwargs={"model_name": "RawCrash"}),
                crash_id,
            )
        )
        assert bar_dump_url in smart_str(response.content)

    def test_symbol_url_in_modules(self, client, db, storage_helper, user_helper):
        json_dump = {
            "status": "OK",
            "threads": [],
            "modules": [
                {
                    "base_addr": "0x769c0000",
                    "code_id": "411096B9b3000",
                    "debug_file": "userenv.pdb",
                    "debug_id": "C72199CE55A04CD2A965557CF1D97F4E2",
                    "end_addr": "0x76a73000",
                    "filename": "userenv.dll",
                    "version": "5.1.2600.2180",
                },
                {
                    "base_addr": "0x76b40000",
                    "code_id": "411096D62d000",
                    "debug_file": "winmm.pdb",
                    "debug_id": "4FC9F179964745CAA3C78D6FADFC28322",
                    "end_addr": "0x76b6d000",
                    "filename": "winmm.dll",
                    "loaded_symbols": True,
                    "symbol_disk_cache_hit": True,
                    "symbol_url": "https://s3.example.com/winmm.sym",
                    "version": "5.1.2600.2180",
                },
            ],
        }

        crash_id, raw_crash, processed_crash = build_crash_data()
        raw_crash["additional_minidumps"] = "foo, bar,"
        processed_crash["json_dump"] = json_dump
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        url = reverse("crashstats:report_index", args=(crash_id,))
        response = client.get(url)
        assert response.status_code == 200

        assert 'id="modules-list"' in smart_str(response.content)
        assert '<a href="https://s3.example.com/winmm.sym">winmm.dll</a>' in smart_str(
            response.content
        )

    def test_cert_subject_in_modules(self, client, db, storage_helper):
        json_dump = {
            "status": "OK",
            "threads": [],
            "modules": [
                {
                    "base_addr": "0x769c0000",
                    "code_id": "411096B9b3000",
                    "debug_file": "userenv.pdb",
                    "debug_id": "C72199CE55A04CD2A965557CF1D97F4E2",
                    "end_addr": "0x76a73000",
                    "filename": "userenv.dll",
                    "version": "5.1.2600.2180",
                },
                {
                    "base_addr": "0x76b40000",
                    "cert_subject": "Microsoft Windows",
                    "code_id": "411096D62d000",
                    "debug_file": "winmm.pdb",
                    "debug_id": "4FC9F179964745CAA3C78D6FADFC28322",
                    "end_addr": "0x76b6d000",
                    "filename": "winmm.dll",
                    "loaded_symbols": True,
                    "symbol_disk_cache_hit": True,
                    "symbol_url": "https://s3.example.com/winmm.sym",
                    "version": "5.1.2600.2180",
                },
            ],
            "modules_contains_cert_info": True,
        }

        crash_id, raw_crash, processed_crash = build_crash_data()
        processed_crash["json_dump"] = json_dump
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        url = reverse("crashstats:report_index", args=(crash_id,))
        response = client.get(url)
        assert response.status_code == 200

        assert 'id="modules-list"' in smart_str(response.content)
        assert re.search(
            r"<td>userenv\.pdb</td>\s*?<td></td>", smart_str(response.content)
        )
        assert re.search(
            r"<td>winmm\.pdb</td>\s*?<td>Microsoft Windows</td>",
            smart_str(response.content),
        )

    def test_unloaded_modules(self, client, db, storage_helper):
        json_dump = {
            "status": "OK",
            "threads": [],
            "unloaded_modules": [
                {
                    "base_addr": "0x56ea0000",
                    "cert_subject": None,
                    "code_id": "206ce69b6000",
                    "end_addr": "0x56ea6000",
                    "filename": "KBDUS.DLL",
                },
                {
                    "base_addr": "0x642c0000",
                    "cert_subject": "Microsoft Windows",
                    "code_id": "e00ed7eff000",
                    "end_addr": "0x642cf000",
                    "filename": "resourcepolicyclient.dll",
                },
            ],
        }

        crash_id, raw_crash, processed_crash = build_crash_data()
        processed_crash["json_dump"] = json_dump
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        url = reverse("crashstats:report_index", args=(crash_id,))
        response = client.get(url)
        assert response.status_code == 200

        assert 'id="unloaded-modules-list"' in smart_str(response.content)
        # Assert the first unloaded module filename shows up
        assert "<td>KBDUS.DLL</td>" in smart_str(response.content)
        # Assert that the second unloaded module cert subject shows up
        assert "<td>Microsoft Windows</td>" in smart_str(response.content)

    def test_shutdownhang_signature(self, client, db, storage_helper):
        json_dump = {
            "crash_info": {"crashing_thread": 2},
            "status": "OK",
            "threads": [
                {"frame_count": 0, "frames": []},
                {"frame_count": 0, "frames": []},
                {"frame_count": 0, "frames": []},
            ],
            "modules": [],
        }

        crash_id, raw_crash, processed_crash = build_crash_data()
        processed_crash["json_dump"] = json_dump
        processed_crash["crashing_thread"] = json_dump["crash_info"]["crashing_thread"]
        processed_crash["json_dump"] = json_dump
        processed_crash["signature"] = "shutdownhang | foo::bar()"
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        url = reverse("crashstats:report_index", args=(crash_id,))
        response = client.get(url)
        assert response.status_code == 200

        assert "Crashing Thread (2)" not in smart_str(response.content)
        assert "Crashing Thread (0)" in smart_str(response.content)

    def test_no_crashing_thread(self, client, db, storage_helper):
        # If the json_dump has no crashing thread available, do not display a
        # specific crashing thread, but instead display all threads.
        json_dump = {
            "crash_info": {},
            "status": "OK",
            "threads": [
                {"frame_count": 0, "frames": []},
                {"frame_count": 0, "frames": []},
                {"frame_count": 0, "frames": []},
            ],
            "modules": [],
        }

        crash_id, raw_crash, processed_crash = build_crash_data()
        processed_crash["json_dump"] = json_dump
        processed_crash["signature"] = "foo::bar()"
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        url = reverse("crashstats:report_index", args=(crash_id,))
        response = client.get(url)
        assert response.status_code == 200

        assert "Crashing Thread" not in smart_str(response.content)
        assert "Thread 0" in smart_str(response.content)
        assert "Thread 1" in smart_str(response.content)
        assert "Thread 2" in smart_str(response.content)

    def test_crashing_thread_table(self, client, db, storage_helper):
        json_dump = {
            "crash_info": {"crashing_thread": 0},
            "status": "OK",
            "threads": [
                {
                    "frame_count": 0,
                    "frames": [
                        {
                            "frame": 0,
                            "file": "hg:hg.mozilla.org/000",
                            "function": "js::something",
                            "function_offset": "0x00",
                            "line": 1000,
                            "module": "xul.dll",
                            "module_offset": "0x000000",
                            "offset": "0x00000000",
                            "registers": {
                                "eax": "0x00000001",
                                "ebp": "0x00000002",
                                "ebx": "0x00000003",
                                "ecx": "0x00000004",
                                "edi": "0x00000005",
                                "edx": "0x00000006",
                                "efl": "0x00000007",
                                "eip": "0x00000008",
                                "esi": "0x00000009",
                                "esp": "0x0000000a",
                            },
                            "trust": "context",
                        },
                        {
                            "frame": 1,
                            "file": "hg:hg.mozilla.org/bbb",
                            "function": "js::somethingelse",
                            "function_offset": "0xbb",
                            "line": 1001,
                            "module": "xul.dll",
                            "module_offset": "0xbbbbbb",
                            "offset": "0xbbbbbbbb",
                            "trust": "frame_pointer",
                        },
                        {
                            "file": "hg:hg.mozilla.org/ccc",
                            "frame": 2,
                            "function": "js::thirdthing",
                            "function_offset": "0xcc",
                            "line": 1002,
                            "module": "xul.dll",
                            "module_offset": "0xcccccc",
                            "offset": "0xcccccccc",
                            "trust": "frame_pointer",
                        },
                    ],
                }
            ],
            "modules": [],
        }

        crash_id, raw_crash, processed_crash = build_crash_data()
        processed_crash["json_dump"] = json_dump
        processed_crash["crashing_thread"] = json_dump["crash_info"]["crashing_thread"]
        processed_crash["signature"] = "shutdownhang | foo::bar()"
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        url = reverse("crashstats:report_index", args=(crash_id,))
        response = client.get(url)
        assert response.status_code == 200

        # Make sure the "trust" parts show up in the page
        assert "context" in smart_str(response.content)
        assert "frame_pointer" in smart_str(response.content)

    def test_inlines(self, client, db, storage_helper):
        json_dump = {
            "crash_info": {"crashing_thread": 0},
            "status": "OK",
            "threads": [
                {
                    "frame_count": 0,
                    "frames": [
                        {
                            "frame": 0,
                            "file": "hg:hg.mozilla.org/000",
                            "function": "js::something",
                            "function_offset": "0x00",
                            "inlines": [
                                {
                                    "file": "hg:hg.mozilla.org/inlinefile1.cpp",
                                    "function": "InlineFunction1",
                                    "line": 381,
                                },
                                {
                                    "file": "hg:hg.mozilla.org/inlinefile2.cpp",
                                    "function": "InlineFunction2",
                                    "line": 374,
                                },
                            ],
                            "line": 1000,
                            "module": "xul.dll",
                            "module_offset": "0x000000",
                            "offset": "0x00000000",
                            "trust": "context",
                        },
                        {
                            "frame": 1,
                            "file": "hg:hg.mozilla.org/bbb",
                            "function": "js::somethingelse",
                            "function_offset": "0xbb",
                            "line": 1001,
                            "module": "xul.dll",
                            "module_offset": "0xbbbbbb",
                            "offset": "0xbbbbbbbb",
                            "trust": "frame_pointer",
                        },
                    ],
                }
            ],
            "modules": [],
        }

        crash_id, raw_crash, processed_crash = build_crash_data()

        processed_crash["crashing_thread"] = json_dump["crash_info"]["crashing_thread"]
        processed_crash["json_dump"] = json_dump
        processed_crash["signature"] = "shutdownhang | foo::bar()"

        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        url = reverse("crashstats:report_index", args=(crash_id,))
        response = client.get(url)
        assert response.status_code == 200

        # Make sure inline function show up
        assert "InlineFunction1" in smart_str(response.content)
        assert "inlinefile1.cpp:381" in smart_str(response.content)
        assert "InlineFunction2" in smart_str(response.content)
        assert "inlinefile2.cpp:374" in smart_str(response.content)

    def test_java_exception_table_not_logged_in(self, client, db, storage_helper):
        java_exception = {
            "exception": {
                "values": [
                    {
                        "stacktrace": {
                            "frames": [
                                {
                                    "module": "modulename",
                                    "filename": "filename.kt",
                                    "lineno": 5,
                                    "in_app": True,
                                    "function": "foo()",
                                }
                            ],
                            "type": "BadException",
                            "module": "org.foo.Bar",
                            "value": "[PII]",
                        }
                    }
                ]
            }
        }

        crash_id, raw_crash, processed_crash = build_crash_data()
        processed_crash["java_exception"] = java_exception
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        url = reverse("crashstats:report_index", args=(crash_id,))
        response = client.get(url)
        assert response.status_code == 200

        # Make sure it printed some java_exception data
        assert "BadException" in smart_str(response.content)

        # Make sure "PII" is not in the crash report
        assert "[PII]" not in smart_str(response.content)

    def test_java_exception_table_logged_in(
        self, client, db, storage_helper, user_helper
    ):
        java_exception = {
            "exception": {
                "values": [
                    {
                        "stacktrace": {
                            "frames": [
                                {
                                    "module": "modulename",
                                    "filename": "filename.kt",
                                    "lineno": 5,
                                    "in_app": True,
                                    "function": "foo()",
                                }
                            ],
                            "type": "BadException",
                            "module": "org.foo.Bar",
                            "value": "[PII]",
                        }
                    }
                ]
            }
        }

        crash_id, raw_crash, processed_crash = build_crash_data()
        processed_crash["java_exception"] = java_exception
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        user = user_helper.create_protected_user()
        client.force_login(user)

        url = reverse("crashstats:report_index", args=(crash_id,))
        response = client.get(url)
        assert response.status_code == 200

        # Make sure it printed some java_exception data
        assert "BadException" in smart_str(response.content)

        # Make sure "PII" is in the crash report
        assert "[PII]" in smart_str(response.content)

    def test_last_error_value(self, client, db, storage_helper):
        json_dump = {
            "crash_info": {
                "crashing_thread": 0,
            },
            "threads": [
                {
                    "last_error_value": "0x5af",
                    "frames": [],
                }
            ],
        }

        crash_id, raw_crash, processed_crash = build_crash_data()
        processed_crash["json_dump"] = json_dump
        processed_crash["crashing_thread"] = json_dump["crash_info"]["crashing_thread"]
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        url = reverse("crashstats:report_index", args=(crash_id,))
        response = client.get(url)
        assert response.status_code == 200

        # Assert it's not in the content
        assert "Last Error Value" in smart_str(response.content)

    def test_unpaired_surrogate(self, client, db, storage_helper):
        """An unpaired surrogate like \udf03 can't be encoded in UTF-8, so it is escaped."""
        json_dump = {
            "crash_info": {"crashing_thread": 0},
            "status": "OK",
            "modules": [
                {
                    "base_addr": "0x7ff83e7a1000",
                    "code_id": "00000000000000000000000000000000",
                    "debug_file": "surrogate@example.com.xpi\udf03",
                    "debug_id": "000000000000000000000000000000000",
                    "end_addr": "0x7ff83e84a000",
                    "filename": "surrogate@example.com.xpi\udf03",
                    "version": "",
                }
            ],
            "threads": [{"frames": []}],
        }

        crash_id, raw_crash, processed_crash = build_crash_data()
        processed_crash["json_dump"] = json_dump
        processed_crash["crashing_thread"] = json_dump["crash_info"]["crashing_thread"]
        processed_crash["signature"] = "shutdownhang | foo::bar()"
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        url = reverse("crashstats:report_index", args=(crash_id,))
        response = client.get(url)
        assert response.status_code == 200

        # The escaped surrogate appears in the page
        assert "surrogate@example.com.xpi\\udf03" in smart_str(response.content)

    def test_telemetry_environment(self, client, db, storage_helper):
        telemetry_environment = {
            "build": {
                "applicationId": "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}",
                "applicationName": "Firefox",
                "displayVersion": "109.0.1",
                "platformVersion": "109.0.1",
                "updaterAvailable": True,
                "vendor": "Mozilla",
                "version": "109.0.1",
            },
        }

        crash_id, raw_crash, processed_crash = build_crash_data()
        raw_crash["TelemetryEnvironment"] = json.dumps(telemetry_environment)
        processed_crash["telemetry_environment"] = telemetry_environment
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        url = reverse("crashstats:report_index", args=(crash_id,))
        response = client.get(url)
        assert response.status_code == 200

        assert "Telemetry Environment" in smart_str(response.content)
        # It's non-trivial to check that the dict above is serialized exactly like jinja
        # does it so let's just check the data attribute is there.
        assert 'id="telemetryenvironment-json"' in smart_str(response.content)

    def test_odd_product_and_version(self, client, db, storage_helper):
        # If the processed JSON references an unfamiliar product and version it should
        # not use that to make links in the nav to reports for that unfamiliar product
        # and version.
        crash_id, raw_crash, processed_crash = build_crash_data()
        raw_crash["ProductName"] = "WaterWolf"
        raw_crash["Version"] = "99.9"
        processed_crash["product"] = "WaterWolf"
        processed_crash["version"] = "99.9"

        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        url = reverse("crashstats:report_index", args=[crash_id])
        response = client.get(url)
        assert response.status_code == 200
        # the title should have the "SummerWolf 99.9" in it
        doc = pyquery.PyQuery(response.content)
        title = doc("title").text()
        assert "WaterWolf" in title
        assert "99.9" in title

        # there shouldn't be any links to reports for the product mentioned in
        # the processed JSON
        bad_url = reverse("crashstats:product_home", args=("WaterWolf",))
        assert bad_url not in smart_str(response.content)

    def test_no_dump(self, client, db, storage_helper):
        crash_id, raw_crash, processed_crash = build_crash_data()
        del processed_crash["json_dump"]
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        url = reverse("crashstats:report_index", args=[crash_id])
        response = client.get(url)
        assert response.status_code == 200
        assert "No dump available" in smart_str(response.content)

    def test_invalid_crash_id(self, client, db, storage_helper):
        # Last 6 digits indicate 30th Feb 2012 which doesn't exist so this is an invalid
        # crash_id
        url = reverse(
            "crashstats:report_index", args=["11cb72f5-eb28-41e1-a8e4-849982120230"]
        )
        response = client.get(url)
        assert response.status_code == 400
        assert "Invalid crash ID" in smart_str(response.content)
        assert response["Content-Type"] == "text/html; charset=utf-8"

    def test_valid_install_time(self, client, db, storage_helper):
        crash_id, raw_crash, processed_crash = build_crash_data()
        raw_crash["InstallTime"] = "1461170304"
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        url = reverse("crashstats:report_index", args=[crash_id])
        response = client.get(url)
        assert "Install Time</th>" in smart_str(response.content)
        # This is what 1461170304 is in human friendly format.
        assert "2016-04-20 16:38:24" in smart_str(response.content)

    def test_invalid_install_time(self, client, db, storage_helper):
        # NOTE(willkg): this is no longer an issue when we switch the template to
        # render the install time from the processed crash
        crash_id, raw_crash, processed_crash = build_crash_data()
        raw_crash["InstallTime"] = "bad number"
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        url = reverse("crashstats:report_index", args=[crash_id])
        response = client.get(url)
        # The heading is there but there should not be a value for it
        doc = pyquery.PyQuery(response.content)
        # Look for a <tr> whose <th> is 'Install Time', then
        # when we've found the row, we look at the text of its <td> child.
        for row in doc("#details tr"):
            if pyquery.PyQuery(row).find("th").text() == "Install Time":
                assert pyquery.PyQuery(row).find("td").text() == ""

    def test_empty_json_dump(self, client, db, storage_helper):
        json_dump = {"stackwalker_version": "minidump_stackwalk 0.10.3 ..."}

        crash_id, raw_crash, processed_crash = build_crash_data()
        processed_crash["json_dump"] = json_dump
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        url = reverse("crashstats:report_index", args=[crash_id])
        response = client.get(url)
        assert response.status_code == 200

    def test_raw_crash_not_found(self, client, db, storage_helper):
        crash_id, raw_crash, processed_crash = build_crash_data()

        bucket = storage_helper.get_crashstorage_bucket()
        validate_instance(processed_crash, PROCESSED_CRASH_SCHEMA)
        processed_key = build_keys("processed_crash", crash_id)[0]
        storage_helper.upload(
            bucket_name=bucket,
            key=processed_key,
            data=dict_to_str(processed_crash).encode("utf-8"),
        )

        url = reverse("crashstats:report_index", args=[crash_id])
        response = client.get(url)

        assert response.status_code == 404
        assert "Crash Report Not Found" in smart_str(response.content)

    def test_processed_crash_not_found(self, client, db, storage_helper, queue_helper):
        crash_id, raw_crash, processed_crash = build_crash_data()

        bucket = storage_helper.get_crashstorage_bucket()
        validate_instance(raw_crash, RAW_CRASH_SCHEMA)
        raw_key = build_keys("raw_crash", crash_id)[0]
        storage_helper.upload(
            bucket_name=bucket, key=raw_key, data=dict_to_str(raw_crash).encode("utf-8")
        )

        url = reverse("crashstats:report_index", args=[crash_id])
        response = client.get(url)

        assert response.status_code == 200
        content = smart_str(response.content)
        assert "Please wait..." in content
        assert "Processing this crash report only takes a few seconds" in content

    def test_redirect_by_prefix(self, client, db, storage_helper):
        crash_id, raw_crash, processed_crash = build_crash_data()
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        url = reverse(
            "crashstats:report_index", args=(f"{settings.CRASH_ID_PREFIX}{crash_id}",)
        )
        response = client.get(url, follow=False)
        expected = reverse("crashstats:report_index", kwargs={"crash_id": crash_id})
        assert response.url == expected

    def test_thread_name(self, client, db, storage_helper):
        # Some threads now have a name. If there is one, verify that name is displayed
        # next to that thread's number.
        json_dump = {
            "crash_info": {"crashing_thread": 1},
            "thread_count": 2,
            "threads": [
                {
                    "frame_count": 0,
                    "frames": [],
                    "thread_name": "I am a Regular Thread",
                },
                {
                    "frame_count": 0,
                    "frames": [],
                    "thread_name": "I am a Crashing Thread",
                },
            ],
        }

        crash_id, raw_crash, processed_crash = build_crash_data()
        processed_crash["json_dump"] = json_dump
        processed_crash["crashing_thread"] = json_dump["crash_info"]["crashing_thread"]
        upload_crash_data(
            storage_helper, raw_crash=raw_crash, processed_crash=processed_crash
        )

        url = reverse("crashstats:report_index", args=[crash_id])
        response = client.get(url)
        assert "Crashing Thread (1), Name: I am a Crashing Thread" in smart_str(
            response.content
        )
        assert "Thread 0, Name: I am a Regular Thread" in smart_str(response.content)


class TestLogin(BaseTestViews):
    def test_login_required(self):
        url = reverse("monitoring:permission_required")
        response = self.client.get(url)
        assert response.status_code == 302
        assert settings.LOGIN_URL in response["Location"] + "?next=%s" % url

    def test_unauthenticated_user_redirected_from_protected_page(self):
        url = reverse("monitoring:permission_required")
        response = self.client.get(url, follow=False)
        expected = "%s?%s=%s" % (reverse("crashstats:login"), REDIRECT_FIELD_NAME, url)
        assert response.url == expected

    def test_login_page_renders(self):
        url = reverse("crashstats:login")
        response = self.client.get(url)
        assert response.status_code == 200
        assert "Login Required" in smart_str(response.content)
        assert "Insufficient Privileges" not in smart_str(response.content)

        self._login()
        response = self.client.get(url)
        assert response.status_code == 200
        assert "Login Required" not in smart_str(response.content)
        assert "Insufficient Privileges" in smart_str(response.content)


class TestProductHomeViews(BaseTestViews):
    def test_product_home(self):
        self.set_product_versions(["20.0", "19.1", "19.0", "18.0"])
        url = reverse("crashstats:product_home", args=("WaterWolf",))
        response = self.client.get(url)
        assert response.status_code == 200

        # Check title
        assert "WaterWolf Crash Data" in smart_str(response.content)

        # Check headings for link sections which are the active versions
        assert "WaterWolf 20.0" in smart_str(response.content)
        assert "WaterWolf 19.1" in smart_str(response.content)
        assert "WaterWolf 19.0" in smart_str(response.content)

        # Featured versions are based on MAJOR.MINOR, so 18.0 won't show up
        assert "WaterWolf 18.0" not in smart_str(response.content)

    def test_product_home_metrics(self):
        url = reverse("crashstats:product_home", args=("WaterWolf",))
        with MetricsMock() as metrics_mock:
            response = self.client.get(url)
        assert response.status_code == 200
        metrics_mock.assert_timing(
            "webapp.view.pageview",
            tags=[
                "ajax:false",
                "api:false",
                "path:/home/product/waterwolf",
                "status:200",
            ],
        )


class TestHomeView:
    def test_home_metrics(self, db, client):
        url = reverse("crashstats:home")
        with MetricsMock() as metrics_mock:
            resp = client.get(url)
        assert resp.status_code == 200
        metrics_mock.assert_timing(
            "webapp.view.pageview",
            tags=["ajax:false", "api:false", "path:/", "status:200"],
        )
