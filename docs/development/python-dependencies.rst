.. index:: python-dependencies

.. _python_dependencies-chapter:

Dependencies
============

requirements.txt
---------------------------

All Python dependencies are tracked in one main file; ``requirements.txt``.

To add another new package to depend on, use ``hashin`` to generate
the necessary hashes into ``requirements.txt`` based on the exact
version you need installed. To install ``hashin`` simply run
``pip install hashin``. Then, run::

    hashin mypackage==1.2.3

See below for a discussion about dependencies within the new packages
you are adding.


Mind those nested dependencies
------------------------------

Pinning exact versions is important because it makes deployment
predictable meaning that what you test and develop against locally is
exactly reflected in production.

Also, Socorro uses ``pip>=8.0`` which has the ability to checksum
check all dependencies so they are the exact same version we've
verified and tested in local development.

And to bootstrap ``pip``, we need a verified and vetted version of pip to boot,
so we've included `./tools/pipstrap.py` (see
https://github.com/erikrose/pipstrap) which makes sure we get that first
``pip`` installed securely.

The best tool to help you add all hashes needed for each package, is
``hashin`` (https://github.com/peterbe/hashin). You can install this
with ``pip install hashin``. This is something you only ever install
in your local virtual environment.

Whilst it's a given that you pin the exact version of the package you
now depend on, that package might have its own dependencies and
sometimes they're not pinned to specific version. For example,
``mypackage`` depends on ``somepackage`` but doesn't state what exact
version. Therefore, it's your job to predict this before it's
installed as a nested dependency.

The best approach is to simply let ``pip install`` find out which
dependencies you ought to install and get hashes for.

For example, if you want to add ``mypackage==1.2.3`` then first hash
it in::

    $ hashin mypackage==1.2.3
    $ tail requirements.txt  # will verify it got added

Now, check what dependencies it "failed" on::

    $ pip install --require-hashes -r requirements.txt

If for example, it said it failed because of ``dependentpackage==0.1.9``
then just add that too::

    $ hashin depdendentpackage==0.1.9

Rinse and repeat.

Keep them up to date
------------------------------

There are various tools for checking your requirements file that checks
that you're using the latest and greatest releases.

The simplest tool is ``piprot`` which is a command line tool that simply
tells you which packages (based on those actively installed) are out of date.

To run ``piprot`` simply install and run it like this::

    $ pip install piprot
    $ piprot
