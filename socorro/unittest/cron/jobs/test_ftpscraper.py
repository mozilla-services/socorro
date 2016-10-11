# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import json
from functools import wraps

import requests
import mock
from nose.tools import eq_, ok_, assert_raises
from crontabber.app import CronTabber
from crontabber.tests.base import TestCaseBase

from socorrolib.lib.datetimeutil import utc_now
from socorro.cron.jobs import ftpscraper
from socorro.unittest.cron.jobs.base import IntegrationTestBase
from socorrolib.lib.util import DotDict
from socorro.unittest.cron.setup_configman import (
    get_config_manager_for_crontabber,
)


class Response(object):
    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code


def responsify(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return Response(func(*args, **kwargs))
    return wrapper


#==============================================================================
class TestFTPScraper(TestCaseBase):

    def get_standard_config(self):
        return get_config_manager_for_crontabber().get_config()

    def setUp(self):
        super(TestFTPScraper, self).setUp()
        self.psycopg2_patcher = mock.patch('psycopg2.connect')
        self.psycopg2 = self.psycopg2_patcher.start()
        self.requests_session_patcher = mock.patch('requests.Session')
        self.mocked_session = self.requests_session_patcher.start()

        def download(url):
            return self.mocked_session.get(url)

        def skip_json_file(url):
            if url.endswith('mozinfo.json'):
                return True
            return False

        self.scrapers = ftpscraper.ScrapersMixin()
        self.scrapers.download = download
        self.scrapers.skip_json_file = skip_json_file
        self.scrapers.config = DotDict({
            'logger': mock.Mock()
        })

    def tearDown(self):
        super(TestFTPScraper, self).tearDown()
        self.psycopg2_patcher.stop()
        self.requests_session_patcher.stop()

    def test_get_links(self):

        def mocked_get(url):
            html_wrap = "<html><body>\n%s\n</body></html>"
            if 'ONE' in url:
                return html_wrap % """
                <a href='One.html'>One.html</a>
                """
            raise NotImplementedError(url)

        self.mocked_session.get.side_effect = mocked_get

        eq_(
            self.scrapers.get_links('ONE', starts_with='One'),
            ['One.html']
        )
        eq_(
            self.scrapers.get_links('ONE', ends_with='.html'),
            ['One.html']
        )
        eq_(
            self.scrapers.get_links('ONE', starts_with='Two'),
            []
        )
        assert_raises(
            NotImplementedError,
            self.scrapers.get_links,
            'ONE'
        )

    def test_get_links_advanced_startswith(self):

        def mocked_get(url):
            html_wrap = "<html><body>\n%s\n</body></html>"
            if '/' in url:
                return html_wrap % """
                <a href='/some/dir/mypage/'>My page</a>
                <a href='/some/dir/otherpage/'>Other page</a>
                """
            raise NotImplementedError(url)

        self.mocked_session.get.side_effect = mocked_get

        eq_(
            self.scrapers.get_links('http://x/some/dir/', starts_with='myp'),
            ['http://x/some/dir/mypage/']
        )

    def test_get_links_with_page_not_found(self):

        def mocked_get(url):
            response = requests.Response()
            response.status_code = 404
            return response

        self.mocked_session.get.side_effect = mocked_get
        eq_(
            self.scrapers.get_links('ONE'),
            []
        )

    def test_parse_info_file(self):

        def mocked_get(url):
            if 'ONE' in url:
                return 'BUILDID=123'
            if 'TWO' in url:
                return 'BUILDID=123\n\nbuildID=456'  # deliberate double \n
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

        self.mocked_session.get.side_effect = mocked_get

        eq_(
            self.scrapers.parse_info_file('ONE'),
            ({'BUILDID': '123'}, [])
        )
        eq_(
            self.scrapers.parse_info_file('TWO'),
            ({'BUILDID': '123',
              'buildID': '456'}, [])
        )
        eq_(
            self.scrapers.parse_info_file('THREE', nightly=True),
            ({'buildID': '123',
              'rev': 'http://hg.mozilla.org/123'}, [])
        )
        eq_(
            self.scrapers.parse_info_file('FOUR', nightly=True),
            ({'buildID': '123',
              'rev': 'http://hg.mozilla.org/123',
              'altrev': 'http://git.mozilla.org/123'}, [])
        )

    def test_parse_info_file_with_bad_lines(self):

        def mocked_get(url):
            if 'ONE' in url:
                return 'BUILDID'
            if 'TWO' in url:
                return 'BUILDID=123\nbuildID'
            raise NotImplementedError(url)

        self.mocked_session.get.side_effect = mocked_get

        eq_(
            self.scrapers.parse_info_file('ONE'),
            ({}, ['BUILDID'])
        )

        eq_(
            self.scrapers.parse_info_file('TWO'),
            ({'BUILDID': '123'}, ['buildID'])
        )

    def test_parse_info_file_with_page_not_found(self):

        def mocked_get(url):
            response = requests.Response()
            response.status_code = 404
            return response

        self.mocked_session.get.side_effect = mocked_get

        eq_(
            self.scrapers.parse_info_file('ONE'),
            ({}, [])
        )

    def test_get_release(self):

        def mocked_get(url):
            html_wrap = "<html><body>\n%s\n</body></html>"
            if 'linux_info.txt' in url:
                return 'BUILDID=123'
            if 'build-11' in url:
                return html_wrap % """
                <a href="ONE-candidates/linux_info.txt">l</a>
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

        self.mocked_session.get.side_effect = mocked_get

        eq_(
            list(self.scrapers.get_release('http://x/TWO')),
            []
        )
        eq_(
            list(self.scrapers.get_release('http://x/ONE')),
            [('linux', 'ONE',
             {'BUILDID': '123', 'version_build': 'build-11'}, [])]
        )

    def test_get_json_nightly(self):

        def mocked_get(url):
            html_wrap = "<html><body>\n%s\n</body></html>"
            if '.json' in url:
                return json.dumps({
                    'buildid': '20151006004017',
                    'moz_source_repo': 'mozilla-aurora',
                    'moz_update_channel': 'aurora',
                })
            if 'ONE' in url:
                return html_wrap % """
                <a href="firefox-43.0a2.multi.linux-i686.json">1</a>
                <a href="firefox-43.0a2.en-US.linux-i686.mozinfo.json">2</a>
                <a href="firefox-43.0a2.en-US.linux-i686.json">3</a>
                <a href="some-other-stuff.json">X</a>
                """
            if 'TWO' in url:
                return html_wrap % """
                <a href="ignore/">ignore</a>
                """
            raise NotImplementedError(url)

        self.mocked_session.get.side_effect = mocked_get

        eq_(
            list(self.scrapers.get_json_nightly('http://x/TWO/', 'TWO')),
            []
        )
        builds = list(self.scrapers.get_json_nightly('http://x/ONE/', 'ONE'))
        assert len(builds) == 2

        kvpairs = {
            'buildID': '20151006004017',
            'buildid': '20151006004017',
            'build_type': 'aurora',
            'moz_update_channel': 'aurora',
            'repository': 'mozilla-aurora',
            'moz_source_repo': 'mozilla-aurora',
        }
        eq_(builds[0], ('linux-i686', 'ONE', '43.0a2', kvpairs))


class TestIntegrationFTPScraper(IntegrationTestBase):

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

        self.conn.commit()
        self.requests_session_patcher = mock.patch('requests.Session')
        self.mocked_session = self.requests_session_patcher.start()

        def download(url):
            return self.mocked_session.get(url)

        def skip_json_file(url):
            return False

        self.scrapers = ftpscraper.ScrapersMixin()
        self.scrapers.download = download
        self.scrapers.skip_json_file = skip_json_file
        self.scrapers.config = DotDict({
            'logger': mock.Mock()
        })

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
        super(TestIntegrationFTPScraper, self).tearDown()
        self.requests_session_patcher.stop()

    def _setup_config_manager_firefox(self):
        # Set a completely bogus looking base_url so it can never
        # accidentally work if the network request mocking leaks
        base_url = 'https://archive.muzilla.hej/pub/'
        return get_config_manager_for_crontabber(
            jobs='socorro.cron.jobs.ftpscraper.FTPScraperCronApp|1d',
            overrides={
                'crontabber.class-FTPScraperCronApp.products': 'firefox',
                'crontabber.class-FTPScraperCronApp.base_url': base_url,
            }
        )

    def _setup_config_manager(self):
        return get_config_manager_for_crontabber(
            jobs='socorro.cron.jobs.ftpscraper.FTPScraperCronApp|1d',
            overrides={
                'crontabber.class-FTPScraperCronApp.products': 'mobile',
            }
        )

    def test_get_json_release(self):

        def mocked_get(url):
            html_wrap = "<html><body>\n%s\n</body></html>"
            if url.endswith('/mobile/'):
                return html_wrap % """
                <a href="../firefox/candidates/">candidates</a>
                """
            if 'firefox-27.0b6.json' in url:
                return json.dumps({
                    'buildid': '20140113161826',
                    'moz_app_maxversion': '27.0.*',
                    'moz_app_name': 'firefox',
                    'moz_app_vendor': 'Mozilla',
                    'moz_app_version': '27.0',
                    'moz_pkg_platform': 'win32',
                    'moz_source_repo': (
                        'http://hg.mozilla.org/releases/mozilla-beta'
                    ),
                    'moz_update_channel': 'beta',
                })
            if 'firefox-27.0b7.json' in url:
                return ' '
            if 'THREE/build-11/win/en-US' in url:
                return html_wrap % """
                <a href="firefox-27.0b7.json">f</a>
                """
            if 'ONE/build-12/win/en-US' in url:
                return html_wrap % """
                <a href="firefox-27.0b6.json">f</a>
                """
            if 'ONE/build-12' in url:
                return html_wrap % """
                <a href="win/">w</a>
                """
            if 'THREE/build-11' in url:
                return html_wrap % """
                <a href="win/">w</a>
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

        self.mocked_session.get.side_effect = mocked_get

        eq_(
            list(self.scrapers.get_json_release('http://x/TWO/', 'TWO')),
            []
        )
        scrapes = list(self.scrapers.get_json_release('http://x/ONE/', 'ONE'))
        assert len(scrapes) == 1, len(scrapes)
        eq_(
            scrapes[0],
            ('win', 'ONE', {
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
            })
        )
        eq_(
            list(self.scrapers.get_json_release('http://x/THREE/', 'THREE')),
            []
        )

    def test_scrape_json_releases(self):

        @responsify
        def mocked_get(url, today=None, timeout=None):
            if today is None:
                today = utc_now()
            html_wrap = "<html><body>\n%s\n</body></html>"
            if url.endswith('/firefox/'):
                return html_wrap % """
                <a href="candidates/">candidates</a>
                <a href="nightly/">nightly</a>
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
                <a href="linux-i686/">linux-i686</a>
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
                    <a href="firefox-10.0b4.en-US.linux-i686.mozinfo.json">
                     firefox-10.0b4.en-US.linux-i686.mozinfo.json</a>
                    <a href="JUNK.json">
                     JUNK.json</a>
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
            # Ignore unrecognized JSON files, see bug 1065071
            if 'JUNK.json' in url:
                return """
                {
                    "something": "unexpected",
                    "nothing": "else"
                }
                """
            # Nightly tests for nightly and aurora builds
            if url.endswith('/firefox/nightly/'):
                return html_wrap % """
                    <a href="2014/">2014</a>
                """
            if url.endswith(today.strftime('/firefox/nightly/%Y/%m/')):
                return html_wrap % """
                    <a href="%s-03-02-03-mozilla-central/">txt</a>
                    <a href="%s-03-02-04-mozilla-central/">txt</a>
                """ % (today.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'))
            if url.endswith(today.strftime('/firefox/nightly/%Y/%m/'
                            '%Y-%m-%d-03-02-03-mozilla-central/')):
                return html_wrap % """
                    <a href="firefox-30.0a1.en-US.linux-i686.json">txt</a>
                """
            if url.endswith(today.strftime(
                '/firefox/nightly/%Y/%m/%Y-%m-%d-03-02-04-mozilla-central/'
            )):
                return html_wrap % """
                    <a href="firefox-30.0a2.en-US.linux-i686.json">txt</a>
                """
            if url.endswith(today.strftime(
                '/firefox/nightly/%Y/%m/%Y-%m-%d-03-02-04-mozilla-central/'
                'firefox-30.0a2.en-US.linux-i686.json'
            )):
                return """
                    {

                        "as": "$(CC)",
                        "buildid": "20140205030204",
                        "cc": "/usr/bin/ccache stuff",
                        "cxx": "/usr/bin/ccache stuff",
                        "host_alias": "x86_64-unknown-linux-gnu",
                        "host_cpu": "x86_64",
                        "host_os": "linux-gnu",
                        "host_vendor": "unknown",
                        "ld": "ld",
                        "moz_app_id": "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}",
                        "moz_app_maxversion": "30.0a2",
                        "moz_app_name": "firefox",
                        "moz_app_vendor": "Mozilla",
                        "moz_app_version": "30.0a2",
                        "moz_pkg_platform": "linux-i686",
                        "moz_source_repo":
                            "https://hg.mozilla.org/mozilla-central",
                        "moz_source_stamp": "1f170f9fead0",
                        "moz_update_channel": "nightly",
                        "target_alias": "i686-pc-linux",
                        "target_cpu": "i686",
                        "target_os": "linux-gnu",
                        "target_vendor": "pc"

                    }
                """
            if url.endswith(today.strftime(
                '/firefox/nightly/%Y/%m/%Y-%m-%d-03-02-03-mozilla-central/'
                'firefox-30.0a1.en-US.linux-i686.json'
            )):
                return """
                    {

                        "as": "$(CC)",
                        "buildid": "20140205030203",
                        "cc": "/usr/bin/ccache ",
                        "cxx": "/usr/bin/ccache stuff",
                        "host_alias": "x86_64-unknown-linux-gnu",
                        "host_cpu": "x86_64",
                        "host_os": "linux-gnu",
                        "host_vendor": "unknown",
                        "ld": "ld",
                        "moz_app_id": "{ec8030f7-c20a-464f-9b0e-13a3a9e97384}",
                        "moz_app_maxversion": "30.0a1",
                        "moz_app_name": "firefox",
                        "moz_app_vendor": "Mozilla",
                        "moz_app_version": "30.0a1",
                        "moz_pkg_platform": "linux-i686",
                        "moz_source_repo":
                            "https://hg.mozilla.org/mozilla-central",
                        "moz_source_stamp": "1f170f9fead0",
                        "moz_update_channel": "nightly",
                        "target_alias": "i686-pc-linux",
                        "target_cpu": "i686",
                        "target_os": "linux-gnu",
                        "target_vendor": "pc"

                    }
                """
            raise NotImplementedError(url)

        self.mocked_session().get.side_effect = mocked_get

        config_manager = self._setup_config_manager_firefox()
        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['ftpscraper']
            assert not information['ftpscraper']['last_error']
            assert information['ftpscraper']['last_success']

            config.logger.warning.assert_any_call(
                'Unable to JSON parse content %r',
                ' ',
                exc_info=True
            )

            base_url = config.crontabber['class-FTPScraperCronApp'].base_url
            config.logger.warning.assert_any_call(
                'warning, unsupported JSON file: %s',
                base_url + 'firefox/candidates/'
                '10.0b4-candidates/build1/linux-i686/en-US/JUNK.json'
            )

        cursor = self.conn.cursor()
        columns = 'product_name', 'build_id', 'build_type'
        cursor.execute("""
            select %s
            from releases_raw
        """ % ','.join(columns))
        builds = [dict(zip(columns, row)) for row in cursor.fetchall()]
        build_ids = dict((str(x['build_id']), x) for x in builds)

        ok_('20140113161827' in build_ids)
        ok_('20140113161826' in build_ids)
        ok_('20140205030203' in build_ids)
        assert len(build_ids) == 4
        eq_(builds, [{
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
        }, {
            'build_id': 20140205030203,
            'product_name': 'firefox',
            'build_type': 'nightly'
        }, {
            'build_id': 20140205030204,
            'product_name': 'firefox',
            'build_type': 'aurora'
        }])
