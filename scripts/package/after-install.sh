#! /bin/bash

# ensure base directories owned
chown socorro /var/log/socorro
chown socorro /var/lock/socorro

# crond doesn't like files with executable bits, and doesn't load
# them.
chmod 644 /etc/cron.d/socorro

# Link the local Django settings to the distributed settings.
ln -fs /etc/socorro/local.py \
    /data/socorro/webapp-django/crashstats/settings/local.py

# create DB if it does not exist
# TODO handle DB not on localhost - could use setupdb for this
su - postgres -c "psql breakpad -c ''" > /var/log/socorro/setupdb.log 2>&1
if [ $? != 0 ]; then
    echo "Creating new DB, may take a few minutes"
    pushd /data/socorro/application > /dev/null
    su postgres -c "PYTHONPATH=. /data/socorro/socorro-virtualenv/bin/python \
        ./socorro/external/postgresql/setupdb_app.py \
        --alembic_config=/etc/socorro/alembic.ini --database_name=breakpad \
        --database_superusername=postgres" &> /var/log/socorro/setupdb.log
    if [ $? != 0 ]; then
        echo "WARN could not create database on localhost"
        echo "See /var/log/socorro/setupdb.log for more info"
    fi
    popd > /dev/null
else
    echo "Running database migrations with alembic"
    pushd /data/socorro/application > /dev/null
    su postgres -c "PYTHONPATH=. ../socorro-virtualenv/bin/python \
        ../socorro-virtualenv/bin/alembic \
        -c /etc/socorro/alembic.ini upgrade head" &> /var/log/socorro/alembic.log
    if [ $? != 0 ]; then
        echo "WARN could not run alembic migrations"
        echo "See /var/log/socorro/alembic.log for more info"
    fi
    popd > /dev/null
fi

/data/socorro/socorro-virtualenv/bin/python \
    /data/socorro/webapp-django/manage.py syncdb --noinput \
    &> /var/log/socorro/django-syncdb.log
if [ $? != 0 ]; then
    echo "WARN could not run django syncdb"
    echo "See /var/log/socorro/django-syncdb.log for more info"
fi

# create ElasticSearch indexes
echo "Creating ElasticSearch indexes"
pushd /data/socorro/application/scripts > /dev/null
su socorro -c "PYTHONPATH=. /data/socorro/socorro-virtualenv/bin/python \
    setup_supersearch_app.py \
    &> /var/log/socorro/setup_supersearch.log"

if [ $? != 0 ]; then
    echo "WARN could not create ElasticSearch indexes"
    echo "See /var/log/socorro/setup_supersearch.log for more info"
    echo "You may want to run"
    echo "/data/socorro/application/scripts/setup_supersearch_app.py manually"
fi
popd > /dev/null

# ensure that partitions have been created
pushd /data/socorro/application > /dev/null
su socorro -c "PYTHONPATH=. /data/socorro/socorro-virtualenv/bin/python \
    socorro/cron/crontabber_app.py --job=weekly-reports-partitions --force \
    --admin.conf=/etc/socorro/crontabber.ini \
    &> /var/log/socorro/crontabber.log"
if [ $? != 0 ]; then
    echo "WARN could not run crontabber weekly-reports-partitions"
    echo "See /var/log/socorro/crontabber.log for more info"
fi
popd > /dev/null

# TODO optional support for crashmover
for service in processor; do
  chkconfig --add socorro-${service}
  chkconfig socorro-${service} on
done

# TODO optional support for crashmover
for service in socorro-processor; do
  if [ -f /etc/init.d/${service} ]; then
    service ${service} start
  fi
done

# Restart Apache
service httpd restart
