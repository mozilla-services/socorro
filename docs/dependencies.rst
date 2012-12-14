.. index:: dependencies

.. _dependencies-chapter:

Dependencies
============

requirements/{dev,prod}.txt
---------------------------

All Python dependencies are tracked in two files:

* `requirements/prod.txt`

* `requirements/dev.txt`

The requirements/dev.txt are not mandatory for running Socorro at all,
but it's there for people to work on the code. For example, to run the test
suites.

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

    $ emacs requirements/prod.txt

