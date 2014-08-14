#! /bin/bash

# deploy system files
cp /data/socorro/application/scripts/crons/socorrorc /etc/socorro/

if [ ! -f /etc/httpd/conf.d/socorro.conf ]; then
    cp /data/socorro/application/config/apache.conf-dist \
        /etc/httpd/conf.d/socorro.conf
fi

cp /data/socorro/application/config/*.ini-dist /etc/socorro
pushd /etc/socorro > /dev/null
for file in *.ini-dist; do
    if [ ! -f `basename $file -dist` ]; then
        cp $file `basename $file -dist`
    fi
done
popd > /dev/null

# copy system files into install, to catch any overrides
cp /etc/socorro/*.ini /data/socorro/application/config/
system_localpy="/etc/socorro/local.py"
socorro_localpy="/data/socorro/webapp-django/crashstats/settings/local.py"
if [ ! -f "$system_localpy" ]; then
    cp "$socorro_localpy" "$system_localpy"

    echo
    echo "NOTICE: Please edit the configuration files in /etc/socorro and re-run this script"
    exit 0
fi

if [ -f "$socorro_localpy" ]; then
    mv "$socorro_localpy" "${socorro_localpy}.dist"
fi

ln -vsf "$system_localpy" "$socorro_localpy"

# TODO optional support for crashmover
for service in processor
do
  cp /data/socorro/application/scripts/init.d/socorro-${service} /etc/init.d/
  chkconfig --add socorro-${service}
  chkconfig socorro-${service} on
done

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
        -c config/alembic.ini upgrade head &> /var/log/socorro/alembic.log
    popd > /dev/null
fi

# ensure that partitions have been created
pushd /data/socorro/application > /dev/null
su socorro -c "PYTHONPATH=. /data/socorro/socorro-virtualenv/bin/python \
    socorro/cron/crontabber_app.py --job=weekly-reports-partitions --force \
    --admin.conf=/etc/socorro/crontabber.ini \
    &> /var/log/socorro/crontabber.log"
popd > /dev/null

if [ ! -f /etc/cron.d/socorro ]; then
    # crond doesn't like files with executable bits, and doesn't load
    # them.
    chmod 644 /data/socorro/application/config/crontab-dist

    cp -a /data/socorro/application/config/crontab-dist \
        /etc/cron.d/socorro
fi

# TODO optional support for crashmover
for service in socorro-processor httpd
do
  if [ -f /etc/init.d/${service} ]
  then
    /sbin/service ${service} status > /dev/null
    if [ $? != 0 ]; then
        /sbin/service ${service} start
    else
        /sbin/service ${service} restart
    fi
  fi
done

/data/socorro/socorro-virtualenv/bin/python \
    /data/socorro/webapp-django/manage.py syncdb --noinput \
    &> /var/log/socorro/django-syncdb.log

