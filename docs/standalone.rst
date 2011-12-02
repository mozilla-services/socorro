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


Pulling crash reports from production
----------------
The Socorro PostgreSQL database only contains a small subset of the information 
about individual crashes (enough to run aggregate reports). For instance the
full stack is only available in long-term storage (such as HBase).

If you have imported a database from a production instance, you may want
to configure the web UI to pull individual crash reports from production via 
the web service (so URLs such as https://crash-stats.mozilla.com/report/index/0f3f3360-40a6-4188-8659-b2a5c2110808 will work). 

The /report/index page actually pulls it's data from a URL such as:
https://crash-stats.mozilla.com/dumps/0f3f3360-40a6-4188-8659-b2a5c2110808.jsonz

You can simply point your dev instance to production by modifying:
::
  webapp-php/application/config/application.php

Change the URL in this config value to point to your desired production instance:

.. code-block:: php

  <?php
  $config['crash_dump_local_url'] = 'http://crash-stats/dumps/%1$s.jsonz';
  ?>

See https://github.com/mozilla/socorro/blob/master/webapp-php/application/config/application.php-dist 
