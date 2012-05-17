.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. index:: databasesetup

.. _databasesetup-chapter:


Database Setup
==============


This app is under development. For progress information see: `Bugzilla
454438 <https://bugzilla.mozilla.org/show_bug.cgi?id=454438>`_

This is an application that will set up the PostgreSQL database schema
for Socorro. It starts with an empty database and creates all the
tables, indexes, constraints, stored procedures and triggers needed to
run a Socorro instance.     

Before this application can be run, however, there have been set up a
regular user that will be used for the day to day operations. While it
is not recommended that the regular user have the full set of super
user privileges, the regular user must be privileged enough to create
tables within the database.      

Before the application that sets up the database can be run, the
:ref:`commonconfig-chapter` must be set up. The configuration file for this
app itself is outlined at the end of this page.     


Running the setupDatabase app
-----------------------------

``.../scripts/setupDatabase.py``

Configuring setupDatabase app
-----------------------------

This application relies on its own configuration file as well as the
common configuration file :ref:`commonconfig-chapter`.     

copy the ``.../scripts/config/setupdatabaseconfig.py.dist`` file to
``.../scripts/config/setupdatabase.py`` and edit the file to make site
specific changes.     

**logFilePathname**

Monitor can log its actions to a set of automatically rotating log
files. This is the name and location of the logs.::

 logFilePathname = cm.Option()
 logFilePathname.doc = 'full pathname for the log file'
 logFilePathname.default = './monitor.log'

**logFileMaximumSize**

This is the maximum size in bytes allowed for a log file. Once this
number is achieved, the logs rotate and a new log is started.:: 

 logFileMaximumSize = cm.Option()
 logFileMaximumSize.doc = 'maximum size in bytes of the log file'
 logFileMaximumSize.default = 1000000

**logFileMaximumBackupHistory**

The maximum number of log files to keep.::

 logFileMaximumBackupHistory = cm.Option()
 logFileMaximumBackupHistory.doc = 'maximum number of log files to keep'
 logFileMaximumBackupHistory.default = 50

**logFileLineFormatString**

A Python format string that controls the format of individual lines in
the logs::

 logFileLineFormatString = cm.Option()
 logFileLineFormatString.doc = 'python logging system format for log file entries'
 logFileLineFormatString.default = '%(asctime)s %(levelname)s - %(message)s'

**logFileErrorLoggingLevel**

Logging is done in severity levels - the lower the number, the more
verbose the logs.::

 logFileErrorLoggingLevel = cm.Option()
 logFileErrorLoggingLevel.doc = 'logging level for the log file (10 - DEBUG, 20 - INFO, 30 - WARNING, 40 - ERROR, 50 - CRITICAL)'
 logFileErrorLoggingLevel.default = 10

**stderrLineFormatString**

In parallel with creating log files, Monitor can log to stderr. This
is a Python format string that controls the format of individual lines
sent to stderr.::

 stderrLineFormatString = cm.Option()
 stderrLineFormatString.doc = 'python logging system format for logging to stderr'
 stderrLineFormatString.default = '%(asctime)s %(levelname)s - %(message)s'

**stderrErrorLoggingLevel**

Logging to stderr is done in severity levels independently from the
log file severity levels - the lower the number, the more verbose the
output to stderr.::

 stderrErrorLoggingLevel = cm.Option()
 stderrErrorLoggingLevel.doc = 'logging level for the logging to stderr (10 - DEBUG, 20 - INFO, 30 - WARNING, 40 - ERROR, 50 - CRITICAL)'
 stderrErrorLoggingLevel.default = 40

