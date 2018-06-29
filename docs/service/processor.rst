.. _processor-chapter:

==================
Service: Processor
==================

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

  $ docker-compose run processor bash


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


fetch_crashids
--------------

This will generate a list of crash ids from crash-stats.mozilla.com that meet
specified criteria. Crash ids are printed to stdout, so you can use this in
conjunction with other scripts or redirect to a file.

This pulls 100 crash ids from yesterday for Firefox product::

  $ docker-compose run processor ./socorro-cmd fetch_crashids

This pulls 5 crash ids from 2017-09-01::

  $ docker-compose run processor ./socorro-cmd fetch_crashids --num=5 --date=2017-09-01

This pulls 100 crash ids for criteria specified with a Super Search url that we
copy and pasted::

  $ docker-compose run processor ./socorro-cmd fetch_crashids "--url=https://crash-stats.mozilla.com/search/?product=Firefox&date=%3E%3D2017-09-05T15%3A09%3A00.000Z&date=%3C2017-09-12T15%3A09%3A00.000Z&_sort=-date&_facets=signature&_columns=date&_columns=signature&_columns=product&_columns=version&_columns=build_id&_columns=platform"

You can get command help::

  $ docker-compose run processor ./socorro-cmd fetch_crash_data --help


fetch_crash_data
----------------

This will fetch raw crash data from crash-stats.mozilla.com and save it in the
appropriate directory structure rooted at outputdir.

Usage from host::

  $ docker-compose run processor ./socorro-cmd fetch_crash_data <outputdir> <crashid> [<crashid> ...]


For example (assumes this crash exists)::

  $ docker-compose run processor ./socorro-cmd fetch_crash_data ./testdata 5c9cecba-75dc-435f-b9d0-289a50170818


Use with ``fetch_crashids`` to fetch crash data from 100 crashes from yesterday
for Firefox::

  $ docker-compose run processor bash
  app@processor:/app$ ./socorro-cmd fetch_crashids | socorro-cmd fetch_crash_data ./testdata


You can get command help::

  $ docker-compose run processor ./socorro-cmd fetch_crash_data --help


You should run this with ``docker-compose run processor`` so that the files that get saved to
the file system are owned by the user/group of the account you're using on your
host.

.. Note::

   This script requires that you have a valid API token from the
   crash-stats.mozilla.com environment that has the "View Raw Dumps" permission
   in order to download personally identifiable information and dumps.

   You can generate API tokens at `<https://crash-stats.mozilla.com/api/tokens/>`_.

   Add the API token value to your ``my.env`` file::

       SOCORRO_API_TOKEN=apitokenhere

   If you don't have an API token, this will download some raw crash
   information, but it will be redacted.


.. Note::

   Make sure you treat any data you pull from production in accordance with our
   data policies that you agreed to when granted access to it.


scripts/socorro_aws_s3.sh
-------------------------

This script is a convenience wrapper around the aws cli s3 subcommand that uses
Socorro environment variables to set the credentials and endpoint.

Usage from host::

  $ docker-compose run processor ./scripts/socorro_aws_s3.sh <s3cmd> ...


For example, this creates an S3 bucket named ``dev_bucket``::

  $ docker-compose run processor ./scripts/socorro_aws_s3.sh mb s3://dev_bucket/


This copies the contents of ``./testdata`` into the ``dev_bucket``::

  $ docker-compose run processor ./scripts/socorro_aws_s3.sh sync ./testdata s3://dev_bucket/


This lists the contents of the bucket::

  $ docker-compose run processor ./scripts/socorro_aws_s3.sh ls s3://dev_bucket/


Since this is just a wrapper, you can get help::

  $ docker-compose run processor ./scripts/socorro_aws_s3.sh help


add_crashid_to_queue
--------------------

This script adds crash ids to the specified queue. Typically, you want to add
crash ids to the ``socorro.normal`` queue, but if you're testing priority
processing you'd use ``socorro.priority``.

Usage from host::

  $ ./docker-compose run processor ./socorro-cmd add_crashid_to_queue <queue> <crashid> [<crashid> ...]


For example::

  $ ./docker-compose run processor ./socorro-cmd add_crashid_to_queue socorro.normal 5c9cecba-75dc-435f-b9d0-289a50170818


.. Note::

   Processing will fail unless the crash data is in the S3 container first!


Example using all the scripts
-----------------------------

Let's process crashes for Firefox from yesterday. We'd do this:

.. code-block:: shell

  # Start bash in the processor container
  $ docker-compose run processor bash

  # Generate a file of crashids--one per line
  app@processor:/app$ socorro-cmd fetch_crashids > crashids.txt

  # Pull raw crash data from -prod for each crash id and put it in the
  # "crashdata" directory on the host
  app@processor:/app$ cat crashids.txt | socorro-cmd fetch_crash_data ./crashdata

  # Create a dev_bucket in localstack-s3
  app@processor:/app$ ./scripts/socorro_aws_s3.sh mb s3://dev_bucket/

  # Copy that data from the host into the localstack-s3 container
  app@processor:/app$ scripts/socorro_aws_s3.sh sync ./crashdata s3://dev_bucket/

  # Add all the crash ids to the queue
  app@processor:/app$ cat crashids.txt | socorro-cmd add_crashid_to_queue socorro.normal

  # Then exit the container
  app@processor:/app$ exit

  # Run the processor to process all those crashes
  $ docker-compose up processor


.. Note::

   That's a lot of commands. Definitely worth writing shell scripts to automate
   this for your specific needs.


Processing crashes from Antenna
===============================

`Antenna <https://antenna.readthedocs.io/>`_ is the collector of the Socorro
crash ingestion pipeline. It was originally part of the Socorro repository, but
we extracted and rewrote it and now it lives in its own repository and
infrastructure.

Antenna deployments are based on images pushed to Docker Hub.

To run Antenna in the Socorro local dev environment, do::

  $ docker-compose up antenna


It will listen on ``http://localhost:8888/`` for incoming crashes from a
breakpad crash reporter. It will save crash data to the ``dev_bucket`` in the
local S3 which is where the processor looks for it.

FIXME(willkg): How to get crash ids into the processing queue?
