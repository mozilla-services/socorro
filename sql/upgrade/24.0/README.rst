.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

24.0 Database Updates
=====================

This batch makes the following database changes:

bug #768059
	provide new data access for Crashkill to do stability reports.
	also fix permissions on some new matviews for their access.

...

The above changes should take only a few minutes to deploy.
This upgrade does not require a downtime.

However, after applying the update, you will need to do a backfill
of the product_adu and crashes_by_user views, probably back 4 weeks.