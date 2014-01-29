# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import urllib2
from functools import wraps
from cStringIO import StringIO
import mock
from nose.plugins.attrib import attr
from socorro.cron import crontabber
from socorro.lib.datetimeutil import utc_now
from socorro.cron.jobs import ftpscraper
from ..base import TestCaseBase, IntegrationTestCaseBase


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

    @mock.patch('socorro.cron.jobs.ftpscraper.time')
    def test_patient_urlopen(self, mocked_time):

        sleeps = []

        def mocked_sleeper(seconds):
            sleeps.append(seconds)

        mocked_time.sleep = mocked_sleeper

        mock_calls = []

        @stringioify
        def mocked_urlopener(url):
            mock_calls.append(url)
            if len(mock_calls) == 1:
                raise urllib2.HTTPError(url, 500, "Server Error", {}, None)
            if len(mock_calls) == 2:
                raise urllib2.HTTPError(url, 504, "Timeout", {}, None)
            if len(mock_calls) == 3:
                raise urllib2.URLError("BadStatusLine")

            return "<html>content</html>"

        self.urllib2.side_effect = mocked_urlopener
        content = ftpscraper.patient_urlopen(
            'http://doesntmatt.er',
            sleep_time=25
        )
        self.assertEqual(content, "<html>content</html>")
        self.assertEqual(sleeps, [25, 25, 25])

    @mock.patch('socorro.cron.jobs.ftpscraper.time')
    def test_patient_urlopen_impatient_retriederror(self, mocked_time):

        sleeps = []

        def mocked_sleeper(seconds):
            sleeps.append(seconds)

        mock_calls = []

        @stringioify
        def mocked_urlopener(url):
            mock_calls.append(url)
            if len(mock_calls) == 1:
                raise urllib2.HTTPError(url, 500, "Server Error", {}, None)
            if len(mock_calls) == 2:
                raise urllib2.HTTPError(url, 504, "Timeout", {}, None)
            if len(mock_calls) == 3:
                raise urllib2.URLError("BadStatusLine")

            return "<html>content</html>"

        self.urllib2.side_effect = mocked_urlopener
        # very impatient version
        self.assertRaises(
            ftpscraper.RetriedError,
            ftpscraper.patient_urlopen,
            'http://doesntmatt.er',
            max_attempts=1
        )
        self.assertEqual(len(mock_calls), 1)

        # less impatient
        mock_calls = []
        self.assertRaises(
            ftpscraper.RetriedError,
            ftpscraper.patient_urlopen,
            'http://doesntmatt.er',
            max_attempts=2
        )
        self.assertEqual(len(mock_calls), 2)

    @mock.patch('socorro.cron.jobs.ftpscraper.time')
    def test_patient_urlopen_some_raise_errors(self, mocked_time):

        sleeps = []

        def mocked_sleeper(seconds):
            sleeps.append(seconds)

        mocked_time.sleep = mocked_sleeper

        mock_calls = []

        @stringioify
        def mocked_urlopener(url):
            mock_calls.append(url)
            if len(mock_calls) == 1:
                raise urllib2.HTTPError(url, 500, "Server Error", {}, None)
            raise urllib2.HTTPError(url, 400, "Bad Request", {}, None)

        self.urllib2.side_effect = mocked_urlopener
        # very impatient version
        self.assertRaises(
            urllib2.HTTPError,
            ftpscraper.patient_urlopen,
            'http://doesntmatt.er',
        )

    def test_patient_urlopen_pass_404_errors(self):
        mock_calls = []

        @stringioify
        def mocked_urlopener(url):
            mock_calls.append(url)
            raise urllib2.HTTPError(url, 404, "Not Found", {}, None)

        self.urllib2.side_effect = mocked_urlopener
        response = ftpscraper.patient_urlopen('http://doesntmatt.er')
        self.assertEqual(response, None)
        assert len(mock_calls) == 1, mock_calls

    @mock.patch('socorro.cron.jobs.ftpscraper.time')
    def test_patient_urlopen_eventual_retriederror(self, mocked_time):

        sleeps = []

        def mocked_sleeper(seconds):
            sleeps.append(seconds)

        mocked_time.sleep = mocked_sleeper

        mock_calls = []

        @stringioify
        def mocked_urlopener(url):
            mock_calls.append(url)
            if len(mock_calls) % 2:
                raise urllib2.HTTPError(url, 500, "Server Error", {}, None)
            else:
                raise urllib2.URLError("BadStatusLine")

        self.urllib2.side_effect = mocked_urlopener
        # very impatient version
        self.assertRaises(
            ftpscraper.RetriedError,
            ftpscraper.patient_urlopen,
            'http://doesntmatt.er',
        )
        self.assertTrue(len(mock_calls) > 1)

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

    def test_getLinks_with_page_not_found(self):
        @stringioify
        def mocked_urlopener(url):
            raise urllib2.HTTPError(url, 404, "Not Found", {}, None)

        self.urllib2.side_effect = mocked_urlopener
        self.assertEqual(
            ftpscraper.getLinks('ONE'),
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
            if 'FIVE' in url:
                return (
                    '{"buildid": "20130309070203", '
                    '"update_channel": "nightly", "version": "18.0"}'
                )
            raise NotImplementedError(url)
        self.urllib2.side_effect = mocked_urlopener

        self.assertEqual(
            ftpscraper.parseInfoFile('ONE'),
            ({'BUILDID': '123'}, [])
        )
        self.assertEqual(
            ftpscraper.parseInfoFile('TWO'),
            ({'BUILDID': '123',
              'buildID': '456'}, [])
        )
        self.assertEqual(
            ftpscraper.parseInfoFile('THREE', nightly=True),
            ({'buildID': '123',
              'rev': 'http://hg.mozilla.org/123'}, [])
        )
        self.assertEqual(
            ftpscraper.parseInfoFile('FOUR', nightly=True),
            ({'buildID': '123',
              'rev': 'http://hg.mozilla.org/123',
              'altrev': 'http://git.mozilla.org/123'}, [])
        )
        self.assertEqual(
            ftpscraper.parseB2GFile('FIVE', nightly=True),
            ({"buildid": "20130309070203",
              "update_channel": "nightly",
              "version": "18.0",
              'build_type': 'nightly'}))

    def test_parseInfoFile_with_bad_lines(self):
        @stringioify
        def mocked_urlopener(url):
            if 'ONE' in url:
                return 'BUILDID'
            if 'TWO' in url:
                return 'BUILDID=123\nbuildID'
            raise NotImplementedError(url)
        self.urllib2.side_effect = mocked_urlopener

        self.assertEqual(
            ftpscraper.parseInfoFile('ONE'),
            ({}, ['BUILDID'])
        )

        self.assertEqual(
            ftpscraper.parseInfoFile('TWO'),
            ({'BUILDID': '123'}, ['buildID'])
        )

    def test_parseInfoFile_with_page_not_found(self):

        @stringioify
        def mocked_urlopener(url):
            raise urllib2.HTTPError(url, 404, "Not Found", {}, None)

        self.urllib2.side_effect = mocked_urlopener

        self.assertEqual(
            ftpscraper.parseInfoFile('ONE'),
            ({}, [])
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
            [('linux', 'ONE',
             {'BUILDID': '123', 'version_build': 'build-11'}, [])]
        )

    def test_parseB2GFile_with_page_not_found(self):
        @stringioify
        def mocked_urlopener(url):
            raise urllib2.HTTPError(url, 404, "Not Found", {}, None)
        self.urllib2.side_effect = mocked_urlopener

        self.assertEqual(
            ftpscraper.parseB2GFile('FIVE', nightly=True),
            None
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
              {'buildID': '123', 'rev': 'http://hg.mozilla.org/123'}, []),
             ('linux', 'ONE', 'firefox',
              {'buildID': '123', 'rev': 'http://hg.mozilla.org/123'}, [])]
        )

    def test_getB2G(self):
        @stringioify
        def mocked_urlopener(url):
            html_wrap = "<html><body>\n%s\n</body></html>"
            if '.json' in url:
                return (
                    '{"buildid": "20130309070203", '
                    '"update_channel": "nightly", "version": "18.0"}'
                )
            if 'ONE' in url:
                return '{}'
            if 'TWO' in url:
                return html_wrap % """
                <a href="socorro_unagi_date_version.json">l</a>
                <a href="socorro_unagi_date2_version.json">l</a>
                <a href="somethingelse_unagi_date3_version.json">l</a>
                """
            if 'TWO' in url:
                return html_wrap % """
                <a href="build-10/">build-10</a>
                <a href="build-11/">build-11</a>
                """
            raise NotImplementedError(url)

        self.urllib2.side_effect = mocked_urlopener

        self.assertEqual(
            list(ftpscraper.getB2G('ONE', 'http://x')),
            []
        )
        self.assertEqual(
            list(ftpscraper.getB2G('TWO', 'http://x')),
            [
                ('unagi', 'b2g-release', u'18.0', {
                    u'buildid': u'20130309070203',
                    u'update_channel': u'nightly',
                    u'version': u'18.0',
                    'build_type': u'nightly'
                }),
                ('unagi', 'b2g-release', u'18.0', {
                    u'buildid': u'20130309070203',
                    u'update_channel': u'nightly',
                    u'version': u'18.0',
                    'build_type': u'nightly'
                })
            ]
        )


@attr(integration='postgres')  # for nosetests
class TestIntegrationFTPScraper(IntegrationTestCaseBase):

    def setUp(self):
        super(TestIntegrationFTPScraper, self).setUp()
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
            ),
            (
            'Fennec',
            1,
            'mobile'
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
                'nightly'
            )
            ,(
                2,
                'Firefox',
                '24.5',
                '24.5.0esr',
                '24.5.0esr',
                '024005000x000',
                '%(build_date)s',
                '%(sunset_date)s',
                't',
                'esr'
            )
            ;
        """ % {"build_date": build_date, "sunset_date": sunset_date})

        cursor.execute("""
            TRUNCATE release_channels CASCADE;
            INSERT INTO release_channels
            (release_channel, sort)
            VALUES
            ('nightly', 1),
            ('aurora', 2),
            ('beta', 3),
            ('release', 4);
        """)

        cursor.execute("""
            TRUNCATE product_release_channels CASCADE;
            INSERT INTO product_release_channels
            (product_name, release_channel, throttle)
            VALUES
            ('Firefox', 'nightly', 1),
            ('Firefox', 'aurora', 1),
            ('Firefox', 'beta', 1),
            ('Firefox', 'release', 1),
            ('Fennec', 'release', 1),
            ('Fennec', 'beta', 1);
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
        cursor = self.conn.cursor()
        cursor.execute("""
            TRUNCATE TABLE releases_raw CASCADE;
            TRUNCATE product_versions CASCADE;
            TRUNCATE products CASCADE;
            TRUNCATE releases_raw CASCADE;
            TRUNCATE release_channels CASCADE;
            TRUNCATE product_release_channels CASCADE;
        """)
        self.conn.commit()
        self.urllib2_patcher.stop()
        super(TestIntegrationFTPScraper, self).tearDown()

    def _setup_config_manager_firefox(self):
        _super = super(TestIntegrationFTPScraper, self)._setup_config_manager
        return _super(
            'socorro.cron.jobs.ftpscraper.FTPScraperCronApp|1d',
            extra_value_source={
                'crontabber.class-FTPScraperCronApp.products': 'firefox',
            }
        )

    def _setup_config_manager(self):
        _super = super(TestIntegrationFTPScraper, self)._setup_config_manager
        return _super(
            'socorro.cron.jobs.ftpscraper.FTPScraperCronApp|1d',
            extra_value_source={
                'crontabber.class-FTPScraperCronApp.products': 'mobile',
            }
        )

    def test_info_txt_run(self):

        @stringioify
        def mocked_urlopener(url, today=None):
            if today is None:
                today = utc_now()
            html_wrap = "<html><body>\n%s\n</body></html>"
            if url.endswith('/firefox/'):
                return html_wrap % """
                <a href="../mobile/candidates/">candidates</a>
                <a href="../mobile/nightly/">nightly</a>
                """
            if url.endswith('/mobile/'):
                return html_wrap % """
                <a href="candidates/">candidates</a>
                <a href="nightly/">nightly</a>
                """
            if url.endswith('/mobile/nightly/'):
                return html_wrap % """
                <a href="10.0-candidates/">10.0-candidiates</a>
                """
            if url.endswith('/mobile/candidates/'):
                return html_wrap % """
                <a href="10.0b4-candidates/">10.0b4-candidiates</a>
                """
            if (url.endswith('/mobile/nightly/10.0-candidates/') or
                url.endswith('/mobile/candidates/10.0b4-candidates/')):
                return html_wrap % """
                <a href="build1/">build1</a>
                """
            if (url.endswith('/mobile/nightly/10.0-candidates/build1/') or
                url.endswith('/mobile/candidates/10.0b4-candidates/build1/')):
                return html_wrap % """
                <a href="linux_info.txt">linux_info.txt</a>
                """
            if url.endswith(today.strftime('/mobile/nightly/%Y/%m/')):
                return html_wrap % today.strftime("""
                <a href="%Y-%m-%d-trunk/">%Y-%m-%d-trunk</a>
                """)
            if url.endswith(
                today.strftime(
                    '/mobile/nightly/%Y/%m/%Y-%m-%d-trunk/'
                )
            ):
                return html_wrap % """
                <a href="mozilla-nightly-15.0a1.en-US.linux-x86_64.txt">txt</a>
                <a href="mozilla-nightly-15.0a2.en-US.linux-x86_64.txt">txt</a>
                """
            if url.endswith(
                today.strftime(
                    '/mobile/nightly/%Y/%m/%Y-%m-%d-trunk/'
                    'mozilla-nightly-15.0a1.en-US.linux-x86_64.txt'
                )
            ):
                return (
                    "20120505030510\n"
                    "http://hg.mozilla.org/mozilla-central/rev/0a48e6561534"
                )
            if url.endswith(
                today.strftime(
                    '/mobile/nightly/%Y/%m/%Y-%m-%d-trunk/'
                    'mozilla-nightly-15.0a2.en-US.linux-x86_64.txt'
                )
            ):
                return (
                    "20120505443322\n"
                    "http://hg.mozilla.org/mozilla-central/rev/xxx123"
                )
            if url.endswith(
                '/mobile/nightly/10.0-candidates/build1/linux_info.txt'
            ):
                return "buildID=20120516113045"
            if url.endswith(
                '/mobile/candidates/10.0b4-candidates/build1/linux_info.txt'
            ):
                return "buildID=20120516114455"

            # bad testing boy!
            raise NotImplementedError(url)

        self.urllib2.side_effect = mocked_urlopener

        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            print information['ftpscraper']['last_error']
            assert information['ftpscraper']
            assert not information['ftpscraper']['last_error']
            assert information['ftpscraper']['last_success']

        cursor = self.conn.cursor()

        columns = 'product_name', 'build_id', 'build_type'
        cursor.execute("""
            select %s
            from releases_raw
        """ % ','.join(columns))
        builds = [dict(zip(columns, row)) for row in cursor.fetchall()]
        build_ids = dict((str(x['build_id']), x) for x in builds)
        self.assertTrue('20120516114455' in build_ids)
        self.assertTrue('20120516113045' in build_ids)
        self.assertTrue('20120505030510' in build_ids)
        self.assertTrue('20120505443322' in build_ids)
        self.assertEqual(builds, [{
            'build_id': 20120516113045,
            'product_name': 'mobile',
            'build_type': 'release'
        }, {
            'build_id': 20120516113045,
            'product_name': 'mobile',
            'build_type': 'release'
        }, {
            'build_id': 20120516114455,
            'product_name': 'mobile',
            'build_type': 'beta'
        }, {
            'build_id': 20120505030510,
            'product_name': 'mobile',
            'build_type': 'nightly'
        }, {
            'build_id': 20120505443322,
            'product_name': 'mobile',
            'build_type': 'aurora'
        }])

        assert len(build_ids) == 4
        self.assertEqual(build_ids['20120516114455']['build_type'],
                         'beta')
        self.assertEqual(build_ids['20120516113045']['build_type'],
                         'release')
        self.assertEqual(build_ids['20120505030510']['build_type'],
                         'nightly')
        self.assertEqual(build_ids['20120505443322']['build_type'],
                         'aurora')

        # just one more time, pretend that we run it immediately again
        cursor.execute('select count(*) from releases_raw')
        count_before, = cursor.fetchall()[0]
        assert count_before == 5, count_before

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['ftpscraper']
            assert not information['ftpscraper']['last_error']
            assert information['ftpscraper']['last_success']

        cursor.execute('select count(*) from releases_raw')
        count_after, = cursor.fetchall()[0]
        assert count_after == count_before, count_before

    def test_run_with_broken_lines(self):
        """This test demonstrates what happens if a line of buildIDs isn't of
        the format `BUILDID=BUILDVALUE`.

        What should happen is that no error should be raised and the bad lines
        are sent to logging.warning.

        Stupidity bug based on:
            https://bugzilla.mozilla.org/show_bug.cgi?id=826551
        """

        @stringioify
        def mocked_urlopener(url, today=None):
            if today is None:
                today = utc_now()
            html_wrap = "<html><body>\n%s\n</body></html>"
            if url.endswith('/mobile/'):
                return html_wrap % """
                <a href="candidates/">candidates</a>
                <a href="nightly/">nightly</a>
                """
            if url.endswith('/mobile/nightly/'):
                return html_wrap % """
                <a href="10.0-candidates/">10.0-candidiates</a>
                """
            if url.endswith('/mobile/candidates/'):
                return html_wrap % """
                <a href="10.0b4-candidates/">10.0b4-candidiates</a>
                """
            if (url.endswith('/mobile/nightly/10.0-candidates/') or
                url.endswith('/mobile/candidates/10.0b4-candidates/')):
                return html_wrap % """
                <a href="build1/">build1</a>
                """
            if (url.endswith('/mobile/nightly/10.0-candidates/build1/') or
                url.endswith('/mobile/candidates/10.0b4-candidates/build1/')):
                return html_wrap % """
                <a href="linux_info.txt">linux_info.txt</a>
                """
            if url.endswith(today.strftime('/mobile/nightly/%Y/%m/')):
                return html_wrap % today.strftime("""
                <a href="%Y-%m-%d-trunk/">%Y-%m-%d-trunk</a>
                """)
            if url.endswith(
                today.strftime('/mobile/nightly/%Y/%m/%Y-%m-%d-trunk/')
            ):
                return html_wrap % """
                <a href="mozilla-nightly-15.0a1.en-US.linux-x86_64.txt">txt</a>
                <a href="mozilla-nightly-15.0a2.en-US.linux-x86_64.txt">txt</a>
                """
            if url.endswith(
                today.strftime(
                    '/mobile/nightly/%Y/%m/%Y-%m-%d-trunk/'
                    'mozilla-nightly-15.0a1.en-US.linux-x86_64.txt'
                )
            ):
                return (
                    "20120505030510\n"
                    "http://hg.mozilla.org/mozilla-central/rev/0a48e6561534"
                )
            if url.endswith(
                today.strftime(
                    '/mobile/nightly/%Y/%m/%Y-%m-%d-'
                    'trunk/mozilla-nightly-15.0a2.en'
                    '-US.linux-x86_64.txt'
                )
            ):
                return (
                    "20120505443322\n"
                    "http://hg.mozilla.org/mozilla-central/rev/xxx123"
                )
            if url.endswith('/mobile/nightly/10.0-candidates/build1/'
                            'linux_info.txt'):
                return (
                    "20120505443322\n"
                    "http://hg.mozilla.org/mozilla-central/rev/xxx123"
                )
            if url.endswith('/mobile/candidates/10.0b4-candidates/build1/'
                            'linux_info.txt'):
                return "bOildID"

            # bad testing boy!
            raise NotImplementedError(url)

        self.urllib2.side_effect = mocked_urlopener

        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = self._load_structure()

            assert information['ftpscraper']
            assert not information['ftpscraper']['last_error']
            assert information['ftpscraper']['last_success']

            config.logger.warning.assert_called_with(
                'BuildID not found for %s on %s',
                '10.0b4-candidates/',
                'http://ftp.mozilla.org/pub/mozilla.org/mobile/candidates/',
            )

        cursor = self.conn.cursor()

        columns = 'product_name', 'build_id', 'build_type'
        cursor.execute("""
            select %s
            from releases_raw
        """ % ','.join(columns))
        builds = [dict(zip(columns, row)) for row in cursor.fetchall()]
        build_ids = dict((str(x['build_id']), x) for x in builds)
        self.assertTrue('20120516114455' not in build_ids)
        self.assertTrue('20120505030510' in build_ids)
        self.assertTrue('20120505443322' in build_ids)
        self.assertEqual(len(build_ids), 2)

    def test_getJsonRelease(self):
        @stringioify
        def mocked_urlopener(url):
            html_wrap = "<html><body>\n%s\n</body></html>"
            if url.endswith('/mobile/'):
                return html_wrap % """
                <a href="../firefox/candidates/">candidates</a>
                """
            if 'firefox-27.0b6.json' in url:
                return """
                {
                    "buildid": "20140113161826",
                    "moz_app_maxversion": "27.0.*",
                    "moz_app_name": "firefox",
                    "moz_app_vendor": "Mozilla",
                    "moz_app_version": "27.0",
                    "moz_pkg_platform": "win32",
                    "moz_source_repo":
                        "http://hg.mozilla.org/releases/mozilla-beta",
                    "moz_update_channel": "beta"
                }
                """
            if 'firefox-27.0b7.json' in url:
                return """ """
            if 'THREE/build-11/win32/en-US' in url:
                return html_wrap % """
                <a href="firefox-27.0b7.json">f</a>
                """
            if 'ONE/build-12/win32/en-US' in url:
                return html_wrap % """
                <a href="firefox-27.0b6.json">f</a>
                """
            if 'ONE/build-12' in url:
                return html_wrap % """
                <a href="win32">w</a>
                """
            if 'THREE/build-11' in url:
                return html_wrap % """
                <a href="win32">w</a>
                """
            if 'ONE' in url:
                return html_wrap % """
                <a href="build-10/">build-10</a>
                <a href="build-12/">build-12</a>
                """
            if 'TWO' in url:
                return html_wrap % """
                <a href="ignore/">ignore</a>
                """
            if 'THREE' in url:
                return html_wrap % """
                <a href="build-11/">build-11</a>
                """
            raise NotImplementedError(url)

        self.urllib2.side_effect = mocked_urlopener

        self.assertEqual(
            list(ftpscraper.getJsonRelease('TWO', 'http://x')),
            []
        )
        self.assertEqual(
            list(ftpscraper.getJsonRelease('ONE', 'http://x')),
            [('win', 'ONE', {
                u'moz_app_version': u'27.0',
                u'moz_app_name': u'firefox',
                u'moz_app_vendor': u'Mozilla',
                u'moz_source_repo':
                u'http://hg.mozilla.org/releases/mozilla-beta',
                u'buildid': u'20140113161826',
                'repository': u'http://hg.mozilla.org/releases/mozilla-beta',
                u'moz_update_channel': u'beta',
                u'moz_pkg_platform': u'win32',
                'buildID': u'20140113161826',
                'repository': u'mozilla-beta',
                'build_type': u'beta',
                u'moz_app_maxversion': u'27.0.*',
                'version_build': 'build-12'
            })]
        )
        self.assertEqual(
            list(ftpscraper.getJsonRelease('THREE', 'http://x')),
            []
        )

    def test_scrapeJsonReleases(self):
        @stringioify
        def mocked_urlopener(url, today=None):
            if today is None:
                today = utc_now()
            html_wrap = "<html><body>\n%s\n</body></html>"
            if url.endswith('/mobile/'):
                return ''
            if url.endswith('/firefox/'):
                return html_wrap % """
                <a href="candidates/">candidates</a>
                """
            if url.endswith('/firefox/candidates/'):
                return html_wrap % """
                <a href="28.0-candidates/">28.0-candidiates</a>
                <a href="10.0b4-candidates/">10.0b4-candidiates</a>
                <a href="None-candidates/">None-candidiates</a>
                """
            if url.endswith('-candidates/'):
                return html_wrap % """
                <a href="build1/">build1</a>
                """
            if url.endswith('/build1/'):
                return html_wrap % """
                <a href="linux-i686">linux-i686</a>
                """
            if url.endswith('/firefox/candidates/28.0-candidates/'
                            'build1/linux-i686/en-US/'):
                return html_wrap % """
                    <a href="firefox-28.0.json">firefox-28.0.json</a>
                """
            if url.endswith('/firefox/candidates/10.0b4-candidates/'
                            'build1/linux-i686/en-US/'):
                return html_wrap % """
                    <a href="firefox-10.0b4.json">firefox-10.0b4.json</a>
                """
            if url.endswith('/firefox/candidates/None-candidates/'
                            'build1/linux-i686/en-US/'):
                return html_wrap % """
                    <a href="None.json">None.json</a>
                """
            if 'None.json' in url:
                return """ """
            if 'firefox-28.0.json' in url:
                return """
                {
                    "buildid": "20140113161827",
                    "moz_app_maxversion": "28.0.*",
                    "moz_app_name": "firefox",
                    "moz_app_vendor": "Mozilla",
                    "moz_app_version": "28.0",
                    "moz_pkg_platform": "linux-i686",
                    "moz_source_repo":
                        "http://hg.mozilla.org/releases/mozilla-release",
                    "moz_update_channel": "release"
                }
                """
            if 'firefox-10.0b4.json' in url:
                return """
                {
                    "buildid": "20140113161826",
                    "moz_app_maxversion": "10.0.*",
                    "moz_app_name": "firefox",
                    "moz_app_vendor": "Mozilla",
                    "moz_app_version": "27.0",
                    "moz_pkg_platform": "linux-i686",
                    "moz_source_repo":
                        "http://hg.mozilla.org/releases/mozilla-beta",
                    "moz_update_channel": "beta"
                }
                """
            raise NotImplementedError(url)

        self.urllib2.side_effect = mocked_urlopener
        config_manager = self._setup_config_manager_firefox()
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['ftpscraper']
            assert not information['ftpscraper']['last_error']
            assert information['ftpscraper']['last_success']

        cursor = self.conn.cursor()
        columns = 'product_name', 'build_id', 'build_type'
        cursor.execute("""
            select %s
            from releases_raw
        """ % ','.join(columns))
        builds = [dict(zip(columns, row)) for row in cursor.fetchall()]
        build_ids = dict((str(x['build_id']), x) for x in builds)
        self.assertTrue('20140113161827' in build_ids)
        self.assertTrue('20140113161826' in build_ids)
        assert len(build_ids) == 2
        self.assertEqual(builds, [{
            'build_id': 20140113161827,
            'product_name': 'firefox',
            'build_type': 'release'
        }, {
            'build_id': 20140113161827,
            'product_name': 'firefox',
            'build_type': 'beta'
        }, {
            'build_id': 20140113161826,
            'product_name': 'firefox',
            'build_type': 'beta'
        }])
