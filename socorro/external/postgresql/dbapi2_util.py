# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""short cuts for ugly Python DBAPI2 syntax"""


#==============================================================================
class SQLDidNotReturnSingleValue (Exception):
    pass


#==============================================================================
class SQLDidNotReturnSingleRow (Exception):
    pass


#------------------------------------------------------------------------------
def single_value_sql(connection, sql, parameters=None):
    a_cursor = connection.cursor()
    a_cursor.execute(sql, parameters)
    result = a_cursor.fetchall()
    try:
        return result[0][0]
    except Exception, x:
        raise SQLDidNotReturnSingleValue("%s: %s" % (str(x), sql))


#------------------------------------------------------------------------------
def single_row_sql(connection, sql, parameters=None):
    a_cursor = connection.cursor()
    a_cursor.execute(sql, parameters)
    result = a_cursor.fetchall()
    try:
        return result[0]
    except Exception, x:
        raise SQLDidNotReturnSingleRow("%s: %s" % (str(x), sql))


#------------------------------------------------------------------------------
def execute_query_iter(connection, sql, parameters=None):
    a_cursor = connection.cursor()
    a_cursor.execute(sql, parameters)
    while True:
        aRow = a_cursor.fetchone()
        if aRow is not None:
            yield aRow
        else:
            break


#------------------------------------------------------------------------------
def execute_query_fetchall(connection, sql, parameters=None):
    a_cursor = connection.cursor()
    a_cursor.execute(sql, parameters)
    return a_cursor.fetchall()


#------------------------------------------------------------------------------
def execute_no_results(connection, sql, parameters=None):
    a_cursor = connection.cursor()
    a_cursor.execute(sql, parameters)
