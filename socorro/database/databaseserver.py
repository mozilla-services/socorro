# database server routines
#
#  these routines are called from within the PostgreSQL server to help partitioning triggers

import datetime as dt

#-----------------------------------------------------------------------------------------------------------------
def targetTableName (parentTableName, dateAsString):
  year = int(dateAsString[:4])
  month = int(dateAsString[5:7])
  day = int(dateAsString[8:10])
  date = dt.datetime(year, month, day)
  isoYear, isoWeek, isoDay = date.isocalendar()
  return'%s_%s%0d' % (parentTableName, year, isoWeek)

#-----------------------------------------------------------------------------------------------------------------
def targetTableInsertPlanName (tableName):
  return "%s_insert_plan" % tableName

#-----------------------------------------------------------------------------------------------------------------
def _getValueList (triggerData, savedData, plpy):
  valueList = []
  for columnName in savedData["%s_columns_types" % triggerData["table_name"]]:
    try:
      valueList.append (triggerData["new"][columnName])
    except KeyError:
      # column missing in the insert
      plpy.error("inserts to table %s requires all columns.  '%s' is missing" % (triggerData["table_name"], columnName))
  return valueList

#-----------------------------------------------------------------------------------------------------------------
def getValuesList (triggerData, savedData, plpy):
  try:
    return _getValueList (triggerData, savedData, plpy)
  except KeyError:
    savedData["%s_columns_types" % triggerData["table_name"]] = columnNameTypeDictionaryForTable(triggerData["table_name"], plpy)
    return _getValueList (triggerData, savedData, plpy)

#-----------------------------------------------------------------------------------------------------------------
def _createNewInsertQueryPlan(triggerData, savedData, targetTableName, planName, tableColumnTypesSavedDataName, plpy):
  columnList = [x for x in sorted(savedData[tableColumnTypesSavedDataName].keys())]
  typeList = [savedData[tableColumnTypesSavedDataName][x] for x in sorted(savedData[tableColumnTypesSavedDataName].keys())]
  placeHolderList = ["$%d" % x for x in range(len(typeList))]
  sql = "insert into %s (%s) values (%s)" % (targetTableName, ",".join(columnList), ",".join(placeHolderList))
  savedData[planName] = plpy.prepare(sql, typeList)

#-----------------------------------------------------------------------------------------------------------------
def createNewInsertQueryPlan (triggerData, savedData, targetTableName, planName, plpy):
  tableColumnTypesSavedDataName = "%s_columns_types" % triggerData["table_name"]
  try:
    _createNewInsertQueryPlan (triggerData, savedData, targetTableName, planName, tableColumnTypesSavedDataName, plpy)
  except KeyError:
    savedData[tableColumnTypesSavedDataName] = columnNameTypeDictionaryForTable(triggerData["table_name"], plpy)
    _createNewInsertQueryPlan (triggerData, savedData, targetTableName, planName, tableColumnTypesSavedDataName, plpy)

#-----------------------------------------------------------------------------------------------------------------
def columnNameTypeDictionaryForTable (tableName, plpy):
  return plpy.execute("""
      select
        pg_attribute.attname,
        pg_type.typname
      from
        pg_type join pg_attribute on pg_type.oid = pg_attribute.atttypid
          join pg_class on (pg_attribute.attrelid = pg_class.oid and pg_class.relname = '%s')
      where
        pg_type.typname not in ('oid', 'cid', 'tid', 'xid')
      order by
        pg_attribute.attname""" % tableName)