2.4 Database Updates
====================

This batch makes the following database changes:

701255
    daily_crashes.sql
    update_tcbs.sql
    backfill_matviews.sql
    
    Switch the tcbs and daily_crashes cron jobs to use reports_clean
    instead of reports.