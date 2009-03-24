## Test config file for database utilities
import socorro.lib.ConfigurationManager as cm
import datetime

databaseHost = cm.Option()
databaseHost.doc = 'the hostname of the database servers'
databaseHost.default = 'localhost'

databaseName = cm.Option()
databaseName.doc = 'the name of the database within the server'
databaseName.default = 'test'

databaseUserName = cm.Option()
databaseUserName.doc = 'the user name for the database servers'
databaseUserName.default = 'test'

databasePassword = cm.Option()
databasePassword.doc = 'the password for the database user'
databasePassword.default = 't3st'

logFilePathname = cm.Option()
logFilePathname.doc = 'full pathname for the log file'
logFilePathname.default = '%(testDir)s/logs/db_test.log'

