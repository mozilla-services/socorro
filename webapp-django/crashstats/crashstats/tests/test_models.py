# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import random
from urllib.parse import urlparse, parse_qs
from unittest import mock

import pytest

from django.core.cache import cache
from django.conf import settings
from django.utils import dateparse

from crashstats.crashstats import models
from crashstats.crashstats.tests.conftest import Response
from crashstats.crashstats.tests.testbase import DjangoTestCase
from socorro.lib import BadArgumentError
from socorro.lib.libooid import create_new_ooid
from socorro.unittest.external.sqs import get_sqs_config, SQSHelper


class TestGraphicsDevices(DjangoTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def test_get_pairs(self):
        """Test get_pairs() works correctly

        The GraphicsDevice.get_pairs() lets you expand a bunch of (vendor, adapter)
        pairs at the same time. It's more performant since it does a single query.

        """
        models.GraphicsDevice.objects.create(
            vendor_hex="vhex3",
            vendor_name="V 3",
            adapter_hex="ahex3",
            adapter_name="A 3",
        )
        models.GraphicsDevice.objects.create(
            vendor_hex="vhex2",
            vendor_name="V 2",
            adapter_hex="ahex2",
            adapter_name="A 2",
        )
        models.GraphicsDevice.objects.create(
            vendor_hex="vhex1",
            vendor_name="V 1",
            adapter_hex="ahex1",
            adapter_name="A 1",
        )

        r = models.GraphicsDevice.objects.get_pairs(
            ["vhex1", "vhex2"], ["ahex1", "ahex2"]
        )
        expected = {
            ("vhex1", "ahex1"): ("V 1", "A 1"),
            ("vhex2", "ahex2"): ("V 2", "A 2"),
        }
        assert r == expected

        r = models.GraphicsDevice.objects.get_pairs(
            ["vhex2", "vhex3"], ["ahex2", "ahex3"]
        )
        assert len(r) == 2
        expected = {
            ("vhex2", "ahex2"): ("V 2", "A 2"),
            ("vhex3", "ahex3"): ("V 3", "A 3"),
        }
        assert r == expected


class TestBugs(DjangoTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def test_get_one(self):
        models.BugAssociation.objects.create(bug_id="999999", signature="OOM | small")

        api = models.Bugs()

        resp = api.get(signatures=["OOM | small"])
        assert resp == {
            "hits": [{"id": 999999, "signature": "OOM | small"}],
            "total": 1,
        }

    def test_get_multiple(self):
        models.BugAssociation.objects.create(bug_id="999999", signature="OOM | small")
        models.BugAssociation.objects.create(bug_id="1000000", signature="OOM | large")

        api = models.Bugs()

        resp = api.get(signatures=["OOM | small", "OOM | large"])
        assert resp == {
            "hits": [
                {"id": 999999, "signature": "OOM | small"},
                {"id": 1000000, "signature": "OOM | large"},
            ],
            "total": 2,
        }

    def test_related(self):
        models.BugAssociation.objects.create(bug_id="999999", signature="OOM | small")
        models.BugAssociation.objects.create(bug_id="999999", signature="OOM | medium")
        models.BugAssociation.objects.create(bug_id="1000000", signature="OOM | large")

        api = models.Bugs()

        resp = api.get(signatures=["OOM | small"])
        assert resp == {
            "hits": [
                {"id": 999999, "signature": "OOM | medium"},
                {"id": 999999, "signature": "OOM | small"},
            ],
            "total": 2,
        }


class TestSignaturesByBugs(DjangoTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def test_get_one(self):
        models.BugAssociation.objects.create(bug_id="999999", signature="OOM | small")

        api = models.SignaturesByBugs()

        resp = api.get(bug_ids=["999999"])
        assert resp == {
            "hits": [{"id": 999999, "signature": "OOM | small"}],
            "total": 1,
        }

    def test_get_multiple(self):
        models.BugAssociation.objects.create(bug_id="999999", signature="OOM | small")
        models.BugAssociation.objects.create(bug_id="1000000", signature="OOM | large")

        api = models.SignaturesByBugs()

        resp = api.get(bug_ids=["999999", "1000000"])
        assert resp == {
            "hits": [
                {"id": 999999, "signature": "OOM | small"},
                {"id": 1000000, "signature": "OOM | large"},
            ],
            "total": 2,
        }


class TestSignatureFirstDate(DjangoTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def test_get_one(self):
        some_date = dateparse.parse_datetime("2018-10-06T00:22:58.074859+00:00")

        models.Signature.objects.create(
            signature="OOM | Small", first_build="20180920131237", first_date=some_date
        )
        models.Signature.objects.create(
            signature="OOM | Large", first_build="20180920131237", first_date=some_date
        )

        api = models.SignatureFirstDate()

        resp = api.get(signatures="OOM | Small")
        assert resp["total"] == 1
        assert resp["hits"] == [
            {
                "first_build": "20180920131237",
                "first_date": "2018-10-06T00:22:58.074859+00:00",
                "signature": "OOM | Small",
            }
        ]

    def test_get_two(self):
        some_date = dateparse.parse_datetime("2018-10-06T00:22:58.074859+00:00")

        models.Signature.objects.create(
            signature="OOM | Small", first_build="20180920131237", first_date=some_date
        )
        models.Signature.objects.create(
            signature="OOM | Large", first_build="20180920131237", first_date=some_date
        )

        api = models.SignatureFirstDate()

        resp = api.get(signatures=["OOM | Small", "OOM | Large"])
        assert resp["total"] == 2
        assert resp["hits"] == [
            {
                "first_build": "20180920131237",
                "first_date": "2018-10-06T00:22:58.074859+00:00",
                "signature": "OOM | Small",
            },
            {
                "first_build": "20180920131237",
                "first_date": "2018-10-06T00:22:58.074859+00:00",
                "signature": "OOM | Large",
            },
        ]


class TestVersionString(DjangoTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def test_bad_args_raise_error(self):
        api = models.VersionString()
        with pytest.raises(models.RequiredParameterError):
            api.get()

        with pytest.raises(models.RequiredParameterError):
            api.get(product="Firefox", channel="beta")

    def test_beta(self):
        models.ProductVersion.objects.create(
            product_name="Firefox",
            release_channel="beta",
            build_id="20161129164126",
            version_string="51.0b5",
            major_version=51,
        )

        api = models.VersionString()
        resp = api.get(product="Firefox", channel="beta", build_id="20161129164126")
        assert resp == {"hits": [{"version_string": "51.0b5"}], "total": 1}

    def test_release_rc(self):
        """If the channel is beta, but there aren't versions with 'b' in them,
        then these are release candidates for a final release, so return an rc one.

        """
        models.ProductVersion.objects.create(
            product_name="Firefox",
            release_channel="beta",
            build_id="20161104212021",
            version_string="50.0rc2",
            major_version=50,
        )

        api = models.VersionString()
        resp = api.get(product="Firefox", channel="beta", build_id="20161104212021")
        assert resp == {"hits": [{"version_string": "50.0rc2"}], "total": 1}

    def test_beta_and_rc(self):
        """If there are multiple version strings for a given (product, channel,
        build_id), and they have 'b' in them, then we want the non-rc one.

        """
        models.ProductVersion.objects.create(
            product_name="Firefox",
            release_channel="beta",
            build_id="20160920155715",
            version_string="50.0b1rc2",
            major_version=50,
        )
        models.ProductVersion.objects.create(
            product_name="Firefox",
            release_channel="beta",
            build_id="20160920155715",
            version_string="50.0b1rc1",
            major_version=50,
        )
        models.ProductVersion.objects.create(
            product_name="Firefox",
            release_channel="beta",
            build_id="20160920155715",
            version_string="50.0b1",
            major_version=50,
        )

        api = models.VersionString()
        resp = api.get(product="Firefox", channel="beta", build_id="20160920155715")
        assert resp == {"hits": [{"version_string": "50.0b1"}], "total": 1}


class TestMiddlewareModels(DjangoTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    @mock.patch("requests.Session")
    def test_bugzilla_api(self, rsession):
        model = models.BugzillaBugInfo

        api = model()

        def mocked_get(url, **options):
            assert url.startswith(settings.BZAPI_BASE_URL)
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            assert query["include_fields"] == ["summary,status,id,resolution"]
            return Response(
                {
                    "bugs": [
                        {
                            "status": "NEW",
                            "resolution": "",
                            "id": 123456789,
                            "summary": "Some summary",
                        }
                    ]
                }
            )

        rsession().get.side_effect = mocked_get
        info = api.get("123456789")
        expected = [
            {
                "status": "NEW",
                "resolution": "",
                "id": 123456789,
                "summary": "Some summary",
            }
        ]
        assert info["bugs"] == expected

        # prove that it's cached
        def new_mocked_get(**options):
            return Response(
                {
                    "bugs": [
                        {
                            "status": "RESOLVED",
                            "resolution": "",
                            "id": 123456789,
                            "summary": "Some summary",
                        }
                    ]
                }
            )

        rsession().get.side_effect = new_mocked_get
        info = api.get("123456789")
        expected = [
            {
                "status": "NEW",
                "resolution": "",
                "id": 123456789,
                "summary": "Some summary",
            }
        ]
        assert info["bugs"] == expected

    @mock.patch("requests.Session")
    def test_bugzilla_api_bad_status_code(self, rsession):
        model = models.BugzillaBugInfo

        api = model()

        def mocked_get(url, **options):
            return Response("I'm a teapot", status_code=418)

        rsession().get.side_effect = mocked_get
        with pytest.raises(models.BugzillaRestHTTPUnexpectedError):
            api.get("123456789")

    def test_processed_crash(self):
        model = models.ProcessedCrash
        api = model()

        def mocked_get(**params):
            assert "datatype" in params
            assert params["datatype"] == "processed"

            return {
                "product": "WaterWolf",
                "uuid": "7c44ade2-fdeb-4d6c-830a-07d302120525",
                "version": "13.0",
                "build": "20120501201020",
                "ReleaseChannel": "beta",
                "os_name": "Windows NT",
                "date_processed": "2022-05-15T11:35:57",
                "success": True,
                "signature": "CLocalEndpointEnumerator::OnMediaNotific",
                "addons": [
                    "testpilot@labs.mozilla.com:1.2.1",
                    "{972ce4c6-7e08-4474-a285-3208198ce6fd}:13.0",
                ],
            }

        model.implementation().get.side_effect = mocked_get
        r = api.get(crash_id="7c44ade2-fdeb-4d6c-830a-07d302120525")
        assert r["product"]

    def test_raw_crash(self):
        model = models.RawCrash
        api = model()

        def mocked_get(**params):
            return {
                "InstallTime": "1339289895",
                "Theme": "classic/1.0",
                "Version": "5.0a1",
                "Vendor": "Mozilla",
                # This is not allowlisted
                "URL": "https://example.com/",
            }

        model.implementation().get.side_effect = mocked_get
        r = api.get(crash_id="some-crash-id")
        assert r["Vendor"] == "Mozilla"
        assert "URL" in r  # no filtering at this level

    def test_raw_crash_invalid_id(self):
        # NOTE(alexisdeschamps): this undoes the mocking of the implementation so we can test
        # the implementation code.
        models.RawCrash.implementation = self._mockeries[models.RawCrash]
        model = models.RawCrash
        api = model()

        with pytest.raises(BadArgumentError):
            api.get(crash_id="821fcd0c-d925-4900-85b6-687250180607docker/as_me.sh")

    def test_raw_crash_raw_data(self):
        model = models.RawCrash
        api = model()

        mocked_calls = []

        def mocked_get(**params):
            mocked_calls.append(params)
            assert params["datatype"] == "raw"
            if params.get("name") == "other":
                return "\xe0\xe0"
            else:
                return "\xe0"

        model.implementation().get.side_effect = mocked_get

        r = api.get(crash_id="some-crash-id", format="raw")
        assert r == "\xe0"

        r = api.get(crash_id="some-crash-id", format="raw", name="other")
        assert r == "\xe0\xe0"

    @mock.patch("requests.Session")
    def test_massive_querystring_caching(self, rsession):
        # doesn't actually matter so much what API model we use
        # see https://bugzilla.mozilla.org/show_bug.cgi?id=803696
        model = models.BugzillaBugInfo
        api = model()

        def mocked_get(url, **options):
            assert url.startswith(settings.BZAPI_BASE_URL)
            return Response(
                {
                    "bugs": [
                        {
                            "id": 123456789,
                            "status": "NEW",
                            "resolution": "",
                            "summary": "Some Summary",
                        }
                    ]
                }
            )

        rsession().get.side_effect = mocked_get
        bugnumbers = [str(random.randint(10000, 100000)) for __ in range(100)]
        info = api.get(bugnumbers)
        assert info

    def test_Reprocessing(self):
        # This test runs against the AWS SQS emulator, so undo the mock to let
        # that work.
        self.undo_implementation_mock(models.Reprocessing)

        config = get_sqs_config()
        sqs_helper = SQSHelper(config)
        api = models.Reprocessing()

        with sqs_helper as helper:
            crash_id = create_new_ooid()
            api.post(crash_ids=crash_id)

            crash_ids = helper.get_published_crashids("reprocessing")
            assert crash_ids == [crash_id]

        # Now try an invalid crash id
        with pytest.raises(BadArgumentError):
            api.post(crash_ids="some-crash-id")

    def test_PriorityJob(self):
        # This test runs against the AWS SQS emulator, so undo the mock to let
        # that work.
        self.undo_implementation_mock(models.PriorityJob)

        config = get_sqs_config()
        sqs_helper = SQSHelper(config)
        api = models.PriorityJob()

        with sqs_helper as helper:
            api.post(crash_ids="some-crash-id")

            crash_ids = helper.get_published_crashids("priority")
            assert crash_ids == ["some-crash-id"]
