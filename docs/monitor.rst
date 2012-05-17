.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. index:: monitor

.. _monitor-chapter:


Monitor
=======

.. raw:: html

Monitor is a multithreaded application with several mandates. It's
main job is to find new JSON/dump pairs and queue them for further
processing. It looks for new JSON/dump pairs in the file system
location designated by the constant storageRoot from the
:ref:`commonconfig-chapter` file. Once it finds a pair, it queues them as a
"job" in the database 'jobs' table and assigns it to a specific
processor. Once queued, the monitor goes on to find other new jobs to
queue.

Monitor also locates and queues priority jobs. If a user requests a
report via the :ref:`reporter-chapter` and that crash report has not yet been
processed, the :ref:`reporter-chapter` puts the requested crash's UUID into
the database's 'priorityjobs' table. Monitor looks in three places for
the requested job:

* the processors - if monitor finds the job already assigned to a
  processor, it raises the priority of that job so the processor will
  do it quickly
* the storageRoot file system - if the job is found here, it queues it
  for priority processing immediately rather than waiting for standard
  mechanism to eventually find it
* the deferredStorageRoot file system - if the requested crash was
  filtered out by server side throttling, monitor will find it and
  queue it immediately from that location.

Monitor is also responsible for keeping the StandardJobStorage file
system neat and tidy. It monitors the 'jobs' queue in the database.
Once it sees that a previously queued job has been completed, it moves
the JSON/dump pairs to long term storage or it deletes them (based on
a configuration setting). Jobs that fail their further processing
stage are also either saved in a "failed" storage area or deleted.

Monitor is a command line application meant to be run continuously as
a daemon. It can log its actions to stderr and/or to automatically
rotating log files. See the configuration options below beginning with
stderr* and logFile* for more information.

The monitor app is found as ``.../scripts/monitor.py`` In order to run
monitor, the socorro package must be visible somewhere on the python
path.

Configuration
-------------

Monitor, like all the Socorro applications, uses the common
configuration for several of its constants. For setup of common
configuration, see :ref:`commonconfig-chapter`.

monitor also has an executable configuration file of its own. A sample
file is found at ``.../scripts/config/monitorconfig.py.dist``. Copy this
file to .../scripts/config/monitorconfig.py and edit it for site
specific settings.

In each case where a site specific value is desired, replace the value
for the .default member.

**standardLoopDelay**

Monitor has to scan the StandardJobStorage looking for jobs. This
value represents the delay between scans.::

 standardLoopDelay = cm.Option()
 standardLoopDelay.doc = 'the time between scans for jobs (HHH:MM:SS)'
 standardLoopDelay.default = '00:05:00'
 standardLoopDelay.fromStringConverter = cm.timeDeltaConverter

**cleanupJobsLoopDelay**

Monitor archives or deletes JSON/dump pairs from the
StandardJobStorageThis? value represents the delay between runs of the
archive/delete routines.::

 cleanupJobsLoopDelay = cm.Option()
 cleanupJobsLoopDelay.doc = 'the time between runs of the job clean up routines (HHH:MM:SS)'
 cleanupJobsLoopDelay.default = '00:05:00'
 cleanupJobsLoopDelay.fromStringConverter = cm.timeDeltaConverter

**priorityLoopDelay**

The frequency to look for priority jobs.::

 priorityLoopDelay = cm.Option()
 priorityLoopDelay.doc = 'the time between checks for priority jobs (HHH:MM:SS)'
 priorityLoopDelay.default = '00:01:00'
 priorityLoopDelay.fromStringConverter = cm.timeDeltaConverter

**saveSuccessfulMinidumpsTo**::

 saveSuccessfulMinidumpsTo = cm.Option()
 saveSuccessfulMinidumpsTo.doc = 'the location for saving successfully processed dumps (leave blank to delete them instead)'
 saveSuccessfulMinidumpsTo.default = '/tmp/socorro-sucessful'

**saveFailedMinidumpsTo**::

 saveFailedMinidumpsTo = cm.Option()
 saveFailedMinidumpsTo.doc = 'the location for saving dumps that failed processing (leave blank to delete them instead)'
 saveSuccessfulMinidumpsTo.default = '/tmp/socorro-failed'

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
