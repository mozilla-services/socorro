# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import elasticsearch
import json

from socorro.lib import (
    DatabaseError,
    MissingArgumentError,
    ResourceNotFound,
)
from socorro.external.es.base import ElasticsearchBase
from socorro.lib import datetimeutil, external_common


class Query(ElasticsearchBase):
    '''Implement the /query service with ElasticSearch. '''

    filters = [
        ('query', None, 'json'),
        ('indices', None, ['list', 'str']),
    ]

    def get_connection(self):
        with self.es_context(
            timeout=self.config.elasticsearch.elasticsearch_timeout_extended
        ) as conn:
            return conn

    def get(self, **kwargs):
        '''Return the result of a custom query. '''
        params = external_common.parse_arguments(self.filters, kwargs)

        if not params.query:
            raise MissingArgumentError('query')

        # Set indices.
        indices = []
        if not params.indices:
            # By default, use the last two indices.
            today = datetimeutil.utc_now()
            last_week = today - datetime.timedelta(days=7)

            indices = self.generate_list_of_indexes(last_week, today)
        elif len(params.indices) == 1 and params.indices[0] == 'ALL':
            # If we want all indices, just do nothing.
            pass
        else:
            indices = params.indices

        search_args = {}
        if indices:
            search_args['index'] = indices
            search_args['doc_type'] = (
                self.config.elasticsearch.elasticsearch_doctype
            )

        connection = self.get_connection()

        try:
            results = connection.search(
                body=json.dumps(params.query),
                **search_args
            )
        except elasticsearch.exceptions.NotFoundError as e:
            missing_index = e.info['error']['index']
            raise ResourceNotFound(
                "elasticsearch index '%s' does not exist" % missing_index
            )
        except elasticsearch.exceptions.TransportError as e:
            raise DatabaseError(e)

        return results
