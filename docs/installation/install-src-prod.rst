.. index:: install-src-prod

.. _prodinstall-chapter:

Production install
==================

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
