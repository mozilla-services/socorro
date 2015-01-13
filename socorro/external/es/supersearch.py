# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import re
from elasticsearch_dsl import Search, F, Q
from elasticsearch.exceptions import NotFoundError

from socorro.external import (
    BadArgumentError,
)
from socorro.external.es.super_search_fields import SuperSearchFields
from socorro.lib import datetimeutil
from socorro.lib.search_common import SearchBase


BAD_INDEX_REGEX = re.compile('\[\[(.*)\] missing\]')


class SuperSearch(SearchBase):

    def __init__(self, *args, **kwargs):
        self.config = kwargs.get('config')
        self.es_context = self.config.elasticsearch.elasticsearch_class(
            self.config.elasticsearch
        )

        self.all_fields = SuperSearchFields(config=self.config).get_fields()

        # Create a map to associate a field's name in the database to its
        # exposed name (in the results and facets).
        self.database_name_to_field_name_map = dict(
            (x['in_database_name'], x['name'])
            for x in self.all_fields.values()
        )

        kwargs.update(fields=self.all_fields)
        super(SuperSearch, self).__init__(
            *args, **kwargs
        )

    def get_connection(self):
        with self.es_context() as conn:
            return conn

    def generate_list_of_indices(self, from_date, to_date, es_index=None):
        """Return the list of indices to query to access all the crash reports
        that were processed between from_date and to_date.

        The naming pattern for indices in elasticsearch is configurable, it is
        possible to have an index per day, per week, per month...

        Parameters:
        * from_date datetime object
        * to_date datetime object
        """
        if es_index is None:
            es_index = self.config.elasticsearch_index

        indices = []
        current_date = from_date
        while current_date <= to_date:
            index = current_date.strftime(es_index)

            # Make sure no index is twice in the list
            # (for weekly or monthly indices for example)
            if index not in indices:
                indices.append(index)
            current_date += datetime.timedelta(days=1)

        return indices

    def get_indices(self, dates):
        """Return the list of indices to use for given dates. """
        start_date = None
        end_date = None
        for date in dates:
            if '>' in date.operator:
                start_date = date.value
            if '<' in date.operator:
                end_date = date.value

        return self.generate_list_of_indices(start_date, end_date)

    def format_field_names(self, hit):
        """Return a hit with each field's database name replaced by its
        exposed name. """
        new_hit = {}
        for field in hit:
            new_field = field

            if '.' in new_field:
                # Remove the prefix ("processed_crash." or "raw_crash.").
                new_field = new_field.split('.')[-1]

            new_field = self.database_name_to_field_name_map.get(
                new_field, new_field
            )

            new_hit[new_field] = hit[field]

        return new_hit

    def format_fields(self, hit):
        """Return a well formatted document.

        Elasticsearch returns values as lists when using the `fields` option.
        This function removes the list when it contains zero or one element.
        It also calls `format_field_names` to correct all the field names.
        """
        hit = self.format_field_names(hit)

        for field in hit:
            if isinstance(hit[field], (list, tuple)):
                if len(hit[field]) == 0:
                    hit[field] = None
                elif len(hit[field]) == 1:
                    hit[field] = hit[field][0]

        return hit

    def format_aggregations(self, aggregations):
        """Return aggregations in a form that looks like facets.

        We used to expose the Elasticsearch facets directly. This is thus
        needed for backwards compatibility.
        """
        aggs = aggregations.to_dict()
        for agg in aggs:
            for i, row in enumerate(aggs[agg]['buckets']):
                aggs[agg]['buckets'][i] = {
                    'term': row['key'],
                    'count': row['doc_count'],
                }
            aggs[agg] = aggs[agg]['buckets']

        return aggs

    def get(self, **kwargs):
        """Return a list of results and aggregations based on parameters.

        The list of accepted parameters (with types and default values) is in
        the database and can be accessed with the super_search_fields service.
        """
        # Filter parameters and raise potential errors.
        params = self.get_parameters(**kwargs)

        # Find the indices to use to optimize the elasticsearch query.
        indices = self.get_indices(params['date'])

        # Create and configure the search object.
        search = Search(
            using=self.get_connection(),
            index=indices,
            doc_type=self.config.elasticsearch.elasticsearch_doctype,
        )

        # Create filters.
        filters = None

        for field, sub_params in params.items():
            sub_filters = None
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
                filter_type = 'term'
                filter_value = None
                if not param.operator:
                    # contains one of the terms
                    if len(param.value) == 1:
                        val = param.value[0]
                        if not isinstance(val, basestring) or (
                            isinstance(val, basestring) and ' ' not in val
                        ):
                            filter_value = val

                        # If the term contains white spaces, we want to perform
                        # a phrase query. Thus we do nothing here and let this
                        # value be handled later.
                    else:
                        filter_type = 'terms'
                        filter_value = param.value
                elif param.operator == '=':
                    # is exactly
                    if field_data['has_full_version']:
                        name = '%s.full' % name
                    filter_value = param.value
                elif param.operator == '>':
                    # greater than
                    filter_type = 'range'
                    filter_value = {
                        'gt': param.value
                    }
                elif param.operator == '<':
                    # lower than
                    filter_type = 'range'
                    filter_value = {
                        'lt': param.value
                    }
                elif param.operator == '>=':
                    # greater than or equal to
                    filter_type = 'range'
                    filter_value = {
                        'gte': param.value
                    }
                elif param.operator == '<=':
                    # lower than or equal to
                    filter_type = 'range'
                    filter_value = {
                        'lte': param.value
                    }
                elif param.operator == '__null__':
                    # is null
                    filter_type = 'missing'
                    args['field'] = name

                if filter_value is not None:
                    args[name] = filter_value

                if args:
                    if param.operator_not:
                        new_filter = ~F(filter_type, **args)
                    else:
                        new_filter = F(filter_type, **args)

                    if sub_filters is None:
                        sub_filters = new_filter
                    elif param.data_type == 'enum':
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

                    query_type = 'wildcard'
                    args[name] = (
                        operator_wildcards[param.operator] % param.value
                    )
                elif not param.operator:
                    # This is a phrase that was passed down.
                    query_type = 'simple_query_string'
                    args['query'] = param.value[0]
                    args['fields'] = [name]
                    args['default_operator'] = 'and'

                if args:
                    query = Q(query_type, **args)
                    if param.operator_not:
                        query = ~query
                    search = search.query(query)
                else:
                    # If we reach this point, that means the operator is
                    # not supported, and we should raise an error about that.
                    raise NotImplementedError(
                        'Operator %s is not supported' % param.operator
                    )

            if filters is None:
                filters = sub_filters
            elif sub_filters is not None:
                filters &= sub_filters

        search = search.filter(filters)

        # Pagination.
        results_to = results_from + results_number
        search = search[results_from:results_to]

        # Create facets.
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

                search.aggs.bucket(
                    value,
                    'terms',
                    field=field_name,
                    size=self.config.facets_max_number
                )

        # Query and compute results.
        hits = []
        fields = [
            '%s.%s' % (x['namespace'], x['in_database_name'])
            for x in self.all_fields.values()
            if x['is_returned']
        ]
        search = search.fields(*fields)

        if params['_return_query'][0].value[0]:
            # Return only the JSON query that would be sent to elasticsearch.
            return {
                'query': search.to_dict(),
                'indices': indices,
            }

        # We call elasticsearch with a computed list of indices, based on
        # the date range. However, if that list contains indices that do not
        # exist in elasticsearch, an error will be raised. We thus want to
        # remove all failing indices until we either have a valid list, or
        # an empty list in which case we return no result.
        while True:
            try:
                results = search.execute()
                for hit in results:
                    hits.append(self.format_fields(hit.to_dict()))

                total = search.count()
                aggregations = self.format_aggregations(results.aggregations)
                break  # Yay! Results!
            except NotFoundError, e:
                missing_index = re.findall(BAD_INDEX_REGEX, e.error)[0]
                if missing_index in indices:
                    del indices[indices.index(missing_index)]
                else:
                    # Wait what? An error caused by an index that was not
                    # in the request? That should never happen, but in case
                    # it does, better know it.
                    raise

                if indices:
                    # Update the list of indices and try again.
                    # Note: we need to first empty the list of indices before
                    # updating it, otherwise the removed indices never get
                    # actually removed.
                    search = search.index().index(*indices)
                else:
                    # There is no index left in the list, return an empty
                    # result.
                    hits = []
                    total = 0
                    aggregations = {}
                    break

        return {
            'hits': hits,
            'total': total,
            'facets': aggregations,
        }

    # For backwards compatibility with the previous elasticsearch module.
    # All those methods used to live in this file, but have been moved to
    # the super_search_fields.py file now. Since the configuration of the
    # middleware expect those to still be here, we bind them for now.
    def get_fields(self, **kwargs):
        return SuperSearchFields(config=self.config).get_fields(**kwargs)

    def create_field(self, **kwargs):
        return SuperSearchFields(config=self.config).create_field(**kwargs)

    def update_field(self, **kwargs):
        return SuperSearchFields(config=self.config).update_field(**kwargs)

    def delete_field(self, **kwargs):
        return SuperSearchFields(config=self.config).delete_field(**kwargs)

    def get_missing_fields(self):
        return SuperSearchFields(config=self.config).get_missing_fields()
