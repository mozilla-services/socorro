.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

26.0 Database Updates
=====================

This batch makes the following database changes:

bug #796153

	Remove SET parameters related to memory from all functions
	Names of functions affected are in functions.txt

	Script to generate the original function files from a dev
	database at generate_function_defs.sh

	Parameters that were removed are in param_cleanup.txt


The above changes should take only a few minutes to deploy.
This upgrade does not require a downtime.
