.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. index:: standalone

.. _standalone-chapter:


Standalone Development Environment
============

You can easily bring up a full Socorro VM, see :ref:`setupdevenv-chapter` for more info.

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

4) copy default Socorro config (also see :ref:`commonconfig-chapter`)
::
  pushd scripts/config
  for file in *.py.dist; do cp $file `basename $file .dist`; done
  edit commonconfig.py (...)
  popd



Install and configure UI
----------------

1) symlink webapp-php/ to HTDOCS area
::
  mv ~/public_html ~/public_html.old
  ln -s ./webapp-php ~/public_html

2) copy default webapp config (also see :ref:`uiinstallation-chapter`)
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

Edit scripts/config/webapiconfig.py and change wsgiInstallation to
False (this allows the middleware to run in standalone mode):
::
  wsgiInstallation.default = False

NOTE - make sure to use an unused port, it should be the same as whatever
you configure in webapp-php/application/config/webserviceclient.php
::
  python scripts/webservices.py 9191

This will use whichever database you configured in commonconfig.py
