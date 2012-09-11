Clone socorro-crashstats
--------

    git clone https://github.com/mozilla/socorro-crashstats
    cd socorro-crashstats

Clone vendor repositories
--------

    git submodule update --init --recursive

Add the LESS Preprocessor
-------------------------

You need to [install less](http://lesscss.org/#-server-side-usage) and
make sure it's available on your `PATH`.


Create virtualenv and populate it
--------

    virtualenv .virtualenv
    source .virtualenv/bin/activate
    pip install -r requirements/compiled.txt
    pip install -r requirements/dev.txt

Copy default config file and customize it
--------

    cp crashstats/settings/local.py-dist crashstats/settings/local.py

Run unit tests
--------

To run a specific test file, use for example:

    ./manage.py test crashstats/crashstats/tests/test_views.py

And to run a specific testcase, use for example:

    ./manage.py test crashstats/crashstats/tests/test_views.py:TestViews

And lastly, to run a specific test, use for example:

    ./manage.py test crashstats/crashstats/tests/test_views.py:TestViews.test_plot_signature

Run the dev server, by default will listen on http://localhost:8000
--------

    ./manage.py runserver
