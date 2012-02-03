.. index:: processor

.. _processor-chapter:

Processor
=========

Introduction
------------

Socorro Processor is a multithreaded application that applies
JSON/dump pairs to the stackwalk_server application, parses the
output, and records the results in the hbase. The processor, coupled
with stackwalk_server, is computationally intensive. Multiple
instances of the processor can be run simultaneously from different
machines.

Important note
--------------

Processor uses temorary storage for dump files. Path to the storage
is specified by the ``temporaryFileSystemStoragePath`` param.

Please, make sure, that this folder (by default ``/home/socorro/temp``
exists, and the socorro user have the rwx permission to it).

`See sample config code on Github
<https://github.com/mozilla/socorro/blob/master/scripts/config/processorconfig.py.dist>`_
