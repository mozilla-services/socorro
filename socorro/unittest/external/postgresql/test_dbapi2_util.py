# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mock import Mock, MagicMock
import pytest

from socorro.external.postgresql import dbapi2_util
from socorro.unittest.testbase import TestCase


class TestDBAPI2Helper(TestCase):

    def test_single_value_sql1(self):
        m_execute = Mock()
        m_fetchall = Mock(return_value=((17,),))
        m_cursor = MagicMock()
        m_cursor.execute = m_execute
        m_cursor.fetchall = m_fetchall
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = m_cursor

        r = dbapi2_util.single_value_sql(conn, "select 17")
        assert r == 17
        assert conn.cursor.call_count == 1
        assert m_cursor.execute.call_count == 1
        m_cursor.execute.assert_called_once_with('select 17', None)

    def test_single_value_sql2(self):
        m_execute = Mock()
        m_fetchall = Mock(return_value=((17,),))
        m_cursor = MagicMock()
        m_cursor.execute = m_execute
        m_cursor.fetchall = m_fetchall
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = m_cursor

        dbapi2_util.single_value_sql(conn, "select 17", (1, 2, 3))
        assert conn.cursor.call_count == 1
        assert m_cursor.execute.call_count == 1
        m_cursor.execute.assert_called_once_with('select 17', (1, 2, 3))

    def test_single_value_sql3(self):
        m_execute = Mock()
        m_fetchall = Mock(return_value=None)
        m_cursor = MagicMock()
        m_cursor.execute = m_execute
        m_cursor.fetchall = m_fetchall
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = m_cursor

        with pytest.raises(dbapi2_util.SQLDidNotReturnSingleValue):
            dbapi2_util.single_value_sql(conn, 'select 17', (1, 2, 3))

        assert conn.cursor.call_count == 1
        assert m_cursor.execute.call_count == 1
        m_cursor.execute.assert_called_once_with('select 17', (1, 2, 3))

    def test_single_row_sql1(self):
        m_execute = Mock()
        m_fetchall = Mock(return_value=((17, 22),))
        m_cursor = MagicMock()
        m_cursor.execute = m_execute
        m_cursor.fetchall = m_fetchall
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = m_cursor

        r = dbapi2_util.single_row_sql(conn, "select 17, 22")
        assert r == (17, 22)
        assert conn.cursor.call_count == 1
        assert m_cursor.execute.call_count == 1
        m_cursor.execute.assert_called_once_with('select 17, 22', None)

    def test_single_value_sql5(self):
        m_execute = Mock()
        m_fetchall = Mock(return_value=((17, 22),))
        m_cursor = MagicMock()
        m_cursor.execute = m_execute
        m_cursor.fetchall = m_fetchall
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = m_cursor

        dbapi2_util.single_row_sql(conn, "select 17, 22", (1, 2, 3))
        assert conn.cursor.call_count == 1
        assert m_cursor.execute.call_count == 1
        m_cursor.execute.assert_called_once_with("select 17, 22", (1, 2, 3))

    def test_single_value_sql4(self):
        m_execute = Mock()
        m_fetchall = Mock(return_value=None)
        m_cursor = MagicMock()
        m_cursor.execute = m_execute
        m_cursor.fetchall = m_fetchall
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = m_cursor

        with pytest.raises(dbapi2_util.SQLDidNotReturnSingleRow):
            dbapi2_util.single_row_sql(conn, 'select 17, 22', (1, 2, 3))
        assert conn.cursor.call_count == 1
        assert m_cursor.execute.call_count == 1
        m_cursor.execute.assert_called_once_with("select 17, 22", (1, 2, 3))

    def test_execute_query1(self):
        m_execute = Mock()
        expected = [(17, 22), (19, 24)]
        returns = [(17, 22), (19, 24), None]

        def foo(*args):
            r = returns.pop(0)
            return r
        m_fetchone = Mock(side_effect=foo)
        m_cursor = MagicMock()
        m_cursor.execute = m_execute
        m_cursor.fetchone = m_fetchone
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = m_cursor

        zipped = zip(
            dbapi2_util.execute_query_iter(
                conn,
                "select * from somewhere"
            ),
            expected
        )
        for x, y in zipped:
            assert x == y
        assert conn.cursor.call_count == 1
        assert m_cursor.execute.call_count == 1
        m_cursor.execute.assert_called_once_with("select * from somewhere",
                                                 None)

    def test_execute_query2(self):
        m_execute = Mock()
        expected = []
        returns = [None]

        def foo(*args):
            r = returns.pop(0)
            return r
        m_fetchone = Mock(side_effect=foo)
        m_cursor = MagicMock()
        m_cursor.execute = m_execute
        m_cursor.fetchone = m_fetchone
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = m_cursor

        zipped = zip(dbapi2_util.execute_query_iter(conn,
                                                    "select * from somewhere"),
                     expected)
        for x, y in zipped:
            assert x == y
        assert conn.cursor.call_count == 1
        assert m_cursor.execute.call_count == 1
        m_cursor.execute.assert_called_once_with("select * from somewhere",
                                                 None)

    def test_execute_no_results(self):
        m_execute = Mock()
        m_cursor = MagicMock()
        m_cursor.execute = m_execute
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = m_cursor

        dbapi2_util.execute_no_results(
            conn,
            "insert into table (a, b, c) values (%s, %s, %s)",
            (1, 2, 3)
        )
        assert conn.cursor.call_count == 1
        assert m_cursor.execute.call_count == 1
        m_cursor.execute.assert_called_once_with(
            "insert into table (a, b, c) values (%s, %s, %s)",
            (1, 2, 3)
        )

    def test_fetch_all_sequence(self):

        # A class so we can pretend to return a psycopg2 cursor object's
        # description object.

        class Description(object):

            def __init__(self, name):
                self.name = name

        things = [
            ['Peter', 'Bengtsson'],
            ['Lars', 'Lohn'],
        ]
        sequence = dbapi2_util.FetchAllSequence(
            things,
            [Description('first_name'), Description('last_name')]
        )
        zipped = sequence.zipped()
        assert isinstance(zipped, list)
        assert zipped[0] == {'first_name': 'Peter', 'last_name': 'Bengtsson'}
        assert zipped[1] == {'first_name': 'Lars', 'last_name': 'Lohn'}

        # __len__
        assert len(zipped) == 2

        # __iter__
        first = second = None
        for item in sequence:
            if first is None:
                first = item
            elif second is None:
                second = item
        assert first and second
        assert first == ['Peter', 'Bengtsson']
        assert second == ['Lars', 'Lohn']

        # __getitem__
        second = sequence[1]
        assert second == ['Lars', 'Lohn']

        # __contains__
        assert ['Peter', 'Bengtsson'] in sequence

        # __str__
        expect = str([
            ['Peter', 'Bengtsson'],
            ['Lars', 'Lohn']
        ])
        assert str(sequence) == expect
