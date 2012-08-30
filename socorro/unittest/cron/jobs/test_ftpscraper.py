# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import datetime
from functools import wraps
from cStringIO import StringIO
import mock
import psycopg2
from nose.plugins.attrib import attr
from socorro.cron import crontabber
from socorro.lib.datetimeutil import utc_now
from socorro.cron.jobs import ftpscraper
from ..base import TestCaseBase, DSN


def stringioify(func):
    @wraps(func)
    def wrapper(*a, **k):
        return StringIO(func(*a, **k))
    return wrapper


#==============================================================================
class TestFTPScraper(TestCaseBase):

    def setUp(self):
        super(TestFTPScraper, self).setUp()
        self.psycopg2_patcher = mock.patch('psycopg2.connect')
        self.psycopg2 = self.psycopg2_patcher.start()
        self.urllib2_patcher = mock.patch('urllib2.urlopen')
        self.urllib2 = self.urllib2_patcher.start()

    def tearDown(self):
        super(TestFTPScraper, self).tearDown()
        self.psycopg2_patcher.stop()
        self.urllib2_patcher.stop()

    def test_urljoin(self):
        self.assertEqual(
            ftpscraper.urljoin('http://google.com', '/page.html'),
            'http://google.com/page.html'
        )
        self.assertEqual(
            ftpscraper.urljoin('http://google.com/', '/page.html'),
            'http://google.com/page.html'
        )
        self.assertEqual(
            ftpscraper.urljoin('http://google.com/', 'page.html'),
            'http://google.com/page.html'
        )
        self.assertEqual(
            ftpscraper.urljoin('http://google.com', 'page.html'),
            'http://google.com/page.html'
        )
        self.assertEqual(
            ftpscraper.urljoin('http://google.com', 'dir1', ''),
            'http://google.com/dir1/'
        )

    def test_getLinks(self):
        @stringioify
        def mocked_urlopener(url):
            html_wrap = "<html><body>\n%s\n</body></html>"
            if 'ONE' in url:
                return html_wrap % """
                <a href='One.html'>One.html</a>
                """
            raise NotImplementedError(url)

        self.urllib2.side_effect = mocked_urlopener
        self.assertEqual(
            ftpscraper.getLinks('ONE'),
            []
        )
        self.assertEqual(
            ftpscraper.getLinks('ONE', startswith='One'),
            ['One.html']
        )
        self.assertEqual(
            ftpscraper.getLinks('ONE', endswith='.html'),
            ['One.html']
        )
        self.assertEqual(
            ftpscraper.getLinks('ONE', startswith='Two'),
            []
        )

    def test_parseInfoFile(self):
        @stringioify
        def mocked_urlopener(url):
            if 'ONE' in url:
                return 'BUILDID=123'
            if 'TWO' in url:
                return 'BUILDID=123\nbuildID=456'
            if 'THREE' in url:
                return '123\nhttp://hg.mozilla.org/123'
            if 'FOUR' in url:
                return ('123\nhttp://hg.mozilla.org/123\n'
                        'http://git.mozilla.org/123')
            raise NotImplementedError(url)
        self.urllib2.side_effect = mocked_urlopener

        self.assertEqual(
            ftpscraper.parseInfoFile('ONE'),
            {'BUILDID': '123'}
        )
        self.assertEqual(
            ftpscraper.parseInfoFile('TWO'),
            {'BUILDID': '123',
             'buildID': '456'}
        )
        self.assertEqual(
            ftpscraper.parseInfoFile('THREE', nightly=True),
            {'buildID': '123',
             'rev': 'http://hg.mozilla.org/123'}
        )
        self.assertEqual(
            ftpscraper.parseInfoFile('FOUR', nightly=True),
            {'buildID': '123',
             'rev': 'http://hg.mozilla.org/123',
             'altrev': 'http://git.mozilla.org/123'}
        )

    def test_getRelease(self):
        @stringioify
        def mocked_urlopener(url):
            html_wrap = "<html><body>\n%s\n</body></html>"
            if 'linux_info.txt' in url:
                return 'BUILDID=123'
            if 'build-11' in url:
                return html_wrap % """
                <a href="linux_info.txt">l</a>
                """
            if 'ONE' in url:
                return html_wrap % """
                <a href="build-10/">build-10</a>
                <a href="build-11/">build-11</a>
                """
            if 'TWO' in url:
                return html_wrap % """
                <a href="ignore/">ignore</a>
                """
            raise NotImplementedError(url)

        self.urllib2.side_effect = mocked_urlopener

        self.assertEqual(
            list(ftpscraper.getRelease('TWO', 'http://x')),
            []
        )
        self.assertEqual(
            list(ftpscraper.getRelease('ONE', 'http://x')),
            [('linux', 'ONE', 'build-11', {'BUILDID': '123'})]
        )

    def test_getNightly(self):
        @stringioify
        def mocked_urlopener(url):
            html_wrap = "<html><body>\n%s\n</body></html>"
            if '.linux.txt' in url:
                return '123\nhttp://hg.mozilla.org/123'
            if 'ONE' in url:
                return html_wrap % """
                <a href="firefox.en-US.linux.txt">l</a>
                <a href="firefox.multi.linux.txt">l</a>
                """
            if 'ONE' in url:
                return html_wrap % """
                <a href="build-10/">build-10</a>
                <a href="build-11/">build-11</a>
                """
            if 'TWO' in url:
                return html_wrap % """
                <a href="ignore/">ignore</a>
                """
            raise NotImplementedError(url)

        self.urllib2.side_effect = mocked_urlopener

        self.assertEqual(
            list(ftpscraper.getNightly('TWO', 'http://x')),
            []
        )
        self.assertEqual(
            list(ftpscraper.getNightly('ONE', 'http://x')),
            [('linux', 'ONE', 'firefox',
              {'buildID': '123', 'rev': 'http://hg.mozilla.org/123'}),
             ('linux', 'ONE', 'firefox',
              {'buildID': '123', 'rev': 'http://hg.mozilla.org/123'})]
        )


#==============================================================================
@attr(integration='postgres')  # for nosetests
class TestIntegrationFTPScraper(TestCaseBase):

    def setUp(self):
        super(TestIntegrationFTPScraper, self).setUp()
        # prep a fake table
        assert 'test' in DSN['database.database_name']
        dsn = ('host=%(database.database_host)s '
               'dbname=%(database.database_name)s '
               'user=%(database.database_user)s '
               'password=%(database.database_password)s' % DSN)
        self.conn = psycopg2.connect(dsn)

        cursor = self.conn.cursor()

        # Insert data
        now = utc_now()
        build_date = now - datetime.timedelta(days=30)
        sunset_date = now + datetime.timedelta(days=30)

        cursor.execute("""
            TRUNCATE products CASCADE;
            INSERT INTO products
            (product_name, sort, release_name)
            VALUES
            (
            'Firefox',
            1,
            'firefox'
            );
        """)

        cursor.execute("""
            TRUNCATE product_versions CASCADE;
            INSERT INTO product_versions
            (product_version_id, product_name, major_version, release_version,
            version_string, version_sort, build_date, sunset_date,
            featured_version, build_type)
            VALUES
            (
                1,
                'Firefox',
                '15.0',
                '15.0',
                '15.0a1',
                '000000150a1',
                '%(build_date)s',
                '%(sunset_date)s',
                't',
                'Nightly'
            );
        """ % {"build_date": build_date, "sunset_date": sunset_date})

        cursor.execute("""
            TRUNCATE release_channels CASCADE;
            INSERT INTO release_channels
            (release_channel, sort)
            VALUES
            ('Nightly', 1),
            ('Aurora', 2),
            ('Beta', 3),
            ('Release', 4);
        """)

        cursor.execute("""
            TRUNCATE product_release_channels CASCADE;
            INSERT INTO product_release_channels
            (product_name, release_channel, throttle)
            VALUES
            ('Firefox', 'Nightly', 1),
            ('Firefox', 'Aurora', 1),
            ('Firefox', 'Beta', 1),
            ('Firefox', 'Release', 1);
        """)

        cursor.execute('select count(*) from crontabber_state')
        if cursor.fetchone()[0] < 1:
            cursor.execute("""
            INSERT INTO crontabber_state (state, last_updated)
            VALUES ('{}', NOW());
            """)
        else:
            cursor.execute("""
            UPDATE crontabber_state SET state='{}';
            """)
        self.conn.commit()
        self.urllib2_patcher = mock.patch('urllib2.urlopen')
        self.urllib2 = self.urllib2_patcher.start()

    def tearDown(self):
        super(TestIntegrationFTPScraper, self).tearDown()
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE crontabber_state SET state='{}';
            TRUNCATE TABLE releases_raw CASCADE;
            TRUNCATE product_versions CASCADE;
            TRUNCATE products CASCADE;
            TRUNCATE releases_raw CASCADE;
            TRUNCATE release_channels CASCADE;
            TRUNCATE product_release_channels CASCADE;
        """)
        self.conn.commit()
        self.urllib2_patcher.stop()

    def _setup_config_manager(self):
        _super = super(TestIntegrationFTPScraper, self)._setup_config_manager
        config_manager, json_file = _super(
          'socorro.cron.jobs.ftpscraper.FTPScraperCronApp|1d',
          extra_value_source={
            'crontabber.class-FTPScraperCronApp.products': 'firefox',
          }
        )
        return config_manager, json_file

    def test_basic_run(self):

        @stringioify
        def mocked_urlopener(url, today=None):
            if today is None:
                today = utc_now()
            html_wrap = "<html><body>\n%s\n</body></html>"
            if url.endswith('/firefox/'):
                return html_wrap % """
                <a href="candidates/">candidates</a>
                <a href="nightly/">nightly</a>
                """
            if url.endswith('/firefox/nightly/'):
                return html_wrap % """
                <a href="10.0-candidates/">10.0-candidiates</a>
                """
            if url.endswith('/firefox/candidates/'):
                return html_wrap % """
                <a href="10.0b4-candidates/">10.0b4-candidiates</a>
                """
            if (url.endswith('/firefox/nightly/10.0-candidates/') or
                url.endswith('/firefox/candidates/10.0b4-candidates/')):
                return html_wrap % """
                <a href="build1/">build1</a>
                """
            if (url.endswith('/firefox/nightly/10.0-candidates/build1/') or
                url.endswith('/firefox/candidates/10.0b4-candidates/build1/')):
                return html_wrap % """
                <a href="linux_info.txt">linux_info.txt</a>
                """
            if url.endswith(today.strftime('/firefox/nightly/%Y/%m/')):
                return html_wrap % today.strftime("""
                <a href="%Y-%m-%d-trunk/">%Y-%m-%d-trunk</a>
                """)
            if url.endswith(today.strftime(
              '/firefox/nightly/%Y/%m/%Y-%m-%d-trunk/')):
                return html_wrap % """
                <a href="mozilla-nightly-15.0a1.en-US.linux-x86_64.txt">txt</a>
                <a href="mozilla-nightly-15.0a2.en-US.linux-x86_64.txt">txt</a>
                """
            if url.endswith(today.strftime(
              '/firefox/nightly/%Y/%m/%Y-%m-%d-trunk/mozilla-nightly-15.0a1.en'
              '-US.linux-x86_64.txt')):
                return (
                   "20120505030510\n"
                   "http://hg.mozilla.org/mozilla-central/rev/0a48e6561534"
                )
            if url.endswith(today.strftime(
              '/firefox/nightly/%Y/%m/%Y-%m-%d-trunk/mozilla-nightly-15.0a2.en'
              '-US.linux-x86_64.txt')):
                return (
                   "20120505443322\n"
                   "http://hg.mozilla.org/mozilla-central/rev/xxx123"
                )
            if url.endswith(
              '/firefox/nightly/10.0-candidates/build1/linux_info.txt'):
                return "buildID=20120516113045"
            if url.endswith(
              '/firefox/candidates/10.0b4-candidates/build1/linux_info.txt'):
                return "buildID=20120516114455"

            # bad testing boy!
            raise NotImplementedError(url)

        self.urllib2.side_effect = mocked_urlopener

        config_manager, json_file = self._setup_config_manager()
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))
            assert information['ftpscraper']
            assert not information['ftpscraper']['last_error']
            assert information['ftpscraper']['last_success']

        cursor = self.conn.cursor()

        columns = 'product_name', 'build_id', 'build_type'
        cursor.execute("""
        select %s
        from releases_raw
        """ % ','.join(columns)
        )
        builds = [dict(zip(columns, row)) for row in cursor.fetchall()]
        build_ids = dict((str(x['build_id']), x) for x in builds)
        self.assertTrue('20120516114455' in build_ids)
        self.assertTrue('20120516113045' in build_ids)
        self.assertTrue('20120505030510' in build_ids)
        self.assertTrue('20120505443322' in build_ids)
        assert len(build_ids) == 4
        self.assertEqual(build_ids['20120516114455']['build_type'],
                         'Beta')
        self.assertEqual(build_ids['20120516113045']['build_type'],
                         'Release')
        self.assertEqual(build_ids['20120505030510']['build_type'],
                         'Nightly')
        self.assertEqual(build_ids['20120505443322']['build_type'],
                         'Aurora')

        # just one more time, pretend that we run it immediately again
        cursor.execute('select count(*) from releases_raw')
        count_before, = cursor.fetchall()[0]
        assert count_before == 4, count_before

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))
            assert information['ftpscraper']
            assert not information['ftpscraper']['last_error']
            assert information['ftpscraper']['last_success']

        cursor.execute('select count(*) from releases_raw')
        count_after, = cursor.fetchall()[0]
        assert count_after == count_before, count_before
