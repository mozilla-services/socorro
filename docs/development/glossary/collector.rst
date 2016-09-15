.. index:: collector

.. _collector-chapter:


Collector
=========

Collector is an application that runs under Apache using mod-python.
Its task is accepting crash reports from remote clients and saving
them in a place and format usable by further applications.

Raw crashes are accepted via HTTP POST. The form data from the POST is
then arranged into a JSON and saved into the local file system. The
collector is responsible for assigning an ooid? (Our Own ID) to the
crash. It also assigns a Throttle? value which determines if the crash
is eventually to go into the relational database.

Should the saving to a local file system fail, there is a fallback
storage mechanism. A second file system can be configured to take the
failed saves. This file system would likely be an NFS mounted file
system.

After a crash is saved, there is an app called :ref:`crashmover-chapter` that
will transfer the crashes to S3.
