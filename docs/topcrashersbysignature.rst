.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. index:: topcrashersbysignature

.. _topcrashersbysignature-chapter:


Top Crashers By Signature
=========================

Introduction
------------

Topcrashers By Signature compiles the 14 days' worth of crash reports
(organized by signature) for a given version. This report is useful
for finding new topcrashes, determining if topcrashes have been filed,
and seeing trending of topcrashes over time (for a specific version).

Details
-------

For the ideal topcrashers by signature report, we want to gather the
following data:

* crashes by version (e.g., Firefox 3.0.9)
* date a crash occurred (to know if it's within our window)
* stack signature
* average uptime (since last browser start) averaged over window
* bug numbers related to crash signature

Additionally, we need the ability to either a) go back in time or b)
"freeze" the topcrashers by signature report on a specific day. This
allows us to compare, say, the last day of a release to the newest
release (e.g., Firefox 3.0.8 to Firefox 3.0.9). Without the ability to
go back to a specific day of topcrash reports or freeze topcrash
reports, we have no easy ability to compare releases (as new crashes
come in for old releases, the topcrash list changes substantially).

**Ideal Outputs**

(to be filled)

See [[SocorroUIInstallation]] for additional details.

Operations
----------

* Need a recalculation every 4 to 6 hours
* Need top 500 signatures, ranked over last 14 days
* Note that this implies for the database that each slice is
  aggregated from the full window (which slides forward each time)
