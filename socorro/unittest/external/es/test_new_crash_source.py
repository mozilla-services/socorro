import datetime
from copy import deepcopy

from nose.tools import eq_

from socorro.lib.datetimeutil import utc_now
from socorro.external.es.new_crash_source import ESNewCrashSource
from socorro.unittest.external.es.base import ElasticsearchTestCase


# A dummy crash report that is used for testing.
a_processed_crash = {
    'addons': [['{1a5dabbd-0e74-41da-b532-a364bb552cab}', '1.0.4.1']],
    'addons_checked': None,
    'address': '0x1c',
    'app_notes': '...',
    'build': '20120309050057',
    'client_crash_date': '2012-04-08T10:52:42+00:00',
    'completeddatetime': '2012-04-08T10:56:50.902884+00:00',
    'cpu_info': 'None | 0',
    'cpu_name': 'arm',
    'crashedThread': 8,
    'date_processed': '2012-04-08T10:56:41.558922+00:00',
    'distributor': None,
    'distributor_version': None,
    'dump': '...',
    'email': 'bogus@bogus.com',
    'flash_version': '[blank]',
    'hangid': None,
    'id': 361399767,
    # 'json_dump': {
    #     'things': 'stackwalker output',
    # },
    'install_age': 22385,
    'last_crash': None,
    'os_name': 'Linux',
    'os_version': '0.0.0 Linux 2.6.35.7-perf-CL727859 #1 ',
    'processor_notes': 'SignatureTool: signature truncated due to length',
    'process_type': 'plugin',
    'product': 'FennecAndroid',
    'PluginFilename': 'dwight.txt',
    'PluginName': 'wilma',
    'PluginVersion': '69',
    'reason': 'SIGSEGV',
    'release_channel': 'default',
    'ReleaseChannel': 'default',
    'signature': 'libxul.so@0x117441c',
    'started_datetime': '2012-04-08T10:56:50.440752+00:00',
    'startedDateTime': '2012-04-08T10:56:50.440752+00:00',
    'success': True,
    'topmost_filenames': [],
    'truncated': False,
    'uptime': 170,
    'url': 'http://embarasing.porn.com',
    'user_comments': None,
    'user_id': None,
    'uuid': '936ce666-ff3b-4c7a-9674-367fe2120408',
    'version': '13.0a1',
    'upload_file_minidump_flash1': {
        'things': 'untouched',
        'json_dump': 'stackwalker output',
    },
    'upload_file_minidump_flash2': {
        'things': 'untouched',
        'json_dump': 'stackwalker output',
    },
    'upload_file_minidump_browser': {
        'things': 'untouched',
        'json_dump': 'stackwalker output',
    },
}

a_processed_crash['date_processed'] = utc_now().isoformat()

a_firefox_processed_crash = deepcopy(a_processed_crash)
a_firefox_processed_crash['product'] = 'Firefox'
a_firefox_processed_crash['version'] = '43.0.1'
a_firefox_processed_crash['uuid'] = '825bc666-ff3b-4c7a-9674-367fe1019397'
a_firefox_processed_crash['date_processed'] = utc_now().isoformat()

a_raw_crash = {
    'foo': 'alpha',
    'bar': 42
}


# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)


class IntegrationTestESNewCrashSource(ElasticsearchTestCase):

    def __init__(self, *args, **kwargs):
        super(IntegrationTestESNewCrashSource, self).__init__(*args, **kwargs)

        self.config = self.get_tuned_config(ESNewCrashSource)

    def test_no_new_crashes(self):
        new_crash_source = ESNewCrashSource(self.config)
        self.health_check()

        generator = new_crash_source.new_crashes(
            utc_now() - datetime.timedelta(days=1),
            'Firefox',
            ['43.0.1']
        )
        eq_(list(generator), [])

        self.index_crash(
            a_processed_crash,
            raw_crash=a_raw_crash,
            crash_id=a_processed_crash['uuid']
        )
        self.refresh_index()

        # Same test now that there is a processed crash in there
        # but notably under a different name and version.
        generator = new_crash_source.new_crashes(
            utc_now() - datetime.timedelta(days=1),
            'Firefox',
            ['43.0.1']
        )
        eq_(list(generator), [])

    def test_new_crashes(self):
        new_crash_source = ESNewCrashSource(self.config)
        self.index_crash(
            a_processed_crash,
            raw_crash=a_raw_crash,
            crash_id=a_processed_crash['uuid']
        )
        self.index_crash(
            a_firefox_processed_crash,
            raw_crash=a_raw_crash,
            crash_id=a_firefox_processed_crash['uuid']
        )
        other_firefox_processed_crash = deepcopy(a_firefox_processed_crash)
        other_firefox_processed_crash['uuid'] = (
            other_firefox_processed_crash['uuid'].replace('a', 'e')
        )
        other_firefox_processed_crash['date_processed'] = (
            utc_now() - datetime.timedelta(days=1)
        )
        self.index_crash(
            other_firefox_processed_crash,
            raw_crash=a_raw_crash,
            crash_id=other_firefox_processed_crash['uuid']
        )
        self.refresh_index()

        assert self.connection.get(
            index=self.config.elasticsearch.elasticsearch_index,
            id=a_processed_crash['uuid']
        )
        assert self.connection.get(
            index=self.config.elasticsearch.elasticsearch_index,
            id=a_firefox_processed_crash['uuid']
        )

        # same test now that there is a processed crash in there
        generator = new_crash_source.new_crashes(
            utc_now() - datetime.timedelta(days=1),
            'Firefox',
            ['43.0.1']
        )
        eq_(list(generator), [a_firefox_processed_crash['uuid']])
