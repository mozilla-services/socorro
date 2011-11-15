.. index:: standalone

.. _standalone-chapter:


Standalone Development Environment
============

You can easily bring up a full Socorro VM:
https://github.com/rhelmer/socorro-vagrant

However, in some cases it can make sense to run components standalone in 
a development environment, for example if you want to run just one or 
two components and connect them to an existing Socorro install for debugging.

Setting up
----------------

1) clone the repo (http://github.com/mozilla/socorro)
::
  git clone git://github.com/mozilla/socorro.git
  cd socorro/

2) set up Python path
::
  export PYTHONPATH=.:thirdparty/

3) create virtualenv and use it (this installs all needed Socorro dependencies)
::
  make virtualenv
  . socorro-virtualenv/bin/activate

4) configure Socorro (also see :ref:`commonconfig-chapter`)
::
  pushd scripts/config
  for file in *.py.dist; do cp $file `basename $file .dist`; done
  edit commonconfig.py (...)
  popd


Install and configure UI
----------------

1) copy contents of webapp-php/ to HTDOCS area
::
  rsync -av ./webapp-php/ ~/public_html/

2) configure webapp (also see :ref:`uiinstallation-chapter` and :ref:`uitroubleshooting-chapter`)
::
  cp htaccess-dist .htaccess
  pushd webapp-php/application/config/
  for file in *.php-dist; do cp $file `basename $file -dist`; done
  edit database.php config.php (...)
  popd

3) make sure log area is writable to webserver user
::
  chmod o+rwx webapp-php/application/logs


Launch standalone Middleware instance
----------------
NOTE - make sure to use an unused port, it should be the same as whatever
you configure in webapp-php/application/config/webserviceclient.php
::
  python scripts/webservices.py 9191

This will use whichever database you configured in commonconfig.py


