.. index:: installation-mac

.. _mac-chapter:

Mac OS X
--------

Install dependencies
::
  brew update
  brew tap homebrew/versions
  brew install python26 git gpp postgresql subversion rabbitmq memcached npm
  sudo easy_install virtualenv virtualenvwrapper pip
  sudo pip-2.7 install docutils
  brew install mercurial
  npm install -g less

Set your PATH
::
  export PATH=/usr/local/bin:$PATH

Initialize and run PostgreSQL
::
  initdb -D /usr/local/pgsql/data -E utf8
  export PGDATA=/usr/local/pgsql/data
  pg_ctl start

Create a symbolic link to pgsql_socket
::
  mkdir /var/pgsql_socket/
  ln -s /private/tmp/.s.PGSQL.5432 /var/pgsql_socket/

Modify postgresql config
::
  sudo editor /usr/local/pgsql/data/postgresql.conf

Ensure that timezone is set to UTC
::
  timezone = 'UTC'

Restart PostgreSQL to activate config changes, if the above was changed
::
  pg_ctl restart
