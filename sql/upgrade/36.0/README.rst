.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

36.0 Database Updates
=====================

This batch makes the following database changes:

bug #834802
	Add column to raw_adu to track receipt time

bug #843788
	Add 'raw_crashes' table to store JSON of non-throttled crashes

...

The above changes should take only a few minutes to deploy.
This upgrade does not require a downtime.
