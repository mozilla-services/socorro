.. index:: systemtest

.. _systemtest-chapter:

System Test
-----------

Generate a test crash:

1) Install http://code.google.com/p/crashme/ add-on for Firefox
2) Point your Firefox install at http://crash-reports/submit

Note that if you're running a dev install (e.g. "honcho start") and 
not under Apache, you'll need to specify the port number:

http://crash-reports:5100/submit

See: https://developer.mozilla.org/en/Environment_variables_affecting_crash_reporting

If you already have a crash available and wish to submit it, you can
use the standalone submitter tool (there is an example JSON and dump
file for your crash are in the "./testcrash" directory you can use)
::
  python socorro/collector/submitter_app.py -u http://crash-reports/submit -s ./testcrash/raw/

You should get a "CrashID" returned.

Attempt to pull up the newly inserted crash:
http://crash-stats/report/index/YOUR_CRASH_ID_GOES_HERE
