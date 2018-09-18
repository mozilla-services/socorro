# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import re

from configman import Namespace, RequiredConfig
from configman.converters import class_converter

from socorro.lib.datetimeutil import utc_now


class IndexCleaner(RequiredConfig):
    """Delete elasticsearch indices from our databases."""

    required_config = Namespace()
    required_config.add_option(
        'retention_policy',
        default=26,
        doc='Number of weeks to keep an index alive. ',
    )
    required_config.namespace('elasticsearch')
    required_config.elasticsearch.add_option(
        'elasticsearch_class',
        default='socorro.external.es.connection_context.ConnectionContext',
        from_string_converter=class_converter,
        reference_value_from='resource.elasticsearch',
    )
    required_config.elasticsearch.add_option(
        'elasticsearch_index_regex',
        default='^socorro[0-9]{6}$',
        reference_value_from='resource.elasticsearch',
    )

    def __init__(self, config):
        super(IndexCleaner, self).__init__()
        self.config = config

    def delete_indices(self, predicate=None):
        """Delete crash indices that match the given predicate.

        :arg callable predicate: A callable of the form
            ``predicate(index)``, where ``index`` is a string containing
            the name of the index. If the callable returns true, the
            index will be deleted.

            The default is None, which deletes all crash indices.
        :returns: List of indexes that were deleted

        """
        es_class = self.config.elasticsearch.elasticsearch_class(
            self.config.elasticsearch
        )
        index_client = es_class.indices_client()

        status = index_client.status()
        indices = status['indices'].keys()

        aliases = index_client.get_aliases()

        deleted_indices = []
        for index in indices:
            # Some indices look like 'socorro%Y%W_%Y%M%d', but they are
            # aliased to the expected format of 'socorro%Y%W'. In such cases,
            # replace the index with the alias.
            if index in aliases and 'aliases' in aliases[index]:
                index_aliases = list(aliases[index]['aliases'].keys())
                if index_aliases:
                    index = index_aliases[0]

            if not re.match(
                self.config.elasticsearch.elasticsearch_index_regex,
                index
            ):
                # This index doesn't look like a crash index, let's skip it.
                continue

            if predicate is None or predicate(index):
                index_client.delete(index)
                deleted_indices.append(index)

        return deleted_indices

    def delete_old_indices(self):
        self.delete_indices(self.is_index_old)

    def is_index_old(self, index):
        now = utc_now()
        policy_delay = datetime.timedelta(weeks=self.config.retention_policy)
        time_limit = (now - policy_delay).replace(tzinfo=None)

        # strptime ignores week numbers if a day isn't specified, so we append
        # '-1' and '-%w' to specify Monday as the day.
        index_date = datetime.datetime.strptime(
            index + '-1',
            self.config.elasticsearch.elasticsearch_index + '-%w'
        )

        return index_date < time_limit
