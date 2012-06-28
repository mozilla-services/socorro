from mock import Mock
import unittest

from socorro.external.postgresql import dbapi2_util

class TestDBAPI2Helper(unittest.TestCase):

    def test_single_value_sql1(self):
        m_execute = Mock()
        m_fetchall = Mock(return_value=((17,),))
        m_cursor = Mock()
        m_cursor.execute = m_execute
        m_cursor.fetchall = m_fetchall
        conn = Mock()
        conn.cursor.return_value = m_cursor

        r = dbapi2_util.single_value_sql(conn, "select 17")
        self.assertEqual(r, 17)
        self.assertEqual(conn.cursor.call_count, 1)
        self.assertEqual(m_cursor.execute.call_count, 1)
        m_cursor.execute.assert_called_once_with('select 17', None)

    def test_single_value_sql2(self):
        m_execute = Mock()
        m_fetchall = Mock(return_value=((17,),))
        m_cursor = Mock()
        m_cursor.execute = m_execute
        m_cursor.fetchall = m_fetchall
        conn = Mock()
        conn.cursor.return_value = m_cursor

        r = dbapi2_util.single_value_sql(conn, "select 17", (1, 2, 3))
        self.assertEqual(conn.cursor.call_count, 1)
        self.assertEqual(m_cursor.execute.call_count, 1)
        m_cursor.execute.assert_called_once_with('select 17', (1, 2, 3))

    def test_single_value_sql3(self):
        m_execute = Mock()
        m_fetchall = Mock(return_value=None)
        m_cursor = Mock()
        m_cursor.execute = m_execute
        m_cursor.fetchall = m_fetchall
        conn = Mock()
        conn.cursor.return_value = m_cursor

        self.assertRaises(dbapi2_util.SQLDidNotReturnSingleValue,
                          dbapi2_util.single_value_sql,
                          conn,
                          "select 17",
                          (1, 2, 3))
        self.assertEqual(conn.cursor.call_count, 1)
        self.assertEqual(m_cursor.execute.call_count, 1)
        m_cursor.execute.assert_called_once_with('select 17', (1, 2, 3))

    def test_single_row_sql1(self):
        m_execute = Mock()
        m_fetchall = Mock(return_value=((17, 22),))
        m_cursor = Mock()
        m_cursor.execute = m_execute
        m_cursor.fetchall = m_fetchall
        conn = Mock()
        conn.cursor.return_value = m_cursor

        r = dbapi2_util.single_row_sql(conn, "select 17, 22")
        self.assertEqual(r, (17, 22))
        self.assertEqual(conn.cursor.call_count, 1)
        self.assertEqual(m_cursor.execute.call_count, 1)
        m_cursor.execute.assert_called_once_with('select 17, 22', None)

    def test_single_value_sql2(self):
        m_execute = Mock()
        m_fetchall = Mock(return_value=((17, 22),))
        m_cursor = Mock()
        m_cursor.execute = m_execute
        m_cursor.fetchall = m_fetchall
        conn = Mock()
        conn.cursor.return_value = m_cursor

        r = dbapi2_util.single_row_sql(conn, "select 17, 22", (1, 2, 3))
        self.assertEqual(conn.cursor.call_count, 1)
        self.assertEqual(m_cursor.execute.call_count, 1)
        m_cursor.execute.assert_called_once_with("select 17, 22", (1, 2, 3))

    def test_single_value_sql3(self):
        m_execute = Mock()
        m_fetchall = Mock(return_value=None)
        m_cursor = Mock()
        m_cursor.execute = m_execute
        m_cursor.fetchall = m_fetchall
        conn = Mock()
        conn.cursor.return_value = m_cursor

        self.assertRaises(dbapi2_util.SQLDidNotReturnSingleRow,
                          dbapi2_util.single_row_sql,
                          conn,
                          "select 17, 22",
                          (1, 2, 3))
        self.assertEqual(conn.cursor.call_count, 1)
        self.assertEqual(m_cursor.execute.call_count, 1)
        m_cursor.execute.assert_called_once_with("select 17, 22", (1, 2, 3))

    def test_execute_query1(self):
        m_execute = Mock()
        expected = [(17, 22), (19, 24)]
        returns = [(17, 22), (19, 24), None]
        def foo(*args):
            r = returns.pop(0)
            return r
        m_fetchone = Mock(side_effect=foo)
        m_cursor = Mock()
        m_cursor.execute = m_execute
        m_cursor.fetchone = m_fetchone
        conn = Mock()
        conn.cursor.return_value = m_cursor

        zipped = zip(dbapi2_util.execute_query_iter(conn,
                                               "select * from somewhere"),
                     expected)
        for x, y in zipped:
            self.assertEqual(x, y)
        self.assertEqual(conn.cursor.call_count, 1)
        self.assertEqual(m_cursor.execute.call_count, 1)
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
        m_cursor = Mock()
        m_cursor.execute = m_execute
        m_cursor.fetchone = m_fetchone
        conn = Mock()
        conn.cursor.return_value = m_cursor

        zipped = zip(dbapi2_util.execute_query_iter(conn,
                                               "select * from somewhere"),
                     expected)
        for x, y in zipped:
            self.assertEqual(x, y)
        self.assertEqual(conn.cursor.call_count, 1)
        self.assertEqual(m_cursor.execute.call_count, 1)
        m_cursor.execute.assert_called_once_with("select * from somewhere",
                                                 None)

    def test_execute_no_results(self):
        m_execute = Mock()
        m_cursor = Mock()
        m_cursor.execute = m_execute
        conn = Mock()
        conn.cursor.return_value = m_cursor

        dbapi2_util.execute_no_results(
          conn,
          "insert into table (a, b, c) values (%s, %s, %s)",
          (1, 2 , 3)
        )
        self.assertEqual(conn.cursor.call_count, 1)
        self.assertEqual(m_cursor.execute.call_count, 1)
        m_cursor.execute.assert_called_once_with(
          "insert into table (a, b, c) values (%s, %s, %s)",
          (1, 2, 3)
        )

