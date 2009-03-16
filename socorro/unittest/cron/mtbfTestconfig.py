## Test config file for testMtbf
import socorro.lib.ConfigurationManager as cm
import datetime

processingDay = cm.Option()
processingDay.doc = 'Day to process in (YYYY-MM-DD) format'
processingDay.default = (datetime.date.today() - datetime.timedelta(1)).isoformat() # yesterday
processingDay.singleCharacter = 'd'

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
logFilePathname.default = '%(testDir)s/logs/mtbf_test.log'

mtbfTables = cm.Option()
mtbfTables.doc = 'The tables to create before or destroy after testing'
mtbfTables.default = ['productdims','mtbfconfig','mtbffacts',]
