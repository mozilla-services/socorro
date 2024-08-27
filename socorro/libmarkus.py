# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Holds Markus utility functions and global state."""

import logging
from pathlib import Path

import markus
from markus.filters import AddTagFilter, RegisteredMetricsFilter
import yaml


_IS_MARKUS_SET_UP = False

LOGGER = logging.getLogger(__name__)
METRICS = markus.get_metrics("socorro")


# Complete index of all metrics. This is used in documentation and to filter outgoing
# metrics.
def _load_registered_metrics():
    # Load the metrics yaml file in this directory
    path = Path(__file__).parent / "statsd_metrics.yaml"
    with open(path) as fp:
        data = yaml.safe_load(fp)
    return data


STATSD_METRICS = _load_registered_metrics()


def set_up_metrics(statsd_host, statsd_port, hostname, debug=False):
    """Initialize and configures the metrics system.

    :arg statsd_host: the statsd host to send metrics to
    :arg statsd_port: the port on the host to send metrics to
    :arg hostname: the host name
    :arg debug: whether or not to additionally log metrics to the logger

    """
    global _IS_MARKUS_SET_UP, METRICS
    if _IS_MARKUS_SET_UP:
        return

    markus_backends = [
        {
            "class": "markus.backends.datadog.DatadogMetrics",
            "options": {
                "statsd_host": statsd_host,
                "statsd_port": statsd_port,
            },
        }
    ]
    if debug:
        markus_backends.append(
            {
                "class": "markus.backends.logging.LoggingMetrics",
                "options": {
                    "logger_name": "markus",
                    "leader": "METRICS",
                },
            }
        )

        # In local dev and test environments, we want the RegisteredMetricsFilter to
        # raise exceptions when metrics are used incorrectly.
        metrics_filter = RegisteredMetricsFilter(
            registered_metrics=STATSD_METRICS, raise_error=True
        )
        METRICS.filters.append(metrics_filter)

    if hostname:
        METRICS.filters.append(AddTagFilter(f"host:{hostname}"))

    markus.configure(markus_backends)

    _IS_MARKUS_SET_UP = True


def build_prefix(*parts):
    new_prefix = []
    for part in parts:
        part = part.strip()
        if part:
            new_prefix.append(part)

    return ".".join(parts)
