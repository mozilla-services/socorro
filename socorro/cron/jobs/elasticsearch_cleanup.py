# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import pyelasticsearch
import re

from configman import Namespace
from configman.converters import class_converter
from crontabber.base import BaseCronApp

from socorro.lib.datetimeutil import utc_now


class ElasticsearchCleanupCronApp(BaseCronApp):
    """Delete old elasticsearch indices from our databases. """

    app_name = 'elasticsearch-cleanup'
    app_version = '1.0'
    app_description = 'Remove old indices from our elasticsearch database. '

    required_config = Namespace()
    required_config.add_option(
        'retention_policy',
        default=26,
        doc='Number of weeks to keep an index alive. ',
    )
    required_config.namespace('elasticsearch')
    required_config.elasticsearch.add_option(
        'elasticsearch_class',
        default='socorro.external.elasticsearch.connection_context.'
                'ConnectionContext',
        from_string_converter=class_converter,
        reference_value_from='resource.elasticsearch',
    )
    required_config.elasticsearch.add_option(
        'elasticsearch_index_regex',
        default='socorro[0-9]{6}$',
        reference_value_from='resource.elasticsearch',
    )

    def run(self):
        now = utc_now()
        policy_delay = datetime.timedelta(weeks=self.config.retention_policy)
        time_limit = (now - policy_delay).replace(tzinfo=None)

        es = pyelasticsearch.ElasticSearch(
            self.config.elasticsearch.elasticsearch_urls,
            timeout=self.config.elasticsearch.elasticsearch_timeout
        )

        state = es.cluster_state()
        indices = state['metadata']['indices'].keys()

        aliases = es.aliases()

        for index in indices:
            # Some indices look like 'socorro%Y%W_%Y%M%d', but they are
            # aliased to the expected format of 'socorro%Y%W'. In such cases,
            # replace the index with the alias.
            if index in aliases:
                index_aliases = aliases[index]['aliases'].keys()
                if index_aliases:
                    index = index_aliases[0]

            if not re.match(
                self.config.elasticsearch.elasticsearch_index_regex,
                index
            ):
                # This index doesn't look like a crash index, let's skip it.
                continue

            # This won't take the week part of our indices into account...
            index_date = datetime.datetime.strptime(
                index,
                self.config.elasticsearch.elasticsearch_index
            )
            # So we need to get that differently, and then add it to the date.
            index_date += datetime.timedelta(weeks=int(index[-2:]))

            if index_date < time_limit:
                es.delete_index(index)  # Bad index! Go away!
