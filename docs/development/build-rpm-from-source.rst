.. index:: build-rpm-from-source

.. _build-rpm-from-source-chapter:

Build RPM from source
=====================

RHEL (or clones e.g. CentOS)
----------------------------

Install the fpm dependency for rpm build
::

  sudo yum install rpm-build 
  sudo yum install ruby ruby-devel ruby-ri ruby-rdoc rubygems 
  sudo gem install fpm 

From inside the Socorro checkout:
::

  make package BUILD_TYPE=rpm

This will create a Socorro RPM in the current directory:
::
  sudo rpm -i socorro-*.rpm

Configuration is in /etc/socorro and crashes are in /home/socorro.
