# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Utility functions for working with configman components.
"""

from configman import configuration, Namespace

from django.conf import settings

from socorro.app.socorro_app import App
from socorro.external.boto.crash_data import SimplifiedCrashData, TelemetryCrashData
from socorro.external.es.connection_context import ConnectionContext as ESConnectionContext
from socorro.external.pubsub.crashqueue import PubSubCrashQueue


def config_from_configman():
    """Generate a configman DotDict to pass to configman components."""
    definition_source = Namespace()
    definition_source.namespace('logging')
    definition_source.logging = App.required_config.logging

    definition_source.namespace('metricscfg')
    definition_source.metricscfg = App.required_config.metricscfg

    definition_source.namespace('elasticsearch')
    definition_source.elasticsearch.add_option(
        'elasticsearch_class',
        default=ESConnectionContext,
    )
    definition_source.namespace('queue')
    definition_source.add_option(
        'crashqueue_class',
        default=PubSubCrashQueue
    )
    definition_source.namespace('crashdata')
    definition_source.crashdata.add_option(
        'crash_data_class',
        default=SimplifiedCrashData,
    )
    definition_source.namespace('telemetrydata')
    definition_source.telemetrydata.add_option(
        'telemetry_data_class',
        default=TelemetryCrashData,
    )

    return configuration(
        definition_source=definition_source,
        values_source_list=[
            settings.SOCORRO_IMPLEMENTATIONS_CONFIG,
        ]
    )
