====================
minidump-stackwalker
====================

This is the directory holding the stackwalker binaries that parse minidump
files.


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


Building with Taskcluster
=========================

The ``build-stackwalker.sh`` script will download a pre-built breakpad
client binary if possible.

To update this binary, copy the task definition from ``taskcluster_script.txt``
into the `TaskCluster task creation tool`_ and run it.

This task will update a Taskcluster index if it succeeds, such that the
most recent tarball can be fetched from:

https://index.taskcluster.net/v1/task/project.socorro.breakpad.v1.builds.linux64.latest/artifacts/public/breakpad.tar.gz

You must be a member of the ``socorro`` project in Taskcluster for this
task to work properly.

.. _TaskCluster task creation tool: https://tools.taskcluster.net/task-creator/
