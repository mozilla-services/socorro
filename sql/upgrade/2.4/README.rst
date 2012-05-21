.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

2.4 Upgrade
===========

This upgrade focuses entirely on the shift to using consistent
TIMESTAMP WITH TIME ZONE and UTC dates and times throughout the
code.

701255
	Move TCBS and daily_crashes updates to depending on reports_clean
	rather than reports.
	
715333
	change all columns in all non-depricated tables to timestamptz
	instead of timestamp-without-timezone
	
	Note: this change requires a 2-hour downtime window, since
	it must be done with no concurrent access to the database 
	system.  It can take up to 2 hours to run.
	
715335
	Fix all matview generators to be UTC/timestamptz correct.
	
715342
	Drop timezone conversion functions which are no longer useful
	after conversion to default UTC.
	
IMPORTANT:  While applying these migrations, the database must be
inaccessible to users and processors (i.e.application down).

IMPORTANT: After applying changes, you must change the default timezone
for PostgreSQL to 'UTC'.
	
	

	
