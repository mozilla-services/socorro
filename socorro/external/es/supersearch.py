# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import re
from collections import defaultdict

from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import A, F, Q, Search
from socorrolib.lib import (
    BadArgumentError,
    MissingArgumentError,
    datetimeutil,
)

from socorro.middleware.search_common import SearchBase


BAD_INDEX_REGEX = re.compile('\[\[(.*)\] missing\]')


class SuperSearch(SearchBase):

    def __init__(self, *args, **kwargs):
        self.config = kwargs.get('config')
        self.es_context = self.config.elasticsearch.elasticsearch_class(
            self.config.elasticsearch
        )

        super(SuperSearch, self).__init__(*args, **kwargs)

    def get_connection(self):
        with self.es_context() as conn:
            return conn

    def get_list_of_indices(self, from_date, to_date, es_index=None):
        """Return the list of indices to query to access all the crash reports
        that were processed between from_date and to_date.

        The naming pattern for indices in elasticsearch is configurable, it is
        possible to have an index per day, per week, per month...

        Parameters:
        * from_date datetime object
        * to_date datetime object
        """
        if es_index is None:
            es_index = self.config.elasticsearch.elasticsearch_index

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

        return self.get_list_of_indices(start_date, end_date)

    def format_field_names(self, hit):
        """Return a hit with each field's database name replaced by its
        exposed name. """
        new_hit = {}
        for field_name in self.request_columns:
            field = self.all_fields[field_name]
            database_field_name = '{}.{}'.format(
                field['namespace'],
                field['in_database_name'],
            )
            new_hit[field_name] = hit.get(database_field_name)

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

    def get_field_name(self, value, full=True):
        try:
            field_ = self.all_fields[value]
        except KeyError:
            raise BadArgumentError(
                value,
                msg='Unknown field "%s"' % value
            )

        if not field_['is_returned']:
            # Returning this field is not allowed.
            raise BadArgumentError(
                value,
                msg='Field "%s" is not allowed to be returned' % value
            )

        field_name = '%s.%s' % (
            field_['namespace'],
            field_['in_database_name']
        )

        if full and field_['has_full_version']:
            # If the param has a full version, that means what matters
            # is the full string, and not its individual terms.
            field_name += '.full'

        return field_name

    def format_aggregations(self, aggregations):
        """Return aggregations in a form that looks like facets.

        We used to expose the Elasticsearch facets directly. This is thus
        needed for backwards compatibility.
        """
        aggs = aggregations.to_dict()

        def _format(aggregation):
            if 'buckets' not in aggregation:
                # This is a cardinality aggregation, there are no terms.
                return aggregation

            for i, bucket in enumerate(aggregation['buckets']):
                new_bucket = {
                    'term': bucket.get('key_as_string', bucket['key']),
                    'count': bucket['doc_count'],
                }
                facets = {}

                for key in bucket:
                    # Go through all sub aggregations. Those are contained in
                    # all the keys that are not 'key' or 'count'.
                    if key in ('key', 'key_as_string', 'doc_count'):
                        continue

                    facets[key] = _format(bucket[key])

                if facets:
                    new_bucket['facets'] = facets

                aggregation['buckets'][i] = new_bucket

            return aggregation['buckets']

        for agg in aggs:
            aggs[agg] = _format(aggs[agg])

        return aggs

    def get(self, **kwargs):
        """Return a list of results and aggregations based on parameters.

        The list of accepted parameters (with types and default values) is in
        the database and can be accessed with the super_search_fields service.
        """
        # Require that the list of fields be passed.
        if not kwargs.get('_fields'):
            raise MissingArgumentError('_fields')
        self.all_fields = kwargs['_fields']

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
        filters = []
        histogram_intervals = {}

        for field, sub_params in params.items():
            sub_filters = None
            for param in sub_params:
                if param.name.startswith('_'):
                    # By default, all param values are turned into lists,
                    # even when they have and can have only one value.
                    # For those we know there can only be one value,
                    # so we just extract it from the made-up list.
                    if param.name == '_results_offset':
                        results_from = param.value[0]
                    elif param.name == '_results_number':
                        results_number = param.value[0]
                        if results_number > 1000:
                            raise BadArgumentError(
                                '_results_number',
                                msg=(
                                    '_results_number cannot be greater '
                                    'than 1,000'
                                )
                            )
                        if results_number < 0:
                            raise BadArgumentError(
                                '_results_number',
                                msg='_results_number cannot be negative'
                            )
                    elif param.name == '_facets_size':
                        facets_size = param.value[0]

                    for f in self.histogram_fields:
                        if param.name == '_histogram_interval.%s' % f:
                            histogram_intervals[f] = param.value[0]

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

                # Operators needing wildcards, and the associated value
                # transformation with said wildcards.
                operator_wildcards = {
                    '~': '*%s*',  # contains
                    '^': '%s*',  # starts with
                    '$': '*%s'  # ends with
                }
                # Operators needing ranges, and the associated Elasticsearch
                # comparison operator.
                operator_range = {
                    '>': 'gt',
                    '<': 'lt',
                    '>=': 'gte',
                    '<=': 'lte',
                }

                args = {}
                filter_type = 'term'
                filter_value = None

                if not param.operator:
                    # contains one of the terms
                    if len(param.value) == 1:
                        val = param.value[0]

                        if not isinstance(val, basestring) or ' ' not in val:
                            # There's only one term and no white space, this
                            # is a simple term filter.
                            filter_value = val
                        else:
                            # If the term contains white spaces, we want to
                            # perform a phrase query.
                            filter_type = 'query'
                            args = Q(
                                'simple_query_string',
                                query=param.value[0],
                                fields=[name],
                                default_operator='and',
                            ).to_dict()
                    else:
                        # There are several terms, this is a terms filter.
                        filter_type = 'terms'
                        filter_value = param.value
                elif param.operator == '=':
                    # is exactly
                    if field_data['has_full_version']:
                        name = '%s.full' % name
                    filter_value = param.value
                elif param.operator in operator_range:
                    filter_type = 'range'
                    filter_value = {
                        operator_range[param.operator]: param.value
                    }
                elif param.operator == '__null__':
                    filter_type = 'missing'
                    args['field'] = name
                elif param.operator == '__true__':
                    filter_type = 'term'
                    filter_value = True
                elif param.operator == '@':
                    filter_type = 'regexp'
                    if field_data['has_full_version']:
                        name = '%s.full' % name
                    filter_value = param.value
                elif param.operator in operator_wildcards:
                    filter_type = 'query'

                    # Wildcard operations are better applied to a non-analyzed
                    # field (called "full") if there is one.
                    if field_data['has_full_version']:
                        name = '%s.full' % name

                    q_args = {}
                    q_args[name] = (
                        operator_wildcards[param.operator] % param.value
                    )
                    query = Q('wildcard', **q_args)
                    args = query.to_dict()

                if filter_value is not None:
                    args[name] = filter_value

                if args:
                    new_filter = F(filter_type, **args)
                    if param.operator_not:
                        new_filter = ~new_filter

                    if sub_filters is None:
                        sub_filters = new_filter
                    elif filter_type == 'range':
                        sub_filters &= new_filter
                    else:
                        sub_filters |= new_filter

                    continue

            if sub_filters is not None:
                filters.append(sub_filters)

        search = search.filter(F('bool', must=filters))

        # Restricting returned fields.
        fields = []

        # We keep track of the requested columns in order to make sure we
        # return those column names and not aliases for example.
        self.request_columns = []
        for param in params['_columns']:
            for value in param.value:
                if not value:
                    continue

                self.request_columns.append(value)
                field_name = self.get_field_name(value, full=False)
                fields.append(field_name)

        search = search.fields(fields)

        # Sorting.
        sort_fields = []
        for param in params['_sort']:
            for value in param.value:
                if not value:
                    continue

                # Values starting with a '-' are sorted in descending order.
                # In order to retrieve the database name of the field, we
                # must first remove the '-' part and add it back later.
                # Example: given ['product', '-version'], the results will be
                # sorted by ascending product then descending version.
                desc = False
                if value.startswith('-'):
                    desc = True
                    value = value[1:]

                field_name = self.get_field_name(value)

                if desc:
                    # The underlying library understands that '-' means
                    # sorting in descending order.
                    field_name = '-' + field_name

                sort_fields.append(field_name)

        search = search.sort(*sort_fields)

        # Pagination.
        results_to = results_from + results_number
        search = search[results_from:results_to]

        # Create facets.
        if facets_size:
            self._create_aggregations(
                params,
                search,
                facets_size,
                histogram_intervals
            )

        # Query and compute results.
        hits = []

        if params['_return_query'][0].value[0]:
            # Return only the JSON query that would be sent to elasticsearch.
            return {
                'query': search.to_dict(),
                'indices': indices,
            }

        errors = []

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

                aggregations = getattr(results, 'aggregations', {})
                if aggregations:
                    aggregations = self.format_aggregations(aggregations)

                shards = getattr(results, '_shards', {})

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

                errors.append({
                    'type': 'missing_index',
                    'index': missing_index,
                })

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
                    shards = None
                    break

        if shards and shards.failed:
            # Some shards failed. We want to explain what happened in the
            # results, so the client can decide what to do.
            failed_indices = defaultdict(int)
            for failure in shards.failures:
                failed_indices[failure.index] += 1

            for index, shards_count in failed_indices.items():
                errors.append({
                    'type': 'shards',
                    'index': index,
                    'shards_count': shards_count,
                })

        return {
            'hits': hits,
            'total': total,
            'facets': aggregations,
            'errors': errors,
        }

    def _create_aggregations(
        self, params, search, facets_size, histogram_intervals
    ):
        # Create facets.
        for param in params['_facets']:
            self._add_second_level_aggs(
                param,
                search.aggs,
                facets_size,
                histogram_intervals,
            )

        # Create sub-aggregations.
        for key in params:
            if not key.startswith('_aggs.'):
                continue

            fields = key.split('.')[1:]

            if fields[0] not in self.all_fields:
                continue

            base_bucket = self._get_fields_agg(fields[0], facets_size)
            sub_bucket = base_bucket

            for field in fields[1:]:
                # For each field, make a bucket, then include that bucket in
                # the latest one, and then make that new bucket the latest.
                if field in self.all_fields:
                    tmp_bucket = self._get_fields_agg(field, facets_size)
                    sub_bucket.bucket(field, tmp_bucket)
                    sub_bucket = tmp_bucket

            for value in params[key]:
                self._add_second_level_aggs(
                    value,
                    sub_bucket,
                    facets_size,
                    histogram_intervals,
                )

            search.aggs.bucket(fields[0], base_bucket)

        # Create histograms.
        for f in self.histogram_fields:
            key = '_histogram.%s' % f
            if params.get(key):
                histogram_bucket = self._get_histogram_agg(
                    f, histogram_intervals
                )

                for param in params[key]:
                    self._add_second_level_aggs(
                        param,
                        histogram_bucket,
                        facets_size,
                        histogram_intervals,
                    )

                search.aggs.bucket('histogram_%s' % f, histogram_bucket)

    def _get_histogram_agg(self, field, intervals):
        histogram_type = (
            self.all_fields[field]['query_type'] == 'date' and
            'date_histogram' or 'histogram'
        )
        return A(
            histogram_type,
            field=self.get_field_name(field),
            interval=intervals[field],
        )

    def _get_cardinality_agg(self, field):
        return A(
            'cardinality',
            field=self.get_field_name(field),
        )

    def _get_fields_agg(self, field, facets_size):
        return A(
            'terms',
            field=self.get_field_name(field),
            size=facets_size,
        )

    def _add_second_level_aggs(
        self, param, recipient, facets_size, histogram_intervals
    ):
        for field in param.value:
            if not field:
                continue

            if field.startswith('_histogram'):
                field_name = field[len('_histogram.'):]
                if field_name not in self.histogram_fields:
                    continue

                bucket_name = 'histogram_%s' % field_name
                bucket = self._get_histogram_agg(
                    field_name, histogram_intervals
                )

            elif field.startswith('_cardinality'):
                field_name = field[len('_cardinality.'):]

                bucket_name = 'cardinality_%s' % field_name
                bucket = self._get_cardinality_agg(field_name)

            else:
                bucket_name = field
                bucket = self._get_fields_agg(field, facets_size)

            recipient.bucket(
                bucket_name,
                bucket
            )
