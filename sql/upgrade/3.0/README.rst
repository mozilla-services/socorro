.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

3.0 Database Updates
====================

This batch makes the following database changes:

No Bug
	Add function for middleware to retrieve lists of product_versions
	from the DB.
	
729208
	Drop redundant build_date column from reports.
	
...

Bug 729208 may require locking on reports, and thus require a brief (5 minutes) processor downtime.
Aside from locking, neither should take more than a couple minutes to run.