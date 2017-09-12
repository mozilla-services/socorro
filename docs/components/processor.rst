.. _processor-chapter:

=========
Processor
=========

.. Note::

   We're in the process of extracting the processor out of Socorro as a separate
   project. There's no ETA for that work, yet.


Running the processor
=====================

To run the processor using the processor configuration, do::

  $ docker-compose up processor


That will bring up all the services the processor requires to run and start the
processor using the ``/app/docker/run_processor.sh`` script and the processor
configuration.

To ease debugging in the container, you can run a shell::

  $ docker-compose run processor /bin/bash


Then you can start and stop the processor and tweak files and all that jazz.

.. Note::

   The stackwalk binaries are in ``/stackwalk`` in the container.


Processing crashes
==================

Running the processor is pretty uninteresting since it'll just sit there until
you give it something to process.

In order to process something, you first need to acquire raw crash data, put the
data in the S3 container in the appropriate place, then you need to add the
crash id to the "socorro.normal" RabbitMQ queue.

We have helper scripts for these steps.


``scripts/fetch_crash_data.py``
-------------------------------

This will fetch raw crash data from -prod and save it in the appropriate
directory structure.

By default, this saves crash data to ``crashdata/``, but you can specify the
directory using the ``--outputdir`` argument.

Usage from host::

  $ docker/as_me.sh scripts/fetch_crash_data.py <crashid> [<crashid> ...]


For example (assumes this crash exists)::

  $ docker/as_me.sh scripts/fetch_crash_data.py 5c9cecba-75dc-435f-b9d0-289a50170818


You can get command help::

  $ docker/as_me.sh scripts/fetch_crash_data.py --help


You should run this with ``docker/as_me.sh`` so that the files that get saved to
the file system are owned by the user/group of the account you're using on your
host.

.. Note::

   If you want full crash data including the dumps, then you have a valid API token
   from the -prod environment that has the "View Raw Dumps" permission.

   You can generate API tokens at `<https://crash-stats.mozilla.com/api/tokens/>`_.

   Add the API token value to your ``my.env`` file::

       SOCORRO_API_TOKEN=apitokenhere

   If you don't do that, then the crash data you fetch will only be publicly
   available crash data.


You can also run this script to grab a bunch of publicly available raw crash
data. For example::

  $ docker/as_me.sh scripts/fetch_crash_data.py --num=100 --date=2017-09-01

This will fetch 100 crashes from September 1st, 2017.


``scripts/socorro_aws_s3.sh``
-----------------------------

This script is a convenience wrapper around the aws cli s3 subcommand that uses
Socorro environment variables to set the credentials and endpoint.

Usage from host::

  $ docker/as_me.sh scripts/socorro_aws_s3.sh <s3cmd> ...


For example, this creates an S3 bucket named ``dev_bucket``::

  $ docker/as_me.sh scripts/socorro_aws_s3.sh mb s3://dev_bucket/


This copies the contents of ``./testdata`` into the ``dev_bucket``::

  $ docker/as_me.sh scripts/socorro_aws_s3.sh sync ./testdata s3://dev_bucket/


This lists the contents of the bucket::

  $ docker/as_me.sh scripts/socorro_aws_s3.sh ls s3://dev_bucket/


Since this is just a wrapper, you can get help::

  $ docker/as_me.sh scripts/socorro_aws_s3.sh help


``scripts/add_crashid_to_queue.py``
-----------------------------------

This script adds crash ids to the specified queue. Typically, you want to add
crash ids to the ``socorro.normal`` queue, but if you're testing priority
processing you'd use ``socorro.priority``.

Usage from host::

  $ docker-compose run processor scripts/add_crashid_to_queue.py <queue> <crashid> [<crashid> ...]


.. Note::

   You can run this script with ``docker/as_me.sh``, too. It's adding items to a
   queue, so it doesn't touch your file system and thus it doesn't matter what
   uid/gid it runs under.


For example::

  $ docker-compose run processor scripts/add_crashid_to_queue.py socorro.normal 5c9cecba-75dc-435f-b9d0-289a50170818


.. Note::

   Processing will fail unless the crash data is in the S3 container first!


.. Warning::

   August 17th, 2017: Everything below this point is outdated.


Troubleshooting
===============

journalctl is a good place to look for Socorro logs, especially if services
are not starting up or are crashing.

Socorro supports syslog and raven for application-level logging of all
services (including web services).
