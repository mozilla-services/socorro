.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. index:: server

.. _server-chapter:

Server
======

The Socorro Server is a collection of Python applications and a Python
package ([[SocorroPackage]]) that runs the backend of the Socorro system.


The Applications
----------------

Executables for the applications are generally found in the
.../scripts directory.

* ../scripts/startCollector.py - :ref:`collector-chapter`
* ../scripts/startDeferredCleanup.py - :ref:`deferredcleanup-chapter`
* ../scripts/startMonitor.py - :ref:`monitor-chapter`
* ../scripts/startProcessor.py - :ref:`processor-chapter`
* ../scripts/startTopCrashes.py - :ref:`topcrashersbysignature-chapter`
* ../scripts/startBugzilla.py - BugzillaAssociations
* ../scripts/startMtfb.py - MeanTimeBeforeFailure
* ../scripts/startServerStatus.py - server status
* ../scripts/startTopCrashByUrl.py - :ref:`topcrashersbyurl-chapter`
