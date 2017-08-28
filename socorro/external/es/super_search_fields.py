# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import json
import os

import elasticsearch

from socorro.external.es.base import ElasticsearchBase
from socorro.lib import datetimeutil, BadArgumentError


class SuperSearchFields(ElasticsearchBase):

    # Defining some filters that need to be considered as lists.
    filters = [
        ('form_field_choices', None, ['list', 'str']),
        ('permissions_needed', None, ['list', 'str']),
    ]

    def get_fields(self):
        """Return all the fields from our super_search_fields.json file."""
        return FIELDS

    # The reason for this alias is because this class gets used from
    # the webapp and it expects to be able to execute
    # SuperSearchFields.get() but there's a subclass of this class
    # called SuperSearchMissingFields which depends on calling
    # self.get_fields(). That class has its own `get` method.
    # If you don't refer to `get_fields` with `get_fields` you'd get
    # an infinite recursion loop.

    get = get_fields

    def get_missing_fields(self):
        """Return a list of all missing fields in our JSON file.

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
                '_source': {
                    'compress': True,
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


# Tree of super search fields
FIELDS = {
    'ActiveExperiment': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'The telemetry experiment active at the time of the crash, if any.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'ActiveExperiment',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'ActiveExperiment',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'ActiveExperimentBranch': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'The experiment branch of the ActiveExperiment, if set.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'ActiveExperimentBranch',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'ActiveExperimentBranch',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'AdapterRendererIDs': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'AdapterRendererIDs',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'AdapterRendererIDs',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'Add-ons': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'Add-ons',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'Add-ons',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'BuildID': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'BuildID',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'BuildID',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'Comments': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'Comments',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'Comments',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'CrashTime': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'CrashTime',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'CrashTime',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'FlashVersion': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'FlashVersion',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'FlashVersion',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'Hang': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'Hang',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'Hang',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'boolean'
        }
    },
    'InstallTime': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'InstallTime',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'InstallTime',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'Notes': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'Notes',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'Notes',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'PluginFilename': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'PluginFilename',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'PluginFilename',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'PluginName': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'PluginName',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'PluginName',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'PluginUserComment': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'PluginUserComment',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'PluginUserComment',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'PluginVersion': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'PluginVersion',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'PluginVersion',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'ProcessType': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'ProcessType',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'ProcessType',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'ProductID': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'ProductID',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'ProductID',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'ProductName': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'ProductName',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'ProductName',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'ReleaseChannel': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'ReleaseChannel',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'ReleaseChannel',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'SecondsSinceLastCrash': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'SecondsSinceLastCrash',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'SecondsSinceLastCrash',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'TextureUsage': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'TextureUsage',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'TextureUsage',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'Version': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'Version',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'Version',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'Winsock_LSP': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'Winsock_LSP',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'Winsock_LSP',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'abort_message': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'The abort message.',
        'form_field_choices': [],
        'has_full_version': True,
        'in_database_name': 'AbortMessage',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'abort_message',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'index': 'analyzed',
            'type': 'string'
        }
    },
    'accessibility': {
        'data_validation_type': 'bool',
        'default_value': None,
        'description': (
            'The presence of this field indicates that accessibility services were accessed.'
        ),
        'form_field_choices': [],
        'form_field_type': 'BooleanField',
        'has_full_version': False,
        'in_database_name': 'Accessibility',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'accessibility',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'bool',
        'storage_mapping': {
            'type': 'boolean'
        }
    },
    'accessibility_client': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'Out-of-process accessibility client program name and version information.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'AccessibilityClient',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'accessibility_client',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'accessibility_in_proc_client': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': (
            'In-process accessibility client detection information. See Compatibility.h for more '
            'details.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'AccessibilityInProcClient',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'accessibility_in_proc_client',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'adapter_device_id': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'The graphics adapter device identifier.',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'AdapterDeviceID',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'adapter_device_id',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'adapter_driver_version': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'The graphics adapter driver version.',
        'form_field_choices': [],
        'form_field_type': 'StringField',
        'has_full_version': False,
        'in_database_name': 'AdapterDriverVersion',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'adapter_driver_version',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': None
    },
    'adapter_subsys_id': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'The graphics adapter subsystem identifier.',
        'form_field_choices': [],
        'form_field_type': 'StringField',
        'has_full_version': False,
        'in_database_name': 'AdapterSubsysID',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'adapter_subsys_id',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': None
    },
    'adapter_vendor_id': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': (
            'The graphics adapter vendor. This value is sometimes a name, and sometimes a '
            'hexidecimal identifier. Common identifiers include: 0x8086 (Intel), 0x1002 (AMD), '
            '0x10de (NVIDIA).'
        ),
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'AdapterVendorID',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'adapter_vendor_id',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'additional_minidumps': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'additional_minidumps',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'additional_minidumps',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'addons': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': (
            'A list of the addons currently enabled at the time of the crash. This takes the form '
            'of "addonid:version,[addonid:version...]". This value could be empty if the crash '
            'happens during startup before the addon manager is enabled, and on products/platforms '
            'which do not support addons.'
        ),
        'form_field_choices': [],
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'addons',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'addons',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'addons_checked': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'addons_checked',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'addons_checked',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'boolean'
        }
    },
    'addons_should_have_blocked_e10s': {
        'data_validation_type': 'bool',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'AddonsShouldHaveBlockedE10s',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'addons_should_have_blocked_e10s',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'bool',
        'storage_mapping': {
            'type': 'boolean'
        }
    },
    'address': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': (
            'The crashing address. This value is only meaningful for crashes involving bad memory '
            'accesses.'
        ),
        'form_field_choices': [],
        'form_field_type': 'StringField',
        'has_full_version': False,
        'in_database_name': 'address',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'address',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'android_board': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'The board used by the Android device.',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'Android_Board',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'android_board',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'android_brand': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'The Android device brand.',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'Android_Brand',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'android_brand',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'android_cpu_abi': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'The Android primary CPU ABI being used.',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'Android_CPU_ABI',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'android_cpu_abi',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'android_cpu_abi2': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'The Android secondary CPU ABI being used.',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'Android_CPU_ABI2',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'android_cpu_abi2',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'android_device': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'The android device name.',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'Android_Device',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'android_device',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'android_display': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'Android_Display',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'android_display',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'android_fingerprint': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'Android_Fingerprint',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'android_fingerprint',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'android_hardware': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'The android device hardware.',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'Android_Hardware',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'android_hardware',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'android_manufacturer': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'The Android device manufacturer.',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'Android_Manufacturer',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'android_manufacturer',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'android_model': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'The Android device model name.',
        'form_field_choices': [],
        'form_field_type': 'StringField',
        'has_full_version': True,
        'in_database_name': 'Android_Model',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'android_model',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'Android_Model': {
                    'type': 'string'
                },
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'type': 'multi_field'
        }
    },
    'android_version': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'The Android version.',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'Android_Version',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'android_version',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'app_init_dlls': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'DLLs injected through the AppInit_DLLs registry key.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'AppInitDLLs',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'app_init_dlls',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'analyzer': 'semicolon_keywords',
            'type': 'string'
        }
    },
    'app_notes': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': (
            'Notes from the application that crashed. Mostly contains graphics-related '
            'annotations.'
        ),
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': True,
        'in_database_name': 'app_notes',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'app_notes',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'index': 'analyzed',
            'type': 'string'
        }
    },
    'async_plugin_init': {
        'data_validation_type': 'bool',
        'default_value': None,
        'description': 'https://bugzilla.mozilla.org/show_bug.cgi?id=1155511',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'AsyncPluginInit',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'async_plugin_init',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'bool',
        'storage_mapping': {
            'null_value': 'False',
            'type': 'boolean'
        }
    },
    'async_plugin_shutdown': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'has_full_version': True,
        'in_database_name': 'AsyncPluginShutdown',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'async_plugin_shutdown',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'index': 'analyzed',
            'type': 'string'
        }
    },
    'async_plugin_shutdown_states': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'has_full_version': True,
        'in_database_name': 'AsyncPluginShutdownStates',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'async_plugin_shutdown_states',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'index': 'analyzed',
            'type': 'string'
        }
    },
    'async_shutdown_timeout': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'form_field_type': 'StringField',
        'has_full_version': True,
        'in_database_name': 'AsyncShutdownTimeout',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'async_shutdown_timeout',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'AsyncShutdownTimeout': {
                    'analyzer': 'standard',
                    'index': 'analyzed',
                    'type': 'string'
                },
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'type': 'multi_field'
        }
    },
    'available_page_file': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The maximum amount of memory the current process can commit. This value is equal '
            'to or smaller than the system-wide available commit value.'
        ),
        'form_field_choices': [],
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'AvailablePageFile',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'available_page_file',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'available_physical_memory': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The amount of physical memory currently available. This is the amount of physical '
            'memory that can be immediately reused without having to write its contents to disk '
            'first.'
        ),
        'form_field_choices': [],
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'AvailablePhysicalMemory',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'available_physical_memory',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'available_virtual_memory': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The amount of unreserved and uncommited (i.e. available) memory in the process\'s '
            'address space. Note that this memory may be fragmented into many separate segments, '
            'so an allocation attempt may fail even when this value is substantially greater than '
            'zero.'
        ),
        'form_field_choices': [],
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'AvailableVirtualMemory',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'available_virtual_memory',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'b2g_os_version': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'B2G_OS_Version',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'b2g_os_version',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'bios_manufacturer': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'The BIOS manufacturer.',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'BIOS_Manufacturer',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'bios_manufacturer',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'bug836263-size': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'bug836263-size',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'bug836263-size',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'build_date': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'build_date',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'build_date',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'format': 'yyyy-MM-dd\'T\'HH:mm:ssZZ||yyyy-MM-dd\'T\'HH:mm:ss.SSSSSSZZ',
            'type': 'date'
        }
    },
    'build_id': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The unique build identifier of this version, which is a timestamp of the form '
            'YYYYMMDDHHMMSS.'
        ),
        'form_field_choices': [],
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'build',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'build_id',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'buildid': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'buildid',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'buildid',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'classifications': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'classifications',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'classifications',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'dynamic': 'true',
            'properties': {
                'skunk_works': {
                    'dynamic': 'true',
                    'properties': {
                        'classification': {
                            'type': 'string'
                        },
                        'classification_data': {
                            'type': 'string'
                        },
                        'classification_version': {
                            'analyzer': 'keyword',
                            'type': 'string'
                        }
                    }
                },
                'support': {
                    'dynamic': 'true',
                    'properties': {
                        'classification': {
                            'type': 'string'
                        },
                        'classification_data': {
                            'type': 'string'
                        },
                        'classification_version': {
                            'analyzer': 'keyword',
                            'type': 'string'
                        }
                    }
                }
            },
            'type': 'object'
        }
    },
    'client_crash_date': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'client_crash_date',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'client_crash_date',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'format': 'yyyy-MM-dd\'T\'HH:mm:ssZZ||yyyy-MM-dd\'T\'HH:mm:ss.SSSSSSZZ',
            'type': 'date'
        }
    },
    'co_get_interface_and_release_stream_failure': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': (
            'Contains the hexadecimal value of the return code from Windows '
            'CoGetInterfaceAndReleaseStream API when invoked by IPDL serialization and '
            'deserialization code.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'CoGetInterfaceAndReleaseStreamFailure',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'co_get_interface_and_release_stream_failure',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'co_marshal_interface_failure': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': (
            'Contains the hexadecimal value of the return code from Windows '
            'CoMarshalInterfaceFailure API when invoked by IPDL serialization and '
            'deserialization code.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'CoMarshalInterfaceFailure',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'co_marshal_interface_failure',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'completeddatetime': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'completeddatetime',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'completeddatetime',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'format': 'yyyy-MM-dd\'T\'HH:mm:ssZZ||yyyy-MM-dd\'T\'HH:mm:ss.SSSSSSZZ',
            'type': 'date'
        }
    },
    'contains_memory_report': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'Has content for processed_crash.memory_report or not.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'ContainsMemoryReport',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'contains_memory_report',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'flag',
        'storage_mapping': {
            'type': 'short'
        }
    },
    'content_sandbox_capabilities': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'ContentSandboxCapabilities',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'content_sandbox_capabilities',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'integer'
        }
    },
    'content_sandbox_capable': {
        'data_validation_type': 'bool',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'ContentSandboxCapable',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'content_sandbox_capable',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'bool',
        'storage_mapping': {
            'null_value': False,
            'type': 'boolean'
        }
    },
    'content_sandbox_enabled': {
        'data_validation_type': 'bool',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'ContentSandboxEnabled',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'content_sandbox_enabled',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'bool',
        'storage_mapping': {
            'null_value': False,
            'type': 'boolean'
        }
    },
    'content_sandbox_level': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'ContentSandboxLevel',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'content_sandbox_level',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'short'
        }
    },
    'cpu_arch': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': (
            'The build architecture. Usually one of: "x86", "amd64" (a.k.a. x86-64), "arm", '
            '"arm64".\n\nDuplicate of cpu_name, with a better name.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'cpu_name',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'cpu_arch',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'cpu_count': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': 'Number of processor units in the CPU.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'cpu_count',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'cpu_count',
        'namespace': 'processed_crash.json_dump.system_info',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'short'
        }
    },
    'cpu_info': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': (
            'Detailed processor info. Usually contains information such as the family, model, '
            'and stepping number.'
        ),
        'form_field_choices': [],
        'form_field_type': 'StringField',
        'has_full_version': True,
        'in_database_name': 'cpu_info',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'cpu_info',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'cpu_info': {
                    'analyzer': 'standard',
                    'index': 'analyzed',
                    'type': 'string'
                },
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'type': 'multi_field'
        }
    },
    'cpu_microcode_version': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'Microcode version of the CPU.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'CPUMicrocodeVersion',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'cpu_microcode_version',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'cpu_name': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'Architecture of the processor. Deprecated, use cpu_arch instead.',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'cpu_name',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'cpu_name',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'cpu_usage_flash_process1': {
        'data_validation_type': 'int',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'CpuUsageFlashProcess1',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'cpu_usage_flash_process1',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'double'
        }
    },
    'cpu_usage_flash_process2': {
        'data_validation_type': 'int',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'CpuUsageFlashProcess2',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'cpu_usage_flash_process2',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'double'
        }
    },
    'crash_address': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'Address of the crash.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'crash_address',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'crash_address',
        'namespace': 'processed_crash.json_dump.crash_info',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'crash_time': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'crash_time',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'crash_time',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'crash_type': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'Type of the crash.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'type',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'crash_type',
        'namespace': 'processed_crash.json_dump.crash_info',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'crashedThread': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'crashedThread',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'crashedThread',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'crashing_thread': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': 'Index of the crashing thread.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'crashing_thread',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'crashing_thread',
        'namespace': 'processed_crash.json_dump.crash_info',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': None
    },
    'date': {
        'data_validation_type': 'datetime',
        'default_value': None,
        'description': 'Date at which the crash report was received by Socorro.',
        'form_field_choices': [],
        'form_field_type': 'DateTimeField',
        'has_full_version': False,
        'in_database_name': 'date_processed',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'date',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'date',
        'storage_mapping': {
            'format': 'yyyy-MM-dd\'T\'HH:mm:ssZZ||yyyy-MM-dd\'T\'HH:mm:ss.SSSSSSZZ',
            'type': 'date'
        }
    },
    'distributor': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'distributor',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'distributor',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'distributor_version': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'distributor_version',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'distributor_version',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'dom_ipc_enabled': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': (
            'The value of the "dom.ipc.enabled" preference (in other terms, whether e10s is '
            'enabled).'
        ),
        'form_field_choices': [],
        'form_field_type': 'BooleanField',
        'has_full_version': False,
        'in_database_name': 'DOMIPCEnabled',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'dom_ipc_enabled',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'flag',
        'storage_mapping': {
            'None_value': 0,
            'type': 'short'
        }
    },
    'dump': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'form_field_type': 'StringField',
        'has_full_version': False,
        'in_database_name': 'dump',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'dump',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'index': 'not_analyzed',
            'type': 'string'
        }
    },
    'dump_cpu_arch': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'Architecture of the CPU.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'cpu_arch',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'dump_cpu_arch',
        'namespace': 'processed_crash.json_dump.system_info',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'dump_cpu_info': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'Extended name of the CPU.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'cpu_info',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'dump_cpu_info',
        'namespace': 'processed_crash.json_dump.system_info',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'e10s_cohort': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': (
            'The e10s cohort. Values can be: \'test\', \'control\', \'unsupportedChannel\', '
            '\'optedIn\', \'optedOut\', \'disqualified\', \'unsupportedChannel\' or \'unknown\'.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'E10SCohort',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'e10s_cohort',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'em_check_compatibility': {
        'data_validation_type': 'bool',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': 'BooleanField',
        'has_full_version': False,
        'in_database_name': 'EMCheckCompatibility',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'em_check_compatibility',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'bool',
        'storage_mapping': {
            'type': 'boolean'
        }
    },
    'email': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': (
            'Users may opt in to providing their email address so that Mozilla may contact them '
            'about their crash report.'
        ),
        'form_field_choices': [],
        'form_field_type': 'StringField',
        'has_full_version': False,
        'in_database_name': 'email',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'email',
        'namespace': 'processed_crash',
        'permissions_needed': [
            'crashstats.view_pii'
        ],
        'query_type': 'string',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'exploitability': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'An automated estimate of how exploitable this crash is.',
        'form_field_choices': [
            'high',
            'normal',
            'low',
            'none',
            'unknown',
            'error'
        ],
        'form_field_type': 'MultipleValueField',
        'has_full_version': True,
        'in_database_name': 'exploitability',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'exploitability',
        'namespace': 'processed_crash',
        'permissions_needed': [
            'crashstats.view_exploitability'
        ],
        'query_type': 'enum',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'index': 'analyzed',
            'type': 'string'
        }
    },
    'flash_process_dump': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': '',
        'form_field_choices': [
            'sandbox',
            'broker',
            '__null__'
        ],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'FlashProcessDump',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'flash_process_dump',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'flash_version': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'Version of the Flash Player plugin.',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'flash_version',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'flash_version',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'frame_poison_base': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'FramePoisonBase',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'frame_poison_base',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'frame_poison_size': {
        'data_validation_type': 'int',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'FramePoisonSize',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'frame_poison_size',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'gmp_plugin': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'Whether it is a GMP plugin crash.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'GMPPlugin',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'gmp_plugin',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'flag',
        'storage_mapping': {
            'type': 'short'
        }
    },
    'graphics_critical_error': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'Log of graphics-related errors.',
        'form_field_choices': [],
        'has_full_version': True,
        'in_database_name': 'GraphicsCriticalError',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'graphics_critical_error',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'index': 'analyzed',
            'type': 'string'
        }
    },
    'graphics_startup_test': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'Whether the crash occured in the DriverCrashGuard.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'GraphicsStartupTest',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'graphics_startup_test',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'flag',
        'storage_mapping': {
            'type': 'short'
        }
    },
    'hang_type': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': (
            'Tells if a report was caused by a crash or a hang. In the database, the value '
            'is `0` if the problem was a crash of the software, and `1` or `-1` if the problem '
            'was a hang of the software. \n\nNote: for querying, you should use `crash` or '
            '`hang`, since those are automatically transformed into the correct underlying '
            'values.'
        ),
        'form_field_choices': [
            'any',
            'crash',
            'hang',
            'all'
        ],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'hang_type',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'hang_type',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'short'
        }
    },
    'hangid': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'hangid',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'hangid',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'id': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'id',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'id',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'install_age': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': 'Length of time since this version was installed.',
        'form_field_choices': [],
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'install_age',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'install_age',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'install_time': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'Epoch time of when this version was installed. Commonly used as a unique '
            'identifier for software installations (since it is unlikely that two instances '
            'are installed at the very same second).'
        ),
        'form_field_choices': [],
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'InstallTime',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'install_time',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'ipc_channel_error': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'The IPC channel error.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'ipc_channel_error',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'ipc_channel_error',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': None
    },
    'ipc_extra_system_error': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'has_full_version': True,
        'in_database_name': 'IPCExtraSystemError',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'ipc_extra_system_error',
        'namespace': 'raw_crash',
        'permissions_needed': [
            'crashstats.view_pii'
        ],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'index': 'analyzed',
            'type': 'string'
        }
    },
    'ipc_fatal_error_msg': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'The message linked to an IPC fatal error.',
        'form_field_choices': [],
        'has_full_version': True,
        'in_database_name': 'IPCFatalErrorMsg',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'ipc_fatal_error_msg',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'index': 'analyzed',
            'type': 'string'
        }
    },
    'ipc_fatal_error_protocol': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'The protocol linked to an IPC fatal error.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'IPCFatalErrorProtocol',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'ipc_fatal_error_protocol',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'ipc_message_name': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'The name of the IPC message.',
        'form_field_choices': [],
        'has_full_version': True,
        'in_database_name': 'IPCMessageName',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'ipc_message_name',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'index': 'analyzed',
            'type': 'string'
        }
    },
    'ipc_message_size': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'IPCMessageSize',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'ipc_message_size',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'ipc_shutdown_state': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': (
            'Shows that a shutdown hang was after we have received RecvShutdown but never '
            'each SendFinishShutdown or the hang happened before or after RecvShutdown. '
            'https://bugzilla.mozilla.org/show_bug.cgi?id=1301339'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'IPCShutdownState',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'ipc_shutdown_state',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'ipc_system_error': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'A replacement of `system_error`. '
            'https://bugzilla.mozilla.org/show_bug.cgi?id=1267222'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'IPCSystemError',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'ipc_system_error',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'integer'
        }
    },
    'is_garbage_collecting': {
        'data_validation_type': 'bool',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': 'BooleanField',
        'has_full_version': False,
        'in_database_name': 'IsGarbageCollecting',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'is_garbage_collecting',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'bool',
        'storage_mapping': {
            'type': 'boolean'
        }
    },
    'java_stack_trace': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': (
            'When Java code crashes due to an unhandled exception, this is the Java Stack Trace. '
            'It is usually more useful than the system stack trace given for the crashing thread.'
        ),
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': True,
        'in_database_name': 'java_stack_trace',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'java_stack_trace',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'index': 'analyzed',
            'type': 'string'
        }
    },
    'jit_category': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'JIT classification.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'category',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'jit_category',
        'namespace': 'processed_crash.classifications.jit',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'jit_category_return_code': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'JIT classification.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'category_return_code',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'jit_category_return_code',
        'namespace': 'processed_crash.classifications.jit',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'json_dump': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'The dump as a JSON object.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'json_dump',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'json_dump',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'largest_free_vm_block': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'largest_free_vm_block',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'largest_free_vm_block',
        'namespace': 'processed_crash.json_dump',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'last_crash': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'Length of time between the previous crash submission and this one. Low values '
            'indicate repeated crashes.'
        ),
        'form_field_choices': [],
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'last_crash',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'last_crash',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'legacy_processing': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'legacy_processing',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'legacy_processing',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'boolean'
        }
    },
    'main_module': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': 'Index into modules.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'main_module',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'main_module',
        'namespace': 'processed_crash.json_dump',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': None
    },
    'memory_explicit': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The "explicit" measurement from the memory report. See about:memory for '
            'a fuller description.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'explicit',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'memory_explicit',
        'namespace': 'processed_crash.memory_measures',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'memory_gfx_textures': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The "gfx-textures" measurement from the memory report. See about:memory for '
            'a fuller description.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'gfx_textures',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'memory_gfx_textures',
        'namespace': 'processed_crash.memory_measures',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'memory_ghost_windows': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The "ghost-windows" measurement from the memory report. See about:memory for '
            'a fuller description.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'ghost_windows',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'memory_ghost_windows',
        'namespace': 'processed_crash.memory_measures',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'memory_heap_allocated': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The "heap-allocated" measurement from the memory report. See about:memory for '
            'a fuller description.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'heap_allocated',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'memory_heap_allocated',
        'namespace': 'processed_crash.memory_measures',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'memory_heap_overhead': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The "heap-overhead" measurement from the memory report. See about:memory for '
            'a fuller description.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'heap_overhead',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'memory_heap_overhead',
        'namespace': 'processed_crash.memory_measures',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'memory_heap_unclassified': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The "heap-unclassified" measurement from the memory report. See about:memory for '
            'a fuller description.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'heap_unclassified',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'memory_heap_unclassified',
        'namespace': 'processed_crash.memory_measures',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'memory_host_object_urls': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The "host-object-urls" measurement from the memory report. See about:memory for '
            'a fuller description.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'host_object_urls',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'memory_host_object_urls',
        'namespace': 'processed_crash.memory_measures',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'memory_images': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The "images" measurement from the memory report. See about:memory for a fuller '
            'description.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'images',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'memory_images',
        'namespace': 'processed_crash.memory_measures',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'memory_js_main_runtime': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The "js-main-runtime" measurement from the memory report. See about:memory for a '
            'fuller description.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'js_main_runtime',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'memory_js_main_runtime',
        'namespace': 'processed_crash.memory_measures',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'memory_measures': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'memory_measures',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'memory_measures',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'memory_private': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The "private" measurement from the memory report. See about:memory for a fuller '
            'description.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'private',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'memory_private',
        'namespace': 'processed_crash.memory_measures',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'memory_resident': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The "resident" measurement from the memory report. See about:memory for a fuller '
            'description.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'resident',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'memory_resident',
        'namespace': 'processed_crash.memory_measures',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'memory_resident_unique': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The "resident-unique" measurement from the memory report. See about:memory for a '
            'fuller description.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'resident_unique',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'memory_resident_unique',
        'namespace': 'processed_crash.memory_measures',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'memory_system_heap_allocated': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The "system-heap-allocated" measurement from the memory report. See about:memory for '
            'a fuller description.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'system_heap_allocated',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'memory_system_heap_allocated',
        'namespace': 'processed_crash.memory_measures',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'memory_top_none_detached': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The "top(none)/detached" measurement from the memory report. See about:memory for a '
            'fuller description.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'top_none_detached',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'memory_top_none_detached',
        'namespace': 'processed_crash.memory_measures',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'memory_vsize': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The "vsize" measurement from the memory report. See about:memory for a fuller '
            'description.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'vsize',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'memory_vsize',
        'namespace': 'processed_crash.memory_measures',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'memory_vsize_max_contiguous': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The "vsize-max-contiguous" measurement from the memory report. See about:memory for '
            'a fuller description.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'vsize_max_contiguous',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'memory_vsize_max_contiguous',
        'namespace': 'processed_crash.memory_measures',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'min_arm_version': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'Min_ARM_Version',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'min_arm_version',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'moz_crash_reason': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': (
            'For aborts caused by MOZ_CRASH, MOZ_RELEASE_ASSERT and related macros, this is the '
            'accompanying description.'
        ),
        'form_field_choices': [],
        'has_full_version': True,
        'in_database_name': 'MozCrashReason',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'moz_crash_reason',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'index': 'analyzed',
            'type': 'string'
        }
    },
    'number_of_processors': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': 'Alias to `cpu_count`. Deprecated.',
        'form_field_choices': [],
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'cpu_count',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'number_of_processors',
        'namespace': 'processed_crash.json_dump.system_info',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': None
    },
    'oom_allocation_size': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'A measure or estimate of the allocation request size that triggered an OOM crash. '
            'Note that allocators usually work with large (e.g. 1 MiB) chunks of memory, and a '
            'small request may have triggered a large chunk request, in which case the latter '
            'actually caused the OOM crash.'
        ),
        'form_field_choices': [],
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'OOMAllocationSize',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'oom_allocation_size',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'os': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'Operating System.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'os',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'os',
        'namespace': 'processed_crash.json_dump.system_info',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'os_ver': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'Operating System Version.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'os_ver',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'os_ver',
        'namespace': 'processed_crash.json_dump.system_info',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'platform': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': (
            'Basic name of the operating system. Can be \'Windows NT\', \'Mac OS X\' or '
            '\'Linux\'. Use `platform_pretty_version` for a more precise OS name including '
            'version.'
        ),
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': True,
        'in_database_name': 'os_name',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'platform',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                },
                'os_name': {
                    'type': 'string'
                }
            },
            'type': 'multi_field'
        }
    },
    'platform_pretty_version': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'A better platform name, including version for Windows and Mac OS X.',
        'form_field_choices': [],
        'has_full_version': True,
        'in_database_name': 'os_pretty_version',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'platform_pretty_version',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'index': 'analyzed',
            'type': 'string'
        }
    },
    'platform_version': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'Version of the operating system.',
        'form_field_choices': [],
        'form_field_type': 'StringField',
        'has_full_version': True,
        'in_database_name': 'os_version',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'platform_version',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'index': 'analyzed',
            'type': 'string'
        }
    },
    'plugin_cpu_usage': {
        'data_validation_type': 'int',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'PluginCpuUsage',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'plugin_cpu_usage',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'double'
        }
    },
    'plugin_filename': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': (
            'When a plugin process crashes, this is the name of the file of the plugin loaded '
            'into that process.'
        ),
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': True,
        'in_database_name': 'PluginFilename',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'plugin_filename',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'fields': {
                'PluginFilename': {
                    'index': 'analyzed',
                    'type': 'string'
                },
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'type': 'multi_field'
        }
    },
    'plugin_hang': {
        'data_validation_type': 'bool',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': 'BooleanField',
        'has_full_version': False,
        'in_database_name': 'PluginHang',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'plugin_hang',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'bool',
        'storage_mapping': {
            'type': 'boolean'
        }
    },
    'plugin_hang_ui_duration': {
        'data_validation_type': 'int',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'PluginHangUIDuration',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'plugin_hang_ui_duration',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'plugin_name': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': (
            'When a plugin process crashes, this is the name of the plugin loaded into that '
            'process.'
        ),
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': True,
        'in_database_name': 'PluginName',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'plugin_name',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'fields': {
                'PluginName': {
                    'index': 'analyzed',
                    'type': 'string'
                },
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'type': 'multi_field'
        }
    },
    'plugin_version': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': (
            'When a plugin process crashes, this is the version of the plugin loaded into that '
            'process.'
        ),
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': True,
        'in_database_name': 'PluginVersion',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'plugin_version',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'fields': {
                'PluginVersion': {
                    'index': 'analyzed',
                    'type': 'string'
                },
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'type': 'multi_field'
        }
    },
    'process_type': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': (
            'What type of process the crash happened in. When the main process crashes, this will '
            'not be present. But when a plugin or content process crashes, this will be '
            '\'plugin\' or \'content\'.'
        ),
        'form_field_choices': [
            'any',
            'browser',
            'plugin',
            'content',
            'gpu',
            'all'
        ],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'process_type',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'process_type',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'processor_notes': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': (
            'Notes of the Socorro processor, contains information about what changes were made to '
            'the report during processing.'
        ),
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': True,
        'in_database_name': 'processor_notes',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'processor_notes',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'index': 'analyzed',
            'type': 'string'
        }
    },
    'product': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'Name of the software.',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': True,
        'in_database_name': 'product',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'product',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                },
                'product': {
                    'index': 'analyzed',
                    'type': 'string'
                }
            },
            'type': 'multi_field'
        }
    },
    'productid': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'Identifier of the software.',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'productid',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'productid',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'proto_signature': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': (
            'A concatenation of the signatures of all the frames of the crashing thread.'
        ),
        'form_field_choices': [],
        'has_full_version': True,
        'in_database_name': 'proto_signature',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'proto_signature',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'index': 'analyzed',
            'type': 'string'
        }
    },
    'reason': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': (
            'The crash\'s exception kind. Different OSes have different exception kinds. Example'
            'values: "EXCEPTION_ACCESS_VIOLATION_READ", "EXCEPTION_BREAKPOINT", "SIGSEGV".'
        ),
        'form_field_choices': [],
        'form_field_type': 'StringField',
        'has_full_version': True,
        'in_database_name': 'reason',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'reason',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                },
                'reason': {
                    'analyzer': 'standard',
                    'type': 'string'
                }
            },
            'type': 'multi_field'
        }
    },
    'release_channel': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': (
            'The update channel that the user is on. Typically \'nightly\', \'aurora\', \'beta\', '
            'or \'release\', but this may also be other values like \'release-cck-partner\'.'
        ),
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'release_channel',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'release_channel',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'remote_type': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': (
            '"extension" if a WebExtension, "web" or missing otherwise. This is only set for '
            'content crashes.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'RemoteType',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'remote_type',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'safe_mode': {
        'data_validation_type': 'bool',
        'default_value': None,
        'description': 'Was the browser running in Safe mode?',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'SafeMode',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'safe_mode',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'bool',
        'storage_mapping': {
            'type': 'boolean'
        }
    },
    'shutdown_progress': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'See https://bugzilla.mozilla.org/show_bug.cgi?id=1038342',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'ShutdownProgress',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'shutdown_progress',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'signature': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': (
            'This is the field most commonly used for aggregating individual crash reports '
            'into a group. It usually contains one or more stack frames from the crashing '
            'thread. The stack frames may also be augmented or replaced with other tokens such '
            'as "OOM | small" or "shutdownhang" that further identify the crash kind.'
        ),
        'form_field_choices': [],
        'form_field_type': 'StringField',
        'has_full_version': True,
        'in_database_name': 'signature',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'signature',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                },
                'signature': {
                    'type': 'string'
                }
            },
            'type': 'multi_field'
        }
    },
    'skunk_classification': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': (
            'The skunk classification of this crash report, assigned by the processors.'
        ),
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'classification',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'skunk_classification',
        'namespace': 'processed_crash.classifications.skunk_works',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'startedDateTime': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'startedDateTime',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'startedDateTime',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'format': 'yyyy-MM-dd\'T\'HH:mm:ssZZ||yyyy-MM-dd\'T\'HH:mm:ss.SSSSSSZZ',
            'type': 'date'
        }
    },
    'startup_crash': {
        'data_validation_type': 'bool',
        'default_value': None,
        'description': (
            'Annotation that tells whether the crash happened before the startup phase was '
            'finished or not.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'StartupCrash',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'startup_crash',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'bool',
        'storage_mapping': {
            'null_value': 'False',
            'type': 'boolean'
        }
    },
    'startup_time': {
        'data_validation_type': 'int',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'StartupTime',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'startup_time',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'status': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': (
            'Status of the output of the stackwalker. Can be \'OK\', \'ERROR_*\' or '
            '\'SYMBOL_SUPPLIER_INTERRUPTED\'.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'status',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'status',
        'namespace': 'processed_crash.json_dump',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'submitted_from_infobar': {
        'data_validation_type': 'bool',
        'default_value': None,
        'description': (
            'True if the crash report was submitted after the crash happened, from an infobar '
            'in the UI.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'SubmittedFromInfobar',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'submitted_from_infobar',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'bool',
        'storage_mapping': {
            'type': 'boolean'
        }
    },
    'submitted_timestamp': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'submitted_timestamp',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'submitted_timestamp',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'success': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'success',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'success',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'boolean'
        }
    },
    'support_classification': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': (
            'The support classification of this crash report, assigned by the processors.'
        ),
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'classification',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'support_classification',
        'namespace': 'processed_crash.classifications.support',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'system_error': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'SystemError',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'system_error',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'system_memory_use_percentage': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': 'The approximate percentage of physical memory that is in use.',
        'form_field_choices': [],
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'SystemMemoryUsePercentage',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'system_memory_use_percentage',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'telemetry_environment': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': (
            'A field containing the entire Telemetry Environment, as sent with crash pings to '
            'Telemetry.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'TelemetryEnvironment',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'telemetry_environment',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'index': 'not_analyzed',
            'type': 'string'
        }
    },
    'theme': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'The current theme.',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'Theme',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'theme',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'thread_count': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': 'Number of threads.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'thread_count',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'thread_count',
        'namespace': 'processed_crash.json_dump',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': None
    },
    'threads_index': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': 'Index of this thread in the list of threads?',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'threads_index',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'threads_index',
        'namespace': 'processed_crash.json_dump.crashing_thread',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': None
    },
    'throttle_rate': {
        'data_validation_type': 'int',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'throttle_rate',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'throttle_rate',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'throttleable': {
        'data_validation_type': 'bool',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': 'BooleanField',
        'has_full_version': False,
        'in_database_name': 'Throttleable',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'throttleable',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'bool',
        'storage_mapping': {
            'type': 'boolean'
        }
    },
    'timestamp': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'timestamp',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'timestamp',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'double'
        }
    },
    'tiny_block_size': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'tiny_block_size',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'tiny_block_size',
        'namespace': 'processed_crash.json_dump',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'topmost_filenames': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'Paths of the files at the top of the stack.',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'topmost_filenames',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'topmost_filenames',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'analyzer': 'semicolon_keywords',
            'type': 'string'
        }
    },
    'total_frames': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': 'Total number of frames in the thread.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'total_frames',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'total_frames',
        'namespace': 'processed_crash.json_dump.crashing_thread',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': None
    },
    'total_page_file': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'TotalPageFile',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'total_page_file',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'total_physical_memory': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': 'The total amount of physical memory.',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'TotalPhysicalMemory',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'total_physical_memory',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'total_virtual_memory': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'The size of the user-mode portion of the virtual address space of the calling '
            'process. This value depends on the type of process, the type of processor, and '
            'the configuration of the operating system. 32-bit processes usually have values '
            'in the range 2--4 GiB. 64-bit processes usually have *much* larger values.'
        ),
        'form_field_choices': [],
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'TotalVirtualMemory',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'total_virtual_memory',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'truncated': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'truncated',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'truncated',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'boolean'
        }
    },
    'upload_file_minidump_browser': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'upload_file_minidump_browser',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'upload_file_minidump_browser',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'upload_file_minidump_flash1': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'upload_file_minidump_flash1',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'upload_file_minidump_flash1',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'upload_file_minidump_flash2': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'upload_file_minidump_flash2',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'upload_file_minidump_flash2',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': None
    },
    'uptime': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': (
            'Length of time the process was running before it crashed. Small values (from 0 to '
            '5 or so) usually indicate start-up crashes.'
        ),
        'form_field_choices': [],
        'form_field_type': 'IntegerField',
        'has_full_version': False,
        'in_database_name': 'uptime',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'uptime',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'uptime_ts': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': 'TimeStamp based uptime.',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'UptimeTS',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'uptime_ts',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'double'
        }
    },
    'url': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': (
            'The website which the user most recently visited in the browser before the crash. '
            'Users have the option of opting in or out of sending the current URL. This '
            'information may not always be valuable, because pages in other tabs or windows '
            'may be responsible for a particular crash.'
        ),
        'form_field_choices': [],
        'form_field_type': 'StringField',
        'has_full_version': False,
        'in_database_name': 'url',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'url',
        'namespace': 'processed_crash',
        'permissions_needed': [
            'crashstats.view_pii'
        ],
        'query_type': 'string',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'user_comments': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': 'Comments entered by the user when they crashed.',
        'form_field_choices': [],
        'form_field_type': 'StringField',
        'has_full_version': True,
        'in_database_name': 'user_comments',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'user_comments',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                },
                'user_comments': {
                    'type': 'string'
                }
            },
            'type': 'multi_field'
        }
    },
    'useragent_locale': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'The locale of the software installation.',
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'useragent_locale',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'useragent_locale',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'analyzer': 'semicolon_keywords',
            'type': 'string'
        }
    },
    'uuid': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': 'Unique identifier of the report.',
        'form_field_choices': [],
        'form_field_type': None,
        'has_full_version': False,
        'in_database_name': 'uuid',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'uuid',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'index': 'not_analyzed',
            'type': 'string'
        }
    },
    'vendor': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'form_field_type': 'MultipleValueField',
        'has_full_version': False,
        'in_database_name': 'Vendor',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'vendor',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'version': {
        'data_validation_type': 'enum',
        'default_value': None,
        'description': (
            'The product version number. A value lacking any letters indicates a normal release; '
            'a value with a "b" indicates a Beta release; a value with an "a" indicates an Aurora '
            '(a.k.a. Developer Edition) release; a value with "esr" indicates an Extended Service '
            'Release.'
        ),
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'version',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'version',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'winsock_lsp': {
        'data_validation_type': 'str',
        'default_value': None,
        'description': (
            'On Windows, a string of data from the Windows OS about the list of installed LSPs '
            '(Layered Service Provider).'
        ),
        'form_field_choices': [],
        'form_field_type': 'MultipleValueField',
        'has_full_version': True,
        'in_database_name': 'Winsock_LSP',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'winsock_lsp',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'index': 'analyzed',
            'type': 'string'
        }
    },
    'write_combine_size': {
        'data_validation_type': 'int',
        'default_value': None,
        'description': '',
        'form_field_choices': [],
        'has_full_version': False,
        'in_database_name': 'write_combine_size',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'write_combine_size',
        'namespace': 'processed_crash.json_dump',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    }
}
