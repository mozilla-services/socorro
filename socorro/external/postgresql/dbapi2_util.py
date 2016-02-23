# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""short cuts for ugly Python DBAPI2 syntax"""

from collections import Sequence


#==============================================================================
class SQLDidNotReturnSingleValue (Exception):
    pass


#==============================================================================
class SQLDidNotReturnSingleRow (Exception):
    pass


#==============================================================================
class FetchAllSequence(Sequence):
    """A sequence wrapper for results of a PG cursor's fetchall()
    that when supplied with the cursor description gives you an
    iterable that works the same as regular fetchall() but
    also offers the convenience method zipped().

    You can use this like this::

        >>> sql = "select col1, col2 from some_table"
        >>> cursor = connection.cursor()
        >>> cursor.excute(sql, ())
        >>> seq = FetchAllSequence(cursor.fetchall(), cursor.description)
        >>> seq.zipped()
        [{'col1': value1, 'col2': value2}, {'col1': valueA, 'col2': valueB}]

    """

    def __init__(self, rows, description):
        self.rows = rows
        self.description = description

    def __getitem__(self, index):
        return self.rows[index]

    def __len__(self):
        return len(self.rows)

    def __contains__(self, value):
        return value in self.rows

    def __iter__(self):
        for x in self.rows:
            yield x

    def __str__(self):
        return str(self.rows)

    def zipped(self):
        names = [x.name for x in self.description]
        return [dict(zip(names, x)) for x in self.rows]


#------------------------------------------------------------------------------
def single_value_sql(connection, sql, parameters=None):
    with connection.cursor() as a_cursor:
        a_cursor.execute(sql, parameters)
        result = a_cursor.fetchall()
        try:
            return result[0][0]
        except Exception, x:
            raise SQLDidNotReturnSingleValue("%s: %s" % (str(x), sql))


#------------------------------------------------------------------------------
def single_row_sql(connection, sql, parameters=None):
    with connection.cursor() as a_cursor:
        a_cursor.execute(sql, parameters)
        result = a_cursor.fetchall()
        try:
            return result[0]
        except Exception, x:
            raise SQLDidNotReturnSingleRow("%s: %s" % (str(x), sql))


#------------------------------------------------------------------------------
def execute_query_iter(connection, sql, parameters=None):
    with connection.cursor() as a_cursor:
        a_cursor.execute(sql, parameters)
        while True:
            aRow = a_cursor.fetchone()
            if aRow is not None:
                yield aRow
            else:
                break


#------------------------------------------------------------------------------
def execute_query_fetchall(connection, sql, parameters=None):
    with connection.cursor() as a_cursor:
        a_cursor.execute(sql, parameters)
        return FetchAllSequence(
            a_cursor.fetchall(),
            a_cursor.description
        )


#------------------------------------------------------------------------------
def execute_no_results(connection, sql, parameters=None):
    with connection.cursor() as a_cursor:
        a_cursor.execute(sql, parameters)
