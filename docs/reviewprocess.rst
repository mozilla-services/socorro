.. index:: reviewprocess

.. _reviewprocess-chapter:

How to Review a Pull Request
============================

Part of our job as developers is to review and provide feedback on what
our colleagues do. The goal of this process is to:

    * test that a new feature works as expected
    * make sure the code is clean
    * make sure the code doesn't break anything

Here are several steps you can follow when reviewing a pull request. Depending
on the size of that pull request, you might want to skip some phases.

Read the code
-------------

The first task when reviewing is to read the code and verify that it is
coherent and clean. Try to understand the algorithm and its goal, make sure
that it is what was asked in the related bug. When there is something that
you find non-trivial and that is not documented, ask for a doc-string or
an inline comment so it becomes easier for others to understand the code.

Pull the code into your local environment
-----------------------------------------

To go on testing, you will need to have the code in your local environment.
Let's say you want to test the branch ``my-dev-branch`` of rhelmer's git
repository. Here is one method to get the content of that remote branch into
your repo::

    git remote add rhelmer https://github.com/rhelmer/socorro.git # the first time only
    git fetch rhelmer my-dev-branch:my-dev-branch
    git checkout my-dev-branch

Once you are in that branch, you can actually test the code or run tools on it.

Use a code quality tool
-----------------------

Running a code quality tool is a good and easy way to find coding  and styling
problems. For Python, we use ``check.py`` (`check by jbalogh on github
<https://github.com/jbalogh/check>`_). This tool will run `pyflakes
<http://pypi.python.org/pypi/pyflakes>`_ on a file or a folder, and will then
check that PEP 8 is respected.

To install ``check.py``, run the following command::

    pip install -e git://github.com/jbalogh/check.git#egg=check

Run the unit tests
------------------

Socorro has a growing number of unit tests that are very helpful at verifying
nothing breaks. Before approving and merging a pull request, you should run
all unit tests to make sure they still pass.

Note that those unit tests will be run when the pull request is merged, but
it is easier to fix something before it lands on master than after.

To run the unit tests in a Vagrant VM, do the following::

    make test

This installs all the dependencies needed and run all the tests. You need to
have a running PostgreSQL instance for this to work, with a specific config
file for the tests in ``socorro/unittest/config/commonconfig.py``.

For further documentation on unit tests, please read :ref:`unittesting-chapter`.

Test manually
-------------

This is not always possible in a local environment, but when it is you
should make sure the new code behave as expected. Read :ref:`applychanges-label`.

Test before
-----------

This is a process to verify that one's work is good and can go into master
with little risk of breaking something. However, the developer is responsible
for his or her bug and that review process doesn't mean he or she shouldn't
go through all these steps. The reviewer is here to make sure the developer
didn't miss something, but it's easier to fix something before a review
process than after. Please test your code before opening a pull request!
