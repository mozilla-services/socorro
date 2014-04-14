.. index:: dependencies

.. _dependencies-chapter:

Dependencies
============

requirements.txt
---------------------------

All Python dependencies are tracked in one file: `requirements.txt`. It is split
into two sections, one for dev requirements and one for production.

The dev requirements are not mandatory for running Socorro at all,
but are there for people to work on the code. For example, to run the test
suites. The production requirements are there for libraries required to run the
product in a production environment.

When you land code that now needs to depend on an external piece of
code you have two options how to include it:

* Add it by package name **and exact version number** if the package
  is available on PyPi. For example::

      pyparsing==2.0.4

* Add it by git commit. If it's a "Mozilla owned" repo, first follow
  the instructions on
  "gitmirror.mozilla.org":http://gitmirror.mozilla.org/ (see Intranet
  link) then take note of the specific commit hash you want to pin it
  to. For example::

      git+git://github.com/mozilla/configman@3d74ae9#egg=configman


Mind those nested dependencies
------------------------------

Pinning exact versions is important because it makes deployment
predictable meaning that what you test and develop against locally is
exactly reflected in production.

Also, Socorro uses a `pip` wrapper called `peep`
(https://pypi.python.org/pypi/peep) which ensures that the packages
downloaded from the Python Package Index (PyPI) have not been tampered with.

Since we can't trust peep to verify itself, we ship a version in the
`./tools` directory of the Socorro repo.

Whilst it's a given that you pin the exact version of the package you
now depend on, that package might have its own dependencies and
sometimes they're not pinned to specific version. For example,
`web.py` depends on `somepackage` but doesn't state what exact
version. Therefore, it's your job to predict this before it's
installed as a nested dependency. So, do this::

    $ pip install web.py==0.36
    # or use `pip install web.py` to get the latest

    $ pip freeze

    # read the output and see what version of `somepackage`
    # gets installed.

    $ emacs requirements.txt

    peep install -r requirements.txt

    # read the output of peep, which will give you the SHA comments to paste
    # into requirements.txt

    $ emacs requirements.txt

    # finally, install your dependencies!
    peep install -r requirements.txt
