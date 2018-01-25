End-to-End Tests for Socorro
============================

Continuous Integration
----------------------
This directory holds Socorro client-based end-to-end tests, which is why they're different than the rest of the code in this repository.

To review the specific-Python packages the tests use, please review
`requirements/default.txt`.

How to run the tests
====================

Clone the repository
--------------------

If you have cloned this project already, then you can skip this; otherwise
you'll need to clone this repo using Git. If you do not know how to clone a
GitHub repository, check out this [help page][git clone] from GitHub.

If you think you would like to contribute to the tests by writing or
maintaining them in the future, it would be a good idea to create a fork of
this repository first, and then clone that. GitHub also has great instructions
for [forking a repository][git fork].

Set up and run Socorro tests
-----------------------------

Review the documentation for [pytest-selenium][pytest-selenium] and decide
which browser environment you wish to target.

An additional constraint for Firefox users: since version 48, Firefox now uses
GeckoDriver and the Marionette-backed WebDriver. You will need to make sure the
geckodriver binary ([available here][geckodriver]) is in your path. For best
results it's recommended that you use the latest stable Firefox version and the
latest geckodriver release.

If you have multiple versions of Firefox installed, you can specify which to
use by modifying your [PATH variable][path variable] so that the *directory
containing the target binary* is prioritized.

___Running the tests on stage___
```bash
  $ docker build -t socorro-tests .
  $ docker run -it socorro-tests
```
___Running tests against localhost___
```bash
  $ docker build -t socorro-tests .
  $ docker run -it socorro-tests pytest --base-url "http://localhost:8000"
```
___Running tests against production___
```bash
  $ docker build -t socorro-tests .
  $ docker run -it socorro-tests pytest --base-url "https://crash-stats.mozilla.com"
```
___Running tests on SauceLabs___

To use Sauce Labs instead of an instance of Firefox running locally, do the following:

Create a text file called `.saucelabs` and put it in your home directory. Get a
username and key for Sauce Labs and then add the following details to the
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
    socorro-tests pytest --base-url "https://crash-stats.mozilla.com" --driver SauceLabs
```

___Running tests using headless Firefox___

To run the tests using a copy of Firefox that can be run in 'headless' mode
(meaning with no UI), do the following:

Set an environment variable `MOZ_HEADLESS` to be '1'. Check the documentation
for your shell on how to do this. For zsh you can do using the following
command:

	$ export MOZ_HEADLESS=1

To run the tests, you will need to have the following installed:
* Python 2.7
* [Pipenv](https://pipenv.readthedocs.io)

Then run the tests using the following commands:

```bash
  $ pipenv install requirements/requirements.txt
  $ pipenv shell
  $ pytest
```

___Running specific tests___

You can run tests in a given file::

    $ docker run -it socorro-tests pytest tests/test_search.py

You can run tests that match a specific name:

    $ docker run -it socorro-tests pytest tests/test_search::TestSuperSearch::test_search_for_unrealistic_data

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


[git clone]: https://help.github.com/articles/cloning-a-repository/
[git fork]: https://help.github.com/articles/fork-a-repo/
[Docker]: https://www.docker.com
[pytest-selenium]: http://pytest-selenium.readthedocs.org/
[geckodriver]: https://github.com/mozilla/geckodriver/releases
[test envs]: http://pytest-selenium.readthedocs.io/en/latest/user_guide.html#specifying-a-browser
[path variable]: https://en.wikipedia.org/wiki/PATH_(variable)
