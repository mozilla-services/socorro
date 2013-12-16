# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import time
from nose.plugins.attrib import attr

from socorro.external.elasticsearch import crashstorage
from socorro.external.elasticsearch.supersearch import SuperSearch
from socorro.lib.datetimeutil import utc_now
from .unittestbase import ElasticSearchTestCase

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

        with self.get_config_manager().context() as config:
            self.storage = crashstorage.ElasticSearchCrashStorage(config)
            self.api = SuperSearch(config)

            # clear the indices cache so the index is created on every test
            self.storage.indices_cache = set()

        self.now = utc_now()

        # Create the index that will be used.
        es_index = self.storage.get_index_for_crash(self.now)
        self.storage.create_socorro_index(es_index)

        # This an ugly hack to give elasticsearch some time to finish creating
        # the new index. It is needed for jenkins only, because we have a
        # special case here where we index only one or two documents before
        # querying. Other tests are not affected.
        # TODO: try to remove it, or at least understand why it is needed.
        time.sleep(1)

    def tearDown(self):
        # clear the test index
        with self.get_config_manager().context() as config:
            self.storage.es.delete_index(config.webapi.elasticsearch_index)

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
        self.assertEqual(res['total'], 1)

        # Several words, with upper case.
        res = self.api.get(dump='~Windows NT')
        self.assertEqual(res['total'], 1)

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
        self.assertEqual(res['total'], 1)
        self.assertTrue('model' in res['hits'][0]['cpu_info'])

        # Several words, with upper case, 'starts with' mode.
        res = self.api.get(cpu_info='$GenuineIntel family')
        self.assertEqual(res['total'], 1)
        self.assertTrue('GenuineIntel family' in res['hits'][0]['cpu_info'])
