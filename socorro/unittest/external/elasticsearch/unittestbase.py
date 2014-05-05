# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock
import os

from configman import ConfigurationManager

from socorro.external.elasticsearch import crashstorage
from socorro.middleware.middleware_app import MiddlewareApp
from socorro.unittest.testbase import TestCase


class ElasticSearchTestCase(TestCase):
    """Base class for Elastic Search related unit tests. """

    def get_config_context(self, es_index=None):
        mock_logging = mock.Mock()

        storage_config = \
            crashstorage.ElasticSearchCrashStorage.get_required_config()
        middleware_config = MiddlewareApp.get_required_config()
        middleware_config.add_option('logger', default=mock_logging)

        values_source = {
            'logger': mock_logging,
            'elasticsearch_index': 'socorro_integration_test',
            'backoff_delays': [1],
            'elasticsearch_timeout': 5,
        }
        if es_index:
            values_source['elasticsearch_index'] = es_index

        config_manager = ConfigurationManager(
            [storage_config, middleware_config],
            app_name='testapp',
            app_version='1.0',
            app_description='app description',
            values_source_list=[os.environ, values_source],
            argv_source=[],
        )

        with config_manager.context() as config:
            # This is an ugly hack to compensate for a bug in configman.
            # See https://github.com/mozilla/configman/issues/103
            config.backoff_delays = [1]
            return config
