# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from configman import ConfigurationManager, Namespace


class ElasticSearchTestCase(unittest.TestCase):
    """Base class for Elastic Search related unit tests. """

    app_name = 'ElasticSearchTestCase'
    app_version = '1.0'
    app_description = __doc__
    metadata = ''

    required_config = Namespace()
    required_config.add_option(
        name='searchMaxNumberOfDistinctSignatures',
        default=1000,
        doc='Integer containing the maximum allowed number of distinct '
            'signatures the system should retrieve. '
            'Used mainly for performances in ElasticSearch',
    )

    required_config.add_option(
        name='elasticSearchHostname',
        default='localhost',
        doc='String containing the URI of the Elastic Search instance.',
    )

    required_config.add_option(
        name='elasticSearchPort',
        default='9200',
        doc='String containing the port on which calling the Elastic '
            'Search instance.',
    )

    required_config.add_option(
        name='elasticsearch_urls',
        default='http://localhost:9200',
        doc='The urls to the elasticsearch instances.',
    )

    required_config.add_option(
        name='elasticsearch_index',
        default='socorro_integration_test',
        doc="An index format to pull crashes from elasticsearch. Use "
            "datetime's strftime format to have daily, weekly or monthly "
            "indexes."
    )

    required_config.add_option(
        name='elasticsearch_doctype',
        default='crash_reports',
        doc='The default doctype to use in elasticsearch.',
    )

    required_config.add_option(
        name='elasticsearch_timeout',
        default=5,
        doc='The time in seconds before a query to elasticsearch fails.',
    )

    required_config.add_option(
        name='facets_max_number',
        default=50,
        doc='The maximum number of results a facet will return in search.',
    )

    required_config.add_option(
        'platforms',
        default=[{
            "id": "windows",
            "name": "Windows NT"
        }, {
            "id": "mac",
            "name": "Mac OS X"
        }, {
            "id": "linux",
            "name": "Linux"
        }],
        doc='Array associating OS ids to full names.',
    )

    required_config.add_option(
        name='non_release_channels',
        default=['beta', 'aurora', 'nightly'],
        doc='List of release channels, excluding the `release` one.',
    )

    required_config.add_option(
        name='restricted_channels',
        default=['beta'],
        doc='List of release channels to restrict based on build ids.',
    )

    def get_standard_config(self):
        config_manager = ConfigurationManager(
            [self.required_config],
            app_name='ElasticSearchTestCase',
            app_description=__doc__
        )

        with config_manager.context() as config:
            return config

    def setUp(self):
        """Create a configuration context. """
        self.config = self.get_standard_config()
