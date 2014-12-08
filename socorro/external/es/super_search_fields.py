# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


class SuperSearchFields(object):

    def __init__(self, *args, **kwargs):
        # super(SuperSearchFields, self).__init__(*args, **kwargs)

        self.config = kwargs.get('config')
        self.es_context = self.config.elasticsearch.elasticsearch_class(
            self.config.elasticsearch
        )

    def get_connection(self):
        with self.es_context() as conn:
            return conn

    def get_fields(self):
        """ Return all the fields from our database, as a dict where field
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
                self.config.elasticsearch.elasticsearch_doctype: {
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
