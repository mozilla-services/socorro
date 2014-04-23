# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import json
import pyelasticsearch
import re
from pyelasticsearch.exceptions import (
    ElasticHttpError,
    ElasticHttpNotFoundError,
    InvalidJsonResponseError,
)

from socorro.external import (
    BadArgumentError,
    DatabaseError,
    MissingArgumentError,
    ResourceNotFound,
)
from socorro.external.elasticsearch.base import ElasticSearchBase
from socorro.external.elasticsearch.supersearch import BAD_INDEX_REGEX
from socorro.lib import external_common
from socorro.lib.datetimeutil import utc_now


class Query(ElasticSearchBase):
    '''Implement the /query service with ElasticSearch. '''

    filters = [
        ('query', None, 'str'),
        ('indices', None, ['list', 'str']),
    ]

    def get(self, **kwargs):
        '''Return the result of a custom query. '''
        params = external_common.parse_arguments(self.filters, kwargs)

        if not params.query:
            raise MissingArgumentError('query')

        try:
            query = json.loads(params.query)
        except ValueError:
            raise BadArgumentError(
                'query',
                msg="Invalid JSON value for parameter 'query'"
            )

        es = pyelasticsearch.ElasticSearch(
            urls=self.config.elasticsearch_urls,
            timeout=self.config.elasticsearch_timeout_extended,
        )

        # Set indices.
        indices = []
        if not params.indices:
            # By default, use the last two indices.
            today = utc_now()
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
            search_args['doc_type'] = self.config.elasticsearch_doctype

        try:
            results = es.search(
                query,
                **search_args
            )
        except ElasticHttpNotFoundError, e:
            missing_index = re.findall(BAD_INDEX_REGEX, e.error)[0]
            raise ResourceNotFound(
                "elasticsearch index '%s' does not exist" % missing_index
            )
        except (InvalidJsonResponseError, ElasticHttpError), e:
            raise DatabaseError(e)

        return results

    post = get
