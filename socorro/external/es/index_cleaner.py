# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import re

from configman import Namespace, RequiredConfig
from configman.converters import class_converter

from socorro.lib.datetimeutil import utc_now


class IndexCleaner(RequiredConfig):
    """Delete old elasticsearch indices from our databases. """

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

    def delete_old_indices(self):
        now = utc_now()
        policy_delay = datetime.timedelta(weeks=self.config.retention_policy)
        time_limit = (now - policy_delay).replace(tzinfo=None)

        es_class = self.config.elasticsearch.elasticsearch_class(
            self.config.elasticsearch
        )
        index_client = es_class.indices_client()
        cat_client = es_class.cat_client()

        # Get the list of all indices in the cluster, as well as all
        # existing aliases.
        indices = [x['index'] for x in cat_client.indices(format='json')]
        aliases = dict(
            (x['alias'], x['index'])
            for x in cat_client.aliases(format='json')
        )

        # Some indices look like 'socorro%Y%W_%Y%M%d', but they are
        # aliased to the expected format of 'socorro%Y%W'. To cover such
        # cases, we add all aliases to the list of indices we loop over.
        indices += aliases.keys()

        for index in indices:
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
                # In the case of an alias, we want to first delete that alias,
                # then make sure we delete the associated index.
                if index in aliases:
                    index_client.delete_alias(name=index, index=aliases[index])
                    index = aliases[index]

                index_client.delete(index)  # Bad index! Go away!
