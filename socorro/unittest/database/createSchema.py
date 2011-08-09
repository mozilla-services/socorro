#! /usr/bin/env python
"""
Just set up the database and exit. Assume we can get config details from the test config file, but allow sys.argv to override
"""
import logging
import sys
import socorro.lib.ConfigurationManager as configurationManager
from socorro.unittest.testlib.testDB import TestDB
import dbTestconfig as testConfig

def help():
  print """Usage: (python) createSchema.py [config-options] [--help]
First removes all the known socorro tables, then creates an instance of
the current socorro schema in an existing database. Does NOT drop tables
other than the ones known to this schema.
Default: use current unittest config for host, database, user and password.
  --help: print this message and exit
  config-options: You may pass any of the following:
    [--]host=someHostName
    [--]dbname=someDatabaseName
    [--]user=someUserName
    [--]password=somePassword
  """

def main():
  logger = logging.getLogger("topcrashes_summary")
  logger.setLevel(logging.WARNING)
  
  stderrLog = logging.StreamHandler()
  stderrLog.setLevel(logging.WARNING)
  stderrLogFormatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
  stderrLog.setFormatter(stderrLogFormatter)
  logger.addHandler(stderrLog)

  kwargs = {}
  for i in sys.argv[1:]:
    if i.startswith('-h') or i.startswith('--he'):
      help()
      sys.exit(0)
    j = i
    if i.startswith('-'):
      j = i.lstrip('-')
    if '=' in j:
      name,value = (s.strip() for s in j.split('='))
      kwargs[name] = value
    else:
      print >> sys.stderr,"Ignoring unkown argument '%s'"%(i)
  sys.argv = sys.argv[:1]
  config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Create Database')
  config.update(kwargs)
  testDB = TestDB()
  testDB.removeDB(config,logger)
  testDB.createDB(config,logger)

if __name__ == '__main__':
  main()

