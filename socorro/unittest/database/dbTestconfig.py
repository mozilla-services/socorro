# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# XXX Set to be deprecated in favor of socorro/external/postgresql/models.py

## Test config file for database utilities
import socorro.lib.ConfigurationManager as cm
import datetime

from socorro.unittest.config.commonconfig \
    import databaseHost as database_hostname
from socorro.unittest.config.commonconfig \
    import oldDatabaseName as database_name
from socorro.unittest.config.commonconfig \
    import databaseUserName as database_username
from socorro.unittest.config.commonconfig \
    import databasePassword as database_password

logFilePathname = cm.Option()
logFilePathname.doc = 'full pathname for the log file'
logFilePathname.default = '%(testDir)s/logs/db_test.log'

