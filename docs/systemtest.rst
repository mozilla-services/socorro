.. index:: systemtest

.. _systemtest-chapter:

System Test
-----------

Generate a test crash:

1) Install http://code.google.com/p/crashme/ add-on for Firefox
2) Point your Firefox install at http://crash-reports/submit

Note: crashme is `currently not working on Mac OS X <https://bugzilla.mozilla.org/show_bug.cgi?id=1086624>`_. The workaround is to kill the Firefox process manually in the Terminal:

.. code-block:: bash

    $ kill -ABRT <firefox pid>

Also see: https://developer.mozilla.org/en/Environment_variables_affecting_crash_reporting

If you already have a crash available and wish to submit it, you can
use the standalone submitter tool (there is an example JSON and dump
file for your crash are in the "./testcrash" directory you can use)
::
  python socorro/collector/submitter_app.py -u http://crash-reports/submit -s ./testcrash/raw/

You should get a "CrashID" returned.

Attempt to pull up the newly inserted crash:
http://crash-stats/report/index/YOUR_CRASH_ID_GOES_HERE
