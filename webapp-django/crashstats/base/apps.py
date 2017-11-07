from django.apps import AppConfig
from django.conf import settings

import markus


class BaseConfig(AppConfig):
    name = 'crashstats.base'

    def ready(self):
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

        # If we're in DEBUG mode, then use the logging metrics backend, too
        if settings.DEBUG:
            backends.append(
                {
                    'class': 'markus.backends.logging.LoggingMetrics',
                }
            )

        markus.configure(backends=backends)
