.. index:: uitroubleshooting

.. _uitroubleshooting-chapter:


UI Trouble Shooting
===================

println the sql
---------------

To see what SQL queries are being executed: Edit
'webapp-php/system/libraries/Database.php' line 443 Kohana::log('debug', $sql);
Do a svn ignore on this file, if you plan on checking in code.

This will show up in the debug log 'application/logs/date.log.php'

Examine you database and see why you don't get the expected results.

404?
----

Is your '.htaccess' properly setup?


/report/pending never goes to /report/index?
--------------------------------------------

If you see a pending screen and didn't expect one this means that the
record in report and dumps couldn't be joined so it's waiting for the
processor on the backend to populate one or both tables. Investigate
with the uuid and look at reports and dump tables.


Config Files
------------

Ensure that the appropriate config files in webapp/application/config
have been copied from ``.php-dist`` to ``.php``
