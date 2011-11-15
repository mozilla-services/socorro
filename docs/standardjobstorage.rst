.. index:: standardjobstorage

.. _standardjobstorage-chapter:


Standard Job Storage
====================

Standard storage is where the JSON/dump pairs are saved while they
wait for processing. The location of the standard storage is
determined by the configuration parameter storageRoot found in the
:ref:`commonconfig-chapter`.

The file system is divided into two parts: date based storage and name
based storage. Both branches use a radix sort breakdown to locate
files. The original version of Socorro used only the date based
storage, but it was found to be too slow to search when under a heavy
load.

For a deeper discussion of the storage technique: see
:ref:`filesystem-chapter`
