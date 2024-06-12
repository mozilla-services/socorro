# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# This tests whether sentry is set up correctly in the webapp.

from unittest.mock import ANY

from fillmore.test import diff_structure
from markus.testing import MetricsMock
from werkzeug.test import Client

from django.contrib.auth.models import User

from crashstats.crashstats.apps import count_sentry_scrub_error
from crashstats.tokens.models import Token
from crashstats.wsgi import application


# NOTE(willkg): If this changes, we should update it and look for new things that should
# be scrubbed. Use ANY for things that change between tests like timestamps, source code
# data (line numbers, file names, post/pre_context), event ids, build ids, versions,
# etc.
BROKEN_EVENT = {
    "breadcrumbs": ANY,
    "contexts": {
        "runtime": {
            "build": ANY,
            "name": "CPython",
            "version": ANY,
        },
        "trace": {
            "parent_span_id": ANY,
            "span_id": ANY,
            "trace_id": ANY,
        },
    },
    "environment": "production",
    "event_id": ANY,
    "exception": {
        "values": [
            {
                "mechanism": {"handled": False, "type": "django"},
                "module": "crashstats.monitoring.views",
                "stacktrace": {
                    "frames": [
                        {
                            "abs_path": "/usr/local/lib/python3.11/site-packages/django/core/handlers/exception.py",
                            "context_line": ANY,
                            "filename": "django/core/handlers/exception.py",
                            "function": "inner",
                            "in_app": False,
                            "lineno": ANY,
                            "module": "django.core.handlers.exception",
                            "post_context": ANY,
                            "pre_context": ANY,
                        },
                        {
                            "abs_path": "/usr/local/lib/python3.11/site-packages/django/core/handlers/base.py",
                            "context_line": ANY,
                            "filename": "django/core/handlers/base.py",
                            "function": "_get_response",
                            "in_app": False,
                            "lineno": ANY,
                            "module": "django.core.handlers.base",
                            "post_context": ANY,
                            "pre_context": ANY,
                        },
                        {
                            "abs_path": "/app/webapp/crashstats/monitoring/views.py",
                            "context_line": ANY,
                            "filename": "crashstats/monitoring/views.py",
                            "function": "broken",
                            "in_app": True,
                            "lineno": ANY,
                            "module": "crashstats.monitoring.views",
                            "post_context": ANY,
                            "pre_context": ANY,
                        },
                    ]
                },
                "type": "IntentionalException",
                "value": "",
            }
        ]
    },
    "level": "error",
    "modules": ANY,
    "platform": "python",
    "release": ANY,
    "request": {
        "data": "",
        "env": {"SERVER_NAME": "localhost", "SERVER_PORT": "80"},
        "headers": {
            "Auth-Token": "[Scrubbed]",
            "Content-Length": ANY,
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "localhost",
            "X-Forwarded-For": "[Scrubbed]",
            "X-Real-Ip": "[Scrubbed]",
        },
        "method": "GET",
        "query_string": "code=%5BScrubbed%5D&state=%5BScrubbed%5D",
        "url": "http://localhost/__broken__",
    },
    "sdk": {
        "integrations": [
            "atexit",
            "boto3",
            "dedupe",
            "django",
            "excepthook",
            "modules",
            "stdlib",
            "threading",
        ],
        "name": "sentry.python.django",
        "packages": [{"name": "pypi:sentry-sdk", "version": ANY}],
        "version": ANY,
    },
    "server_name": ANY,
    "timestamp": ANY,
    "transaction": "/__broken__",
    "transaction_info": {"source": "route"},
}


def test_sentry_scrubbing(sentry_helper, transactional_db):
    """Test sentry scrubbing configuration

    This verifies that the scrubbing configuration is working by using the /__broken__
    view to trigger an exception that causes Sentry to emit an event for.

    This also helps us know when something has changed when upgrading sentry_sdk that
    would want us to update our scrubbing code or sentry init options.

    This test will fail whenever we:

    * update sentry_sdk to a new version
    * update Django to a new version that somehow adjusts the callstack for an
      exception happening in view code

    In those cases, we should copy the new event, read through it for new problems, and
    redact the parts that will change using ANY so it passes tests.

    """
    client = Client(application)

    # Create a user and a token so the token is valid
    user = User.objects.create(username="francis", email="francis@example.com")
    token = Token.objects.create(user=user)

    with sentry_helper.reuse() as sentry_client:
        resp = client.get(
            "/__broken__",
            query_string={"code": "codeabcde", "state": "stateabcde"},
            headers=[
                ("Auth-Token", token.key),
                ("X-Forwarded-For", "forabcde"),
                ("X-Real-Ip", "forip"),
            ],
            data={
                "csrfmiddlewaretoken": "csrfabcde",
                "client_secret": "clientabcde",
            },
        )
        assert resp.status_code == 500

        (event,) = sentry_client.envelope_payloads

        # Drop the "_meta" bit because we don't want to compare that.
        del event["_meta"]

        differences = diff_structure(event, BROKEN_EVENT)
        assert differences == []


def test_count_sentry_scrub_error():
    with MetricsMock() as metricsmock:
        metricsmock.clear_records()
        count_sentry_scrub_error("foo")
        metricsmock.assert_incr("webapp.sentry_scrub_error", value=1)
