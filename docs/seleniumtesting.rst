.. index:: seleniumtesting

.. _seleniumtesting-chapter:


Selenium Testing
============

There are (some, and a growing number of) Selenium tests for the Socorro code.

These tests instrument the browser, and only work against real Mozilla data
(for now). Help wanted to convert these over to the fakedata/WaterWolf set!

Installing and running Selenium
----------------

Clone the Socorro-Tests repo and install dependencies (including Selenium):
::
  git clone git://github.com/mozilla/Socorro-Tests.git
  cd Socorro-Tests
  virtualenv .virtualenv
  .virtualenv/bin/activate
  pip install -r requirements.txt

Assuming the above works and you have Firefox installed, you are ready to run
tests:
::
  py.test --baseurl=http://localhost:8000 --driver=firefox

By default this runs all tests in the tests in the ./tests/ directory, you
can restrict it to just one suite with:
::
  py.test --baseurl=http://localhost:8000 --driver=firefox tests/test_search.py

Or just a specific test with "-k":
::
  py.test --baseurl=http://localhost:8000 --driver=firefox tests/test_search.py -k test_that_search_for_valid_signature

If you are on Linux, you can run the X virtual frame buffer server in the 
background, so you are not constantly interrupted by the test browser stealing
focus (it is restarted for each test):
::
  Xvfb > xvfb.log 2>&1 &
  DISPLAY=:1 py.test --baseurl=http://localhost:8000 --driver=firefox tests/test_search.py

