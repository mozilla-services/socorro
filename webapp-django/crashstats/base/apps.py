from django.apps import AppConfig
from django.conf import settings

import markus


class BaseConfig(AppConfig):
    name = 'crashstats.base'

    def ready(self):
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
