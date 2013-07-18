Clone socorro-crashstats
------------------------

    git clone https://github.com/mozilla/socorro
    cd socorro/webapp-django

Clone vendor repositories
-------------------------

    git submodule update --init --recursive

Add the LESS Preprocessor
-------------------------

You need to [install less](http://lesscss.org/#-server-side-usage) and
make sure it's available on your `PATH`.


Create virtualenv and populate it
---------------------------------

    virtualenv --python=python2.6 .virtualenv
    source .virtualenv/bin/activate
    pip install -r requirements/compiled.txt
    pip install -r requirements/dev.txt

Copy default config file and customize it
-----------------------------------------

    cp crashstats/settings/local.py-dist crashstats/settings/local.py

Run unit tests
--------------

Before running the tests, you will have to make sure your configuration has the
CACHES key set to use LocMemCache as a backend. See
``crashstats/settings/local.py-dist`` for a working example. Then you will need to compress static files, using the
following:

    ./manage.py collectstatic --noinput && ./manage.py compress_jingo --force

First running `collectstatic` and `compress_jingo` is more realistic compared
to how the production server is run. Also, it's faster.
If you want to disable static file compression you can add
``COMPRESS_OFFLINE = False`` to your ``settings/local.py``.

To run a specific test file, use for example:

    ./manage.py test crashstats/crashstats/tests/test_views.py

And to run a specific testcase, use for example:

    ./manage.py test crashstats/crashstats/tests/test_views.py:TestViews

And lastly, to run a specific test, use for example:

    ./manage.py test crashstats/crashstats/tests/test_views.py:TestViews.test_plot_signature

Run the dev server, by default will listen on http://localhost:8000
-------------------------------------------------------------------

    ./manage.py runserver

How to pretend you're Jenkins running the tests
-----------------------------------------------

If jenkins is failing and you might want to debug it locally to try to
find out what's going on. Then follow these steps:

1. `cd /tmp`
2. `git clone git://github.com/mozilla/socorro.git`
3. `cd socorro`
4. `git submodule update --init --recursive`
5. `cd webapp-django`
6. `WORKSPACE=/tmp/socorro/webapp-django ./bin/jenkins.sh`

It will take care of creating and using a virtualenv for you.


How to run coverage tests
-------------------------

There are more options available if you run `./manage.py test --help`
but this is the basic command to run coverage tests on the
`crashstats` package:

    ./manage.py test --cover-erase --with-coverage \
    --cover-package=crashstats --cover-html

That'll create `./cover/index.html` for your viewing pleasures.


Enable your pre-commit hook
---------------------------

Paste this into `.git/hooks/pre-commit`:

    check.py | grep "\s" | grep -v 'unable to detect undefined names'
    if [ "$?" -ne "1" ]
    then
        echo "Aborting commit.  Fix above errors or do 'git commit --no-verify'."
        exit 1
    fi

Then, make the file executable:

    chmod +x .git/hooks/pre-commit


Production notes
----------------
Do not use locmem cache, as it will break work of an anonymous CSRF on servers
with more than one web-server thread.
[More details](https://github.com/mozilla/django-session-csrf#differences-from-django)

