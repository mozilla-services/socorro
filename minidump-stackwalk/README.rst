====================
minidump-stackwalker
====================

This directory (`minidump-stackwalk/`) holds the stackwalker binaries that
parse minidump files.


Usage
=====

dumplookup
----------

FIXME(willkg): Document this.

For help, do::

  $ dumplookup --help


stackwalker
-----------

Parses the minidump and spits out information about the crash, crashing thread,
and stacks.

Example::

  $ stackwalker --pretty <MINDUMPFILE>


For help, do::

  $ stackwalker --help


jit-crash-categorize
--------------------

States whether the minidump represents a JIT crash.

Example::

  $ jit-crash-categorize <MINIDUMPFILE>


Building
========

The stackwalker binaries get built in the local development environment and live
in the app image in ``/stackwalk``.

If you want to build them outside of Docker, you can use these two build
scripts:

* ``scripts/build-breakpad.sh``

  This will build breakpad from source and place the resulting bits in
  ``./build/breakpad``.

* ``scripts/build-stackwalker.sh``

  This will build stackwalker.
