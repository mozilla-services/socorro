#! /bin/bash

# ensure base directories owned
chown socorro /var/log/socorro
chown socorro /var/lock/socorro

# crond doesn't like files with executable bits, and doesn't load
# them.
chmod 644 /etc/cron.d/socorro

# create DB if it does not exist
# TODO handle DB not on local device - could use setupdb for this
psql -U postgres -h localhost -l | grep breakpad > /dev/null
if [ $? != 0 ]; then
    echo "Creating new DB, may take a few minutes"
    pushd /data/socorro/application > /dev/null
    PYTHONPATH=. /data/socorro/socorro-virtualenv/bin/python \
        ./socorro/external/postgresql/setupdb_app.py \
        --database_name=breakpad --fakedata \
        --database_superusername=postgres \
        &> /var/log/socorro/setupdb.log
    popd > /dev/null
else
    echo "Running database migrations with alembic"
    pushd /data/socorro/application > /dev/null
    PYTHONPATH=. ../socorro-virtualenv/bin/python \
        ../socorro-virtualenv/bin/alembic \
        -c /etc/socorro/alembic.ini upgrade head &> /var/log/socorro/alembic.log
    popd > /dev/null
fi

/data/socorro/socorro-virtualenv/bin/python \
    /data/socorro/webapp-django/manage.py syncdb --noinput \
    &> /var/log/socorro/django-syncdb.log

# ensure that partitions have been created
pushd /data/socorro/application > /dev/null
su socorro -c "PYTHONPATH=. /data/socorro/socorro-virtualenv/bin/python \
    socorro/cron/crontabber_app.py --job=weekly-reports-partitions --force \
    --admin.conf=/etc/socorro/crontabber.ini \
    &> /var/log/socorro/crontabber.log"
popd > /dev/null

# TODO optional support for crashmover
for service in processor
do
  chkconfig --add socorro-${service}
  chkconfig socorro-${service} on
done

# TODO optional support for crashmover
for service in socorro-processor
do
  if [ -f /etc/init.d/${service} ]
  then
    /sbin/service ${service} start
  fi
done

# Restart Apache
/sbin/service httpd restart
