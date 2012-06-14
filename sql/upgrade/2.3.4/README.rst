.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

2.3.4 Database Updates
======================

This batch makes the following database changes:

703416
	edit_product_info_log.sql
	
	Add logging to edit_product_info so that we can log whether
	it's users causing the outages.
	
701255
	removed from 2.3.4; not ready for freeze
	
697669
	version_sort_prep.sql
	product_views.sql
	
	Modify the product views to have a consistent sort column
	across both old and new products.
	
703429
	truncate_reports_bad.sql
	update_reports_clean.sql*
	
	Add automated trimming of the reports_bad audit table.
	
703731
	fix_tz_functions.sql
	
	Fix date-tz conversion functions to work on days when
	DST is beginning or ending.
	
704630
	unknown.sql
	update_reports_clean.sql*
	
	Fix reports_clean to count corrupt dumps.

None of the above require backfilling, so this should be a fast migration.

* this script is called by more than one feature, so removing one of the two features will require some rewriting.