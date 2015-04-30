#!/usr/bin/env bash

if (( EUID != 0 )); then
    echo "This script must be run as root."
    exit 1
fi

function help {
    echo "USAGE: ${0} <role>"
    echo "Valid roles are: postgres, webapp, elasticsearch, admin."
    exit 1
}

function validate {
    # No argument? That's a paddlin'.
    if [ "x${1}" == "x" ]; then
        help
    fi

    # Invalid function? That's a paddin'.
    VALID_FUNC=`type -t $1 | grep -q function`
    if [ $? != 0 ]; then
        help
    fi
}

function postgres {
    # create DB if it does not exist
    su - postgres -c "psql breakpad -c ''" > /var/log/socorro/setupdb.log 2>&1
    if [ $? != 0 ]; then
        echo "Creating new DB, may take a few minutes"
        pushd /data/socorro/application > /dev/null
        su postgres -c "PYTHONPATH=. /data/socorro/socorro-virtualenv/bin/python \
            ./socorro/external/postgresql/setupdb_app.py --createdb \
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
}

function webapp {
    /data/socorro/socorro-virtualenv/bin/python \
        /data/socorro/webapp-django/manage.py syncdb --noinput \
        &> /var/log/socorro/django-syncdb.log
    if [ $? != 0 ]; then
        echo "WARN could not run django syncdb"
        echo "See /var/log/socorro/django-syncdb.log for more info"
    fi
    
    /data/socorro/socorro-virtualenv/bin/python \
        /data/socorro/webapp-django/manage.py migrate --noinput \
        &> /var/log/socorro/django-migrate.log
    if [ $? != 0 ]; then
        echo "WARN could not run django migration"
        echo "See /var/log/socorro/django-migrate.log for more info"
    fi
}

function elasticsearch {
    # create Elasticsearch indexes
    echo "Creating Elasticsearch indexes"
    pushd /data/socorro/application/scripts > /dev/null
    su socorro -c "PYTHONPATH=. /data/socorro/socorro-virtualenv/bin/python \
        setup_supersearch_app.py \
        &> /var/log/socorro/setup_supersearch.log"
    
    if [ $? != 0 ]; then
        echo "WARN could not create Elasticsearch indexes"
        echo "See /var/log/socorro/setup_supersearch.log for more info"
        echo "You may want to run"
        echo "/data/socorro/application/scripts/setup_supersearch_app.py manually"
    fi
    popd > /dev/null
}

function admin {
    # ensure that partitions have been created
    pushd /data/socorro/application > /dev/null
    su socorro -c "PYTHONPATH=. /data/socorro/socorro-virtualenv/bin/python \
        socorro/cron/crontabber_app.py --job=weekly-reports-partitions --force \
        &> /var/log/socorro/crontabber.log"
    if [ $? != 0 ]; then
        echo "WARN could not run crontabber weekly-reports-partitions"
        echo "See /var/log/socorro/crontabber.log for more info"
    fi
    popd > /dev/null
}

# Aaaaand go!
validate $1
echo "Initialising ${1}."
$1
exit 0
