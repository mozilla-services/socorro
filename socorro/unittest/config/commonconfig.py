import socorro.lib.ConfigurationManager as cm
databaseHost = cm.Option()
databaseHost.doc = 'the hostname of the database servers'
databaseHost.default = 'bearmouth.local'

databaseName = cm.Option()
databaseName.doc = 'the name of the database within the server'
databaseName.default = 'breakpad4'

databaseUserName = cm.Option()
databaseUserName.doc = 'the user name for the database servers'
databaseUserName.default = 'lars'

databasePassword = cm.Option()
databasePassword.doc = 'the password for the database user'
databasePassword.default = 'Yellow84'

