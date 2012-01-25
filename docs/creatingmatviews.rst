.. index:: database

.. _creatingmatviews-chapter:

Creating a New Matview
======================

A materialized view, or "matview" is the results of a query stored as a table in the PostgreSQL database.  Matviews make user interfaces much more responsive by eliminating searches over many GB or sparse data at request time.  The majority of the time, new matviews will have the following characteristics:

* they will pull data from reports_clean and/or reports_user_info
* they will be updated once per day and store daily summary data
* they will be updated by a cron job calling a stored procedure

The rest of this guide assumes that all three conditions above are true.  For matviews for which one or more conditions are not true, consult the PostgreSQL DBAs for your matview.

Do I Want a Matview?
====================

Before proceeding to construct a new matview, test the responsiveness of simply running a query over reports_clean and/or reports_user_info.  You may find that the query returns fast enough ( < 100ms ) without its own matview.  Remember to test the extreme cases: Firefox release version on Windows, or Fennec aurora version. 

Also, matviews are really only effective if they are smaller than 1/4 the size of the base data from which they are constructed.   Otherwise, it's generally better to simply look at adding new indexes to the base data.  Try populating a couple days of the matview, ad-hoc, and checking its size (pg_total_relation_size()) compared to the base table from which it's drawn.  The new signature summaries was a good example of this; the matviews to meet the spec would have been 1/3 the size of reports_clean, so we added a couple new indexes to reports_clean instead.

Components of a Matview
=======================

In order to create a new matview, you will create or modify five or six things:

1. a table to hold the matview data
2. an update function to insert new matview data once per day
3. a backfill function to backfill one day of the matview
4. add a line in the general backfill_matviews function
5. if the matview is to be backfilled from deployment, a script to do this
6. a test that the matview is being populated correctly.

Point (6) is not yet addressed by a test framework for Socorro, so we're skipping it currently.

For the rest of this doc, please refer to the template matview code sql/templates/general_matview_template.sql in the Socorro source code.

Creating the Matview Table
==========================

The matview table should be the basis for the report or screen you want.  It's important that it be able to cope with all of the different filter and grouping criteria which users are allowed to supply.  On the other hand, most of the time it's not helpful to try to have one matview support several different reports; the matview gets bloated and slow.

In general, each matview will have the following things:

* one or more grouping columns
* a report_date column
* one or more summary data columns

If they are available, all columns should use surrogate keys to lookup lists (i.e. use signature_id, not the full text of the signature).  Generally the primary key of the matview will be the combination of all grouping columns plus the report date.


