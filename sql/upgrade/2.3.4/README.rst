2.3.4 Database Updates
======================

This batch makes the following database changes:

703416
	edit_product_info_log.sql
	
	Add logging to edit_product_info so that we can log whether
	it's users causing the outages.
	
701255
	daily_crashes.sql
	update_tcbs.sql
	
	Switch the tcbs and daily_crashes cron jobs to use reports_clean
	instead of reports.
	
697669
	version_sort_prep.sql
	product_views.sql
	
	Modify the product views to have a consistent sort column
	across both old and new products.
	
703429
	truncate_reports_bad.sql
	update_reports_clean.sql
	
	Add automated trimming of the reports_bad audit table.

None of the above require backfilling, so this should be a fast migration.