End-to-End Tests for Socorro
============================

Continuous Integration
----------------------
[![stage](https://img.shields.io/jenkins/s/https/webqa-ci.mozilla.com/socorro.stage.svg?label=stage)](https://webqa-ci.mozilla.com/job/socorro.stage/)
[![prod](https://img.shields.io/jenkins/s/https/webqa-ci.mozilla.com/socorro.prod.svg?label=prod)](https://webqa-ci.mozilla.com/job/socorro.prod/)


This directory holds Socorro client-based end-to-end tests which is why they're different than the rest of the code in this repository.

To review the specific Python packages the tests utilize, please review `requirements.txt`.

Set up and run Socorro tests
-----------------------------

Review the documentation for [pytest-selenium][pytest-selenium] and decide which browser
environment you wish to target.

We suggest using a different virtual environment for these tests than the
rest of Socorro so you're not mixing requirements:

	$ mkvirtualenv socorro-tests
	$ # make sure you DON'T run the next command in
	$ # your dev virtualenv.
	$ pip install -r requirements.txt

An additional constraint for Firefox users, with the release of Firefox 48, Webdriver support is currently broken until GeckoDriver is out of Alpha. We suggest using an older version of Firefox which can be [downloaded here][firefoxdownloads].

If you have multiple versions of Firefox installed, you can specifiy a specific one by using the `--firefox-path <path to firefox binary>` flag.

___Running the tests on stage___

	$ py.test --driver Firefox tests/

___Running tests against localhost___

	$ py.test --driver Firefox --base-url http://localhost:8000 tests/
	$ py.test --driver Firefox --firefox-path /path/to/firefox/binary --base-url http://localhost:8000 tests/

___Running tests against production___

	$ py.test --driver Firefox --base-url https://crash-stats.mozilla.com tests/

___Running specific tests___

You can run tests in a given file::

    $ py.test --driver Firefox tests/desktop/test_search.py

You can run tests that match a specific name:

    $ py.test --driver Firefox -k test_search_for_unrealistic_data

You can run tests whose names match a specific pattern:

    $ py.test --driver Firefox -k test_search

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
command line options available. To see the options available, run
`py.test --help`. The full documentation for the plugin can be found
[here][pytest-selenium].

__Troubleshooting__

If the test run hangs with Firefox open but no URL gets entered in the address
box, some combinations of the Firefox version, and the python Selenium bindings
version may not be compatible. Upgrading each of them to latest often fixes it.

Tips and tricks
---------------

Because Selenium opens real browser windows, it will steal focus and switch
workspaces. Firefox doesn't have a headless mode of operation, so we can't
simply turn off the UI.

__Generate HTML report__

If you add `--html /tmp/selenium/index.html` to the `py.test` command it
generates a useful report that has the HTML and a screenshot of the page
right before an exception happened.

__Use a different driver__

[pytest-selenium] provides the ability to run tests against [many other][test envs] browser environments -- consider using a different driver executable or external provider.

It is important to note that tests must pass with Firefox driver otherwise they will not be accepted for merging.

    $ # tests must pass with Firefox driver before submitting a pull request
    $ py.test --driver PhantomJS --driver-path `which phantomjs` ...

__xvfb__

Xvfb provides a fairly easily work around on Linux.


On Linux:

    Install Xvfb and run the tests with it's xvfb-run binary. For
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
[mozwebqa]:http://02.chat.mibbit.com/?server=irc.mozilla.org&channel=#mozwebqa
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
[firefoxdownloads]: https://ftp.mozilla.org/pub/firefox/releases/44.0.2/
[test envs]: http://pytest-selenium.readthedocs.io/en/latest/user_guide.html#specifying-a-browser
