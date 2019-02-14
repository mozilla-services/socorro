# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.apps import AppConfig
from django.conf import settings

import markus


class CrashstatsConfig(AppConfig):
    name = 'crashstats.crashstats'

    def ready(self):
        # Import signals kicking off signal registration
        from crashstats.crashstats import signals  # noqa

        # Set up markus
        if settings.LOCAL_DEV_ENV:
            # If we're in the local development environment, then use the
            # logging and statsd backends
            backends = [
                {
                    'class': 'markus.backends.logging.LoggingMetrics',
                },
                {
                    'class': 'markus.backends.statsd.StatsdMetrics',
                    'options': {
                        'statsd_host': settings.STATSD_HOST,
                        'statsd_port': settings.STATSD_PORT,
                        'statsd_prefix': settings.STATSD_PREFIX,
                    }
                }
            ]
        else:
            # Otherwise we're in a server environment and we use the datadog
            # backend there
            backends = [
                {
                    # Log metrics to Datadog
                    'class': 'markus.backends.datadog.DatadogMetrics',
                    'options': {
                        'statsd_host': settings.STATSD_HOST,
                        'statsd_port': settings.STATSD_PORT,
                        'statsd_namespace': settings.STATSD_PREFIX,
                    }
                }
            ]

        markus.configure(backends=backends)
