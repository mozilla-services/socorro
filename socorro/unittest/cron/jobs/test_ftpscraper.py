# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from functools import wraps
import unittest

import mock
import requests
import requests_mock
import pytest

from socorro.cron.crontabber_app import CronTabberApp
from socorro.cron.jobs import ftpscraper
from socorro.lib.datetimeutil import utc_now
from socorro.lib.util import DotDict
from socorro.unittest.cron.jobs.base import IntegrationTestBase
from socorro.unittest.cron.setup_configman import get_config_manager_for_crontabber


BASE_URL = 'https://archive.example.com/pub/'


class Response(object):
    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code


def responsify(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return Response(func(*args, **kwargs))
    return wrapper


@requests_mock.Mocker()
class TestFTPScraper(unittest.TestCase):
    def get_standard_config(self):
        return get_config_manager_for_crontabber().get_config()

    def setUp(self):
        super(TestFTPScraper, self).setUp()
        self.psycopg2_patcher = mock.patch('psycopg2.connect')
        self.psycopg2 = self.psycopg2_patcher.start()

        self.mocked_session = requests.Session()

        def download(url):
            return self.mocked_session.get(url).content

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

    def test_get_links(self, requests_mocker):
        def text_callback(request, context):
            if 'ONE' in request.url:
                return """<html><body>
                <a href="One.html">One.html</a>
                </body></html>"""
            raise NotImplementedError(request.url)

        url = BASE_URL + 'ONE'
        requests_mocker.get(url, text=text_callback)
        assert self.scrapers.get_links(url, starts_with='One') == [BASE_URL + 'One.html']
        assert self.scrapers.get_links(url, ends_with='.html') == [BASE_URL + 'One.html']
        assert self.scrapers.get_links(url, starts_with='Two') == []
        with pytest.raises(NotImplementedError):
            self.scrapers.get_links(url)

    def test_get_links_advanced_startswith(self, requests_mocker):
        def text_callback(request, context):
            if request.url.endswith('/'):
                return """<html><body>
                <a href="/pub/some/dir/mypage/">My page</a>
                <a href="/pub/some/dir/otherpage/">Other page</a>
                </body></html>"""
            raise NotImplementedError(request.url)

        url = BASE_URL + 'some/dir/'
        requests_mocker.get(url, text=text_callback)
        links = self.scrapers.get_links(url, starts_with='myp')
        assert links == [BASE_URL + 'some/dir/mypage/']

    def test_get_links_with_page_not_found(self, requests_mocker):
        url = BASE_URL + 'one'
        requests_mocker.get(url, status_code=404)
        assert self.scrapers.get_links(url) == []

    def test_parse_info_file(self, requests_mocker):
        requests_mocker.get(BASE_URL + 'ONE', text='BUILDID=123')
        # Deliberate double \n
        requests_mocker.get(BASE_URL + 'TWO', text='BUILDID=123\n\nbuildID=456')
        requests_mocker.get(BASE_URL + 'THREE', text='123\nhttp://hg.mozilla.org/123')
        requests_mocker.get(
            BASE_URL + 'FOUR',
            text='123\nhttp://hg.mozilla.org/123\nhttp://git.mozilla.org/123'
        )

        assert self.scrapers.parse_info_file(BASE_URL + 'ONE') == (
            {'BUILDID': '123'}, []
        )
        assert self.scrapers.parse_info_file(BASE_URL + 'TWO') == (
            {'BUILDID': '123', 'buildID': '456'}, []
        )
        assert self.scrapers.parse_info_file(BASE_URL + 'THREE', nightly=True) == (
            {'buildID': '123', 'rev': 'http://hg.mozilla.org/123'}, []
        )
        assert self.scrapers.parse_info_file(BASE_URL + 'FOUR', nightly=True) == (
            {
                'buildID': '123',
                'rev': 'http://hg.mozilla.org/123',
                'altrev': 'http://git.mozilla.org/123'
            },
            []
        )

    def test_parse_info_file_with_bad_lines(self, requests_mocker):
        requests_mocker.get(BASE_URL + 'ONE', text='BUILDID')
        # Only one \n
        requests_mocker.get(BASE_URL + 'TWO', text='BUILDID=123\nbuildID')

        assert self.scrapers.parse_info_file(BASE_URL + 'ONE') == (
            {}, ['BUILDID']
        )
        assert self.scrapers.parse_info_file(BASE_URL + 'TWO') == (
            {'BUILDID': '123'}, ['buildID']
        )

    def test_parse_info_file_with_page_not_found(self, requests_mocker):
        requests_mocker.get(BASE_URL + 'ONE', status_code=404)
        assert self.scrapers.parse_info_file(BASE_URL + 'ONE') == ({}, [])

    def test_get_release(self, requests_mocker):
        requests_mocker.get(BASE_URL + 'ONE-candidates/linux_info.txt', text='BUILDID=123')
        requests_mocker.get(
            BASE_URL + 'ONE/build-10/',
            status_code=404
        )
        requests_mocker.get(
            BASE_URL + 'ONE/build-11/',
            text="""<html><body>
            <a href="/pub/ONE-candidates/linux_info.txt">l</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'ONE/',
            text="""<html><body>
            <a href="build-10/">build-10</a>
            <a href="build-11/">build-11</a>
            </body></html>"""
        )

        # Links to nothing
        requests_mocker.get(
            BASE_URL + 'TWO/',
            text="""<html><body>
            <a href="/pub/ignore/">ignore</a>
            </body></html>"""
        )

        assert list(self.scrapers.get_release(BASE_URL + 'ONE/')) == [
            ('linux', 'ONE', {'BUILDID': '123', 'version_build': 'build-11'}, [])
        ]
        assert list(self.scrapers.get_release(BASE_URL + 'TWO/')) == []

    def test_get_json_nightly(self, requests_mocker):
        requests_mocker.get(
            BASE_URL + 'ONE/',
            text="""<html><body>
            <a href="firefox-43.0a2.multi.linux-i686.json">1</a>
            <a href="firefox-43.0a2.en-US.linux-i686.mozinfo.json">2</a>
            <a href="firefox-43.0a2.en-US.linux-i686.json">3</a>
            <a href="some-other-stuff.json">X</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'ONE/firefox-43.0a2.multi.linux-i686.json',
            json={
                'buildid': '20151006004017',
                'moz_source_repo': 'mozilla-aurora',
                'moz_update_channel': 'aurora',
            }
        )
        requests_mocker.get(
            BASE_URL + 'ONE/firefox-43.0a2.en-US.linux-i686.mozinfo.json',
            json={
                'buildid': '20151006004017',
                'moz_source_repo': 'mozilla-aurora',
                'moz_update_channel': 'aurora',
            }
        )
        requests_mocker.get(
            BASE_URL + 'ONE/firefox-43.0a2.en-US.linux-i686.json',
            json={
                'buildid': '20151006004017',
                'moz_source_repo': 'mozilla-aurora',
                'moz_update_channel': 'aurora',
            }
        )
        requests_mocker.get(
            BASE_URL + 'ONE/some-other-stuff.json',
            json={
                'buildid': '20151006004017',
                'moz_source_repo': 'mozilla-aurora',
                'moz_update_channel': 'aurora',
            }
        )

        requests_mocker.get(
            BASE_URL + 'TWO/',
            text="""<html><body>
            <a href="ignore/">ignore</a>
            </body></html>"""
        )

        assert list(self.scrapers.get_json_nightly(BASE_URL + 'TWO/', 'TWO')) == []
        builds = list(self.scrapers.get_json_nightly(BASE_URL + 'ONE/', 'ONE'))
        assert len(builds) == 2

        kvpairs = {
            'buildID': '20151006004017',
            'buildid': '20151006004017',
            'build_type': 'aurora',
            'moz_update_channel': 'aurora',
            'repository': 'mozilla-aurora',
            'moz_source_repo': 'mozilla-aurora',
        }
        assert builds[0] == ('linux-i686', 'ONE', '43.0a2', kvpairs)


@requests_mock.Mocker()
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
        self.mocked_session = requests.Session()

        def download(url):
            return self.mocked_session.get(url).content

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

    def _setup_config_manager_firefox(self):
        # Set a completely bogus looking base_url so it can never
        # accidentally work if the network request mocking leaks
        return super(TestIntegrationFTPScraper, self)._setup_config_manager(
            jobs_string='socorro.cron.jobs.ftpscraper.FTPScraperCronApp|1d',
            extra_value_source={
                'crontabber.class-FTPScraperCronApp.products': 'firefox',
                'crontabber.class-FTPScraperCronApp.base_url': BASE_URL,
            }
        )

    def _setup_config_manager(self):
        return get_config_manager_for_crontabber(
            jobs='socorro.cron.jobs.ftpscraper.FTPScraperCronApp|1d',
            overrides={
                'crontabber.class-FTPScraperCronApp.products': 'mobile',
            }
        )

    def test_get_json_release(self, requests_mocker):
        # There's no build information in TWO
        requests_mocker.get(
            BASE_URL + 'TWO/',
            text="""<html><body><a href="ignore/">ignore</a></body></html>"""
        )

        # THREE is a directory tree that leads to an empty file.
        requests_mocker.get(
            BASE_URL + 'THREE/',
            text="""<html><body>
            <a href="build-11/">build-11</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'THREE/build-11/',
            text="""<html><body>
            <a href="win/">win</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'THREE/build-11/win/',
            text="""<html><body>
            <a href="en-US/">en-US</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'THREE/build-11/win/en-US/',
            text="""<html><body>
            <a href="firefox-27.0b7.json">firefox-27.0b7.json</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'THREE/build-11/win/en-US/firefox-27.0b7.json',
            text=' '
        )

        requests_mocker.get(
            BASE_URL + 'ONE/',
            text="""<html><body>
            <a href="build-10/">build-10</a>
            <a href="build-12/">build-12</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'ONE/build-10/',
            status_code=404
        )
        requests_mocker.get(
            BASE_URL + 'ONE/build-12/',
            text="""<html><body>
            <a href="win/">win</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'ONE/build-12/win/',
            text="""<html><body>
            <a href="en-US/">en-US</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'ONE/build-12/win/en-US/',
            text="""<html><body>
            <a href="firefox-27.0b6.json">firefox-27.0b6.json</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'ONE/build-12/win/en-US/firefox-27.0b6.json',
            json={
                'buildid': '20140113161826',
                'moz_app_maxversion': '27.0.*',
                'moz_app_name': 'firefox',
                'moz_app_vendor': 'Mozilla',
                'moz_app_version': '27.0',
                'moz_pkg_platform': 'win32',
                'moz_source_repo': 'http://hg.mozilla.org/releases/mozilla-beta',
                'moz_update_channel': 'beta',
            }
        )

        # Navigates the tree and gets the build information with additional
        # bits
        scrapes = list(self.scrapers.get_json_release(BASE_URL + 'ONE/', 'ONE'))
        assert scrapes == [
            ('win', 'ONE', {
                u'moz_app_version': u'27.0',
                u'moz_app_name': u'firefox',
                u'moz_app_vendor': u'Mozilla',
                u'moz_source_repo': u'http://hg.mozilla.org/releases/mozilla-beta',
                u'buildid': u'20140113161826',
                u'moz_update_channel': u'beta',
                u'moz_pkg_platform': u'win32',
                u'buildID': u'20140113161826',
                u'repository': u'mozilla-beta',
                u'build_type': u'beta',
                u'moz_app_maxversion': u'27.0.*',
                u'version_build': 'build-12'
            })
        ]

        # Nothing in TWO
        assert list(self.scrapers.get_json_release(BASE_URL + 'TWO/', 'TWO')) == []

        # Nothing in THREE
        assert list(self.scrapers.get_json_release(BASE_URL + 'THREE/', 'THREE')) == []

    def test_scrape_json_releases(self, requests_mocker):
        today = utc_now()

        requests_mocker.get(
            BASE_URL + 'firefox/',
            text="""<html><body>
            <a href="candidates/">candidates</a>
            <a href="nightly/">nightly</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'firefox/candidates/',
            text="""<html><body>
            <a href="28.0-candidates/">28.0-candidiates</a>
            <a href="10.0b4-candidates/">10.0b4-candidiates</a>
            <a href="None-candidates/">None-candidiates</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'firefox/candidates/28.0-candidates/',
            text="""<html><body>
            <a href="build1/">build1</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'firefox/candidates/28.0-candidates/build1/',
            text="""<html><body>
            <a href="linux-i686/">linux-i686</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'firefox/candidates/28.0-candidates/build1/linux-i686/',
            text="""<html><body>
            <a href="en-US/">en-US</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'firefox/candidates/28.0-candidates/build1/linux-i686/en-US/',
            text="""<html><body>
            <a href="firefox-28.0.json">firefox-28.0.json</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL +
            'firefox/candidates/28.0-candidates/build1/linux-i686/en-US/firefox-28.0.json',
            json={
                'buildid': '20140113161827',
                'moz_app_maxversion': '28.0.*',
                'moz_app_name': 'firefox',
                'moz_app_vendor': 'Mozilla',
                'moz_app_version': '28.0',
                'moz_pkg_platform': 'linux-i686',
                'moz_source_repo': 'http://hg.mozilla.org/releases/mozilla-release',
                'moz_update_channel': 'release'
            }
        )
        requests_mocker.get(
            BASE_URL + 'firefox/candidates/10.0b4-candidates/',
            text="""<html><body>
            <a href="build1/">build1</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'firefox/candidates/10.0b4-candidates/build1/',
            text="""<html><body>
            <a href="linux-i686/">linux-i686</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'firefox/candidates/10.0b4-candidates/build1/linux-i686/',
            text="""<html><body>
            <a href="en-US/">en-US</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'firefox/candidates/10.0b4-candidates/build1/linux-i686/en-US/',
            text="""<html><body>
            <a href="firefox-10.0b4.json">firefox-10.0b4.json</a>
            <a href="firefox-10.0b4.en-US.linux-i686.mozinfo.json">
            firefox-10.0b4.en-US.linux-i686.mozinfo.json</a>
            <a href="JUNK.json">JUNK.json</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL +
            'firefox/candidates/10.0b4-candidates/build1/linux-i686/en-US/firefox-10.0b4.json',
            json={
                'buildid': '20140113161826',
                'moz_app_maxversion': '10.0.*',
                'moz_app_name': 'firefox',
                'moz_app_vendor': 'Mozilla',
                'moz_app_version': '27.0',
                'moz_pkg_platform': 'linux-i686',
                'moz_source_repo': 'http://hg.mozilla.org/releases/mozilla-beta',
                'moz_update_channel': 'beta'
            }
        )
        # Ignore unrecognized JSON files, see bug 1065071
        requests_mocker.get(
            BASE_URL + 'firefox/candidates/10.0b4-candidates/build1/linux-i686/en-US/JUNK.json',
            json={
                'something': 'unexpected',
                'nothing': 'else'
            }
        )

        requests_mocker.get(
            BASE_URL + 'firefox/candidates/None-candidates/',
            text="""<html><body>
            <a href="build1/">build1</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'firefox/candidates/None-candidates/build1/',
            text="""<html><body>
            <a href="linux-i686/">linux-i686</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'firefox/candidates/None-candidates/build1/linux-i686/',
            text="""<html><body>
            <a href="en-US/">en-US</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'firefox/candidates/None-candidates/build1/linux-i686/en-US/',
            text="""<html><body>
            <a href="None.json">None.json</a>
            </body></html>"""
        )
        requests_mocker.get(
            BASE_URL + 'firefox/candidates/None-candidates/build1/linux-i686/en-US/None.json',
            text=""" """
        )

        requests_mocker.get(
            BASE_URL + 'firefox/nightly/',
            text="""<html><body>
            <a href="%(year)s/">%(year)s</a>
            </body></html>""" % {'year': today.strftime('%Y')}
        )
        requests_mocker.get(
            today.strftime(BASE_URL + 'firefox/nightly/%Y/'),
            text="""<html><body>
            <a href="%(month)s/">%(month)s</a>
            </body></html>""" % {'month': today.strftime('%m')}
        )
        requests_mocker.get(
            today.strftime(BASE_URL + 'firefox/nightly/%Y/%m/'),
            text="""<html><body>
            <a href="%(date)s-03-02-03-mozilla-central/">txt</a>
            <a href="%(date)s-03-02-04-mozilla-central/">txt</a>
            """ % {'date': today.strftime('%Y-%m-%d')}
        )
        requests_mocker.get(
            today.strftime(BASE_URL + 'firefox/nightly/%Y/%m/%Y-%m-%d-03-02-03-mozilla-central/'),
            text="""<html><body>
            <a href="firefox-30.0a1.en-US.linux-i686.json">txt</a>
            </body></html>"""
        )
        requests_mocker.get(
            today.strftime(
                BASE_URL +
                'firefox/nightly/%Y/%m/%Y-%m-%d-03-02-03-mozilla-central/' +
                'firefox-30.0a1.en-US.linux-i686.json'
            ),
            json={
                'as': '$(CC)',
                'buildid': '20140205030203',
                'cc': '/usr/bin/ccache ',
                'cxx': '/usr/bin/ccache stuff',
                'host_alias': 'x86_64-unknown-linux-gnu',
                'host_cpu': 'x86_64',
                'host_os': 'linux-gnu',
                'host_vendor': 'unknown',
                'ld': 'ld',
                'moz_app_id': '{ec8030f7-c20a-464f-9b0e-13a3a9e97384}',
                'moz_app_maxversion': '30.0a1',
                'moz_app_name': 'firefox',
                'moz_app_vendor': 'Mozilla',
                'moz_app_version': '30.0a1',
                'moz_pkg_platform': 'linux-i686',
                'moz_source_repo': 'https://hg.mozilla.org/mozilla-central',
                'moz_source_stamp': '1f170f9fead0',
                'moz_update_channel': 'nightly',
                'target_alias': 'i686-pc-linux',
                'target_cpu': 'i686',
                'target_os': 'linux-gnu',
                'target_vendor': 'pc'
            }
        )
        requests_mocker.get(
            today.strftime(BASE_URL + 'firefox/nightly/%Y/%m/%Y-%m-%d-03-02-04-mozilla-central/'),
            text="""<html><body>
            <a href="firefox-30.0a2.en-US.linux-i686.json">txt</a>
            </body></html>"""
        )
        requests_mocker.get(
            today.strftime(
                BASE_URL +
                'firefox/nightly/%Y/%m/%Y-%m-%d-03-02-04-mozilla-central/' +
                'firefox-30.0a2.en-US.linux-i686.json'
            ),
            json={
                'as': '$(CC)',
                'buildid': '20140205030204',
                'cc': '/usr/bin/ccache stuff',
                'cxx': '/usr/bin/ccache stuff',
                'host_alias': 'x86_64-unknown-linux-gnu',
                'host_cpu': 'x86_64',
                'host_os': 'linux-gnu',
                'host_vendor': 'unknown',
                'ld': 'ld',
                'moz_app_id': '{ec8030f7-c20a-464f-9b0e-13a3a9e97384}',
                'moz_app_maxversion': '30.0a2',
                'moz_app_name': 'firefox',
                'moz_app_vendor': 'Mozilla',
                'moz_app_version': '30.0a2',
                'moz_pkg_platform': 'linux-i686',
                'moz_source_repo': 'https://hg.mozilla.org/mozilla-central',
                'moz_source_stamp': '1f170f9fead0',
                'moz_update_channel': 'nightly',
                'target_alias': 'i686-pc-linux',
                'target_cpu': 'i686',
                'target_os': 'linux-gnu',
                'target_vendor': 'pc'
            }
        )

        config_manager = self._setup_config_manager_firefox()
        with config_manager.context() as config:
            tab = CronTabberApp(config)
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

            config.logger.warning.assert_any_call(
                'warning, unsupported JSON file: %s',
                BASE_URL + 'firefox/candidates/'
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

        assert '20140113161827' in build_ids
        assert '20140113161826' in build_ids
        assert '20140205030203' in build_ids
        assert len(build_ids) == 4
        expected = [
            {
                'build_id': 20140113161827,
                'product_name': 'firefox',
                'build_type': 'release'
            },
            {
                'build_id': 20140113161827,
                'product_name': 'firefox',
                'build_type': 'beta'
            },
            {
                'build_id': 20140113161826,
                'product_name': 'firefox',
                'build_type': 'beta'
            },
            {
                'build_id': 20140205030203,
                'product_name': 'firefox',
                'build_type': 'nightly'
            },
            {
                'build_id': 20140205030204,
                'product_name': 'firefox',
                'build_type': 'aurora'
            }
        ]
        assert builds == expected
