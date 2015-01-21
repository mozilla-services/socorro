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

You can use the "curl" command to submit a test crash. If you don't
have a minidump available, you can download a test dump from the
Socorro repo:
.. code-block:: bash
  curl -o test.dump https://raw.githubusercontent.com/mozilla/socorro/master/testcrash/raw/7d381dc5-51e2-4887-956b-1ae9c2130109.dump

Then submit it using curl's multipart-form POST support:
.. code-block:: bash
  curl -X POST -F ProductName=TestProduct \
               -F Version=1.0 \
               -F upload_file_minidump=@test.dump \
               http://crash-reports/submit

You should see a "CrashID" returned.

Attempt to pull up the newly inserted crash:
http://crash-stats/report/index/YOUR_CRASH_ID_GOES_HERE
