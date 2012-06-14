.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

2.5.1 Database Updates
======================

This batch makes the following database changes:

bug 733489
	add dynamic views to support Metrics nightly reports
	daily crash ratio
	
bug 715676
	drop deprecated signature matviews

The above changes should take only a few minutes to deploy.
This upgrade does not require a downtime.