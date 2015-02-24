#! /bin/bash
INSTALL_PREFIX=/data

# ensure base directories owned
chown socorro /var/log/socorro
chown -R www-data.socorro $INSTALL_PREFIX/socorro/webapp-django/static/CACHE

# crond doesn't like files with executable bits, and doesn't load
# them.
chmod 644 /etc/cron.d/socorro

# Link the local Django settings to the distributed settings.
ln -fs /etc/socorro/local.py $INSTALL_PREFIX/socorro/webapp-django/crashstats/settings/local.py

if [ -f '/usr/lib/apache2/modules/mod_wsgi.so-2.6' ]; then
    # change mod_wsgi to python 2.6
    ln -fs /usr/lib/apache2/modules/mod_wsgi.so-2.6 /usr/lib/apache2/modules/mod_wsgi.so
fi

# add postgres user
su -c "psql template1 -c \"create user breakpad_rw with encrypted password 'aPassword' superuser\"" postgres
if [ $? != 0 ]; then
    echo "WARN creating new DB user failed, make sure postgresql is installed"
else
    # change config to use db user/pass
    sed -i 's/postgresql:\/\/postgres@/postgresql:\/\/breakpad_rw:aPassword@/' /etc/socorro/alembic.ini
fi

# create DB if it does not exist
# TODO handle DB not on localhost - could use setupdb for this
su - postgres -c "psql breakpad -c ''" > /var/log/socorro/setupdb.log 2>&1
if [ $? != 0 ]; then
    echo "Creating new DB, may take a few minutes"
    pushd $INSTALL_PREFIX/socorro/application > /dev/null
    su postgres -c "PYTHONPATH=. $INSTALL_PREFIX/socorro/socorro-virtualenv/bin/python \
        ./socorro/external/postgresql/setupdb_app.py \
        --alembic_config=/etc/socorro/alembic.ini --database_name=breakpad \
        --database_superusername=breakpad_rw" &> /var/log/socorro/setupdb.log
    if [ $? != 0 ]; then
        echo "WARN could not create database on localhost"
        echo "See /var/log/socorro/setupdb.log for more info"
    fi
    popd > /dev/null
else
    echo "Running database migrations with alembic"
    pushd $INSTALL_PREFIX/socorro/application > /dev/null
    su postgres -c "PYTHONPATH=. $INSTALL_PREFIX/socorro/socorro-virtualenv/bin/python \
        $INSTALL_PREFIX/socorro/socorro-virtualenv/bin/alembic \
        -c /etc/socorro/alembic.ini upgrade heads" &> /var/log/socorro/alembic.log
    if [ $? != 0 ]; then
        echo "WARN could not run alembic migrations"
        echo "See /var/log/socorro/alembic.log for more info"
    fi
    popd > /dev/null
fi

$INSTALL_PREFIX/socorro/socorro-virtualenv/bin/python \
    $INSTALL_PREFIX/socorro/webapp-django/manage.py syncdb --noinput \
    &> /var/log/socorro/django-syncdb.log
if [ $? != 0 ]; then
    echo "WARN could not run django syncdb"
    echo "See /var/log/socorro/django-syncdb.log for more info"
fi

$INSTALL_PREFIX/socorro/socorro-virtualenv/bin/python \
    $INSTALL_PREFIX/socorro/webapp-django/manage.py migrate --noinput \
    &> /var/log/socorro/django-migrate.log
if [ $? != 0 ]; then
    echo "WARN could not run django migration"
    echo "See /var/log/socorro/django-migrate.log for more info"
fi

# create ElasticSearch indexes
echo "Creating ElasticSearch indexes"
pushd $INSTALL_PREFIX/socorro/application/scripts > /dev/null
su socorro -c "PYTHONPATH=. $INSTALL_PREFIX/socorro/socorro-virtualenv/bin/python \
    setup_supersearch_app.py \
    &> /var/log/socorro/setup_supersearch.log"

if [ $? != 0 ]; then
    echo "WARN could not create ElasticSearch indexes"
    echo "See /var/log/socorro/setup_supersearch.log for more info"
    echo "You may want to run"
    echo "$INSTALL_PREFIX/socorro/application/scripts/setup_supersearch_app.py manually"
fi
popd > /dev/null

# ensure that partitions have been created
pushd $INSTALL_PREFIX/socorro/application > /dev/null
su socorro -c "PYTHONPATH=. $INSTALL_PREFIX/socorro/socorro-virtualenv/bin/python \
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
  update-rc.d socorro-${service} enable
done

# TODO optional support for crashmover
for service in socorro-processor; do
  if [ -f /etc/init.d/${service} ]; then
    service ${service} start
  fi
done

# Restart Apache
if [ -f /etc/init.d/apache2 ]; then
    service apache2 restart
fi
