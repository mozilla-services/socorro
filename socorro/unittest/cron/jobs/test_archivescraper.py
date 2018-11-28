# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os

from jinja2 import Environment
import psycopg2
import pytest
import requests_mock

from socorro.cron.crontabber_app import CronTabberApp
from socorro.cron.jobs.archivescraper import ArchiveScraperCronApp
from socorro.unittest.cron.crontabber_tests_base import get_config_manager


HOST = 'http://archive.example.com'

INDEX_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8">
        <title>Directory Listing: {{ path }}</title>
    </head>
    <body>
        <h1>Index of {{ path }}</h1>
        <table>
            <tr>
                <th>Type</th>
                <th>Name</th>
                <th>Size</th>
                <th>Last Modified</th>
            </tr>
            {% for link in links %}
            {% set is_dir = link.name.endswith('/') %}
            <tr>
                <td>{% if is_dir %}Dir{% else %}File{% endif %}</td>
                <td><a href="{{ link.path }}">{{ link.name }}</a></td>
                <td>{% if not is_dir %}18K{% endif %}</td>
                <td>{% if not is_dir %}26-Oct-2018 03:14{% endif %}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
</html>
"""


def absolute_links_parents(path):
    """Generate (path, link name) for all parents of a given path

    :arg path: a url path

    :returns: iterator over all the (parent path, child link) pairs

    For example:

    >>> list(absolute_links_parents('/pub/firefox/candidates/64.0b13-candidates/'))
    [('/', 'pub/'), ('/pub/', 'firefox/'), ('/pub/firefox/', 'candidates/'),
    ('/pub/firefox/candidates/', '64.0b13-candidates/')]

    """
    path_parts = path.strip('/').split('/')
    for i, path_part in enumerate(path_parts):
        parent_path = '/' + '/'.join(path_parts[0:i])
        if parent_path != '/':
            parent_path += '/'

        if not path_part.endswith('.json'):
            path_part += '/'

        yield (parent_path, path_part)


def render_index_template(path, links):
    """Given a list of links, generates an HTML index page"""
    jinja_env = Environment()
    index_template = jinja_env.from_string(INDEX_PAGE_TEMPLATE)
    return index_template.render(path=path, links=links)


def setup_site(req_mock, root, file_contents):
    """Generates all the req_mock.get calls to simulate a site

    :arg req_mock: a requests_mock mock instance
    :arg str root: the root path to prepend to all paths
    :arg list file_contents: list of (path, contents)

    """
    root = root.rstrip('/')

    # map of path -> set of links
    path_to_links = {}

    for path, contents in file_contents:
        path = root + '/' + path
        req_mock.get(HOST + path, json=contents)

        for parent_path, link in absolute_links_parents(path):
            path_to_links.setdefault(parent_path, set()).add(link)

    for path, links in path_to_links.items():
        links = [
            {
                'path': path + link,
                'name': link
            }
            for link in links
        ]

        index_page = render_index_template(path, links)
        req_mock.get(HOST + path, text=index_page)


@pytest.fixture
def config():
    """Pytest fixture that returns config for ArchiveScraperCronApp"""
    # Configuration for crontabber jobs is buried in CrontabberApp, so we
    # create one of those and then extract the configuration that we want. It's
    # either that or we have to hard-code expanding all the configuration bits.
    config_manager = get_config_manager(
        jobs='socorro.cron.jobs.archivescraper.ArchiveScraperCronApp|1h',
        overrides={
            'crontabber.class-ArchiveScraperCronApp.base_url': HOST + '/pub/',
        }
    )
    with config_manager.context() as config:
        crontabberapp = CronTabberApp(config)
        class_config = crontabberapp.config.crontabber['class-ArchiveScraperCronApp']
        yield class_config


@pytest.fixture
def req_mock():
    with requests_mock.mock() as mock:
        yield mock


class TestArchiveScraper(object):
    @classmethod
    def setup_class(cls):
        cls.conn = psycopg2.connect(os.environ['DATABASE_URL'])

    def setup_method(self, method):
        self.truncate_productversions()

    def teardown_method(self, method):
        self.truncate_productversions()

    def truncate_productversions(self):
        cursor = self.conn.cursor()
        cursor.execute('TRUNCATE crashstats_productversion')
        self.conn.commit()

    def fetch_data(self):
        cursor = self.conn.cursor()
        columns = [
            'product_name', 'release_channel', 'release_version', 'version_string', 'build_id',
            'archive_url', 'major_version'
        ]
        cursor.execute("""
        SELECT %s
        FROM crashstats_productversion
        """ % ', '.join(columns))
        data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        data.sort(key=lambda item: (item['build_id'], item['version_string']))
        return data

    # FIXME(willkg): test scraping a Firefox directory with various properties and
    # making sure the right builds get inserted
    def test_basic(self, config, req_mock):
        # Set up a site with the following things:
        site = [
            (
                # Create a 63.0 build1 which will add just a 63.0rc1
                # beta entry because there's a build2
                '63.0-candidates/build1/win32/en-US/buildhub.json', {
                    'build': {
                        'id': '20181015152800'
                    },
                    'target': {
                        'channel': 'release',
                        'version': '63.0'
                    }
                }
            ),
            (
                # Create a 63.0 build2 which will add just a 63.0rc2
                # beta entry and a 63.0 release entry
                '63.0-candidates/build2/win32/en-US/buildhub.json', {
                    'build': {
                        'id': '20181018182531'
                    },
                    'target': {
                        'channel': 'release',
                        'version': '63.0'
                    }
                }
            ),
            (
                # Create a 64.0b4 build1 which will add just a 64.0b4rc1
                # entry because there's a build2
                '64.0b4-candidates/build1/win32/en-US/buildhub.json', {
                    'build': {
                        'id': '20181025143507'
                    },
                    'target': {
                        'channel': 'beta',
                        'version': '64.0'
                    }
                }
            ),
            (
                # Create a 64.0b4 build2 which will add a 64.0b4rc1 and a
                # 64.0b4 because this is the last buildN/ and also, there's
                # an entry on the /releases/ page
                '64.0b4-candidates/build2/win32/en-US/buildhub.json', {
                    'build': {
                        'id': '20181025233934'
                    },
                    'target': {
                        'channel': 'beta',
                        'version': '64.0'
                    }
                }
            )
        ]
        setup_site(req_mock, '/pub/firefox/candidates', site)

        # Add the releases page
        release_page = render_index_template(
            path='/pub/firefox/releases/',
            links=[
                {'path': '/pub/firefox/releases/63.0', 'name': '63.0/'},
                {'path': '/pub/firefox/releases/64.0b4', 'name': '64.0b4/'},
            ]
        )
        req_mock.get(HOST + '/pub/firefox/releases/', text=release_page)

        expected_data = [
            # 63.0 should have a 63.0rc1/beta, a 63.rc2/beta, and a 63.0/release
            {
                'build_id': '20181015152800',
                'version_string': '63.0rc1',
                'release_channel': 'beta',
                'archive_url': 'http://archive.example.com/pub/firefox/candidates/63.0-candidates/build1/win32/en-US/buildhub.json',  # noqa
                'major_version': 63,
                'release_version': '63.0',
                'product_name': 'Firefox'
            },
            {
                'build_id': '20181018182531',
                'version_string': '63.0',
                'release_channel': 'release',
                'archive_url': 'http://archive.example.com/pub/firefox/candidates/63.0-candidates/build2/win32/en-US/buildhub.json',  # noqa
                'major_version': 63,
                'release_version': '63.0',
                'product_name': 'Firefox'
            },
            {
                'build_id': '20181018182531',
                'version_string': '63.0rc2',
                'release_channel': 'beta',
                'archive_url': 'http://archive.example.com/pub/firefox/candidates/63.0-candidates/build2/win32/en-US/buildhub.json',  # noqa
                'major_version': 63,
                'release_version': '63.0',
                'product_name': 'Firefox'
            },
            # 64.0b4 should have a 64.0b4rc1/beta, a 64.0b4rc2/beta, and a 64.0b4/beta
            {
                'build_id': '20181025143507',
                'version_string': '64.0b4rc1',
                'release_channel': 'beta',
                'archive_url': 'http://archive.example.com/pub/firefox/candidates/64.0b4-candidates/build1/win32/en-US/buildhub.json',  # noqa
                'major_version': 64,
                'release_version': '64.0',
                'product_name': 'Firefox'
            },
            {
                'build_id': '20181025233934',
                'version_string': '64.0b4',
                'release_channel': 'beta',
                'archive_url': 'http://archive.example.com/pub/firefox/candidates/64.0b4-candidates/build2/win32/en-US/buildhub.json',  # noqa
                'major_version': 64,
                'release_version': '64.0',
                'product_name': 'Firefox'
            },
            {
                'build_id': '20181025233934',
                'version_string': '64.0b4rc2',
                'release_channel': 'beta',
                'archive_url': 'http://archive.example.com/pub/firefox/candidates/64.0b4-candidates/build2/win32/en-US/buildhub.json',  # noqa
                'major_version': 64,
                'release_version': '64.0',
                'product_name': 'Firefox'
            },
        ]

        # Create an archive scraper
        archive_scraper = ArchiveScraperCronApp(config, {})

        # Scrape a first time with an empty db and assert that it inserted all
        # the versions we expected
        archive_scraper.scrape_candidates('Firefox', '/pub/firefox/candidates/')
        data = self.fetch_data()
        assert data == expected_data

        # Scrape it a second time and assert that the contents haven't
        # changed
        archive_scraper.scrape_candidates('Firefox', '/pub/firefox/candidates/')
        data = self.fetch_data()
        assert data == expected_data
