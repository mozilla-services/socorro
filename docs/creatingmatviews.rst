.. index:: database

.. _creatingmatviews-chapter:

Creating a New Matview
======================

A materialized view, or "matview" is the results of a query stored as a table in the PostgreSQL database.  Matviews make user interfaces much more responsive by eliminating searches over many GB or sparse data at request time.  The majority of the time, new matviews will have the following characteristics:

* they will pull data from reports_clean and/or reports_user_info
* they will be updated once per day and store daily summary data
* they will be updated by a cron job calling a stored procedure

The rest of this guide assumes that all three conditions above are true.  For matviews for which one or more conditions are not true, consult the PostgreSQL DBAs for your matview.

Components of a Matview
=======================

In progress ...
