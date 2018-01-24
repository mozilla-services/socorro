End-to-End Tests for Socorro
============================

Continuous Integration
----------------------
This directory holds Socorro client-based end-to-end tests, which is why they're different than the rest of the code in this repository.

To review the specific-Python packages the tests use, please review
`requirements/default.txt`.

Prerequisites
-------------
These tests assume that the following software is installed:

* Pip 8.0.0 or higher

Set up and run Socorro tests
-----------------------------

Review the documentation for [pytest-selenium][pytest-selenium] and decide
which browser environment you wish to target.

* [Install Tox](https://tox.readthedocs.io/en/latest/install.html) (1.6.1 or
  higher)
* Run `tox`

An additional constraint for Firefox users: since version 48, Firefox now uses
GeckoDriver and the Marionette-backed WebDriver. You will need to make sure the
geckodriver binary ([available here][geckodriver]) is in your path. For best
results it's recommended that you use the latest stable Firefox version and the
latest geckodriver release.

If you have multiple versions of Firefox installed, you can specify which to
use by modifying your [PATH variable][path variable] so that the *directory
containing the target binary* is prioritized.

___Running the tests on stage___

	$ docker build -t socorro-tests .
  $ docker run -it socorro-tests

___Running tests against localhost___

	$ docker build -t socorro-tests .
	$ docker run -it socorro-tests pytest --base-url "http://localhost:8000"

___Running tests against production___

	$ docker build -t socorro-tests .
  $ docker run -it socorro-tests pytest --base-url "https://crash-stats.mozilla.com"

___Running tests on SauceLabs___

To use SauceLabs instead of an instance of Firefox running locally, do the following:

Create a text file called `.saucelabs` and put it in your home directory. Get a
username and key for SauceLabs and then add the following details to the
`.saucelabs` file:

```ini
[credentials]
username = <SauceLabs user name>
key = <SauceLabs API key>
```

Then you can run the tests against Sauce Labs using [Docker][] by passing the
`--driver SauceLabs` argument as shown below. The `--mount` argument is
important, as it allows your `.saucelabs` file to be accessed by the Docker
container:

```bash
  $ docker build -t socorro-tests .
  $ docker run -it \
    --mount type=bind,source=$HOME/.saucelabs,destination=/src/.saucelabs,readonly \
    socorro-tests pytest --driver SauceLabs
```

To run them against different environments, such as **production**, change
the last command, like so:
```bash
  $ docker run -it \
    --mount type=bind,source=$HOME/.saucelabs,destination=/src/.saucelabs,readonly \
    socorro-tests pytest --base-url=https://crash-stats.mozilla.com --driver SauceLabs
```

___Running tests using headless Firefox___

To run the tests using a copy of Firefox that can be run in 'headless' mode
(meaning with no UI), do the following:

Set an environment variable `MOZ_HEADLESS` to be '1'. Check the documentation
for your shell on how to do this. For zsh you can do using the following
command:

	$ export MOZ_HEADLESS=1

Then run the tests using the following command:

	$ tox -e py27

___Running specific tests___

You can run tests in a given file::

    $ tox -e py27 -- tests/test_search.py

You can run tests that match a specific name:

    $ tox -e py27 -- -k test_search_for_unrealistic_data

You can run tests whose names match a specific pattern:

    $ tox -e py27 -- -k test_search

__Output__

Output of a test run should look something like this:

    ======================== test session starts =========================
    platform linux2 -- Python 2.7.3 -- pytest-2.2.4
    collected 73 items

    tests/test_crash_reports.py .........................xx..........x.xx....x.
    tests/test_layout.py xx
    tests/test_search.py .........x.x.
    tests/test_smoke_tests.py ...........

    ============== 63 passed, 10 xfailed in 970.27 seconds ===============

The pytest plugin that we use for running tests has a number of advanced
command-line options available. To see the options available, run
`pytest --help`. The full documentation for the plugin can be found
[here][pytest-selenium].

__Troubleshooting__

If the test run hangs with Firefox open but no URL gets entered in the address
box, some combinations of the Firefox version, and the Python Selenium bindings
version may not be compatible. Upgrading each of them to latest often fixes it.

Tips and tricks
---------------

__Use a different driver__

[pytest-selenium] provides the ability to run tests against
[many other][test envs] browser environments -- consider using a different
driver executable or external provider.

It is important to note that tests must pass with Firefox driver otherwise
they will not be accepted for merging.

    $ tox -e py27 -- --driver PhantomJS --driver-path `which phantomjs` ...

[Docker]: https://www.docker.com
[pytest-selenium]: http://pytest-selenium.readthedocs.org/
[geckodriver]: https://github.com/mozilla/geckodriver/releases
[test envs]: http://pytest-selenium.readthedocs.io/en/latest/user_guide.html#specifying-a-browser
[path variable]: https://en.wikipedia.org/wiki/PATH_(variable)
