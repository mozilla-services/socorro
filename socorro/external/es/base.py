# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from configman import Namespace, class_converter, RequiredConfig


def generate_list_of_indexes(from_date, to_date, index_format):
    """Return the list of indexes for crash reports processed between from_date and to_date

    The naming pattern for indexes in elasticsearch is configurable, it is
    possible to have an index per day, per week, per month...

    :arg from_date: datetime object
    :arg to_date: datetime object
    :arg index_format: the format to use for the index name

    :returns: list of strings

    """
    indexes = []
    current_date = from_date
    while current_date <= to_date:
        index_name = current_date.strftime(index_format)

        # Make sure no index is twice in the list
        # (for weekly or monthly indexes for example)
        if index_name not in indexes:
            indexes.append(index_name)
        current_date += datetime.timedelta(days=1)

    return indexes


class ElasticsearchConfig(RequiredConfig):
    required_config = Namespace()
    required_config.namespace('elasticsearch')
    required_config.elasticsearch.add_option(
        'elasticsearch_class',
        doc='a class that implements the ES connection object',
        default='socorro.external.es.connection_context.ConnectionContext',
        from_string_converter=class_converter
    )
    required_config.elasticsearch.add_option(
        'elasticsearch_timeout_extended',
        default=120,
        doc='the time in seconds before a query to elasticsearch fails in '
            'restricted sections',
        reference_value_from='resource.elasticsearch',
    )
    required_config.elasticsearch.add_option(
        'facets_max_number',
        default=50,
        doc='the maximum number of results a facet will return in search'
    )
    required_config.elasticsearch.add_option(
        'mapping_test_crash_number',
        default=100,
        doc='the number of crash reports to test against when attempting to '
            'validate a new Elasticsearch mapping. ',
    )
    # shared and not specifically in the elasticsearch config
    required_config.add_option(
        'index_creator_class',
        doc='a class that can create Elasticsearch indices',
        default='socorro.external.es.index_creator.IndexCreator',
        from_string_converter=class_converter
    )
    required_config.add_option(
        'search_default_date_range',
        default=7,  # in days
        doc='the default date range for searches, in days'
    )
    required_config.add_option(
        'search_maximum_date_range',
        default=365,  # in days
        doc='the maximum date range for searches, in days'
    )
