.. index:: install-src-prod

.. _prodinstall-chapter:

Production install
==================

RHEL (or clones e.g. CentOS)
----------------------------

From inside the Socorro checkout:
::

  make package BUILD_TYPE=rpm

This will create a Socorro RPM in the current directory:
::
  sudo rpm -i socorro-*.rpm

Configuration is in /etc/socorro and crashes are in /home/socorro.
