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


Getting a build/debug shell for minidump-stackwalk
==================================================

To get a shell to build and debug minidump-stackwalk, do::

    $ make mdswshell


The files for building minidump-stackwalk are all in ``/mdsw/``.

This is a copy of the code in ``./minidump-stackwalk/`` so any changes you make
to ``/mdsw/`` things need to be copied.

To run the build script, do::

    app@socorro:/app$ cd /mdsw
    app@socorro:/mdsw$ STACKWALKDIR=/stackwalk SRCDIR=/mdsw /mdsw/scripts/build-stackwalker.sh


``vim`` and ``gdb`` are available in the shell.

Things to keep in mind with ``mdswshell``:

1. It's pretty rough and there might be issues--let us know.
2. The code in ``/mdsw/minidump-stackwalk/`` is a copy of the code in
   ``/app/minidump-stackwalk/`` so any changes you make to ``/mdsw/`` things
   need to be copied.
3. When you're done with ``mdswshell``, it makes sense to run ``make clean`` to
   clean out any extra bits from minidump-stackwalk floating around.


Build scripts
=============

The stackwalker binaries get built in the local development environment and live
in the app image in ``/stackwalk``.

If you want to build them outside of Docker, you can use these two build
scripts:

* ``scripts/build-breakpad.sh``

  This will build breakpad from source and place the resulting bits in
  ``./build/breakpad``.

* ``scripts/build-stackwalker.sh``

  This will build stackwalker.
