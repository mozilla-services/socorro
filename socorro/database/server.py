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
  weekDay = date.weekday()
  if weekDay:
    date = date - dt.timedelta(weekDay) # begin on Monday before minDate
  return'%s_%4d%02d%02d' %  ((parentTableName,) + date.timetuple()[:3])

#-----------------------------------------------------------------------------------------------------------------
def targetTableInsertPlanName (tableName):
  return "%s_insert_plan" % tableName

#-----------------------------------------------------------------------------------------------------------------
def columnAndTypeInformation (tableName, savedData, plpy):
  keyForColumnAndTypeDictionary = "%s_ColumnAndTypeDictionary" % tableName
  keyForSortedColumnList = "%s_SortedColumnList" % tableName
  try:
    return (savedData[keyForColumnAndTypeDictionary], savedData[keyForSortedColumnList])
  except KeyError:
    columnAndTypeDict = savedData[keyForColumnAndTypeDictionary] = columnNameTypeDictionaryForTable(tableName, plpy)
    #sortedColumnList = savedData[keyForSortedColumnList] = [x for x in sorted(columnAndTypeDict.keys()) if x != 'id']
    sortedColumnList = savedData[keyForSortedColumnList] = [x for x in sorted(columnAndTypeDict.keys())]
    return (columnAndTypeDict, sortedColumnList)

#-----------------------------------------------------------------------------------------------------------------
def getValuesList (triggerData, savedData, plpy):
  columnAndTypeDictionary, sortedColumnList = columnAndTypeInformation(triggerData["table_name"], savedData, plpy)
  valueList = []
  for columnName in sortedColumnList:
    try:
      #plpy.info("%s - %s" % (columnName, triggerData["new"][columnName]))
      valueList.append (triggerData["new"][columnName])
    except KeyError, x:
      # column missing in the insert
      if x != 'id':
        plpy.error("inserts to table %s requires all columns except 'id'.  '%s' is missing" % (triggerData["table_name"], columnName))
  return valueList

#-----------------------------------------------------------------------------------------------------------------
def createNewInsertQueryPlan (triggerData, savedData, targetTableName, planName, plpy):
  #plpy.info("making columnList")
  columnAndTypeDictionary, sortedColumnList = columnAndTypeInformation(triggerData["table_name"], savedData, plpy)
  #plpy.info("column list: %s" % ",".join(sortedColumnList))
  #plpy.info("making typeList")
  typeList = [columnAndTypeDictionary[x] for x in sortedColumnList]
  #plpy.info("making placeHolderList")
  placeHolderList = ["$%d" % (x+1,) for x in range(len(typeList))]
  sql = "insert into %s (%s) values (%s)" % (targetTableName, ",".join(sortedColumnList), ",".join(placeHolderList))
  #plpy.info(sql)
  return plpy.prepare(sql, typeList)

#-----------------------------------------------------------------------------------------------------------------
def columnNameTypeDictionaryForTable (tableName, plpy):
  result = plpy.execute("""
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
  for aRow in result:
    #plpy.info(str(aRow))
    namesToTypesDict[aRow['columnname']] = aRow['columntype']
  return namesToTypesDict
