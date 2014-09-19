# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.plugins.attrib import attr
from nose.tools import eq_, ok_

from socorro.external.elasticsearch import crashstorage
from socorro.external.elasticsearch.supersearch import SuperSearch
from socorro.lib.datetimeutil import utc_now
from .unittestbase import ElasticSearchTestCase
from .test_supersearch import (
    SUPERSEARCH_FIELDS
)

# Remove debugging noise during development
# import logging
# logging.getLogger('pyelasticsearch').setLevel(logging.ERROR)
# logging.getLogger('elasticutils').setLevel(logging.ERROR)
# logging.getLogger('requests.packages.urllib3.connectionpool')\
#        .setLevel(logging.ERROR)


EXAMPLE_DUMP = '''OS|Windows NT|6.1.7601 Service Pack 1
CPU|x86|GenuineIntel family 6 model 15 stepping 13|2
Crash|EXCEPTION_BREAKPOINT|0x76f570f4|0
Module|plugin-container.exe|26.0.0.5087|plugin-container.pdb
'''


@attr(integration='elasticsearch')  # for nosetests
class IntegrationTestSettings(ElasticSearchTestCase):
    """Test the settings and mappings used in elasticsearch, through
    the supersearch service. """

    def setUp(self):
        super(IntegrationTestSettings, self).setUp()

        config = self.get_config_context()
        self.storage = crashstorage.ElasticSearchCrashStorage(config)

        # clear the indices cache so the index is created on every test
        self.storage.indices_cache = set()

        self.now = utc_now()

        # Create the supersearch fields.
        self.storage.es.bulk_index(
            index=config.webapi.elasticsearch_default_index,
            doc_type='supersearch_fields',
            docs=SUPERSEARCH_FIELDS.values(),
            id_field='name',
            refresh=True,
        )

        # Create the index that will be used.
        es_index = self.storage.get_index_for_crash(self.now)
        self.storage.create_socorro_index(es_index)

        self.api = SuperSearch(config=config)

    def tearDown(self):
        # clear the test index
        config = self.get_config_context()
        self.storage.es.delete_index(config.webapi.elasticsearch_index)
        self.storage.es.delete_index(config.webapi.elasticsearch_default_index)

        super(IntegrationTestSettings, self).tearDown()

    def test_dump_field(self):
        """Verify that the 'dump' field can be queried as expected. """
        # Index some data.
        processed_crash = {
            'uuid': '06a0c9b5-0381-42ce-855a-ccaaa2120100',
            'date_processed': self.now,
            'dump': EXAMPLE_DUMP,
        }
        self.storage.save_processed(processed_crash)
        self.storage.es.refresh()

        # Simple test with one word, no upper case.
        res = self.api.get(dump='~family')
        eq_(res['total'], 1)

        # Several words, with upper case.
        res = self.api.get(dump='~Windows NT')
        eq_(res['total'], 1)

    def test_cpu_info_field(self):
        """Verify that the 'cpu_info' field can be queried as expected. """
        processed_crash = {
            'uuid': '06a0c9b5-0381-42ce-855a-ccaaa2120101',
            'date_processed': self.now,
            'cpu_info': 'GenuineIntel family 6 model 15 stepping 13',
        }
        self.storage.save_processed(processed_crash)
        self.storage.es.refresh()

        # Simple test with one word, no upper case.
        res = self.api.get(cpu_info='~model')
        eq_(res['total'], 1)
        ok_('model' in res['hits'][0]['cpu_info'])

        # Several words, with upper case, 'starts with' mode.
        res = self.api.get(cpu_info='$GenuineIntel family')
        eq_(res['total'], 1)
        ok_('GenuineIntel family' in res['hits'][0]['cpu_info'])

    def test_dom_ipc_enabled_field(self):
        """Verify that the 'dom_ipc_enabled' field can be queried as
        expected. """
        processed_crash = {
            'uuid': '06a0c9b5-0381-42ce-855a-ccaaa2120101',
            'date_processed': self.now,
        }
        raw_crash = {
            'DOMIPCEnabled': True,
        }
        self.storage.save_raw_and_processed(
            raw_crash, None, processed_crash, processed_crash['uuid']
        )
        processed_crash = {
            'uuid': '06a0c9b5-0381-42ce-855a-ccaaa2120102',
            'date_processed': self.now,
        }
        raw_crash = {
            'DOMIPCEnabled': False,
        }
        self.storage.save_raw_and_processed(
            raw_crash, None, processed_crash, processed_crash['uuid']
        )
        processed_crash = {
            'uuid': '06a0c9b5-0381-42ce-855a-ccaaa2120103',
            'date_processed': self.now,
        }
        raw_crash = {
            'DOMIPCEnabled': None,
        }
        self.storage.save_raw_and_processed(
            raw_crash, None, processed_crash, processed_crash['uuid']
        )
        self.storage.es.refresh()

        res = self.api.get(dom_ipc_enabled='true')
        eq_(res['total'], 1)
        ok_(res['hits'][0]['dom_ipc_enabled'])

        res = self.api.get(dom_ipc_enabled='false')
        eq_(res['total'], 2)

    def test_platform_field(self):
        """Verify that the 'platform' field can be queried as expected. """
        processed_crash = {
            'uuid': '06a0c9b5-0381-42ce-855a-ccaaa2120102',
            'date_processed': self.now,
            'os_name': 'Mac OS X',
        }
        self.storage.save_processed(processed_crash)
        self.storage.es.refresh()

        # Testing the phrase mode, when a term query contains white spaces.
        res = self.api.get(platform='Mac OS X')
        eq_(res['total'], 1)
        eq_(res['hits'][0]['platform'], 'Mac OS X')

    def test_app_notes_field(self):
        """Verify that the 'app_notes' field can be queried as expected. """
        processed_crash = {
            'uuid': '06a0c9b5-0381-42ce-855a-ccaaa2120103',
            'date_processed': self.now,
            'app_notes': 'there is a cycle collector fault here',
        }
        self.storage.save_processed(processed_crash)
        self.storage.es.refresh()

        # Testing the phrase mode, when a term query contains white spaces.
        res = self.api.get(app_notes='cycle collector fault')
        eq_(res['total'], 1)
        ok_('cycle collector fault' in res['hits'][0]['app_notes'])

    def test_process_type_field(self):
        """Verify that the 'process_type' field can be queried as expected. """
        processed_crash = {
            'uuid': '06a0c9b5-0381-42ce-855a-ccaaa2120100',
            'date_processed': self.now,
            'process_type': 'plugin',
        }
        self.storage.save_processed(processed_crash)
        processed_crash = {
            'uuid': '06a0c9b5-0381-42ce-855a-ccaaa2120101',
            'date_processed': self.now,
            'process_type': None,
        }
        self.storage.save_processed(processed_crash)
        self.storage.es.refresh()

        res = self.api.get(process_type='plugin')
        eq_(res['total'], 1)
        ok_('plugin' in res['hits'][0]['process_type'])

        res = self.api.get(process_type='browser')
        eq_(res['total'], 1)
        # In the case of a 'browser' crash, the process_type is None and thus
        # is not returned.
        ok_('process_type' not in res['hits'][0])

        res = self.api.get(process_type='!browser')
        eq_(res['total'], 1)
        ok_('plugin' in res['hits'][0]['process_type'])

        res = self.api.get(process_type=['plugin', 'browser'])
        eq_(res['total'], 2)

    def test_hang_type_field(self):
        """Verify that the 'hang_type' field can be queried as expected. """
        processed_crash = {
            'uuid': '06a0c9b5-0381-42ce-855a-ccaaa2120100',
            'date_processed': self.now,
            'hang_type': 0,
        }
        self.storage.save_processed(processed_crash)
        processed_crash = {
            'uuid': '06a0c9b5-0381-42ce-855a-ccaaa2120101',
            'date_processed': self.now,
            'hang_type': 1,
        }
        self.storage.save_processed(processed_crash)
        self.storage.es.refresh()

        res = self.api.get(hang_type='hang')
        eq_(res['total'], 1)
        eq_(res['hits'][0]['hang_type'], 1)

        res = self.api.get(hang_type='crash')
        eq_(res['total'], 1)
        eq_(res['hits'][0]['hang_type'], 0)

        res = self.api.get(hang_type='!crash')
        eq_(res['total'], 1)
        eq_(res['hits'][0]['hang_type'], 1)

        res = self.api.get(hang_type=['crash', 'hang'])
        eq_(res['total'], 2)

    def test_exploitability_field(self):
        """Verify that the 'exploitability' field can be queried as expected.
        """
        processed_crash = {
            'uuid': '06a0c9b5-0381-42ce-855a-ccaaa2120100',
            'date_processed': self.now,
            'exploitability': 'high',
        }
        self.storage.save_processed(processed_crash)
        processed_crash = {
            'uuid': '06a0c9b5-0381-42ce-855a-ccaaa2120101',
            'date_processed': self.now,
            'exploitability': 'unknown',
        }
        self.storage.save_processed(processed_crash)
        self.storage.es.refresh()

        res = self.api.get(exploitability='high')
        eq_(res['total'], 1)
        eq_(res['hits'][0]['exploitability'], 'high')

        res = self.api.get(exploitability='unknown')
        eq_(res['total'], 1)
        eq_(res['hits'][0]['exploitability'], 'unknown')

        res = self.api.get(exploitability=['high', 'unknown'])
        eq_(res['total'], 2)

    def test_platform_version_field(self):
        """Verify that the 'platform_version' field can be queried as expected.
        """
        processed_crash = {
            'uuid': '06a0c9b5-0381-42ce-855a-ccaaa2120100',
            'date_processed': self.now,
            'os_version': '6.0.001',
        }
        self.storage.save_processed(processed_crash)
        processed_crash = {
            'uuid': '06a0c9b5-0381-42ce-855a-ccaaa2120101',
            'date_processed': self.now,
            'os_version': '6.0.001 Service Pack 1',
        }
        self.storage.save_processed(processed_crash)
        self.storage.es.refresh()

        res = self.api.get(platform_version='6.0.001')
        eq_(res['total'], 2)
        ok_('6.0.001' in res['hits'][0]['platform_version'])
        ok_('6.0.001' in res['hits'][1]['platform_version'])

        res = self.api.get(platform_version='6.0.001 Service Pack 1')
        eq_(res['total'], 1)
        eq_(res['hits'][0]['platform_version'], '6.0.001 Service Pack 1')

        res = self.api.get(platform_version='$6.0')
        eq_(res['total'], 2)
        ok_('6.0' in res['hits'][0]['platform_version'])
        ok_('6.0' in res['hits'][1]['platform_version'])
