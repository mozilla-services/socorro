.. index:: coveragetesting

.. _coveragetesting-chapter:


Coverage Testing
================

You can do coverage testing on Socorro code.  Coverage refers to the proportion of source code that has been tested according to some criteria.  When you run coverage testing, essentially you are testing the unit tests!

How to Coverage Test 
--------------------

* Configure your test environment (see the section `How to configure your test environment`_ below)
* cd to the top level of your Socorro Crashstats checkout 
* Run the command::

        ./manage.py test --cover-erase --with-coverage --cover-package=crashstats --cover-html
* The above command is the basic way to coverage test, but more options are available if you run ``./manage.py test --help``
* Here are descriptions of the coverage options reproduced from the help page for your convenience:

  --with-coverage          Enable plugin Coverage:  Activate a coverage report
                           using Ned Batchelder's coverage module.
                           [NOSE_WITH_COVERAGE]
  --cover-package=PACKAGE  Restrict coverage output to selected packages
                           [NOSE_COVER_PACKAGE]
  --cover-erase            Erase previously collected coverage statistics before
                           run
  --cover-tests            Include test modules in coverage report
                           [NOSE_COVER_TESTS]
  --cover-inclusive        Include all python files under working directory in
                           coverage report.  Useful for discovering holes in test
                           coverage if not all files are imported by the test
                           suite. [NOSE_COVER_INCLUSIVE]
  --cover-html             Produce HTML coverage information
  --cover-html-dir=DIR     Produce HTML coverage information in dir
* The coverage tests are run using nose and Ned Batchelder's coverage module.

Results and interpretation
--------------------------

* If you run coverage testing with the ``--cover-html`` option, you can open ``./cover/index.html`` in your browser to view the results in an HTML report.  This page should show the number of lines covered, the number of lines missed, the number of lines skipped, plus the overall coverage expressed as a percentage.  The overall coverage is calculated by the formula: covered / (covered + missed).
* In the HTML report, you can click on module names for more details.  If you do so, you'll get coverage statistics for that particular module and the source code will be annotated by color.  Lines are highlighted in green for executed, in red for missing, and in gray for excluded.
* If you run coverage testing without the ``--cover-html`` option, you'll get a text summary of the above information instead.

Troubleshooting
---------------

* If you observe an error similar to::

        nose.plugins.cover: ERROR: Coverage not available: unable to import coverage module

  then this means that you need to install the Python coverage package.  Simply run the command ``pip install coverage`` 

How to configure your test environment
--------------------------------------

*THIS SECTION IN PARTICULAR MAY NEED EDITING*

* You should have 

  - Installed Python and Postgres with the required dependencies 
  - Configured Postgres and added the appropriate accounts including yourself, ``breakpad_rw`` and ``monitor`` (if not already present), with the appropriate permissions
  - Downloaded and installed Socorro
  - Downloaded and installed Crashstats UI with the required vendor repositories and dependencies 
  - Configured Socorro and Crashstats UI to be ready for running unit tests
  - Setup a virtual environment with the version of Python that is consistent with your Socorro install

* For more details, see the installation chapter :ref:`installation-chapter`.  If you follow the installation instructions from the beginning through the section "Download and install CrashStats Web UI", that should be sufficient. 
