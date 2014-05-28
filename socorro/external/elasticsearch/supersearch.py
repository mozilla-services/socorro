# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import re
import os

from elasticutils import F, S
from pyelasticsearch.exceptions import ElasticHttpNotFoundError

from socorro.external import BadArgumentError
from socorro.external.elasticsearch.base import ElasticSearchBase
from socorro.lib import datetimeutil
from socorro.lib.search_common import SearchBase


BAD_INDEX_REGEX = re.compile('\[\[(.*)\] missing\]')


class SuperS(S):
    """Extend elasticutils' S class with the 'missing' filter feature from
    elasticsearch. """

    def process_filter_missing(self, key, value, action):
        return {
            'missing': {
                'field': key,
                'existence': True,
                'null_value': True,
            }
        }


class SuperSearch(SearchBase, ElasticSearchBase):

    def __init__(self, *args, **kwargs):
        config = kwargs.get('config')

        self.all_fields = self.get_fields()

        self.database_name_to_field_name_map = dict(
            (x['in_database_name'], x['name'])
            for x in self.all_fields.values()
        )

        # We have multiple inheritance here, explicitly calling superclasses's
        # init is mandatory.
        # See http://freshfoo.com/blog/object__init__takes_no_parameters
        SearchBase.__init__(self, config=config, fields=self.all_fields)
        ElasticSearchBase.__init__(self, config=config)

    def get(self, **kwargs):
        """Return a list of results and facets based on parameters.

        The list of accepted parameters (with types and default values) is in
        socorro.lib.search_common.SearchBase
        """
        # Filter parameters and raise potential errors.
        params = self.get_parameters(**kwargs)

        # Find the indexes to use to optimize the elasticsearch query.
        indexes = self.get_indexes(params['date'])

        # Create and configure the search object.
        search = SuperS().es(
            urls=self.config.elasticsearch_urls,
            timeout=self.config.elasticsearch_timeout,
        )
        search = search.indexes(*indexes)
        search = search.doctypes(self.config.elasticsearch_doctype)

        # Create filters.
        filters = F()

        for field, sub_params in params.items():
            sub_filters = F()
            for param in sub_params:

                if param.name.startswith('_'):
                    if param.name == '_results_offset':
                        results_from = param.value[0]
                    elif param.name == '_results_number':
                        results_number = param.value[0]
                    # Don't use meta parameters in the query.
                    continue

                field_data = self.all_fields[param.name]

                name = '%s.%s' % (
                    field_data['namespace'],
                    field_data['in_database_name']
                )

                if param.data_type in ('date', 'datetime'):
                    param.value = datetimeutil.date_to_string(param.value)
                elif param.data_type == 'enum':
                    param.value = [x.lower() for x in param.value]
                elif param.data_type == 'str' and not param.operator:
                    param.value = [x.lower() for x in param.value]

                args = {}
                if not param.operator:
                    # contains one of the terms
                    if len(param.value) == 1:
                        val = param.value[0]
                        if not isinstance(val, basestring) or (
                            isinstance(val, basestring) and ' ' not in val
                        ):
                            args[name] = val

                        # If the term contains white spaces, we want to perform
                        # a phrase query. Thus we do nothing here and let this
                        # value be handled later.
                    else:
                        args['%s__in' % name] = param.value
                elif param.operator == '=':
                    # is exactly
                    if field_data['has_full_version']:
                        name = '%s.full' % name
                    args[name] = param.value
                elif param.operator == '>':
                    # greater than
                    args['%s__gt' % name] = param.value
                elif param.operator == '<':
                    # lower than
                    args['%s__lt' % name] = param.value
                elif param.operator == '>=':
                    # greater than or equal to
                    args['%s__gte' % name] = param.value
                elif param.operator == '<=':
                    # lower than or equal to
                    args['%s__lte' % name] = param.value
                elif param.operator == '__null__':
                    # is null
                    args['%s__missing' % name] = param.value

                if args:
                    if param.operator_not:
                        new_filter = ~F(**args)
                    else:
                        new_filter = F(**args)

                    if param.data_type == 'enum':
                        sub_filters |= new_filter
                    else:
                        sub_filters &= new_filter

                    continue

                # These use a wildcard and thus need to be in a query
                # instead of a filter.
                operator_wildcards = {
                    '~': '*%s*',  # contains
                    '$': '%s*',  # starts with
                    '^': '*%s'  # ends with
                }
                if param.operator in operator_wildcards:
                    if field_data['has_full_version']:
                        name = '%s.full' % name
                    args['%s__wildcard' % name] = \
                        operator_wildcards[param.operator] % param.value
                    args['must_not'] = param.operator_not
                elif not param.operator:
                    # This is phrase that was passed down.
                    args['%s__match_phrase' % name] = param.value[0]

                if args:
                    search = search.query(**args)
                else:
                    # If we reach this point, that means the operator is
                    # not supported, and we should raise an error about that.
                    raise NotImplementedError(
                        'Operator %s is not supported' % param.operator
                    )

            filters &= sub_filters

        search = search.filter(filters)

        # Pagination.
        results_to = results_from + results_number
        search = search[results_from:results_to]

        # Create facets.
        processed_filters = search._process_filters(filters.filters)

        for param in params['_facets']:
            for value in param.value:
                try:
                    field_ = self.all_fields[value]
                except KeyError:
                    # That is not a known field, we can't facet on it.
                    raise BadArgumentError(
                        value,
                        msg='Unknown field "%s", cannot facet on it' % value
                    )

                field_name = '%s.%s' % (
                    field_['namespace'],
                    field_['in_database_name']
                )

                if field_['has_full_version']:
                    # If the param has a full version, that means what matters
                    # is the full string, and not its individual terms.
                    field_name += '.full'

                args = {
                    value: {
                        'terms': {
                            'field': field_name,
                            'size': self.config.facets_max_number,
                        },
                        'facet_filter': processed_filters,
                    }
                }
                search = search.facet_raw(**args)

        # Query and compute results.
        hits = []
        fields = [
            '%s.%s' % (x['namespace'], x['in_database_name'])
            for x in self.all_fields.values()
            if x['is_returned']
        ]

        if params['_return_query'][0].value[0]:
            # Return only the JSON query that would be sent to elasticsearch.
            return {
                'query': search._build_query(),
                'indices': indexes,
            }

        # We call elasticsearch with a computed list of indices, based on
        # the date range. However, if that list contains indices that do not
        # exist in elasticsearch, an error will be raised. We thus want to
        # remove all failing indices until we either have a valid list, or
        # an empty list in which case we return no result.
        while True:
            try:
                for hit in search.values_dict(*fields):
                    hits.append(self.format_field_names(hit))

                total = search.count()
                facets = search.facet_counts()
                break  # Yay! Results!
            except ElasticHttpNotFoundError, e:
                missing_index = re.findall(BAD_INDEX_REGEX, e.error)[0]
                if missing_index in indexes:
                    del indexes[indexes.index(missing_index)]
                else:
                    # Wait what? An error caused by an index that was not
                    # in the request? That should never happen, but in case
                    # it does, better know it.
                    raise

                if indexes:
                    # Update the list of indices and try again.
                    search = search.indexes(*indexes)
                else:
                    # There is no index left in the list, return an empty
                    # result.
                    hits = []
                    total = 0
                    facets = {}
                    break

        return {
            'hits': hits,
            'total': total,
            'facets': facets,
        }

    def get_indexes(self, dates):
        """Return the list of indexes to use for given dates. """
        start_date = None
        end_date = None
        for date in dates:
            if '>' in date.operator:
                start_date = date.value
            if '<' in date.operator:
                end_date = date.value

        return self.generate_list_of_indexes(start_date, end_date)

    def format_field_names(self, hit):
        """Return a hit with each field's database name replaced by its
        exposed name. """
        new_hit = {}
        for field in hit:
            new_field = field

            if '.' in new_field:
                # Remove the prefix ("processed_crash." or "raw_crash.").
                new_field = new_field.split('.', 1)[1]

            new_field = self.database_name_to_field_name_map.get(
                new_field, new_field
            )

            new_hit[new_field] = hit[field]

        return new_hit

    def get_fields(self):
        file_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'supersearch_fields.json'
        )
        return json.loads(open(file_path, 'r').read())
