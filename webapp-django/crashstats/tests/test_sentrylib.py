# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Tests for Sentry event processing."""

from copy import deepcopy
import urllib

import pytest
import requests

from django.conf import settings
from django.test.testcases import LiveServerTestCase

from crashstats.sentrylib import (
    SanitizeHeaders,
    SanitizePostData,
    SanitizeQueryString,
    SanitizeSQLQueryCrumb,
    build_before_breadcrumb,
    build_before_send,
)


class TestSanitizeSQLQueryCrumb:
    """Tests for SanitizeSQLQueryCrumb."""

    CASES = {
        # Select a user by email
        "email": (
            'SELECT "auth_user"."is_active" FROM "auth_user" WHERE'
            ' UPPER("auth_user"."email"::text) = UPPER(\'username@example.com\')'
        ),
        # Find a user by username (usually same as email)
        "username": (
            'SELECT "auth_user"."is_active" FROM "auth_user" WHERE'
            ' "auth_user"."username" = \'username\''
        ),
        # Set a user's password
        "password": (
            'UPDATE "auth_user" SET "password" = \'!unusable_pwd\' WHERE "auth_user"."id" = 2'
        ),
        # Update a session (includes session data, ID)
        "session_data": (
            'UPDATE "django_session" SET "session_data" = \'B64Data\', WHERE'
            ' "django_session"."session_key" = \'a_session_key\''
        ),
        # Store a session (includes session ID, data)
        "session_key": (
            'INSERT INTO "django_session" ("session_key", "session_data") VALUES'
            " ('a_session_key', 'B64SessionData'))"
        ),
        # Load data for an API token
        "tokens_token.key": (
            'SELECT "tokens_token"."id", "tokens_token"."user_id",'
            ' "tokens_token"."key", "tokens_token"."expires",'
        ),
        # Update last login
        "auth_user.id": (
            'UPDATE "auth_user" SET "last_login" ='
            " datetime.datetime(2019, 5, 3, 18, 7, 29, 852498)"
            ' WHERE "auth_user"."id" = 123'
        ),
    }

    @pytest.mark.parametrize(
        "keyword, sql", CASES.items(), ids=tuple(case for case in CASES)
    )
    def test_filtered_queries(self, keyword, sql):
        """Sensitive queries are truncated at the column name."""
        crumb = {"category": "query", "message": sql}
        SanitizeSQLQueryCrumb((keyword,))(crumb, {})
        assert crumb == {"category": "query", "message": "[filtered]"}

    def test_safer_queries_are_untouched(self):
        """Safer queries are passed without modification."""
        message = (
            'SELECT "crashstats_product"."product_name" FROM "crashstats_product"'
            ' WHERE "crashstats_product"."is_active" = True'
            ' ORDER BY "crashstats_product"."sort" ASC'
        )
        crumb = {"category": "query", "message": message}
        SanitizeSQLQueryCrumb(("secret",))(crumb, {})
        assert crumb["message"] == message

    def test_non_queries_are_skipped(self):
        """Non-query breadcrumbs are passed without modification."""
        message = "I am a secret"
        crumb = {"category": "not query", "message": message}
        SanitizeSQLQueryCrumb(("secret",))(crumb, {})
        assert crumb["message"] == message

    def test_table_and_column_psql_quoted(self):
        """If a name contains a dot, it searches PostgreSQL quoted tables and columns."""
        # PostgreSQL-style identifer quoting
        # MS SQL uses [brackets], MySQL uses `backticks`
        sql = 'SELECT * FROM "table" WHERE "table"."id" = 1'
        crumb = {"category": "query", "message": sql}
        SanitizeSQLQueryCrumb(("table.id",))(crumb, {})
        assert crumb == {"category": "query", "message": "[filtered]"}

    def test_table_and_column_unquoted(self):
        """If a name contains a dot, it searches for a tables and columns."""
        sql = "SELECT * FROM table WHERE table.id = 1"
        crumb = {"category": "query", "message": sql}
        SanitizeSQLQueryCrumb(("table.id",))(crumb, {})
        assert crumb == {"category": "query", "message": "[filtered]"}


class TestSanitizeHeaders:
    """Tests for SanitizeHeaders."""

    # Test cases: names, URL, headers, expected headers
    CASES = (
        # Use an API token
        (
            "Auth-Token",
            "http://example.com/api/RawCrash/",
            {
                "Auth-Token": "12345abcde",
                "User-Agent": "curl/7.54.0",
                "Host": "example.com",
            },
            {
                "Auth-Token": "[filtered]",  # This is the sensitive key that changes
                "User-Agent": "curl/7.54.0",
                "Host": "example.com",
            },
        ),
        # Deployed behind an AWS Elastic Load Balancer (ELB)
        (
            "X-Forwarded-For,X-Real-IP",
            "https://example.com/siteadmin/crash-me-now/",
            {
                "Host": "example.com",
                "X-Forwarded-For": "203.0.113.19, 203.0.113.19",
                "X-Forwarded-Port": "443",
                "X-Forwarded-Proto": "https",
                "X-Real-Ip": "203.0.113.19",
            },
            {
                "Host": "example.com",
                "X-Forwarded-For": "[filtered]",  # Sensitive
                "X-Forwarded-Port": "443",
                "X-Forwarded-Proto": "https",
                "X-Real-Ip": "[filtered]",  # Also sensitive
            },
        ),
    )

    @pytest.mark.parametrize(
        "names, url, headers, expected", CASES, ids=tuple(case[0] for case in CASES)
    )
    def test_filtered_headers(self, names, url, headers, expected):
        """Sensitive Headers are filtered."""
        event = {"request": {"url": url, "headers": deepcopy(headers)}}
        SanitizeHeaders(names.split(","))(event, {})
        assert event["request"]["headers"] == expected

    def test_safer_headers_are_untouched(self):
        """Safer headers are passed without modification."""
        safe_headers = {"Accept": "*/*"}
        event = {
            "request": {"url": "https://example.com", "headers": deepcopy(safe_headers)}
        }
        SanitizeHeaders(["Auth-Token"])(event, {})
        assert event["request"]["headers"] == safe_headers

    def test_no_headers(self):
        """An event without headers is unmodified."""
        event = {"request": {"url": "https://example.com"}}
        SanitizeHeaders(["Auth-Token"])(event, {})
        assert event == {"request": {"url": "https://example.com"}}


class TestSanitizePostData:
    """Tests for SanitizePostData."""

    # Test cases: names, URL, data, expected data
    CASES = (
        # Create a new token
        (
            "csrfmiddlewaretoken",
            "http://example.com/api/tokens/",
            {"csrfmiddlewaretoken": "base64_str", "notes": "Test", "permissions": "18"},
            {
                "csrfmiddlewaretoken": "[filtered]",  # This is the sensitive key that changes
                "notes": "Test",
                "permissions": "18",
            },
        ),
    )

    @pytest.mark.parametrize(
        "names, url, post_data, expected", CASES, ids=tuple(case[0] for case in CASES)
    )
    def test_filtered_post_data(self, names, url, post_data, expected):
        """Sensitive POST data are filtered."""
        event = {"request": {"url": url, "data": deepcopy(post_data)}}
        SanitizePostData(names=names.split(","))(event, {})
        assert event["request"]["data"] == expected

    def test_safer_post_data_are_untouched(self):
        """Safer POST data are passed without modification."""
        event = {
            "request": {"url": "https://example.com", "data": {"kittens": "fluffy"}}
        }
        SanitizePostData(names=["secret"])(event, {})
        assert event["request"]["data"] == {"kittens": "fluffy"}

    def test_no_post_data(self):
        """An event without POST data is unmodified."""
        event = {"request": {"url": "https://example.com"}}
        SanitizePostData(names=["secret"])(event, {})
        assert event == {"request": {"url": "https://example.com"}}


class TestSanitizeQueryString:
    """Tests for SanitizeQueryString."""

    # Test cases: names, URL, querystring, expected filtered querystring
    CASES = (
        # OIDC callback for OpenID flow
        (
            "code,state",
            "http://example.com/oidc/callback/",
            "code=abc123&state=base64String",
            "code=%5Bfiltered%5D&state=%5Bfiltered%5D",
        ),
    )

    @pytest.mark.parametrize(
        "names, url, query_string, expected",
        CASES,
        ids=tuple(case[0] for case in CASES),
    )
    def test_filtered_querystrings(self, names, url, query_string, expected):
        """Sensitive querystring values are filtered."""
        event = {"request": {"url": url, "query_string": query_string}}
        SanitizeQueryString(names=names.split(","))(event, {})
        assert event["request"]["query_string"] == expected

    def test_safer_querystrings_are_untouched(self):
        """Safer querystrings are passed without modification."""
        event = {
            "request": {"url": "https://example.com", "query_string": "first_time=1"}
        }
        SanitizeQueryString(names=["secret"])(event, {})
        assert event["request"]["query_string"] == "first_time=1"

    def test_querystrings_are_normalized(self):
        """Some querystrings may be modified by sanitization, even without sensitive params."""
        query_string = "test=%A&random&invalid_utf8=%A0%A1"
        event = {
            "request": {"url": "https://example.com", "query_string": query_string}
        }
        SanitizeQueryString(names=["secret"])(event, {})
        expected = "test=%25A&random=&invalid_utf8=%EF%BF%BD%EF%BF%BD"
        assert event["request"]["query_string"] == expected

    def test_no_querystring(self):
        """An event without a querystring is unmodified."""
        event = {"request": {"url": "https://example.com"}}
        SanitizeQueryString(names=["secret"])(event, {})
        assert event == {"request": {"url": "https://example.com"}}


class TestBeforeSend:
    """Tests for before_send."""

    @pytest.mark.parametrize(
        "names, url, headers, expected_headers",
        TestSanitizeHeaders.CASES,
        ids=tuple(case[0] for case in TestSanitizeHeaders.CASES),
    )
    def test_event_headers_sanitized(self, names, url, headers, expected_headers):
        """Request headers are sanitized of sensitive values."""
        event = {"request": {"url": url, "headers": deepcopy(headers)}}
        processed = build_before_send()(event, {})
        expected = {"request": {"url": url, "headers": expected_headers}}
        assert processed == expected

    @pytest.mark.parametrize(
        "names, url, post_data, expected_post_data",
        TestSanitizePostData.CASES,
        ids=tuple(case[0] for case in TestSanitizePostData.CASES),
    )
    def test_event_post_data_sanitized(self, names, url, post_data, expected_post_data):
        """Request POST data are sanitized of sensitive values."""
        event = {"request": {"url": url, "data": deepcopy(post_data)}}
        processed = build_before_send()(event, {})
        expected = {"request": {"url": url, "data": expected_post_data}}
        assert processed == expected

    @pytest.mark.parametrize(
        "names, url, query_string, expected_query_string",
        TestSanitizeQueryString.CASES,
        ids=tuple(case[0] for case in TestSanitizeQueryString.CASES),
    )
    def test_event_querystring_sanitized(
        self, names, url, query_string, expected_query_string
    ):
        """Request querystrings are sanitized of sensitive values."""
        event = {"request": {"url": url, "query_string": query_string}}
        processed = build_before_send()(event, {})
        expected = {"request": {"url": url, "query_string": expected_query_string}}
        assert processed == expected


class TestBeforeBreadcrumb:
    def test_breadcrumb_queries_truncated(self):
        """Query breadcrumbs are truncated on sensitive column names."""

        for sql in TestSanitizeSQLQueryCrumb.CASES.values():
            breadcrumb = {"category": "query", "message": sql}
            hint = {}
            expected = {"category": "query", "message": "[filtered]"}

            processed = build_before_breadcrumb()(breadcrumb, hint)
            assert processed == expected


class TestIntegration(LiveServerTestCase):
    """Verify that sanitization code works with sentry-sdk."""

    def get_fakesentry_baseurl(self):
        sentry_dsn = settings.SENTRY_DSN

        parsed_dsn = urllib.parse.urlparse(sentry_dsn)
        netloc = parsed_dsn.netloc
        if "@" in netloc:
            netloc = netloc[netloc.find("@") + 1 :]

        return f"{parsed_dsn.scheme}://{netloc}/"

    def test_integration(self):
        fakesentry_api = self.get_fakesentry_baseurl()

        # Flush errors so the list is empty
        resp = requests.get(fakesentry_api + "api/flush/")
        assert resp.status_code == 200

        resp = requests.get(fakesentry_api + "api/errorlist/")
        assert len(resp.json()["errors"]) == 0

        # Call /__broken__ which returns an HTTP 500 and sends an error to Sentry
        resp = requests.get(
            self.live_server_url + "/__broken__", params={"state": "badvalue"}
        )
        assert resp.status_code == 500

        resp = requests.get(fakesentry_api + "api/errorlist/")
        assert len(resp.json()["errors"]) == 1
        error_id = resp.json()["errors"][0]

        # This verifies that sanitization code ran by checking to make sure the
        # querystring was filtered
        resp = requests.get(f"{fakesentry_api}api/error/{error_id}")
        assert (
            resp.json()["payload"]["request"]["query_string"] == "state=%5Bfiltered%5D"
        )
