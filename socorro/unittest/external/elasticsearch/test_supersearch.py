# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import mock
import pyelasticsearch

from nose.plugins.attrib import attr
from nose.tools import eq_, ok_, assert_raises

from socorro.external import (
    BadArgumentError,
    InsertionError,
    MissingArgumentError,
    ResourceNotFound,
)
from socorro.external.elasticsearch import crashstorage
from socorro.external.elasticsearch.supersearch import SuperSearch
from socorro.lib import datetimeutil, search_common
from .unittestbase import ElasticSearchTestCase

# Remove debugging noise during development
import logging
logging.getLogger('pyelasticsearch').setLevel(logging.ERROR)
logging.getLogger('elasticutils').setLevel(logging.ERROR)
logging.getLogger('requests.packages.urllib3.connectionpool')\
       .setLevel(logging.ERROR)


SUPERSEARCH_FIELDS = {
    'signature': {
        'name': 'signature',
        'in_database_name': 'signature',
        'data_validation_type': 'str',
        'query_type': 'str',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'has_full_version': True,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'multi_field',
            'fields': {
                'signature': {
                    'type': 'string'
                },
                'full': {
                    'type': 'string',
                    'index': 'not_analyzed'
                }
            }
        },
    },
    'product': {
        'name': 'product',
        'in_database_name': 'product',
        'data_validation_type': 'enum',
        'query_type': 'enum',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'has_full_version': True,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'multi_field',
            'fields': {
                'product': {
                    'type': 'string'
                },
                'full': {
                    'type': 'string',
                    'index': 'not_analyzed'
                }
            }
        },
    },
    'version': {
        'name': 'version',
        'in_database_name': 'version',
        'data_validation_type': 'enum',
        'query_type': 'enum',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'has_full_version': False,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'string',
            'analyzer': 'keyword'
        },
    },
    'platform': {
        'name': 'platform',
        'in_database_name': 'os_name',
        'data_validation_type': 'enum',
        'query_type': 'enum',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'has_full_version': True,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'multi_field',
            'fields': {
                'os_name': {
                    'type': 'string'
                },
                'full': {
                    'type': 'string',
                    'index': 'not_analyzed'
                }
            }
        },
    },
    'release_channel': {
        'name': 'release_channel',
        'in_database_name': 'release_channel',
        'data_validation_type': 'enum',
        'query_type': 'enum',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'has_full_version': False,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'string'
        },
    },
    'date': {
        'name': 'date',
        'in_database_name': 'date_processed',
        'data_validation_type': 'datetime',
        'query_type': 'date',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'has_full_version': False,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'date',
            'format': 'yyyy-MM-dd\'T\'HH:mm:ssZZ||yyyy-MM-dd\'T\'HH:mm:ss.SSSSSSZZ'
        },
    },
    'address': {
        'name': 'address',
        'in_database_name': 'address',
        'data_validation_type': 'str',
        'query_type': 'str',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'has_full_version': False,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'string'
        },
    },
    'build_id': {
        'name': 'build_id',
        'in_database_name': 'build',
        'data_validation_type': 'int',
        'query_type': 'number',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'has_full_version': False,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'long'
        },
    },
    'reason': {
        'name': 'reason',
        'in_database_name': 'reason',
        'data_validation_type': 'str',
        'query_type': 'str',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'has_full_version': False,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'string'
        },
    },
    'email': {
        'name': 'email',
        'in_database_name': 'email',
        'data_validation_type': 'str',
        'query_type': 'str',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': ['crashstats.view_pii'],
        'default_value': None,
        'has_full_version': False,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'string',
            'analyzer': 'keyword'
        },
    },
    'url': {
        'name': 'url',
        'in_database_name': 'url',
        'data_validation_type': 'str',
        'query_type': 'str',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': ['crashstats.view_pii'],
        'default_value': None,
        'has_full_version': False,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'string',
            'analyzer': 'keyword'
        },
    },
    'uuid': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'uuid',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'uuid',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'index': 'not_analyzed',
            'type': 'string'
        }
    },
    'process_type': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': [
            'any', 'browser', 'plugin', 'content', 'all'
        ],
        'has_full_version': False,
        'in_database_name': 'process_type',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'process_type',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'user_comments': {
        'data_validation_type': 'str',
        'default_value': None,
        'form_field_choices': None,
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
    'accessibility': {
        'data_validation_type': 'bool',
        'default_value': None,
        'form_field_choices': None,
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
    'b2g_os_version': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'B2G_OS_Version',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'b2g_os_version',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'bios_manufacturer': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
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
    'vendor': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
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
    'useragent_locale': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
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
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'is_garbage_collecting': {
        'data_validation_type': 'bool',
        'default_value': None,
        'form_field_choices': None,
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
    'available_virtual_memory': {
        'data_validation_type': 'int',
        'default_value': None,
        'form_field_choices': None,
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
    'install_age': {
        'data_validation_type': 'int',
        'default_value': None,
        'form_field_choices': None,
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
    'plugin_filename': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
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
    'plugin_name': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
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
        'form_field_choices': None,
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
    'android_model': {
        'data_validation_type': 'str',
        'default_value': None,
        'form_field_choices': None,
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
    'dump': {
        'data_validation_type': 'str',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'dump',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'dump',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'index': 'not_analyzed',
            'type': 'string'
        }
    },
    'cpu_info': {
        'data_validation_type': 'str',
        'default_value': None,
        'form_field_choices': None,
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
    'dom_ipc_enabled': {
        'data_validation_type': 'bool',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'DOMIPCEnabled',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'dom_ipc_enabled',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'bool',
        'storage_mapping': {
            'null_value': False,
            'type': 'boolean'
        }
    },
    'app_notes': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'app_notes',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'app_notes',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'hang_type': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': [
            'any', 'crash', 'hang', 'all'
        ],
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
    'exploitability': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': [
            'high', 'normal', 'low', 'none', 'unknown', 'error'
        ],
        'has_full_version': False,
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
            'type': 'string'
        }
    },
    'platform_version': {
        'data_validation_type': 'str',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'os_version',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'platform_version',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'write_combine_size': {
        'data_validation_type': 'int',
        'default_value': None,
        'form_field_choices': None,
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
    },
    'fake_field': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'fake_field',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'fake_field',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
    },
}


class TestSuperSearch(ElasticSearchTestCase):
    """Test SuperSearch's behavior with a mocked elasticsearch database. """

    def setUp(self):
        self.config = self.get_config_context()
        self.storage = crashstorage.ElasticSearchCrashStorage(self.config)
        es_index = self.config.webapi.elasticsearch_default_index

        # Create the supersearch fields.
        self.storage.es.bulk_index(
            index=es_index,
            doc_type='supersearch_fields',
            docs=SUPERSEARCH_FIELDS.values(),
            id_field='name',
            refresh=True,
        )

    def tearDown(self):
        es_index = self.config.webapi.elasticsearch_default_index
        self.storage.es.delete_index(es_index)

    def test_get_indexes(self):
        api = SuperSearch(config=self.config)

        now = datetime.datetime(2000, 2, 1, 0, 0)
        lastweek = now - datetime.timedelta(weeks=1)
        lastmonth = now - datetime.timedelta(weeks=4)

        dates = [
            search_common.SearchParam('date', now, '<'),
            search_common.SearchParam('date', lastweek, '>'),
        ]

        res = api.get_indexes(dates)
        eq_(res, ['socorro_integration_test_reports'])

        config = self.get_config_context(es_index='socorro_%Y%W')
        api = SuperSearch(config=config)

        dates = [
            search_common.SearchParam('date', now, '<'),
            search_common.SearchParam('date', lastweek, '>'),
        ]

        res = api.get_indexes(dates)
        eq_(res, ['socorro_200004', 'socorro_200005'])

        dates = [
            search_common.SearchParam('date', now, '<'),
            search_common.SearchParam('date', lastmonth, '>'),
        ]

        res = api.get_indexes(dates)
        eq_(
            res,
            [
                'socorro_200001', 'socorro_200002', 'socorro_200003',
                'socorro_200004', 'socorro_200005'
            ]
        )


@attr(integration='elasticsearch')  # for nosetests
class IntegrationTestSuperSearch(ElasticSearchTestCase):
    """Test SuperSearch with an elasticsearch database containing fake data.
    """

    def setUp(self):
        super(IntegrationTestSuperSearch, self).setUp()

        config = self.get_config_context()
        self.storage = crashstorage.ElasticSearchCrashStorage(config)

        # clear the indices cache so the index is created on every test
        self.storage.indices_cache = set()

        # Create the supersearch fields.
        self.storage.es.bulk_index(
            index=config.webapi.elasticsearch_default_index,
            doc_type='supersearch_fields',
            docs=SUPERSEARCH_FIELDS.values(),
            id_field='name',
            refresh=True,
        )

        now = datetimeutil.utc_now()

        yesterday = now - datetime.timedelta(days=1)
        yesterday = datetimeutil.date_to_string(yesterday)

        last_month = now - datetime.timedelta(weeks=4)
        last_month = datetimeutil.date_to_string(last_month)

        # insert data into elasticsearch
        default_crash_report = {
            'uuid': 100,
            'address': '0x0',
            'signature': 'js::break_your_browser',
            'date_processed': yesterday,
            'product': 'WaterWolf',
            'version': '1.0',
            'release_channel': 'release',
            'os_name': 'Linux',
            'build': 1234567890,
            'reason': 'MOZALLOC_WENT_WRONG',
            'hangid': None,
            'process_type': None,
            'email': 'example@gmail.com',
            'url': 'https://mozilla.org',
            'user_comments': '',
            'install_age': 0,
            'json_dump': {
                'write_combine_size': 88239132,
            },
        }
        default_raw_crash_report = {
            'Accessibility': True,
            'AvailableVirtualMemory': 10211743,
            'B2G_OS_Version': '1.1.203448',
            'BIOS_Manufacturer': 'SUSA',
            'IsGarbageCollecting': False,
            'Vendor': 'mozilla',
            'useragent_locale': 'en-US',
        }

        self.storage.save_raw_and_processed(
            default_raw_crash_report,
            None,
            default_crash_report,
            default_crash_report['uuid']
        )

        self.storage.save_raw_and_processed(
            dict(default_raw_crash_report, Accessibility=False),
            None,
            dict(default_crash_report, uuid=1, product='EarthRaccoon'),
            1
        )

        self.storage.save_raw_and_processed(
            dict(default_raw_crash_report, AvailableVirtualMemory=0),
            None,
            dict(default_crash_report, uuid=2, version='2.0'),
            2
        )

        self.storage.save_raw_and_processed(
            dict(default_raw_crash_report, B2G_OS_Version='1.3'),
            None,
            dict(default_crash_report, uuid=3, release_channel='aurora'),
            3
        )

        self.storage.save_raw_and_processed(
            dict(default_raw_crash_report, BIOS_Manufacturer='aidivn'),
            None,
            dict(default_crash_report, uuid=4, os_name='Windows NT'),
            4
        )

        self.storage.save_raw_and_processed(
            dict(default_raw_crash_report, IsGarbageCollecting=True),
            None,
            dict(default_crash_report, uuid=5, build=987654321),
            5
        )

        self.storage.save_raw_and_processed(
            dict(default_raw_crash_report, Vendor='gnusmas'),
            None,
            dict(default_crash_report, uuid=6, reason='VERY_BAD_EXCEPTION'),
            6
        )

        self.storage.save_raw_and_processed(
            dict(default_raw_crash_report, useragent_locale='fr'),
            None,
            dict(default_crash_report, uuid=7, hangid=12),
            7
        )

        self.storage.save_raw_and_processed(
            dict(default_raw_crash_report, Android_Model='PediaMad 17 Heavy'),
            None,
            dict(default_crash_report, uuid=8, process_type='plugin'),
            8
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=9, signature='my_bad')
        )

        self.storage.save_processed(
            dict(
                default_crash_report,
                uuid=10,
                date_processed=last_month,
                signature='my_little_signature',
            )
        )

        # for plugin terms test
        self.storage.save_processed(
            dict(
                default_crash_report,
                uuid=11,
                product='PluginSoft',
                process_type='plugin',
                PluginFilename='carly.dll',
                PluginName='Hey I just met you',
                PluginVersion='1.2',
            )
        )

        self.storage.save_processed(
            dict(
                default_crash_report,
                uuid=12,
                product='PluginSoft',
                process_type='plugin',
                PluginFilename='hey.dll',
                PluginName='Hey Plugin',
                PluginVersion='10.7.0.2a',
            )
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=13, email='example@hotmail.com')
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=14, email='sauron@yahoo.com')
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=15, email='sauron@mordor.info')
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=16, install_age=87234)
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=17, url='http://www.mozilla.org')
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=18, url='http://www.example.com')
        )

        self.storage.save_processed(
            dict(
                default_crash_report,
                uuid=19,
                user_comments='I love WaterWolf',
            )
        )

        self.storage.save_processed(
            dict(
                default_crash_report,
                uuid=20,
                user_comments='WaterWolf is so bad',
            )
        )

        self.storage.save_processed(
            dict(default_crash_report, uuid=21, address='0xa2e4509ca0')
        )

        # As indexing is asynchronous, we need to force elasticsearch to
        # make the newly created content searchable before we run the tests
        self.storage.es.refresh()

        self.api = SuperSearch(config=config)

    def tearDown(self):
        # clear the test index
        config = self.get_config_context()
        self.storage.es.delete_index(config.webapi.elasticsearch_index)
        self.storage.es.delete_index(config.webapi.elasticsearch_default_index)

        super(IntegrationTestSuperSearch, self).tearDown()

    def test_get(self):
        """Test a search with default values returns the right structure. """
        res = self.api.get()

        ok_('total' in res)
        eq_(res['total'], 21)

        ok_('hits' in res)
        eq_(len(res['hits']), res['total'])

        ok_('facets' in res)
        ok_('signature' in res['facets'])

        expected_signatures = [
            {'term': 'js::break_your_browser', 'count': 20},
            {'term': 'my_bad', 'count': 1},
        ]
        eq_(res['facets']['signature'], expected_signatures)

        # Test fields are being renamed.
        ok_('date' in res['hits'][0])  # date_processed > date
        ok_('build_id' in res['hits'][0])  # build > build_id
        ok_('platform' in res['hits'][0])  # os_name > platform

        # Test namespaces are correctly removed.
        # processed_crash.json_dump.write_combine_size
        ok_('write_combine_size' in res['hits'][0])

    def test_get_individual_filters(self):
        """Test a search with single filters returns expected results. """
        # Test signature
        kwargs = {
            'signature': 'my_bad',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['signature'], 'my_bad')

        # Test product
        kwargs = {
            'product': 'EarthRaccoon',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['signature'], 'js::break_your_browser')
        eq_(res['hits'][0]['product'], 'EarthRaccoon')

        # Test version
        kwargs = {
            'version': '2.0',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['signature'], 'js::break_your_browser')
        eq_(res['hits'][0]['version'], '2.0')

        # Test release_channel
        kwargs = {
            'release_channel': 'aurora',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['signature'], 'js::break_your_browser')
        eq_(res['hits'][0]['release_channel'], 'aurora')

        # Test platform
        kwargs = {
            'platform': 'Windows',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['signature'], 'js::break_your_browser')
        eq_(res['hits'][0]['platform'], 'Windows NT')

        # Test build_id
        kwargs = {
            'build_id': '987654321',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['signature'], 'js::break_your_browser')
        eq_(res['hits'][0]['build_id'], 987654321)

        # Test reason
        kwargs = {
            'reason': 'MOZALLOC_WENT_WRONG',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 20)
        eq_(res['hits'][0]['reason'], 'MOZALLOC_WENT_WRONG')

        kwargs = {
            'reason': ['very_bad_exception'],
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['signature'], 'js::break_your_browser')
        eq_(res['hits'][0]['reason'], 'VERY_BAD_EXCEPTION')

        # Test process_type
        kwargs = {
            'process_type': 'plugin',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 3)
        eq_(res['hits'][0]['signature'], 'js::break_your_browser')
        eq_(res['hits'][0]['process_type'], 'plugin')

        # Test url
        kwargs = {
            'url': 'https://mozilla.org',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 19)
        eq_(res['hits'][0]['signature'], 'js::break_your_browser')
        ok_('mozilla.org' in res['hits'][0]['url'])

        # Test user_comments
        kwargs = {
            'user_comments': 'WaterWolf',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 2)
        eq_(res['hits'][0]['signature'], 'js::break_your_browser')
        ok_('WaterWolf' in res['hits'][0]['user_comments'])

        # Test address
        kwargs = {
            'address': '0x0',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 20)
        ok_('0x0' in res['hits'][0]['address'])

        # Test accessibility
        kwargs = {
            'accessibility': False,
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        ok_(not res['hits'][0]['accessibility'])

        kwargs = {
            'accessibility': 'True',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 8)
        ok_(res['hits'][0]['accessibility'])

        # Test b2g_os_version
        kwargs = {
            'b2g_os_version': '1.3',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['b2g_os_version'], '1.3')

        # Test bios_manufacturer
        kwargs = {
            'bios_manufacturer': 'aidivn',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['bios_manufacturer'], 'aidivn')

        # Test is_garbage_collecting
        kwargs = {
            'is_garbage_collecting': True,
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        ok_(res['hits'][0]['is_garbage_collecting'])

        # Test vendor
        kwargs = {
            'vendor': 'gnusmas',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['vendor'], 'gnusmas')

        # Test useragent_locale
        kwargs = {
            'useragent_locale': 'fr',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['useragent_locale'], 'fr')

    def test_get_with_range_operators(self):
        """Test a search with several filters and operators returns expected
        results. """
        # Test date
        now = datetimeutil.utc_now()
        lastweek = now - datetime.timedelta(days=7)
        lastmonth = lastweek - datetime.timedelta(weeks=4)
        kwargs = {
            'date': [
                '<%s' % lastweek,
                '>=%s' % lastmonth,
            ]
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['signature'], 'my_little_signature')

        # Test build id
        kwargs = {
            'build_id': '<1234567890',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['signature'], 'js::break_your_browser')
        ok_(res['hits'][0]['build_id'] < 1234567890)

        kwargs = {
            'build_id': '>1234567889',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 20)
        ok_(res['hits'])
        for report in res['hits']:
            ok_(report['build_id'] > 1234567889)

        kwargs = {
            'build_id': '<=1234567890',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 21)
        ok_(res['hits'])
        for report in res['hits']:
            ok_(report['build_id'] <= 1234567890)

        # Test available_virtual_memory
        kwargs = {
            'available_virtual_memory': '>=1',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 8)
        for report in res['hits']:
            ok_(report['available_virtual_memory'] >= 1)

        kwargs = {
            'available_virtual_memory': '<1',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['available_virtual_memory'], 0)

    def test_get_with_string_operators(self):
        """Test a search with several filters and operators returns expected
        results. """
        # Test signature
        kwargs = {
            'signature': ['js', 'break_your_browser'],
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 20)
        ok_(res['hits'])
        for report in res['hits']:
            eq_(report['signature'], 'js::break_your_browser')

        # - Test contains mode
        kwargs = {
            'signature': '~bad',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['signature'], 'my_bad')

        kwargs = {
            'signature': '~js::break',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 20)
        ok_(res['hits'])
        for report in res['hits']:
            eq_(report['signature'], 'js::break_your_browser')

        # - Test is_exactly mode
        kwargs = {
            'signature': '=js::break_your_browser',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 20)
        ok_(res['hits'])
        for report in res['hits']:
            eq_(report['signature'], 'js::break_your_browser')

        kwargs = {
            'signature': '=my_bad',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['signature'], 'my_bad')

        # - Test starts_with mode
        kwargs = {
            'signature': '$js',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 20)
        ok_(res['hits'])
        for report in res['hits']:
            eq_(report['signature'], 'js::break_your_browser')

        # - Test ends_with mode
        kwargs = {
            'signature': '^browser',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 20)
        ok_(res['hits'])
        for report in res['hits']:
            eq_(report['signature'], 'js::break_your_browser')

        # Test email
        kwargs = {
            'email': 'sauron@mordor.info',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        ok_(res['hits'])
        eq_(res['hits'][0]['email'], 'sauron@mordor.info')

        kwargs = {
            'email': '~mail.com',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 19)
        ok_(res['hits'])
        for report in res['hits']:
            ok_('@' in report['email'])
            ok_('mail.com' in report['email'])

        kwargs = {
            'email': '$sauron@',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 2)
        ok_(res['hits'])
        for report in res['hits']:
            ok_('sauron@' in report['email'])

        # Test url
        kwargs = {
            'url': 'https://mozilla.org',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 19)

        kwargs = {
            'url': '~mozilla.org',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 20)
        ok_(res['hits'])
        for report in res['hits']:
            ok_('mozilla.org' in report['url'])

        kwargs = {
            'url': '^.com',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['signature'], 'js::break_your_browser')
        eq_(res['hits'][0]['url'], 'http://www.example.com')

        # Test user_comments
        kwargs = {
            'user_comments': '~love',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['signature'], 'js::break_your_browser')
        eq_(res['hits'][0]['user_comments'], 'I love WaterWolf')

        kwargs = {
            'user_comments': '$WaterWolf',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['signature'], 'js::break_your_browser')
        eq_(
            res['hits'][0]['user_comments'],
            'WaterWolf is so bad'
        )

        kwargs = {
            'user_comments': '__null__',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 19)
        eq_(res['hits'][0]['signature'], 'js::break_your_browser')
        for hit in res['hits']:
            eq_(hit['user_comments'], '')

        # Test address
        kwargs = {
            'address': '^0',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 21)
        kwargs = {
            'address': '~a2',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)

        # Test android_model
        kwargs = {
            'android_model': '~PediaMad',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)

        kwargs = {
            'android_model': '=PediaMad 17 Heavy',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)

    def test_get_with_facets(self):
        """Test a search with facets returns expected results. """
        # Test several facets
        kwargs = {
            '_facets': ['signature', 'platform']
        }
        res = self.api.get(**kwargs)

        ok_('facets' in res)
        ok_('signature' in res['facets'])

        expected_signatures = [
            {'term': 'js::break_your_browser', 'count': 20},
            {'term': 'my_bad', 'count': 1},
        ]
        eq_(res['facets']['signature'], expected_signatures)

        ok_('platform' in res['facets'])
        expected_platforms = [
            {'term': 'Linux', 'count': 20},
            {'term': 'Windows NT', 'count': 1},
        ]
        eq_(res['facets']['platform'], expected_platforms)

        # Test one facet with filters
        kwargs = {
            '_facets': ['release_channel'],
            'release_channel': 'aurora',
        }
        res = self.api.get(**kwargs)

        ok_('release_channel' in res['facets'])

        expected_signatures = [
            {'term': 'aurora', 'count': 1},
        ]
        eq_(res['facets']['release_channel'], expected_signatures)

        # Test one facet with a different filter
        kwargs = {
            '_facets': ['release_channel'],
            'platform': 'linux',
        }
        res = self.api.get(**kwargs)

        ok_('release_channel' in res['facets'])

        expected_signatures = [
            {'term': 'release', 'count': 19},
            {'term': 'aurora', 'count': 1},
        ]
        eq_(res['facets']['release_channel'], expected_signatures)

        # Test errors
        assert_raises(
            BadArgumentError,
            self.api.get,
            _facets=['unkownfield']
        )

    def test_get_with_pagination(self):
        """Test a search with pagination returns expected results. """
        kwargs = {
            '_results_number': '10',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 21)
        eq_(len(res['hits']), 10)

        kwargs = {
            '_results_number': '10',
            '_results_offset': '10',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 21)
        eq_(len(res['hits']), 10)

        kwargs = {
            '_results_number': '10',
            '_results_offset': '15',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 21)
        eq_(len(res['hits']), 6)

        kwargs = {
            '_results_number': '10',
            '_results_offset': '30',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 21)
        eq_(len(res['hits']), 0)

    def test_get_with_not_operator(self):
        """Test a search with a few NOT operators. """
        # Test signature
        kwargs = {
            'signature': ['js', 'break_your_browser'],
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 20)
        ok_(res['hits'])
        for report in res['hits']:
            eq_(report['signature'], 'js::break_your_browser')

        # - Test contains mode
        kwargs = {
            'signature': '!~bad',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 20)

        # - Test is_exactly mode
        kwargs = {
            'signature': '!=js::break_your_browser',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['signature'], 'my_bad')

        # - Test starts_with mode
        kwargs = {
            'signature': '!$js',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['signature'], 'my_bad')

        # - Test ends_with mode
        kwargs = {
            'signature': '!^browser',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['signature'], 'my_bad')

        # Test build id
        kwargs = {
            'build_id': '!<1234567890',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 20)
        ok_(res['hits'])
        for report in res['hits']:
            ok_(report['build_id'] > 1234567889)

        kwargs = {
            'build_id': '!>1234567889',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 1)
        eq_(res['hits'][0]['signature'], 'js::break_your_browser')
        ok_(res['hits'][0]['build_id'] < 1234567890)

        kwargs = {
            'build_id': '!<=1234567890',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], 0)

    @mock.patch(
        'socorro.external.elasticsearch.supersearch.SuperSearch.get_indexes'
    )
    def test_list_of_indices(self, mocked_get_indexes):
        """Test that unexisting indices are handled correctly. """
        mocked_get_indexes.return_value = ['socorro_unknown']

        res = self.api.get()
        res_expected = {
            'hits': [],
            'total': 0,
            'facets': {},
        }
        eq_(res, res_expected)

        mocked_get_indexes.return_value = [
            'socorro_integration_test_reports',
            'something_that_does_not_exist',
            'another_one'
        ]

        res = self.api.get()

        ok_('total' in res)
        eq_(res['total'], 21)

        ok_('hits' in res)
        eq_(len(res['hits']), res['total'])

        ok_('facets' in res)
        ok_('signature' in res['facets'])

    def test_return_query_mode(self):
        kwargs = {
            'signature': ['js', 'break_your_browser'],
            '_return_query': 'true'
        }
        res = self.api.get(**kwargs)
        ok_('query' in res)
        ok_('indices' in res)
        query = res['query']
        ok_('filter' in query)
        ok_('facets' in query)
        ok_('size' in query)

    def test_create_field(self):
        es = self.storage.es
        config = self.get_config_context()

        # Test with all parameters set.
        params = {
            'name': 'plotfarm',
            'data_validation_type': 'str',
            'default_value': None,
            'description': 'a plotfarm like Lunix or Wondiws',
            'form_field_choices': ['lun', 'won', 'cam'],
            'has_full_version': True,
            'in_database_name': 'os_name',
            'is_exposed': True,
            'is_returned': True,
            'is_mandatory': False,
            'query_type': 'str',
            'namespace': 'processed_crash',
            'permissions_needed': ['view_plotfarm'],
            'storage_mapping': {"type": "multi_field"},
        }
        res = self.api.create_field(**params)
        ok_(res)
        field = es.get(
            index=config.webapi.elasticsearch_default_index,
            doc_type='supersearch_fields',
            id='plotfarm',
        )
        field = field['_source']
        eq_(sorted(field.keys()), sorted(params.keys()))
        for key in field.keys():
            eq_(field[key], params[key])

        # Test default values.
        res = self.api.create_field(
            name='brand_new_field',
            in_database_name='brand_new_field',
            namespace='processed_crash',
        )
        ok_(res)
        ok_(
            es.get(
                index=config.webapi.elasticsearch_default_index,
                doc_type='supersearch_fields',
                id='brand_new_field',
            )
        )

        # Test errors.
        assert_raises(
            MissingArgumentError,
            self.api.create_field,
            in_database_name='something',
        )  # `name` is missing
        assert_raises(
            MissingArgumentError,
            self.api.create_field,
            name='something',
        )  # `in_database_name` is missing

        assert_raises(
            InsertionError,
            self.api.create_field,
            name='product',
            in_database_name='product',
            namespace='processed_crash',
        )

        # Test logging.
        res = self.api.create_field(
            name='what_a_field',
            in_database_name='what_a_field',
            namespace='processed_crash',
            storage_mapping='{"type": "long"}',
        )
        ok_(res)
        self.api.config.logger.info.assert_called_with(
            'elasticsearch mapping changed for field "%s", '
            'added new mapping "%s"',
            'what_a_field',
            {u'type': u'long'},
        )

    def test_update_field(self):
        es = self.storage.es
        config = self.get_config_context()

        # Let's create a field first.
        assert self.api.create_field(
            name='super_field',
            in_database_name='super_field',
            namespace='superspace',
            description='inaccurate description',
            permissions_needed=['view_nothing'],
            storage_mapping={'type': 'boolean', 'null_value': False}
        )

        # Now let's update that field a little.
        res = self.api.update_field(
            name='super_field',
            description='very accurate description',
            storage_mapping={'type': 'long', 'analyzer': 'keyword'},
        )
        ok_(res)

        # Test logging.
        self.api.config.logger.info.assert_called_with(
            'elasticsearch mapping changed for field "%s", '
            'was "%s", now "%s"',
            'super_field',
            {'type': 'boolean', 'null_value': False},
            {'type': 'long', 'analyzer': 'keyword'},
        )

        field = es.get(
            index=config.webapi.elasticsearch_default_index,
            doc_type='supersearch_fields',
            id='super_field',
        )
        field = field['_source']

        # Verify the changes were taken into account.
        eq_(field['description'], 'very accurate description')
        eq_(field['storage_mapping'], {'type': 'long', 'analyzer': 'keyword'})

        # Verify other values did not change.
        eq_(field['permissions_needed'], ['view_nothing'])
        eq_(field['in_database_name'], 'super_field')
        eq_(field['namespace'], 'superspace')

        # Test errors.
        assert_raises(
            MissingArgumentError,
            self.api.update_field,
        )  # `name` is missing

        assert_raises(
            ResourceNotFound,
            self.api.update_field,
            name='unkownfield',
        )

    def test_delete_field(self):
        es = self.storage.es
        config = self.get_config_context()

        self.api.delete_field(name='product')

        ok_(
            es.get(
                index=config.webapi.elasticsearch_default_index,
                doc_type='supersearch_fields',
                id='signature',
            )
        )
        assert_raises(
            pyelasticsearch.exceptions.ElasticHttpNotFoundError,
            es.get,
            index=config.webapi.elasticsearch_default_index,
            doc_type='supersearch_fields',
            id='product',
        )

    def test_get_missing_fields(self):
        config = self.get_config_context(
            es_index='socorro_integration_test_%W'
        )

        fake_mappings = [
            {
                'mappings': {
                    config.elasticsearch_doctype: {
                        'properties': {
                            # Add a bunch of unknown fields.
                            'field_z': {
                                'type': 'string'
                            },
                            'namespace1': {
                                'type': 'object',
                                'properties': {
                                    'field_a': {
                                        'type': 'string'
                                    },
                                    'field_b': {
                                        'type': 'long'
                                    }
                                }
                            },
                            'namespace2': {
                                'type': 'object',
                                'properties': {
                                    'subspace1': {
                                        'type': 'object',
                                        'properties': {
                                            'field_b': {
                                                'type': 'long'
                                            }
                                        }
                                    }
                                }
                            },
                            # Add a few known fields that should not appear.
                            'processed_crash': {
                                'type': 'object',
                                'properties': {
                                    'signature': {
                                        'type': 'string'
                                    },
                                    'product': {
                                        'type': 'string'
                                    },
                                }
                            }
                        }
                    }
                }
            },
            {
                'mappings': {
                    config.elasticsearch_doctype: {
                        'properties': {
                            'namespace1': {
                                'type': 'object',
                                'properties': {
                                    'subspace1': {
                                        'type': 'object',
                                        'properties': {
                                            'field_d': {
                                                'type': 'long'
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
        ]

        storage = crashstorage.ElasticSearchCrashStorage(config)
        now = datetimeutil.utc_now()
        indices = []

        try:
            # Using "2" here means that an index will be missing, hence testing
            # that it swallows the subsequent error.
            for i in range(2):
                date = now - datetime.timedelta(weeks=i)
                index = storage.get_index_for_crash(date)
                mapping = fake_mappings[i % len(fake_mappings)]

                storage.create_index(index, mapping)
                indices.append(index)

            api = SuperSearch(config=config)
            missing_fields = api.get_missing_fields()
            expected = [
                'field_z',
                'namespace1.field_a',
                'namespace1.field_b',
                'namespace1.subspace1.field_d',
                'namespace2.subspace1.field_b',
            ]

            eq_(missing_fields['hits'], expected)
            eq_(missing_fields['total'], 5)

        finally:
            for index in indices:
                storage.es.delete_index(index=index)

    def test_get_mapping(self):
        mapping = self.api.get_mapping()['mappings']
        doctype = self.api.config.elasticsearch_doctype

        ok_(doctype in mapping)
        properties = mapping[doctype]['properties']

        ok_('processed_crash' in properties)
        ok_('raw_crash' in properties)

        processed_crash = properties['processed_crash']['properties']

        # Check in_database_name is used.
        ok_('os_name' in processed_crash)
        ok_('platform' not in processed_crash)

        # Those fields have no `storage_mapping`.
        ok_('fake_field' not in properties['raw_crash']['properties'])

        # Those fields have a `storage_mapping`.
        eq_(processed_crash['release_channel'], {'type': 'string'})

        # Test nested objects.
        ok_('json_dump' in processed_crash)
        ok_('properties' in processed_crash['json_dump'])
        ok_('write_combine_size' in processed_crash['json_dump']['properties'])
        eq_(
            processed_crash['json_dump']['properties']['write_combine_size'],
            {'type': 'long'}
        )

        # Test overwriting a field.
        mapping = self.api.get_mapping(overwrite_mapping={
            'name': 'fake_field',
            'storage_mapping': {
                'type': 'long'
            }
        })['mappings']
        properties = mapping[doctype]['properties']

        ok_('fake_field' in properties['raw_crash']['properties'])
        eq_(
            properties['raw_crash']['properties']['fake_field']['type'],
            'long'
        )

    def test_test_mapping(self):
        """Much test. So meta. Wow test_test_. """
        # First test a valid mapping.
        mapping = self.api.get_mapping()
        ok_(self.api.test_mapping(mapping) is None)

        # Insert an invalid storage mapping.
        mapping = self.api.get_mapping({
            'name': 'fake_field',
            'storage_mapping': {
                'type': 'unkwown'
            }
        })
        assert_raises(
            pyelasticsearch.exceptions.ElasticHttpError,
            self.api.test_mapping,
            mapping,
        )

        # Test with a correct mapping but with data that cannot be indexed.
        self.storage.save_processed({
            'uuid': '1234567890',
            'date_processed': datetimeutil.utc_now(),
            'product': 'WaterWolf',
        })
        mapping = self.api.get_mapping({
            'name': 'product',
            'storage_mapping': {
                'type': 'long'
            }
        })
        assert_raises(
            pyelasticsearch.exceptions.ElasticHttpError,
            self.api.test_mapping,
            mapping,
        )
