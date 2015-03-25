# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock
import os
from functools import wraps
from distutils.version import LooseVersion

from configman import ConfigurationManager
from nose import SkipTest

from socorro.external.elasticsearch import crashstorage
from socorro.middleware.middleware_app import MiddlewareApp
from socorro.unittest.testbase import TestCase


# bug 1142475; for legacy purposes only.
def maximum_es_version(maximum_version):
    """Skip the test if the Elasticsearch version is greater than specified.
    :arg minimum_version: string; the maximum Elasticsearch version required.
    """
    def decorated(test):
        """Decorator to only run the test if ES version is greater or
        equal than specified.
        """
        @wraps(test)
        def test_with_version(self):
            "Only run the test if ES version is not more than specified."
            request = self.storage.es.send_request('GET', '')
            actual_version = request['version']['number']
            if LooseVersion(actual_version) <= LooseVersion(maximum_version):
                test(self)
            else:
                raise SkipTest

        return test_with_version

    return decorated


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
            'resource.elasticsearch.elasticsearch_default_index': 'socorro_integration_test',
            'resource.elasticsearch.elasticsearch_index': 'socorro_integration_test_reports',
            'resource.elasticsearch.backoff_delays': [1],
            'resource.elasticsearch.elasticsearch_timeout': 10,
            'resource.postgresql.database_name': 'socorro_integration_test'
        }
        if es_index:
            values_source['resource.elasticsearch.elasticsearch_index'] = es_index

        config_manager = ConfigurationManager(
            [storage_config, middleware_config],
            app_name='testapp',
            app_version='1.0',
            app_description='app description',
            values_source_list=[os.environ, values_source],
            argv_source=[],
        )

        return config_manager.get_config()
