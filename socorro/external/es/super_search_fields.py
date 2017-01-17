# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import elasticsearch

from socorro.lib import (
    BadArgumentError,
    MissingArgumentError,
    ResourceNotFound,
)
from socorro.external.es.base import ElasticsearchBase
from socorro.lib import datetimeutil, external_common


class SuperSearchFields(ElasticsearchBase):

    # Defining some filters that need to be considered as lists.
    filters = [
        ('form_field_choices', None, ['list', 'str']),
        ('permissions_needed', None, ['list', 'str']),
    ]

    def get_fields(self):
        """Return all the fields from our database, as a dict where field
        names are the keys.

        No parameters are accepted.
        """
        es_connection = self.get_connection()

        total = es_connection.count(
            index=self.config.elasticsearch.elasticsearch_default_index,
            doc_type='supersearch_fields',
        )['count']
        results = es_connection.search(
            index=self.config.elasticsearch.elasticsearch_default_index,
            doc_type='supersearch_fields',
            size=total,
        )

        return dict(
            (r['_source']['name'], r['_source'])
            for r in results['hits']['hits']
        )

    # The reason for this alias is because this class gets used from
    # the webapp and it expects to be able to execute
    # SuperSearchFields.get() but there's a subclass of this class
    # called SuperSearchMissingFields which depends on calling
    # self.get_fields(). That class has its own `get` method.
    # If you don't refer to `get_fields` with `get_fields` you'd get
    # an infinite recursion loop.

    get = get_fields

    def create_field(self, **kwargs):
        """Create a new field in the database, to be used by supersearch and
        all Elasticsearch related services.
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

        es_connection = self.get_connection()

        try:
            es_connection.index(
                index=self.config.elasticsearch.elasticsearch_default_index,
                doc_type='supersearch_fields',
                body=params,
                id=params['name'],
                op_type='create',
                refresh=True,
            )
        except elasticsearch.exceptions.ConflictError:
            # This field exists in the database, it thus cannot be created!
            raise BadArgumentError(
                'name',
                msg='The field "%s" already exists in the database, '
                    'impossible to create it. ' % params['name'],
            )

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

        es_connection = self.get_connection()
        es_index = self.config.elasticsearch.elasticsearch_default_index
        es_doc_type = 'supersearch_fields'

        # First verify that the field does exist.
        try:
            old_value = es_connection.get(
                index=es_index,
                doc_type=es_doc_type,
                id=params['name'],
            )['_source']  # Only the actual document is of interest.
        except elasticsearch.exceptions.NotFoundError:
            # This field does not exist yet, it thus cannot be updated!
            raise ResourceNotFound(
                'The field "%s" does not exist in the database, it needs to '
                'be created before it can be updated. ' % params['name']
            )

        # Then, if necessary, verify the new mapping.
        if (
            (
                'storage_mapping' in params and
                params['storage_mapping'] != old_value['storage_mapping']
            ) or (
                'in_database_name' in params and
                params['in_database_name'] != old_value['in_database_name']
            )
        ):
            # This is a change that will have an impact on the Elasticsearch
            # mapping, we first need to make sure it doesn't break.
            new_mapping = self.get_mapping(overwrite_mapping=params)

            # Try the mapping. If there is an error, an exception will be
            # raised. If an exception is raised, the new mapping will be
            # rejected.
            self.test_mapping(new_mapping)

        if (
            'storage_mapping' in params and
            params['storage_mapping'] != old_value['storage_mapping']
        ):
            # The storage mapping is an object, and thus is treated
            # differently than other fields by Elasticsearch. If a user
            # changes the object by removing a field from it, that field won't
            # be removed as part of the update (which performs a merge of all
            # objects in the back-end). We therefore want to perform the merge
            # ourselves, and remove the field from the database before
            # re-indexing it.
            new_doc = old_value.copy()
            new_doc.update(params)

            es_connection.delete(
                index=es_index,
                doc_type=es_doc_type,
                id=new_doc['name'],
            )
            es_connection.index(
                index=es_index,
                doc_type=es_doc_type,
                body=new_doc,
                id=new_doc['name'],
                op_type='create',
                refresh=True,
            )

            # If we made a change to the storage_mapping, log that change.
            self.config.logger.info(
                'Elasticsearch mapping changed for field "%s", '
                'was "%s", now "%s"',
                params['name'],
                old_value['storage_mapping'],
                new_doc['storage_mapping'],
            )
        else:
            # Then update the new field in the database. Note that
            # Elasticsearch takes care of merging the new document into the
            # old one, so missing values won't be changed.
            es_connection.update(
                index=es_index,
                doc_type=es_doc_type,
                body={'doc': params},
                id=params['name'],
                refresh=True,
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

        es_connection = self.get_connection()
        es_connection.delete(
            index=self.config.elasticsearch.elasticsearch_default_index,
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

        es_connection = self.get_connection()
        index_client = elasticsearch.client.IndicesClient(es_connection)
        doctype = self.config.elasticsearch.elasticsearch_doctype

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
                mapping = index_client.get_mapping(
                    index=index,
                )
                properties = mapping[index]['mappings'][doctype]['properties']
                all_existing_fields.update(parse_mapping(properties, None))
            except elasticsearch.exceptions.NotFoundError, e:
                # If an index does not exist, this should not fail
                self.config.logger.warning(
                    'Missing index in elasticsearch while running '
                    'SuperSearchFields.get_missing_fields, error is: %s',
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
            if not namespaces or not namespaces[0]:
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
            self.config.elasticsearch.elasticsearch_doctype: {
                '_all': {
                    'enabled': False,
                },
                'properties': properties,
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

        es_connection = self.get_connection()

        index_creator = self.config.index_creator_class(
            self.config
        )
        try:
            index_creator.create_index(
                temp_index,
                index_creator.get_socorro_index_settings(mapping),
            )

            now = datetimeutil.utc_now()
            last_week = now - datetime.timedelta(days=7)
            current_indices = self.generate_list_of_indexes(last_week, now)

            crashes_sample = es_connection.search(
                index=current_indices,
                doc_type=self.config.elasticsearch.elasticsearch_doctype,
                size=self.config.elasticsearch.mapping_test_crash_number,
            )
            crashes = [x['_source'] for x in crashes_sample['hits']['hits']]

            for crash in crashes:
                es_connection.index(
                    index=temp_index,
                    doc_type=self.config.elasticsearch.elasticsearch_doctype,
                    body=crash,
                )
        except elasticsearch.exceptions.ElasticsearchException as e:
            raise BadArgumentError(
                'storage_mapping',
                msg='Indexing existing data in Elasticsearch failed with the '
                    'new mapping. Error is: %s' % str(e),
            )
        finally:
            try:
                index_creator.get_index_client().delete(temp_index)
            except elasticsearch.exceptions.NotFoundError:
                # If the index does not exist (if the index creation failed
                # for example), we don't need to do anything.
                pass


class SuperSearchMissingFields(SuperSearchFields):

    def get(self):
        # This is the whole reason for making this subclass.
        # This way we can get a dedicated class with a single get method
        # so that it becomes easier to use the big class for multiple
        # API purposes.
        return super(SuperSearchMissingFields, self).get_missing_fields()
