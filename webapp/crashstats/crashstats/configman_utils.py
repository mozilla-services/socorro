# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Utility functions for working with configman components.
"""

import importlib

from configman import ConfigurationManager, configuration, Namespace
from configman.environment import environment

from django.conf import settings
from django.utils.module_loading import import_string

from socorro.app.socorro_app import App
from socorro.external.boto.crash_data import SimplifiedCrashData, TelemetryCrashData
from socorro.external.es.connection_context import (
    ConnectionContext as ESConnectionContext,
)


def get_s3_context():
    """Return an S3ConnectionContext."""
    # The class could be anything, so get the class first
    cls_path = settings.SOCORRO_CONFIG["resource"]["boto"]["resource_class"]
    module, name = cls_path.rsplit(".", 1)
    cls = getattr(importlib.import_module(module), name)

    # Now create a configuration and instantiate the class with it
    cm = ConfigurationManager(
        cls.get_required_config(),
        values_source_list=[
            # We prefer the webapp's configuration over things in the
            # environment which are likely to be configman things
            settings.SOCORRO_CONFIG,
            environment,
        ],
    )
    config = cm.get_config()
    return cls(config)


def config_from_configman():
    """Generate a configman DotDict to pass to configman components."""
    definition_source = Namespace()
    definition_source.namespace("logging")
    definition_source.logging = App.required_config.logging

    definition_source.namespace("metricscfg")
    definition_source.metricscfg = App.required_config.metricscfg

    definition_source.namespace("elasticsearch")
    definition_source.elasticsearch.add_option(
        "elasticsearch_class", default=ESConnectionContext
    )
    definition_source.namespace("queue")
    definition_source.add_option(
        "crashqueue_class", default=import_string(settings.CRASHQUEUE)
    )
    definition_source.namespace("crashdata")
    definition_source.crashdata.add_option(
        "crash_data_class", default=SimplifiedCrashData
    )
    definition_source.namespace("telemetrydata")
    definition_source.telemetrydata.add_option(
        "telemetry_data_class", default=TelemetryCrashData
    )

    return configuration(
        definition_source=definition_source,
        values_source_list=[settings.SOCORRO_CONFIG],
    )
