# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import psycopg2
import socorro.database.schema as db_schema
import socorro.database.postgresql as db_postgresql
import sys

import socorro.unittest.testlib.util as tutil

def setup_module():
  tutil.nosePrintModule(__file__)

class TestDB:
  def __init__(self):
    self.madeConnection = False

  def maybeCloseConnection(self,connection):
    if self.madeConnection:
      self.madeConnection = False
      connection.close()

  def getCursor(self,**kwargs):
    cursor = None
    connection = None
    try:
      cursor = kwargs['cursor']
    except:
      try:
        connection = kwargs['connection']
      except:
        connection = psycopg2.connect(kwargs['dsn'])
        self.madeConnection = True
      cursor = connection.cursor()
    return cursor


  def createDB(self, config, logger):
    """Convenience: Forward to schema to get actual work done each thing in exactly one place"""
    db_schema.setupDatabase(config,logger)

  def removeDB(self, config, logger):
    """Convenience: Forward to schema to get actual work done each thing in exactly one place"""
    db_schema.teardownDatabase(config, logger)
    self.removePriorityTables(config,logger)

  def removePriorityTables(self,config,logger):
    dbCon,dbCur = db_schema.connectToDatabase(config,logger)
    priorityTableNames = db_postgresql.tablesMatchingPattern('priority_job_%%',dbCur)
    if priorityTableNames:
      sql = "DROP TABLE IF EXISTS %s CASCADE;"%(", ".join(priorityTableNames))
      dbCur.execute(sql)
      dbCon.commit()
    else:
      logger.info("There were no priority_job tables to close")

  def populateDB(self,**kwargs):
    cursor = self.getCursor(**kwargs)
    print >> sys.stderr, "PopulateDB() Not yet implemented"
    self.maybeCloseConnection(cursor.connection)


