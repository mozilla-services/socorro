# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import re

from elasticutils import F, S
from pyelasticsearch.exceptions import (
    ElasticHttpError,
    ElasticHttpNotFoundError,
)

from socorro.external import (
    BadArgumentError,
    InsertionError,
    MissingArgumentError,
    ResourceNotFound,
)
from socorro.external.elasticsearch.base import ElasticSearchBase
from socorro.lib import datetimeutil, external_common
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

    # Defining some filters for the field service that need to be considered
    # as lists.
    filters = [
        ('form_field_choices', None, ['list', 'str']),
        ('permissions_needed', None, ['list', 'str']),
    ]

    def __init__(self, *args, **kwargs):
        config = kwargs.get('config')
        ElasticSearchBase.__init__(self, config=config)

        self.all_fields = self.get_fields()

        self.database_name_to_field_name_map = dict(
            (x['in_database_name'], x['name'])
            for x in self.all_fields.values()
        )

        # We have multiple inheritance here, explicitly calling superclasses's
        # init is mandatory.
        # See http://freshfoo.com/blog/object__init__takes_no_parameters
        SearchBase.__init__(self, config=config, fields=self.all_fields)

    def get_connection(self):
        return SuperS().es(
            urls=self.config.elasticsearch_urls,
            timeout=self.config.elasticsearch_timeout,
        )

    def get(self, **kwargs):
        """Return a list of results and facets based on parameters.

        The list of accepted parameters (with types and default values) is in
        the database and can be accessed with the supersearch_fields service.
        """
        # Filter parameters and raise potential errors.
        params = self.get_parameters(**kwargs)

        # Find the indexes to use to optimize the elasticsearch query.
        indexes = self.get_indexes(params['date'])

        # Create and configure the search object.
        search = self.get_connection()
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
                new_field = new_field.split('.')[-1]

            new_field = self.database_name_to_field_name_map.get(
                new_field, new_field
            )

            new_hit[new_field] = hit[field]

        return new_hit

    def get_fields(self):
        """ Return all the fields from our database, as a dict where field
        names are the keys.

        No parameters are accepted.
        """
        # Create and configure the search object.
        search = self.get_connection()
        search = search.indexes(
            self.config.elasticsearch_default_index
        )
        search = search.doctypes('supersearch_fields')

        count = search.count()  # Total number of results.
        search = search[:count]

        # Get all fields from the database.
        return dict((r['name'], r) for r in search.values_dict())

    def create_field(self, **kwargs):
        """Create a new field in the database, to be used by supersearch and
        all elasticsearch related services.
        """
        filters = [
            ('name', None, 'str'),
            ('data_validation_type', 'enum', 'str'),
            ('default_value', None, 'str'),
            ('description', None, 'str'),
            ('form_field_choices', None, ['list', 'str']),
            ('has_full_version', False, 'bool'),
            ('in_database_name', None, 'str'),
            ('is_exposed', False, 'bool'),
            ('is_returned', False, 'bool'),
            ('is_mandatory', False, 'bool'),
            ('query_type', 'enum', 'str'),
            ('namespace', None, 'str'),
            ('permissions_needed', None, ['list', 'str']),
            ('storage_mapping', None, 'json'),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        mandatory_params = ('name', 'in_database_name')
        for param in mandatory_params:
            if not params[param]:
                raise MissingArgumentError(param)

        # Before making the change, make sure it does not break indexing.
        new_mapping = self.get_mapping(overwrite_mapping=params)

        # Try the mapping. If there is an error, an exception will be raised.
        # If an exception is raised, the new mapping will be rejected.
        self.test_mapping(new_mapping)

        es_connection = self.get_connection().get_es()

        try:
            es_connection.index(
                index=self.config.elasticsearch_default_index,
                doc_type='supersearch_fields',
                doc=params,
                id=params['name'],
                overwrite_existing=False,
                refresh=True,
            )
        except ElasticHttpError, e:
            if e.status_code == 409:
                # This field exists in the database, it thus cannot be created!
                raise InsertionError(
                    'The field "%s" already exists in the database, '
                    'impossible to create it. ' % params['name']
                )

            # Else this is an unexpected error and we want to know about it.
            raise

        if params.get('storage_mapping'):
            # If we made a change to the storage_mapping, log that change.
            self.config.logger.info(
                'elasticsearch mapping changed for field "%s", '
                'added new mapping "%s"',
                params['name'],
                params['storage_mapping'],
            )

        return True

    def update_field(self, **kwargs):
        """Update an existing field in the database.

        If the field does not exist yet, a ResourceNotFound error is raised.

        If you want to update only some keys, just do not pass the ones you
        don't want to change.
        """
        filters = [
            ('name', None, 'str'),
            ('data_validation_type', None, 'str'),
            ('default_value', None, 'str'),
            ('description', None, 'str'),
            ('form_field_choices', None, ['list', 'str']),
            ('has_full_version', None, 'bool'),
            ('in_database_name', None, 'str'),
            ('is_exposed', None, 'bool'),
            ('is_returned', None, 'bool'),
            ('is_mandatory', None, 'bool'),
            ('query_type', None, 'str'),
            ('namespace', None, 'str'),
            ('permissions_needed', None, ['list', 'str']),
            ('storage_mapping', None, 'json'),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        if not params['name']:
            raise MissingArgumentError('name')

        # Remove all the parameters that were not explicitely passed.
        for key in params.keys():
            if key not in kwargs:
                del params[key]

        # Before making the change, make sure it does not break indexing.
        new_mapping = self.get_mapping(overwrite_mapping=params)

        # Try the mapping. If there is an error, an exception will be raised.
        # If an exception is raised, the new mapping will be rejected.
        self.test_mapping(new_mapping)

        es_connection = self.get_connection().get_es()

        # First verify that the field does exist.
        try:
            old_value = es_connection.get(
                index=self.config.elasticsearch_default_index,
                doc_type='supersearch_fields',
                id=params['name'],
            )['_source']  # Only the actual document is of interest.
        except ElasticHttpNotFoundError:
            # This field does not exist yet, it thus cannot be updated!
            raise ResourceNotFound(
                'The field "%s" does not exist in the database, it needs to '
                'be created before it can be updated. ' % params['name']
            )

        if 'storage_mapping' in params and old_value['storage_mapping']:
            # The storage mapping is an object, and thus is treated
            # differently than other fields by Elasticsearch. If a user
            # changes the object by removing a field from it, that field won't
            # be removed as part of the update (which performs a merge of all
            # objects in the back-end). We therefore want to remove that field
            # before we do the merge, so that it is entirely overwritten.
            es_connection.update(
                index=self.config.elasticsearch_default_index,
                doc_type='supersearch_fields',
                script='ctx._source.remove("storage_mapping")',
                id=params['name'],
                refresh=True,
            )

        # Then update the new field in the database. Note that pyelasticsearch
        # takes care of merging the new document into the old one, so missing
        # values won't be changed.
        es_connection.update(
            index=self.config.elasticsearch_default_index,
            doc_type='supersearch_fields',
            doc=params,
            id=params['name'],
            refresh=True,
        )

        if 'storage_mapping' in params:
            # If we made a change to the storage_mapping, log that change.
            self.config.logger.info(
                'elasticsearch mapping changed for field "%s", '
                'was "%s", now "%s"',
                params['name'],
                old_value['storage_mapping'],
                params['storage_mapping'],
            )

        return True

    def delete_field(self, **kwargs):
        """Remove a field from the database.

        Removing a field means that it won't be indexed in elasticsearch
        anymore, nor will it be exposed or accessible via supersearch. It
        doesn't delete the data from crash reports though, so it would be
        possible to re-create the field and reindex some indices to get that
        data back.
        """
        filters = [
            ('name', None, 'str'),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        if not params['name']:
            raise MissingArgumentError('name')

        es_connection = self.get_connection().get_es()
        es_connection.delete(
            index=self.config.elasticsearch_default_index,
            doc_type='supersearch_fields',
            id=params['name'],
            refresh=True,
        )

    def get_missing_fields(self):
        """Return a list of all missing fields in our database.

        Take the list of all fields that were indexed in the last 3 weeks
        and do a diff with the list of known fields.
        """
        now = datetimeutil.utc_now()
        two_weeks_ago = now - datetime.timedelta(weeks=2)
        indices = self.generate_list_of_indexes(two_weeks_ago, now)

        es_connection = self.get_connection().get_es()
        doctype = self.config.elasticsearch_doctype

        def parse_mapping(mapping, namespace):
            """Return a set of all fields in a mapping. Parse the mapping
            recursively. """
            fields = set()

            for key in mapping:
                field = mapping[key]
                if namespace:
                    field_full_name = '.'.join((namespace, key))
                else:
                    field_full_name = key

                if 'properties' in field:
                    fields.update(
                        parse_mapping(
                            field['properties'],
                            field_full_name
                        )
                    )
                else:
                    fields.add(field_full_name)

            return fields

        all_existing_fields = set()
        for index in indices:
            try:
                mapping = es_connection.get_mapping(
                    index=index,
                    doc_type=doctype,
                )
                properties = mapping[doctype]['properties']
                all_existing_fields.update(parse_mapping(properties, None))
            except ElasticHttpNotFoundError, e:
                # If an index does not exist, this should not fail
                self.config.logger.warning(
                    'Missing index in elasticsearch while running '
                    'SuperSearch.get_missing_fields, error is: %s',
                    str(e)
                )

        all_known_fields = set(
            '.'.join((x['namespace'], x['in_database_name']))
            for x in self.get_fields().values()
        )

        missing_fields = sorted(all_existing_fields - all_known_fields)

        return {
            'hits': missing_fields,
            'total': len(missing_fields),
        }

    def get_mapping(self, overwrite_mapping=None):
        """Return the mapping to be used in elasticsearch, generated from the
        current list of fields in the database.
        """
        properties = {}
        all_fields = self.get_fields()

        if overwrite_mapping:
            field = overwrite_mapping['name']
            if field in all_fields:
                all_fields[field].update(overwrite_mapping)
            else:
                all_fields[field] = overwrite_mapping

        def add_field_to_properties(properties, namespaces, field):
            if not namespaces:
                properties[field['in_database_name']] = (
                    field['storage_mapping']
                )
                return

            namespace = namespaces.pop(0)

            if namespace not in properties:
                properties[namespace] = {
                    'type': 'object',
                    'dynamic': 'true',
                    'properties': {}
                }

            add_field_to_properties(
                properties[namespace]['properties'],
                namespaces,
                field,
            )

        for field in all_fields.values():
            if not field.get('storage_mapping'):
                continue

            namespaces = field['namespace'].split('.')

            add_field_to_properties(properties, namespaces, field)

        return {
            'index': {
                'query': {
                    'default_field': 'signature'
                }
            },
            'mappings': {
                self.config.elasticsearch_doctype: {
                    '_all': {
                        'enabled': False
                    },
                    '_source': {
                        'compress': True
                    },
                    'properties': properties
                }
            }
        }

    def test_mapping(self, mapping):
        """Verify that a mapping is correct.

        This function does so by first creating a new, temporary index in
        elasticsearch using the mapping. It then takes some recent crash
        reports that are in elasticsearch and tries to insert them in the
        temporary index. Any failure in any of those steps will raise an
        exception. If any is raised, that means the mapping is incorrect in
        some way (either it doesn't validate against elasticsearch's rules,
        or is not compatible with the data we currently store).

        If no exception is raised, the mapping is likely correct.

        This function is to be used in any place that can change the
        `storage_mapping` field in any Super Search Field.
        Methods `create_field` and `update_field` use it, see above.
        """
        temp_index = 'socorro_mapping_test'

        es_connection = self.get_connection().get_es()

        try:
            es_connection.create_index(
                temp_index,
                settings=mapping,
            )

            now = datetimeutil.utc_now()
            last_week = now - datetime.timedelta(days=7)
            current_indices = self.generate_list_of_indexes(last_week, now)

            crashes_sample = es_connection.search(
                query='*',
                index=current_indices,
                doc_type=self.config.elasticsearch_doctype,
                size=self.config.webapi.mapping_test_crash_number,
            )
            crashes = [x['_source'] for x in crashes_sample['hits']['hits']]

            for crash in crashes:
                es_connection.index(
                    index=temp_index,
                    doc_type=self.config.elasticsearch_doctype,
                    doc=crash,
                )

        finally:
            try:
                es_connection.delete_index(temp_index)
            except ElasticHttpNotFoundError:
                # If the index does not exist (if the index creation failed
                # for example), we don't need to do anything.
                pass
