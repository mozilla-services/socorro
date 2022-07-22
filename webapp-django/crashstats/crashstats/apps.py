# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from fillmore.scrubber import (
    build_scrub_query_string,
    Rule,
    Scrubber,
    SCRUB_RULES_DEFAULT,
)
from fillmore.libsentry import set_up_sentry
import markus
from sentry_sdk.integrations.atexit import AtexitIntegration
from sentry_sdk.integrations.boto3 import Boto3Integration
from sentry_sdk.integrations.dedupe import DedupeIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.excepthook import ExcepthookIntegration
from sentry_sdk.integrations.modules import ModulesIntegration
from sentry_sdk.integrations.stdlib import StdlibIntegration
from sentry_sdk.integrations.threading import ThreadingIntegration

from django.apps import AppConfig
from django.conf import settings

from socorro.lib.libdockerflow import get_release_name


metrics = markus.get_metrics("webapp.crashstats.apps")


SCRUB_RULES_WEBAPP = [
    Rule(
        path="request.headers",
        keys=["Auth-Token", "Cookie", "X-Forwarded-For", "X-Real-Ip"],
        scrub="scrub",
    ),
    Rule(
        path="request",
        keys=["query_string"],
        scrub=build_scrub_query_string(params=["code", "state"]),
    ),
    Rule(
        path="request",
        keys=["cookies"],
        scrub="scrub",
    ),
]


def count_sentry_scrub_error(msg):
    metrics.incr("sentry_scrub_error", 1)


def configure_sentry():
    release = get_release_name(settings.SOCORRO_ROOT)
    scrubber = Scrubber(
        rules=SCRUB_RULES_DEFAULT + SCRUB_RULES_WEBAPP,
        error_handler=count_sentry_scrub_error,
    )

    set_up_sentry(
        release=release,
        host_id=settings.HOST_ID,
        sentry_dsn=settings.SENTRY_DSN,
        # Disable frame-local variables
        with_locals=False,
        # Disable request data from being added to Sentry events
        request_bodies="never",
        # All integrations should be intentionally enabled
        default_integrations=False,
        integrations=[
            DjangoIntegration(),
            AtexitIntegration(),
            Boto3Integration(),
            ExcepthookIntegration(),
            DedupeIntegration(),
            StdlibIntegration(),
            ModulesIntegration(),
            ThreadingIntegration(),
        ],
        # Scrub sensitive data
        before_send=scrubber,
    )


class CrashstatsConfig(AppConfig):
    name = "crashstats.crashstats"

    def ready(self):
        # Import signals kicking off signal registration
        from crashstats.crashstats import signals  # noqa

        # Set up markus metrics
        markus.configure(backends=settings.MARKUS_BACKENDS)

        # Set up sentry
        configure_sentry()
