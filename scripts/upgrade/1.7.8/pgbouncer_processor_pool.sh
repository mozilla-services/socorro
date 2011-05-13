#!/bin/bash

set -e

# untar all the new configuration files and directories
tar -xvzf pgbouncer.tgz -C /
cat /etc/pg_auth.conf /etc/pgbouncer/processor_auth > /etc/pgbouncer/pg_auth.conf

su postgres -c "/usr/pgsql-9.0/bin/psql -c 'CREATE USER processor IN ROLE breakpad_rw PASSWORD $$0couria$$'"

# change the active services
chkconfig --add pgbouncer-web
chkconfig pgbouncer-web on
chkconfig --add pgbouncer-processor
chkconfig pgbouncer-processor on
chkconfig pgbouncer off

# switch services
/etc/init.d/pgbouncer stop
/etc/init.d/pgbouncer-web start
/etc/init.d/pgbouncer-processor start

# done
exit 0