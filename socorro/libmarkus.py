# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Holds Markus utility functions and global state."""

import logging

import markus
from markus.filters import AddTagFilter


_IS_MARKUS_SETUP = False

LOGGER = logging.getLogger(__name__)
METRICS = markus.get_metrics("socorro")


def set_up_metrics(statsd_host, statsd_port, hostname, debug=False):
    """Initialize and configures the metrics system.

    :arg statsd_host: the statsd host to send metrics to
    :arg statsd_port: the port on the host to send metrics to
    :arg hostname: the host name
    :arg debug: whether or not to additionally log metrics to the logger

    """
    global _IS_MARKUS_SETUP, METRICS
    if _IS_MARKUS_SETUP:
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

    if hostname:
        METRICS.filters.append(AddTagFilter(f"host:{hostname}"))

    markus.configure(markus_backends)

    _IS_MARKUS_SETUP = True


def build_prefix(*parts):
    new_prefix = []
    for part in parts:
        part = part.strip()
        if part:
            new_prefix.append(part)

    return ".".join(parts)
