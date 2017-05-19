End-to-End Tests for Socorro
============================

Continuous Integration
----------------------
[![stage](https://img.shields.io/jenkins/s/https/webqa-ci.mozilla.com/socorro.stage.svg?label=stage)](https://webqa-ci.mozilla.com/job/socorro.stage/)
[![prod](https://img.shields.io/jenkins/s/https/webqa-ci.mozilla.com/socorro.prod.svg?label=prod)](https://webqa-ci.mozilla.com/job/socorro.prod/)


This directory holds Socorro client-based end-to-end tests, which is why they're different than the rest of the code in this repository.

To review the specific-Python packages the tests use, please review `tox.ini`.

Set up and run Socorro tests
-----------------------------

Review the documentation for [pytest-selenium][pytest-selenium] and decide which browser
environment you wish to target.

* [Install Tox](https://tox.readthedocs.io/en/latest/install.html)
* Run `tox`

An additional constraint for Firefox users: since version 48, Firefox now uses GeckoDriver and the Marionette-backed WebDriver, which currently lacks feature parity with WebDriver.  In the interim (while those are being brought up to WebDriver specification), we recommend using Firefox 47.0.2 which can be [downloaded here][firefoxdownloads].

If you have multiple versions of Firefox installed, you can specify one by using the `--firefox-path <path to firefox binary>` flag.

___Running the tests on stage___

	$ tox

___Running tests against localhost___

	$ export PYTEST_BASE_URL="http://localhost:8000"
	$ tox -e py27 

	$ export PYTEST_BASE_URL="http://localhost:8000"
	$ export PYTEST_ADDOPTS="--firefox-path=/path/to/firefox/binary"
	$ tox -e py27

___Running tests against production___

	$ export PYTEST_BASE_URL="https://crash-stats.mozilla.com"
	$ tox -e py27
	
___Running tests on SauceLabs___

To use SauceLabs instead of an instance of Firefox running locally, do the following:

Create a text file called `.saucelabs` and put it in the e2e-tests directory. Get a username and key for SauceLabs and then add the following details to the `.saucelabs` file:

	[credentials]
	username = <SauceLabs user name>
	key = <SauceLabs API key>
	
Then you can run the tests against staging using the following command

	$ tox -e py27 -- --driver SauceLabs --capability browserName Firefox

If you wish to run them against different environemts, set `PYTEST_BASE_URL` as indicated in the sections above for running tests against localhost or production

___Running specific tests___

You can run tests in a given file::

    $ tox -e py27 -- tests/test_search.py

You can run tests that match a specific name:

    $ tox -e py27 -- -k test_search_for_unrealistic_data

You can run tests whose names match a specific pattern:

    $ tox -e py27 -- -k test_search

__Output__

Output of a test run should look something like this:

    ============================= test session starts ==============================
    platform linux2 -- Python 2.7.3 -- pytest-2.2.4
    collected 73 items

    tests/test_crash_reports.py .........................xx..........x.xx....x.
    tests/test_layout.py xx
    tests/test_search.py .........x.x.
    tests/test_smoke_tests.py ...........

    ============== 63 passed, 10 xfailed in 970.27 seconds ===============

__Note__
"~" will not resolve to the home directory when used in the py.test command line.

The pytest plugin that we use for running tests has a number of advanced
command-line options available. To see the options available, run
`py.test --help`. The full documentation for the plugin can be found
[here][pytest-selenium].

__Troubleshooting__

If the test run hangs with Firefox open but no URL gets entered in the address
box, some combinations of the Firefox version, and the Python Selenium bindings
version may not be compatible. Upgrading each of them to latest often fixes it.

Tips and tricks
---------------

Because Selenium opens real browser windows, it will steal focus and switch
workspaces. Firefox doesn't have a headless mode of operation, so we can't
simply turn off the UI.

__Use a different driver__

[pytest-selenium] provides the ability to run tests against [many other][test envs] browser environments -- consider using a different driver executable or external provider.

It is important to note that tests must pass with Firefox driver otherwise they will not be accepted for merging.

    $ # tests must pass with Firefox driver before submitting a pull request
    $ py.test --driver PhantomJS --driver-path `which phantomjs` ...

__xvfb__

Xvfb provides a fairly easily work around on Linux.


On Linux:

    Install Xvfb and run the tests with its xvfb-run binary. For
    example, if you run tests like::

        $ py.test ...


    You can switch to this to run with Xvfb::

        $ xvfb-run py.test ...


    This creates a virtual X session for Firefox to run in, and sets
    up all the fiddly environment variables to get this working
    well. The tests will run as normal, and no windows will open, if
    all is working right.

License
-------
This software is licensed under the [MPL] 2.0:

    This Source Code Form is subject to the terms of the Mozilla Public
    License, v. 2.0. If a copy of the MPL was not distributed with this
    file, You can obtain one at http://mozilla.org/MPL/2.0/.


[mit]: http://ocw.mit.edu/courses/electrical-engineering-and-computer-science/6-189-a-gentle-introduction-to-programming-using-python-january-iap-2011/
[dive]: http://www.diveintopython.net/toc/index.html
[firefoxtesteng]: https://quality.mozilla.org/teams/test-engineering/
[firefox]: http://quality.mozilla.org/teams/desktop-firefox/
[webdriver]: http://seleniumhq.org/docs/03_webdriver.html
[fxtest]:http://02.chat.mibbit.com/?server=irc.mozilla.org&channel=#fx-test
[GitWin]: http://help.github.com/win-set-up-git/
[GitMacOSX]: http://help.github.com/mac-set-up-git/
[GitLinux]: http://help.github.com/linux-set-up-git/
[breakpad]:http://02.chat.mibbit.com/?server=irc.mozilla.org&channel=#breakpad
[venv]: http://pypi.python.org/pypi/virtualenv
[wrapper]: http://www.doughellmann.com/projects/virtualenvwrapper/
[GitHub Templates]: https://github.com/mozilla/mozwebqa-examples
[Style Guide]: https://wiki.mozilla.org/QA/Execution/Web_Testing/Docs/Automation/StyleGuide
[MPL]: http://www.mozilla.org/MPL/2.0/
[pytest-selenium]: http://pytest-selenium.readthedocs.org/
[firefoxdownloads]: https://ftp.mozilla.org/pub/firefox/releases/47.0.2/
[test envs]: http://pytest-selenium.readthedocs.io/en/latest/user_guide.html#specifying-a-browser
