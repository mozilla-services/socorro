.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

2.4.4 Database Updates
======================

This batch makes the following database changes:

bug 640238
	Create matview to support Nightly Builds chart.
	Requires some backfill.
	
The above changes should take only about half an hour to deploy.
This upgrade does not require a downtime.