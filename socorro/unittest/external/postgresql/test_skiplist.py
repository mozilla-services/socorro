# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.plugins.attrib import attr
from nose.tools import eq_, ok_, assert_raises

from socorro.external import MissingArgumentError, DatabaseError
from socorro.external.postgresql.skiplist import SkipList

from unittestbase import PostgreSQLTestCase


#==============================================================================
@attr(integration='postgres')  # for nosetests
class IntegrationTestSkipList(PostgreSQLTestCase):
    """Test socorro.external.postgresql.crashes.Crashes class. """

    #--------------------------------------------------------------------------
    def setUp(self):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestSkipList, self).setUp()

        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE skiplist
            CASCADE
        """)
        cursor.execute("""
            INSERT INTO skiplist (category, rule)
            VALUES
            ('prefix', 'arena_.*'),
            ('prefix', 'CrashInJS'),
            ('irrelevant', 'ashmem'),
            ('irrelevant', 'CxThrowException'),
            ('line_number', 'signatures_with_line_numbers_re')
            ;
        """)
        self.connection.commit()
        cursor.close()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE skiplist
            CASCADE
        """)
        self.connection.commit()
        cursor.close()
        super(IntegrationTestSkipList, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get(self):
        skiplist = SkipList(config=self.config)

        params = {
        }
        res_expected = {
            "hits": [
                # Note: sort is case-insensitive
                {
                    "category": "irrelevant",
                    "rule": "ashmem",
                },
                {
                    "category": "irrelevant",
                    "rule": "CxThrowException",
                },
                {
                    "category": "line_number",
                    "rule": "signatures_with_line_numbers_re",
                },
                {
                    "category": "prefix",
                    "rule": "arena_.*",
                },
                {
                    "category": "prefix",
                    "rule": "CrashInJS",
                },
            ],
            "total": 5
        }

        res = skiplist.get(**params)
        eq_(res, res_expected)

    def test_get_with_optional_filtering(self):
        skiplist = SkipList(config=self.config)

        # filter by category
        params = {
            'category': 'irrelevant'
        }
        res_expected = {
            "hits": [
                {
                    "category": "irrelevant",
                    "rule": "ashmem",
                },
                {
                    "category": "irrelevant",
                    "rule": "CxThrowException",
                },
            ],
            "total": 2
        }
        res = skiplist.get(**params)
        eq_(res, res_expected)

        # filter by rule
        params = {
            'rule': 'ashmem'
        }
        res_expected = {
            "hits": [
                {
                    "category": "irrelevant",
                    "rule": "ashmem",
                },
            ],
            "total": 1
        }
        res = skiplist.get(**params)
        eq_(res, res_expected)

        # filter by both
        params = {
            'category': 'irrelevant',
            'rule': 'ashmem'
        }
        res_expected = {
            "hits": [
                {
                    "category": "irrelevant",
                    "rule": "ashmem",
                },
            ],
            "total": 1
        }
        res = skiplist.get(**params)
        eq_(res, res_expected)

    def test_post(self):
        skiplist = SkipList(config=self.config)
        assert_raises(MissingArgumentError, skiplist.post)
        assert_raises(
            MissingArgumentError,
            skiplist.post,
            category='something'
        )
        assert_raises(
            MissingArgumentError,
            skiplist.post,
            rule='something'
        )

        # because of an integrity error since it already exists
        assert_raises(
            DatabaseError,
            skiplist.post,
            category='prefix', rule='CrashInJS'
        )

        ok_(
            skiplist.post(category='suffix', rule='Erik*tiny*font')
        )

        cursor = self.connection.cursor()
        cursor.execute("""
        select * from skiplist where category=%s and rule=%s
        """, ('suffix', 'Erik*tiny*font'))
        first, = cursor.fetchall()
        eq_(first[0], 'suffix')
        eq_(first[1], 'Erik*tiny*font')

    def test_delete(self):
        skiplist = SkipList(config=self.config)
        assert_raises(MissingArgumentError, skiplist.delete)
        assert_raises(
            MissingArgumentError,
            skiplist.delete,
            category='something'
        )
        assert_raises(
            MissingArgumentError,
            skiplist.delete,
            rule='something'
        )

        cursor = self.connection.cursor()
        cursor.execute("select count(*) from skiplist")
        first, = cursor.fetchall()
        count = first[0]
        eq_(count, 5)

        ok_(skiplist.delete(category='irrelevant', rule='ashmem'))

        cursor.execute("select count(*) from skiplist")
        first, = cursor.fetchall()
        count = first[0]
        eq_(count, 4)

        cursor.execute("""
        select count(*) from skiplist
        where category=%s and rule=%s
        """, ('irrelevant', 'ashmem'))
        first, = cursor.fetchall()
        count = first[0]
        eq_(count, 0)

        ok_(not skiplist.delete(category='neverheard', rule='of'))
