.. index:: postgres

Set up accounts and access to PostgreSQL
========================================

Add a new superuser account to PostgreSQL
-----------------------------------------

Create a superuser account for yourself. Make sure to put your username
and desired password instead of YOURNAME and YOURPASS.
As the *postgres* user:
::
  psql template1 -c \
    "create user YOURNAME with encrypted password 'YOURPASS' superuser"

For running unit tests, you'll want a test user as well (make sure
to remove this for production installs).
::
  psql template1 -c \
    "create user test with encrypted password 'aPassword' superuser"

Also, before you run unit tests or make, be sure to copy and edit this file:

  cp config/alembic.ini-dist config/alembic.ini

The important line to update is for *sqlalchemy.url*.


Allow local connections for PostgreSQL
--------------------------------------

By default, PostgreSQL will not allow your install to log in as
different users, which you will need to be able to do.

Client authentication is controlled in the pg_hba.conf file, see
http://www.postgresql.org/docs/9.3/static/auth-pg-hba-conf.html

At minimum, you'll want to allow md5 passwords to be used over the
local network connections.

As the *root* user, edit pg_hba.conf.

RHEL/CentOS:
::
    /var/lib/pgsql/9.3/data/pg_hba.conf

Ubuntu:
::
    /etc/postgresql/9.3/main/pg_hba.conf

And change the local connections from *trust* to *md5*.

::

  # IPv4 local connections:
  host    all             all             127.0.0.1/32            md5
  # IPv6 local connections:
  host    all             all             ::1/128                 md5

NOTE Make sure to read and understand the pg_hba.conf documentation before
running a production server.

As the *root* user, restart PostgreSQL for the changes to take effect.

On RHEL/CentOS:
::
  service postgresql-9.3 restart

On Ubuntu:
::
  service postgresql restart

Or on Mac OS X:
::
  pg_ctl -D /usr/local/pgsql/data/ restart
