.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. index:: deferredcleanup

.. _deferredcleanup-chapter:


Deferred Cleanup
================

When the :ref:`collector-chapter` throttles the flow of crash dumps, it saves
deferred crashes into :ref:`deferredjobstorage-chapter`. These JSON/dump pairs will
live in deferred storage for a configurable number of days. It is the
task of the deferred cleanup application to implement the policy to
delete old crash dumps.

The deferred cleanup application is a command line app meant to be run
via as a cron job. It should be set to run once every twenty-four
hours.

Configuration
-------------

deferredcleanup uses the common configuration for to get the constant
deferredStorageRoot. For setup of common configuration, see
:ref:`commonconfig-chapter`.

deferredcleanup also has an executable configuration file of its own.
A sample file is found at
``.../scripts/config/deferredcleanupconfig.py.dist``. Copy this file to
``.../scripts/config/deferredcleanupconfig.py`` and edit it for site
specific settings.

In each case where a site specific value is desired, replace the value
for the .default member.

**maximumDeferredJobAge**

This constant specifies how many days deferred jobs are allowed to
stay in deferred storage. Job deletion is permanent.::

 maximumDeferredJobAge = cm.Option()
 maximumDeferredJobAge.doc = 'the maximum number of days that deferred jobs stick around'
 maximumDeferredJobAge.default = 2

**dryRun**

Used during testing and development, this prevents deferredcleanup
from actually deleting things.::

 dryRun = cm.Option()
 dryRun.doc =  "don't really delete anything"
 dryRun.default = False
 dryRun.fromStringConverter = cm.booleanConverter

**logFilePathname**

Deferredcleanup can log its actions to a set of automatically rotating
log files. This is the name and location of the logs.::

 logFilePathname = cm.Option()
 logFilePathname.doc = 'full pathname for the log file'
 logFilePathname.default = './processor.log'

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
 logFileErrorLoggingLevel.default = 20

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
