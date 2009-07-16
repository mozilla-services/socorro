#-----------------------------------------------------------------------------------------------------------------
def tablesMatchingPattern(tableNamePattern, databaseCursor):
  """ return a list of the names of all indexes for the given table"""
  databaseCursor.execute("""
      select
          ct.relname
      from
          pg_class ct
      where
          ct.relname like '%s'
          and ct.reltype <> 0""" % tableNamePattern)
  return [x[0] for x in databaseCursor.fetchall()]

#-----------------------------------------------------------------------------------------------------------------
def triggersForTable(tableName, databaseCursor):
  """ return a list of the names of all indexes for the given table"""
  databaseCursor.execute("""
      select
          pg_trigger.tgname
      from
          pg_trigger join pg_class on pg_trigger.tgrelid = pg_class.oid and pg_class.relname = '%s'""" % tableName)
  return [x[0] for x in databaseCursor.fetchall()]

#-----------------------------------------------------------------------------------------------------------------
def indexesForTable(tableName, databaseCursor):
  """ return a list of the names of all indexes for the given table"""
  databaseCursor.execute("""
      select
          it.relname
      from
          pg_class ct join pg_index i on ct.oid = i.indrelid and ct.relname = '%s'
              join pg_class it on it.oid = i.indexrelid""" % tableName)
  return [x[0] for x in databaseCursor.fetchall()]

#-----------------------------------------------------------------------------------------------------------------
def rulesForTable(tableName, databaseCursor):
  """ return a list of the names of all rules for the given table"""
  databaseCursor.execute("""
      select
          rulename
      from
          pg_rules
      where
          tablename = '%s'""" % tableName)
  return [x[0] for x in databaseCursor.fetchall()]

#-----------------------------------------------------------------------------------------------------------------
def constraintsAndTypeForTable(tableName, databaseCursor):
  """return a list of (constraintName, constraintType) tuples for the given table"""
  databaseCursor.execute("""
      select
          conname,
          contype
      from
          pg_constraint cn join pg_class cls on cn.conrelid = cls.oid and cls.relname = '%s'""" % tableName)
  return [x for x in databaseCursor.fetchall()]

#-----------------------------------------------------------------------------------------------------------------
def columnNameTypeDictionaryForTable (tableName, databaseCursor):
  """ return a dictionary of column types keys by column name"""
  databaseCursor.execute("""
      select
        pg_attribute.attname as columnname,
        pg_type.typname as columntype
      from
        pg_type join pg_attribute on pg_type.oid = pg_attribute.atttypid
          join pg_class on (pg_attribute.attrelid = pg_class.oid and pg_class.relname = '%s')
      where
        pg_type.typname not in ('oid', 'cid', 'tid', 'xid')
      order by
        pg_attribute.attname""" % tableName)
  namesToTypesDict = {}
  for aRow in databaseCursor.fetchall():
    namesToTypesDict[aRow[0]] = aRow[1]
  return namesToTypesDict

#-----------------------------------------------------------------------------------------------------------------
def childTablesForTable(tableName, databaseCursor):
  """ return a list of tables that are children (via inherits) for the given table"""
  databaseCursor.execute("""
      select
          cls1.relname
      from
          pg_class cls1 join pg_inherits inh on cls1.oid = inh.inhrelid
              join pg_class cls2 on inh.inhparent = cls2.oid and cls2.relname = '%s'""" % tableName)
  return [x[0] for x in databaseCursor.fetchall()]

def connectionStatus(aConnection):
  """Debugging aid. Particularly note transaction status of 'INTRANS' and 'INERROR'"""
  statusStrings = {
    0:'SETUP', 1:'READY', 2:'BEGIN', 3:'SYNC',4:'ASYNC',
    }
  transStatusStrings = {
    0:'IDLE', 1:'ACTIVE', 2:'INTRANS', 3:'INERROR', 4:'UNKNOWN',
    }
  return "Status: %s, Transaction Status: %s"%(statusStrings.get(aConnection.status,'UNK'),transStatusStrings.get(aConnection.get_transaction_status(),"UNK"))

def getSequenceNameForColumn(tableName, columnName, cursor):
  """
  Return the name of the sequence which provides defaults for columns of type serial
  returns None if the values don't identify a column that owns a sequence
  Does NOT commit() the connection.
  Thanks to postgres experts Jonathan Daugherty and  Alvaro Herrera
  http://archives.postgresql.org/pgsql-general/2004-10/msg01375.php # Re: determine sequence name for a serial
  """
  sql = """SELECT seq.relname::text
             FROM pg_class src, pg_class seq, pg_namespace, pg_attribute, pg_depend
             WHERE
               pg_depend.refobjsubid = pg_attribute.attnum AND
               pg_depend.refobjid = src.oid AND
               seq.oid = pg_depend.objid AND
               src.relnamespace = pg_namespace.oid AND
               pg_attribute.attrelid = src.oid AND
               pg_namespace.nspname = 'public' AND
               src.relname = %s AND
               pg_attribute.attname = %s"""
  cursor.execute(sql,(tableName,columnName))
  data = cursor.fetchone()
  if data:
    data = data[0]
  return data

def getCurrentValue(tableName, columnName, cursor):
  """
  Find out which (id) was most recently set for a table and column name. Else None if unavailable.
  Does NOT commit() the connection
  ----
  NOTE: 'SELECT lastval()' is often better: http://www.postgresql.org/docs/8.3/interactive/functions-sequence.html
  """
  ret = None
  seq = getSequenceNameForColumn(tableName,columnName,cursor)
  if seq:
    try:
      cursor.execute("SELECT currval(%s)",(seq,))
      ret = cursor.fetchone()[0]
    except:
      ret = None
  return ret
