.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

9.0 Database Updates
====================

This batch makes the following database changes:

bug #748194
	Restrict product_version_builds to primary repositories.
	
bug #752074
	Add new functions for adding a manual release to releases_raw,
	and changing the featured versions.
	
...

The above changes should take only a few minutes to deploy.
This upgrade does not require a downtime.