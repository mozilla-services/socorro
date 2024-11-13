.. _stage_submitter-chapter:

===============
Stage Submitter
===============

Code is in ``socorro/stage_submitter/``.

Run script is in ``/app/bin/run_service_stage_submitter.sh``.

The stage submitter runs in the production environment to send a subset of
crash reports to a stage environment. The payloads are built from raw crash
data such that they are very much like the original payload the production
collector received.


Configuration
=============

Re-uses processor configuration for queue and storage.

Additionally has:

.. everett:option:: STAGE_SUBMITTER_LOGGING_LEVEL
   :default: ``"INFO"``
   :parser: ``str``

   Default logging level for the stage submitter. Should be one of DEBUG, INFO,
   WARNING, ERROR.


.. everett:option:: STAGE_SUBMITTER_DESTINATIONS
   :default: ``""``
   :parser: ``ListOf(str)``

   Comma-separated pairs of ``DESTINATION_URL|SAMPLE`` where the ``DESTINATION_URL``
   is an https url to submit the crash report to and ``SAMPLE`` is a number
   between 0 and 100 representing the sample rate. For example:

   * ``https://example.com|20``
   * ``https://example.com|30,https://example2.com|100``



Running in a local dev environment
==================================

To run the stage submitter and fake collector, do:

::

  $ just run-submitter

After doing this, you can enter a Socorro container shell and use
``bin/process_crash.sh`` to pull down crash data, put it into storage, and
publish the crash id to the standard queue.

::

  $ just shell
  app@socorro:/app$ ./bin/process_crash.sh a206b51a-5955-4704-be1f-cf1ac0240514


The stage submitter will consume the crash id from the standard queue, download
the data from storage, assemble a crash report payload, and submit it to the
fake collector.

The fake collector will log headers, annotations, and file information for any
crash reports submitted to it.
