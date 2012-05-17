.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. index:: commonconfig

.. _commonconfig-chapter:


Common Config
=============

To avoid repetition between configurations of a half dozen
independently running applications, common settings are consolidated
in a common configuration file:
``OB.../scripts/config/commonconfig.py.dist``.      

All Socorro applications have these constants available to them. For a
Socorro applications that are command line driven, each of these
default values can be overidden by a command line switch of the same
name.     

To setup this configuration file, just copy the example,
``.../scripts/config/commonconfig.py.dist`` to
``.../scripts/config/commonconfig.py``. 

Edit the file for your local situation.::

 import socorro.lib.ConfigurationManager as cm
 import datetime
 import stat

 #---------------------------------------------------------------------------
 # Relational Database Section

 databaseHost = cm.Option()
 databaseHost.doc = 'the hostname of the database servers'
 databaseHost.default = 'localhost'

 databasePort = cm.Option()
 databasePort.doc = 'the port of the database on the host'
 databasePort.default = 5432

 databaseName = cm.Option()
 databaseName.doc = 'the name of the database within the server'
 databaseName.default = ''

 databaseUserName = cm.Option()
 databaseUserName.doc = 'the user name for the database servers'
 databaseUserName.default = ''

 databasePassword = cm.Option()
 databasePassword.doc = 'the password for the database user'
 databasePassword.default = ''

 #---------------------------------------------------------------------------
 # Crash storage system

 jsonFileSuffix = cm.Option()
 jsonFileSuffix.doc = 'the suffix used to identify a json file'
 jsonFileSuffix.default = '.json'

 dumpFileSuffix = cm.Option()
 dumpFileSuffix.doc = 'the suffix used to identify a dump file'
 dumpFileSuffix.default = '.dump'

 #---------------------------------------------------------------------------
 # HBase storage system

 hbaseHost = cm.Option()
 hbaseHost.doc = 'Hostname for hbase hadoop cluster. May be a VIP or load balancer'
 hbaseHost.default = 'localhost'

 hbasePort = cm.Option()
 hbasePort.doc = 'hbase port number'
 hbasePort.default = 9090

 hbaseTimeout = cm.Option()
 hbaseTimeout.doc = 'timeout in milliseconds for an HBase connection'
 hbaseTimeout.default = 5000

 #---------------------------------------------------------------------------
 # misc

 processorCheckInTime = cm.Option()
 processorCheckInTime.doc = 'the time after which a processor is considered dead (hh:mm:ss)'
 processorCheckInTime.default = "00:05:00"
 processorCheckInTime.fromStringConverter = lambda x: str(cm.timeDeltaConverter(x))

 startWindow = cm.Option()
 startWindow.doc = 'The start of the single aggregation window (YYYY-MM-DD [hh:mm:ss])'
 startWindow.fromStringConverter = cm.dateTimeConverter

 deltaWindow = cm.Option()
 deltaWindow.doc = 'The length of the single aggregation window  ([dd:]hh:mm:ss)'
 deltaWindow.fromStringConverter = cm.timeDeltaConverter

 defaultDeltaWindow = cm.Option()
 defaultDeltaWindow.doc = 'The length of the single aggregation window  ([dd:]hh:mm:ss)'
 defaultDeltaWindow.fromStringConverter = cm.timeDeltaConverter

 # override this default for your particular cron task
 defaultDeltaWindow.default = '00:12:00'

 endWindow = cm.Option()
 endWindow.doc = 'The end of the single aggregation window (YYYY-MM-DD [hh:mm:ss])'
 endWindow.fromStringConverter = cm.dateTimeConverter

 startDate = cm.Option()
 startDate.doc = 'The start of the overall/outer aggregation window (YYYY-MM-DD [hh:mm])'
 startDate.fromStringConverter = cm.dateTimeConverter

 deltaDate = cm.Option()
 deltaDate.doc = 'The length of the overall/outer aggregation window  ([dd:]hh:mm:ss)'
 deltaDate.fromStringConverter = cm.timeDeltaConverter

 initialDeltaDate = cm.Option()
 initialDeltaDate.doc = 'The length of the overall/outer aggregation window  ([dd:]hh:mm:ss)'
 initialDeltaDate.fromStringConverter = cm.timeDeltaConverter

 # override this default for your particular cron task
 initialDeltaDate.default = '4:00:00:00'

 minutesPerSlot = cm.Option()
 minutesPerSlot.doc = 'how many minutes per leaf directory in the date storage branch'
 minutesPerSlot.default = 1

 endDate = cm.Option()
 endDate.doc = 'The end of the overall/outer aggregation window (YYYY-MM-DD [hh:mm:ss])'
 endDate.fromStringConverter = cm.dateTimeConverter

 debug = cm.Option()
 debug.doc = 'do debug output and routines'
 debug.default = False
 debug.singleCharacter = 'D'
 debug.fromStringConverter = cm.booleanConverter
