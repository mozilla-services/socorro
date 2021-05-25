# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy
import json
import re
from unittest import mock

import pyquery

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.cache import cache
from django.urls import reverse
from django.utils.encoding import smart_text
from django.test.client import RequestFactory
from django.test.utils import override_settings

from crashstats.crashstats import models
from crashstats.crashstats.tests.conftest import BaseTestViews, Response
from socorro.external.crashstorage_base import CrashIDNotFound


_SAMPLE_META = {
    "InstallTime": "1339289895",
    "FramePoisonSize": "4096",
    "Theme": "classic/1.0",
    "Version": "5.0a1",
    "Email": "some@emailaddress.com",
    "Vendor": "Mozilla",
    "URL": "someaddress.com",
    "Comments": "this is a comment",
}


_SAMPLE_UNREDACTED = {
    "client_crash_date": "2012-06-11T06:08:45",
    "signature": "FakeSignature1",
    "uptime": 14693,
    "release_channel": "nightly",
    "uuid": "11cb72f5-eb28-41e1-a8e4-849982120611",
    "flash_version": "[blank]",
    "hangid": None,
    "truncated": True,
    "process_type": None,
    "id": 383569625,
    "os_version": "10.6.8 10K549",
    "version": "5.0a1",
    "build": "20120609030536",
    "ReleaseChannel": "nightly",
    "addons_checked": None,
    "product": "WaterWolf",
    "os_name": "Mac OS X",
    "os_pretty_version": "OS X 10.11",
    "last_crash": 371342,
    "date_processed": "2012-06-11T06:08:44",
    "cpu_arch": "amd64",
    "cpu_info": "AuthenticAMD family 20 model 2 stepping 0 | 2 ",
    "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
    "address": "0x8",
    "completeddatetime": "2012-06-11T06:08:57",
    "success": True,
    "user_comments": "this is a comment",
    "json_dump": {
        "status": "OK",
        "sensitive": {"exploitability": "high"},
        "threads": [],
    },
}


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
        "flash_version": [
            {"category": "[blank]", "percentage": "100.000", "report_count": 103}
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
        "exploitability": [
            {
                "low_count": 0,
                "high_count": 0,
                "null_count": 0,
                "none_count": 4,
                "report_date": "2014-08-12",
                "medium_count": 0,
            }
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
        assert "Allow: /" in smart_text(response.content)

    @override_settings(ENGAGE_ROBOTS=False)
    def test_robots_txt_disengage(self, settings, client):
        settings.ENGAGE_ROBOTS = False
        url = "/robots.txt"
        response = client.get(url)
        assert response.status_code == 200
        assert response["Content-Type"] == "text/plain"
        assert "Disallow: /" in smart_text(response.content)


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
        fake_request = RequestFactory().request(**{"wsgi.input": None})

        # the reason for first causing an exception to be raised is because
        # the handler500 function is only called by django when an exception
        # has been raised which means sys.exc_info() is something.
        try:
            raise NameError("sloppy code")
        except NameError:
            # do this inside a frame that has a sys.exc_info()
            response = handler500(fake_request)
            assert response.status_code == 500
            assert "Internal Server Error" in smart_text(response.content)
            assert 'id="products_select"' not in smart_text(response.content)

    def test_json(self):
        root_urlconf = __import__(
            settings.ROOT_URLCONF, globals(), locals(), ["urls"], 0
        )
        par, end = root_urlconf.handler500.rsplit(".", 1)
        views = __import__(par, globals(), locals(), [end], 0)
        handler500 = getattr(views, end)

        fake_request = RequestFactory().request(**{"wsgi.input": None})
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
        assert "The requested page could not be found." in smart_text(response.content)

    def test_handler404_json(self, client):
        # Just need any view that has the json_view decorator on it.
        url = reverse("api:model_wrapper", args=("Unknown",))
        response = client.get(url, {"foo": "bar"})
        assert response.status_code == 404
        assert response["Content-Type"] == "application/json"
        result = json.loads(response.content)
        assert result["error"] == "Page not found"
        assert result["path"] == url
        assert result["query_string"] == "foo=bar"


class TestContributeJson:
    def test_view(self, client):
        response = client.get("/contribute.json")
        assert response.status_code == 200
        assert json.loads(response.content)
        assert response["Content-Type"] == "application/json"


class TestFaviconIco:
    def test_view(self, client):
        response = client.get("/favicon.ico")
        assert response.status_code == 200
        assert response["Content-Type"] == "image/vnd.microsoft.icon"


class TestViews(BaseTestViews):
    @mock.patch("requests.Session")
    def test_buginfo(self, rsession):
        url = reverse("crashstats:buginfo")

        def mocked_get(url, **options):
            if "bug?id=123,456" in url:
                return Response(
                    {
                        "bugs": [
                            {
                                "id": 123,
                                "status": "NEW",
                                "resolution": "",
                                "summary": "Some Summary",
                            },
                            {
                                "id": 456,
                                "status": "NEW",
                                "resolution": "",
                                "summary": "Other Summary",
                            },
                        ]
                    }
                )

            raise NotImplementedError(url)

        rsession().get.side_effect = mocked_get

        response = self.client.get(url)
        assert response.status_code == 400

        response = self.client.get(url, {"bug_ids": ""})
        assert response.status_code == 400

        response = self.client.get(url, {"bug_ids": " 123, 456 "})
        assert response.status_code == 200

        struct = json.loads(response.content)
        assert struct["bugs"]
        assert struct["bugs"][0]["summary"] == "Some Summary"

    @mock.patch("requests.Session")
    def test_buginfo_with_caching(self, rsession):
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

        response = self.client.get(
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

    def test_quick_search(self):
        url = reverse("crashstats:quick_search")

        # Test with no parameter.
        response = self.client.get(url)
        assert response.status_code == 302
        target = reverse("supersearch:search")
        assert response["location"].endswith(target)

        # Test with a signature.
        response = self.client.get(url, {"query": "moz"})
        assert response.status_code == 302
        target = reverse("supersearch:search") + "?signature=~moz"
        assert response["location"].endswith(target)

        # Test with a crash_id.
        crash_id = "1234abcd-ef56-7890-ab12-abcdef130802"
        response = self.client.get(url, {"query": crash_id})
        assert response.status_code == 302
        target = reverse("crashstats:report_index", kwargs=dict(crash_id=crash_id))
        assert response["location"].endswith(target)

        # Test a simple search containing a crash id and spaces
        crash_id = "   1234abcd-ef56-7890-ab12-abcdef130802 "
        response = self.client.get(url, {"query": crash_id})
        assert response.status_code == 302
        assert response["location"].endswith(target)

    def test_report_index(self):
        json_dump = {
            "system_info": {
                "os": "Mac OS X",
                "os_ver": "10.6.8 10K549",
                "cpu_arch": "amd64",
                "cpu_info": "family 6 mod",
                "cpu_count": 1,
            },
            "sensitive": {"exploitability": "high"},
        }

        models.BugAssociation.objects.create(bug_id=222222, signature="FakeSignature1")
        models.BugAssociation.objects.create(bug_id=333333, signature="FakeSignature1")
        models.BugAssociation.objects.create(
            bug_id=444444, signature="Other FakeSignature"
        )

        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash["json_dump"] = json_dump
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse(
            "crashstats:report_index", args=["11cb72f5-eb28-41e1-a8e4-849982120611"]
        )
        response = self.client.get(url)
        assert response.status_code == 200
        # which bug IDs appear is important and the order matters too
        content = smart_text(response.content)
        assert (
            -1
            == content.find("444444")
            < content.find("333333")
            < content.find("222222")
        )

        assert "FakeSignature1" in content
        assert "11cb72f5-eb28-41e1-a8e4-849982120611" in content

        # Verify the "AMD CPU bug" marker is there.
        assert "Possible AMD CPU bug related crash report" in content

        assert _SAMPLE_UNREDACTED["user_comments"] not in content
        assert _SAMPLE_META["Email"] not in content
        assert _SAMPLE_META["URL"] not in content
        assert (
            "You need to be logged in and have access to protected data to see "
            "links to crash report data."
        ) in content
        # Should not be able to see sensitive key from stackwalker JSON
        assert "&#34;sensitive&#34;" not in content
        assert "&#34;exploitability&#34;" not in content

        # The pretty platform version should appear.
        assert "OS X 10.11" in content

        # the email address will appear if we log in
        user = self._login()
        group = self._create_group_with_permission("view_pii")
        user.groups.add(group)
        assert user.has_perm("crashstats.view_pii")

        response = self.client.get(url)
        content = smart_text(response.content)
        assert _SAMPLE_UNREDACTED["user_comments"] in content
        assert _SAMPLE_META["Email"] in content
        assert _SAMPLE_META["URL"] in content
        assert "&#34;sensitive&#34;" in content
        assert "&#34;exploitability&#34;" in content
        assert response.status_code == 200

        # Ensure fields have their description in title.
        assert "No description for this field." in content
        # NOTE(willkg): This is the description of "crash address". If we ever
        # change that we'll need to update this to another description that
        # shows up.
        assert "The crashing address." in content

        # If the user ceases to be active, these PII fields should disappear
        user.is_active = False
        user.save()
        response = self.client.get(url)
        assert response.status_code == 200
        content = smart_text(response.content)
        assert _SAMPLE_UNREDACTED["user_comments"] not in content
        assert _SAMPLE_META["Email"] not in content
        assert _SAMPLE_META["URL"] not in content

    def test_report_index_with_raw_crash_unicode_key(self):
        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                raw = copy.deepcopy(_SAMPLE_META)
                raw["Prénom"] = "Peter"
                return raw
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                return copy.deepcopy(_SAMPLE_UNREDACTED)

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        # Be logged in with view_pii to avoid allowlisting
        user = self._login()
        group = self._create_group_with_permission("view_pii")
        user.groups.add(group)
        assert user.has_perm("crashstats.view_pii")

        url = reverse(
            "crashstats:report_index", args=["11cb72f5-eb28-41e1-a8e4-849982120611"]
        )
        response = self.client.get(url)
        assert response.status_code == 200
        # The response is a byte string so look for 'Pr\xc3\xa9nom' in the
        # the client output.
        # NOTE(willkg): the right side should be binary format
        assert "Prénom".encode() in response.content

    def test_report_index_with_refreshed_cache(self):
        raw_crash_calls = []

        def mocked_raw_crash_get(**params):
            raw_crash_calls.append(params)
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        processed_crash_calls = []

        def mocked_processed_crash_get(**params):
            processed_crash_calls.append(params)
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                return copy.deepcopy(_SAMPLE_UNREDACTED)

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse(
            "crashstats:report_index", args=["11cb72f5-eb28-41e1-a8e4-849982120611"]
        )
        response = self.client.get(url)
        assert response.status_code == 200
        assert len(raw_crash_calls) == len(processed_crash_calls) == 1

        # Call it a second time and the cache should kick in
        response = self.client.get(url)
        assert response.status_code == 200
        assert len(raw_crash_calls) == len(processed_crash_calls) == 1  # same!

        response = self.client.get(url, {"refresh": "cache"})
        assert response.status_code == 200
        assert len(raw_crash_calls) == len(processed_crash_calls) == 2

    def test_report_index_with_remote_type_raw_crash(self):
        # If a processed crash has a 'process_type' value *and* if the raw
        # crash has as 'RemoteType' then both of these values should be
        # displayed in the HTML.
        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                raw = copy.deepcopy(_SAMPLE_META)
                raw["ProcessType"] = "content"
                raw["RemoteType"] = "java-applet"
                return raw
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                processed = copy.deepcopy(_SAMPLE_UNREDACTED)
                processed["process_type"] = "content"
                return processed

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        # Log in because RemoteType is PII
        user = self._login()
        group = self._create_group_with_permission("view_pii")
        user.groups.add(group)
        assert user.has_perm("crashstats.view_pii")

        url = reverse(
            "crashstats:report_index", args=["11cb72f5-eb28-41e1-a8e4-849982120611"]
        )
        response = self.client.get(url)
        assert response.status_code == 200

        # Assert that it displays '{process_type}\s+({raw_crash.RemoteType})'
        assert re.findall(
            r"content[\s\n]+\(java-applet\)", smart_text(response.content), re.MULTILINE
        )

    def test_report_index_with_additional_raw_dump_links(self):
        json_dump = {
            "system_info": {
                "os": "Mac OS X",
                "os_ver": "10.6.8 10K549",
                "cpu_arch": "amd64",
                "cpu_info": "family 6 mod",
                "cpu_count": 1,
            }
        }

        def mocked_processed_crash_get(**params):
            assert "datatype" in params

            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash["json_dump"] = json_dump
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        def mocked_raw_crash_get(**params):
            assert "datatype" in params

            if params["datatype"] == "meta":
                return {
                    "InstallTime": "1339289895",
                    "FramePoisonSize": "4096",
                    "Theme": "classic/1.0",
                    "Version": "5.0a1",
                    "Email": "secret@email.com",
                    "Vendor": "Mozilla",
                    "URL": "farmville.com",
                    "dump_checksums": {
                        "upload_file_minidump": "xxx",
                        "upload_file_minidump_foo": "xxx",
                        "upload_file_minidump_bar": "xxx",
                    },
                }

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"
        url = reverse("crashstats:report_index", args=(crash_id,))
        response = self.client.get(url)
        assert response.status_code == 200

        # first of all, expect these basic URLs
        raw_crash_url = "%s?crash_id=%s" % (
            reverse("api:model_wrapper", kwargs={"model_name": "RawCrash"}),
            crash_id,
        )
        dump_url = "%s?crash_id=%s&amp;format=raw&amp;name=upload_file_minidump" % (
            reverse("api:model_wrapper", kwargs={"model_name": "RawCrash"}),
            crash_id,
        )
        # not quite yet
        assert raw_crash_url not in smart_text(response.content)
        assert dump_url not in smart_text(response.content)

        user = self._login()
        response = self.client.get(url)
        assert response.status_code == 200
        # still they don't appear
        assert raw_crash_url not in smart_text(response.content)
        assert dump_url not in smart_text(response.content)

        group = self._create_group_with_permission(["view_pii", "view_rawdump"])
        user.groups.add(group)
        response = self.client.get(url)
        assert response.status_code == 200
        # finally they appear
        assert raw_crash_url in smart_text(response.content)
        assert dump_url in smart_text(response.content)

        # also, check that the other links are there
        foo_dump_url = (
            "%s?crash_id=%s&amp;format=raw&amp;name=upload_file_minidump_foo"
            % (
                reverse("api:model_wrapper", kwargs={"model_name": "RawCrash"}),
                crash_id,
            )
        )
        assert foo_dump_url in smart_text(response.content)
        bar_dump_url = (
            "%s?crash_id=%s&amp;format=raw&amp;name=upload_file_minidump_bar"
            % (
                reverse("api:model_wrapper", kwargs={"model_name": "RawCrash"}),
                crash_id,
            )
        )
        assert bar_dump_url in smart_text(response.content)

    def test_report_index_with_symbol_url_in_modules(self):
        json_dump = {
            "status": "OK",
            "sensitive": {"exploitability": "high"},
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

        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                crash = copy.deepcopy(_SAMPLE_META)
                crash["additional_minidumps"] = "foo, bar,"
                return crash
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash["json_dump"] = json_dump
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"
        url = reverse("crashstats:report_index", args=(crash_id,))
        response = self.client.get(url)
        assert response.status_code == 200

        assert 'id="modules-list"' in smart_text(response.content)
        assert '<a href="https://s3.example.com/winmm.sym">winmm.dll</a>' in smart_text(
            response.content
        )

    def test_report_index_with_cert_subject_in_modules(self):
        json_dump = {
            "status": "OK",
            "sensitive": {"exploitability": "high"},
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

        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                crash = copy.deepcopy(_SAMPLE_META)
                crash["additional_minidumps"] = "foo, bar,"
                return crash
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash["json_dump"] = json_dump
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"
        url = reverse("crashstats:report_index", args=(crash_id,))
        response = self.client.get(url)
        assert response.status_code == 200

        assert 'id="modules-list"' in smart_text(response.content)
        assert re.search(
            r"<td>userenv\.pdb</td>\s*?<td></td>", smart_text(response.content)
        )
        assert re.search(
            r"<td>winmm\.pdb</td>\s*?<td>Microsoft Windows</td>",
            smart_text(response.content),
        )

    def test_report_index_with_shutdownhang_signature(self):
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

        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash["json_dump"] = json_dump
                crash["signature"] = "shutdownhang | foo::bar()"
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"
        url = reverse("crashstats:report_index", args=(crash_id,))
        response = self.client.get(url)
        assert response.status_code == 200

        assert "Crashing Thread (2)" not in smart_text(response.content)
        assert "Crashing Thread (0)" in smart_text(response.content)

    def test_report_index_with_no_crashing_thread(self):
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

        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash["json_dump"] = json_dump
                crash["signature"] = "foo::bar()"
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"
        url = reverse("crashstats:report_index", args=(crash_id,))
        response = self.client.get(url)
        assert response.status_code == 200

        assert "Crashing Thread" not in smart_text(response.content)
        assert "Thread 0" in smart_text(response.content)
        assert "Thread 1" in smart_text(response.content)
        assert "Thread 2" in smart_text(response.content)

    def test_report_index_crashing_thread_table(self):
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

        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash["json_dump"] = json_dump
                crash["signature"] = "shutdownhang | foo::bar()"
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"
        url = reverse("crashstats:report_index", args=(crash_id,))
        response = self.client.get(url)
        assert response.status_code == 200

        # Make sure the "trust" parts show up in the page
        assert "context" in smart_text(response.content)
        assert "frame_pointer" in smart_text(response.content)

    def test_java_exception_table_not_logged_in(self):
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
                            "value": "REDACTED",
                        }
                    }
                ]
            }
        }
        java_exception_raw = copy.deepcopy(java_exception)
        java_exception_raw["exception"]["values"][0]["stacktrace"]["value"] = "PII"

        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash["java_exception_raw"] = java_exception_raw
                crash["java_exception"] = java_exception
                return crash

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"
        url = reverse("crashstats:report_index", args=(crash_id,))
        response = self.client.get(url)
        assert response.status_code == 200

        # Make sure it printed some java_exception data
        assert "BadException" in smart_text(response.content)

        # Make sure "PII" is not in the crash report
        assert "PII" not in smart_text(response.content)
        assert "REDACTED" in smart_text(response.content)

    def test_java_exception_table_logged_in(self):
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
                            "value": "REDACTED",
                        }
                    }
                ]
            }
        }
        java_exception_raw = copy.deepcopy(java_exception)
        java_exception_raw["exception"]["values"][0]["stacktrace"]["value"] = "PII"

        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash["java_exception_raw"] = java_exception_raw
                crash["java_exception"] = java_exception
                return crash

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        user = self._login()
        group = self._create_group_with_permission("view_pii")
        user.groups.add(group)

        crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"
        url = reverse("crashstats:report_index", args=(crash_id,))
        response = self.client.get(url)
        assert response.status_code == 200

        # Make sure it printed some java_exception data
        assert "BadException" in smart_text(response.content)

        # Make sure "PII" is in the crash report
        assert "PII" in smart_text(response.content)
        assert "REDACTED" not in smart_text(response.content)

    def test_last_error_value(self):
        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

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

        def mocked_processed_crash_get(**params):
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                # Create a minimal json_dump with the last_error_value
                crash["json_dump"] = json_dump
                return crash

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"
        url = reverse("crashstats:report_index", args=(crash_id,))
        response = self.client.get(url)
        assert response.status_code == 200

        # Assert it's not in the content
        assert "Last Error Value" in smart_text(response.content)

    def test_report_index_unpaired_surrogate(self):
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

        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash["json_dump"] = json_dump
                crash["signature"] = "shutdownhang | foo::bar()"
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"
        url = reverse("crashstats:report_index", args=(crash_id,))
        response = self.client.get(url)
        assert response.status_code == 200

        # The escaped surrogate appears in the page
        assert "surrogate@example.com.xpi\\udf03" in smart_text(response.content)

    def test_report_index_with_telemetry_environment(self):
        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                crash = copy.deepcopy(_SAMPLE_META)
                crash["TelemetryEnvironment"] = {
                    "key": ["values"],
                    "plainstring": "I am a string",
                    "plainint": 12345,
                    "empty": [],
                    "foo": {"keyA": "AAA", "keyB": "BBB"},
                }
                return crash
            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                return copy.deepcopy(_SAMPLE_UNREDACTED)

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"
        url = reverse("crashstats:report_index", args=(crash_id,))
        response = self.client.get(url)
        assert response.status_code == 200

        assert "Telemetry Environment" in smart_text(response.content)
        # it's non-trivial to check that the dict above is serialized
        # exactly like jinja does it so let's just check the data attribute
        # is there.
        assert 'id="telemetryenvironment-json"' in smart_text(response.content)

    def test_report_index_odd_product_and_version(self):
        # If the processed JSON references an unfamiliar product and version it
        # should not use that to make links in the nav to reports for that
        # unfamiliar product and version.
        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError(params)

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash["product"] = "WaterWolf"
                crash["version"] = "99.9"
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse(
            "crashstats:report_index", args=["11cb72f5-eb28-41e1-a8e4-849982120611"]
        )
        response = self.client.get(url)
        assert response.status_code == 200
        # the title should have the "SummerWolf 99.9" in it
        doc = pyquery.PyQuery(response.content)
        title = doc("title").text()
        assert "WaterWolf" in title
        assert "99.9" in title

        # there shouldn't be any links to reports for the product mentioned in
        # the processed JSON
        bad_url = reverse("crashstats:product_home", args=("WaterWolf",))
        assert bad_url not in smart_text(response.content)

    def test_report_index_no_dump(self):
        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                del crash["json_dump"]
                return crash

            raise NotImplementedError(url)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse(
            "crashstats:report_index", args=["11cb72f5-eb28-41e1-a8e4-849982120611"]
        )
        response = self.client.get(url)
        assert response.status_code == 200
        assert "No dump available" in smart_text(response.content)

    def test_report_index_invalid_crash_id(self):
        # last 6 digits indicate 30th Feb 2012 which doesn't exist
        url = reverse(
            "crashstats:report_index", args=["11cb72f5-eb28-41e1-a8e4-849982120230"]
        )
        response = self.client.get(url)
        assert response.status_code == 400
        assert "Invalid crash ID" in smart_text(response.content)
        assert response["Content-Type"] == "text/html; charset=utf-8"

    def test_report_index_with_valid_install_time(self):
        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return {"InstallTime": "1461170304", "Version": "5.0a1"}

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                return copy.deepcopy(_SAMPLE_UNREDACTED)

            raise NotImplementedError

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse(
            "crashstats:report_index", args=["11cb72f5-eb28-41e1-a8e4-849982120611"]
        )
        response = self.client.get(url)
        assert "Install Time</th>" in smart_text(response.content)
        # This is what 1461170304 is in human friendly format.
        assert "2016-04-20 16:38:24" in smart_text(response.content)

    def test_report_index_with_invalid_install_time(self):
        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                crash = copy.deepcopy(_SAMPLE_META)
                crash["InstallTime"] = "Not a number"
                return crash

            raise NotImplementedError(params)

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                return copy.deepcopy(_SAMPLE_UNREDACTED)

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse(
            "crashstats:report_index", args=["11cb72f5-eb28-41e1-a8e4-849982120611"]
        )
        response = self.client.get(url)
        # The heading is there but there should not be a value for it
        doc = pyquery.PyQuery(response.content)
        # Look for a <tr> whose <th> is 'Install Time', then
        # when we've found the row, we look at the text of its <td> child.
        for row in doc("#details tr"):
            if pyquery.PyQuery(row).find("th").text() == "Install Time":
                assert pyquery.PyQuery(row).find("td").text() == ""

    def test_report_index_empty_os_name(self):
        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash["os_name"] = None
                return crash

            raise NotImplementedError

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse(
            "crashstats:report_index", args=["11cb72f5-eb28-41e1-a8e4-849982120611"]
        )
        response = self.client.get(url)
        # Despite the `os_name` being null, it should work to render
        # this page.
        assert response.status_code == 200
        doc = pyquery.PyQuery(response.content)
        for node in doc("#mainbody"):
            assert node.attrib["data-platform"] == ""

    def test_report_index_with_invalid_parsed_dump(self):
        json_dump = {
            "crash_info": {
                "address": "0x88",
                "type": "EXCEPTION_ACCESS_VIOLATION_READ",
            },
            "main_module": 0,
            "modules": [
                {
                    "base_addr": "0x980000",
                    "debug_file": "FlashPlayerPlugin.pdb",
                    "debug_id": "5F3C0D3034CA49FE9B94FC97EBF590A81",
                    "end_addr": "0xb4d000",
                    "filename": "FlashPlayerPlugin_13_0_0_214.exe",
                    "version": "13.0.0.214",
                }
            ],
            "sensitive": {"exploitability": "none"},
            "status": "OK",
            "system_info": {
                "cpu_arch": "x86",
                "cpu_count": 8,
                "cpu_info": "GenuineIntel family 6 model 26 stepping 4",
                "os": "Windows NT",
                "os_ver": "6.0.6002 Service Pack 2",
            },
            "thread_count": 1,
            "threads": [{"frame_count": 0, "frames": []}],
        }

        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash["json_dump"] = json_dump
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse(
            "crashstats:report_index", args=["11cb72f5-eb28-41e1-a8e4-849982120611"]
        )
        response = self.client.get(url)
        assert "<th>Install Time</th>" not in smart_text(response.content)

    def test_report_index_with_sparse_json_dump(self):
        json_dump = {"status": "ERROR_NO_MINIDUMP_HEADER", "sensitive": {}}

        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash["json_dump"] = json_dump
                return crash

            raise NotImplementedError

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse(
            "crashstats:report_index", args=["11cb72f5-eb28-41e1-a8e4-849982120611"]
        )
        response = self.client.get(url)
        assert response.status_code == 200

    def test_report_index_with_crash_exploitability(self):
        crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"

        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError(params)

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash["exploitability"] = "Unknown Exploitability"
                return crash

            raise NotImplementedError

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse("crashstats:report_index", args=[crash_id])

        response = self.client.get(url)
        assert "Exploitability</th>" not in smart_text(response.content)

        # you must be logged in to see exploitability
        user = self._login()
        group = self._create_group_with_permission("view_exploitability")
        user.groups.add(group)

        response = self.client.get(url)
        assert "Exploitability</th>" in smart_text(response.content)
        assert "Unknown Exploitability" in smart_text(response.content)

    def test_report_index_your_crash(self):
        crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"

        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                copied = copy.deepcopy(_SAMPLE_META)
                copied["Email"] = "peterbe@example.com"
                copied["URL"] = "https://embarrassing.example.com"
                return copied

            raise NotImplementedError(params)

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash["exploitability"] = "Unknown Exploitability"
                return crash

            raise NotImplementedError

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse("crashstats:report_index", args=[crash_id])

        response = self.client.get(url)
        assert "Exploitability</th>" not in smart_text(response.content)
        assert "peterbe@example.com" not in smart_text(response.content)
        assert "https://embarrassing.example.com" not in smart_text(response.content)

        # you must be logged in to see exploitability
        self._login(email="peterbe@example.com")
        response = self.client.get(url)
        assert "Exploitability</th>" in smart_text(response.content)
        assert "Unknown Exploitability" in smart_text(response.content)
        assert "peterbe@example.com" in smart_text(response.content)
        assert "https://embarrassing.example.com" in smart_text(response.content)

    def test_report_index_not_your_crash(self):
        crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"

        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                copied = copy.deepcopy(_SAMPLE_META)
                copied["Email"] = "peterbe@example.com"
                copied["URL"] = "https://embarrassing.example.com"
                return copied

            raise NotImplementedError(params)

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash["exploitability"] = "Unknown Exploitability"
                return crash

            raise NotImplementedError

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse("crashstats:report_index", args=[crash_id])

        # You log in, but a different email address from that in the
        # raw crash. Make sure that doesn't show the sensitive data
        self._login(email="someone@example.com")
        response = self.client.get(url)
        assert "Exploitability</th>" not in smart_text(response.content)
        assert "Unknown Exploitability" not in smart_text(response.content)
        assert "peterbe@example.com" not in smart_text(response.content)
        assert "https://embarrassing.example.com" not in smart_text(response.content)

    def test_report_index_raw_crash_not_found(self):
        crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"

        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                raise CrashIDNotFound(params["uuid"])

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        url = reverse("crashstats:report_index", args=[crash_id])
        response = self.client.get(url)

        assert response.status_code == 404
        assert "Crash Report Not Found" in smart_text(response.content)

    def test_report_index_processed_crash_not_found(self):
        crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"

        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                raise CrashIDNotFound(params["uuid"])

            raise NotImplementedError

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        def mocked_publish(**params):
            assert params["crash_ids"] == [crash_id]
            return True

        models.PriorityJob.implementation().publish.side_effect = mocked_publish

        url = reverse("crashstats:report_index", args=[crash_id])
        response = self.client.get(url)

        assert response.status_code == 200
        content = smart_text(response.content)
        assert "Please wait..." in content
        assert "Processing this crash report only takes a few seconds" in content

    def test_report_index_with_invalid_date_processed(self):
        crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"

        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError(params)

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                # NOTE! A wanna-be valid date that is not valid
                crash["date_processed"] = "2015-10-10 15:32:07.620535"
                return crash
            raise NotImplementedError

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse("crashstats:report_index", args=[crash_id])

        response = self.client.get(url)
        # The date could not be converted in the jinja helper
        # to a more human format.
        assert "2015-10-10 15:32:07.620535" in smart_text(response.content)

    def test_report_index_redirect_by_prefix(self):
        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError(params)

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                return copy.deepcopy(_SAMPLE_UNREDACTED)

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        base_crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"
        crash_id = settings.CRASH_ID_PREFIX + base_crash_id
        assert len(crash_id) > 36
        url = reverse("crashstats:report_index", args=[crash_id])
        response = self.client.get(url, follow=False)
        expected = reverse("crashstats:report_index", args=[base_crash_id])
        assert response.url == expected

    def test_report_index_with_thread_name(self):
        # Some threads now have a name. If there is one, verify that name is
        # displayed next to that thread's number.
        crash_id = "11cb72f5-eb28-41e1-a8e4-849982120611"
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

        def mocked_raw_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "meta":
                return copy.deepcopy(_SAMPLE_META)

            raise NotImplementedError

        models.RawCrash.implementation().get.side_effect = mocked_raw_crash_get

        def mocked_processed_crash_get(**params):
            assert "datatype" in params
            if params["datatype"] == "unredacted":
                crash = copy.deepcopy(_SAMPLE_UNREDACTED)
                crash["json_dump"] = json_dump
                return crash

            raise NotImplementedError(params)

        models.UnredactedCrash.implementation().get.side_effect = (
            mocked_processed_crash_get
        )

        url = reverse("crashstats:report_index", args=[crash_id])

        response = self.client.get(url)
        assert "Crashing Thread (1), Name: I am a Crashing Thread" in smart_text(
            response.content
        )
        assert "Thread 0, Name: I am a Regular Thread" in smart_text(response.content)


class TestLogin(BaseTestViews):
    def test_login_required(self):
        url = reverse("exploitability:report")
        response = self.client.get(url)
        assert response.status_code == 302
        assert settings.LOGIN_URL in response["Location"] + "?next=%s" % url

    def test_unauthenticated_user_redirected_from_protected_page(self):
        url = reverse("exploitability:report")
        response = self.client.get(url, follow=False)
        expected = "%s?%s=%s" % (reverse("crashstats:login"), REDIRECT_FIELD_NAME, url)
        assert response.url == expected

    def test_login_page_renders(self):
        url = reverse("crashstats:login")
        response = self.client.get(url)
        assert response.status_code == 200
        assert "Login Required" in smart_text(response.content)
        assert "Insufficient Privileges" not in smart_text(response.content)

        self._login()
        response = self.client.get(url)
        assert response.status_code == 200
        assert "Login Required" not in smart_text(response.content)
        assert "Insufficient Privileges" in smart_text(response.content)


class TestProductHomeViews(BaseTestViews):
    def test_product_home(self):
        self.set_product_versions(["20.0", "19.1", "19.0", "18.0"])
        url = reverse("crashstats:product_home", args=("WaterWolf",))
        response = self.client.get(url)
        assert response.status_code == 200

        # Check title
        assert "WaterWolf Crash Data" in smart_text(response.content)

        # Check headings for link sections which are the active versions
        assert "WaterWolf 20.0" in smart_text(response.content)
        assert "WaterWolf 19.1" in smart_text(response.content)
        assert "WaterWolf 19.0" in smart_text(response.content)

        # Featured versions are based on MAJOR.MINOR, so 18.0 won't show up
        assert "WaterWolf 18.0" not in smart_text(response.content)
