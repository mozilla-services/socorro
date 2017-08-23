# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import os
import datetime
import elasticsearch

from pkg_resources import resource_stream

from socorro.lib import BadArgumentError, datetimeutil
from socorro.external.es.base import ElasticsearchBase


SUPER_SEARCH_FIELDS_JSON_PATH = os.path.join(
    'data',
    'super_search_fields.json'
)


class SuperSearchFields(ElasticsearchBase):

    # Defining some filters that need to be considered as lists.
    filters = [
        ('form_field_choices', None, ['list', 'str']),
        ('permissions_needed', None, ['list', 'str']),
    ]

    def get_fields(self):
        """Return all the fields from our super_search_fields.json file."""
        with resource_stream(__name__, SUPER_SEARCH_FIELDS_JSON_PATH) as f:
            return json.load(f)

    # The reason for this alias is because this class gets used from
    # the webapp and it expects to be able to execute
    # SuperSearchFields.get() but there's a subclass of this class
    # called SuperSearchMissingFields which depends on calling
    # self.get_fields(). That class has its own `get` method.
    # If you don't refer to `get_fields` with `get_fields` you'd get
    # an infinite recursion loop.

    get = get_fields

    def get_missing_fields(self):
        """Return a list of all missing fields in our .json file.

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
            except elasticsearch.exceptions.NotFoundError as e:
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
