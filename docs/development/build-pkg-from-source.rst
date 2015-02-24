.. index:: build-pkg-from-source

.. _build-pkg-from-source-chapter:

Build pacakge from source
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

Debian/Ubuntu
----------------------------

Install the fpm dependency for deb build
::

  sudo apt-get install ruby ruby-dev rubygems
  sudo gem install fpm 

Install the build dependencies
::

  sudo apt-get install nodejs node-less python2.6-dev python-virtualenv libxml2-dev libxslt1-dev postgresql-contrib-9.3 postgresql-server-dev-9.3 libsasl2-dev pkg-config libcurl4-gnutls-dev rsync

From inside the Socorro checkout:
::

  make package BUILD_TYPE=deb

This will create a Socorro deb in the current directory:
::
  sudo dpkg -i socorro_*.deb


Configuration is in /etc/socorro and crashes are in /home/socorro.
