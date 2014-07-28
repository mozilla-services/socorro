#! /bin/bash

VIRTUALENV=$PWD/socorro-virtualenv

NOSE="${VIRTUALENV}/bin/nosetests socorro -s --with-xunit"
SETUPDB="${VIRTUALENV}/bin/python ./socorro/external/postgresql/setupdb_app.py"
JENKINS_CONF=jenkins.py.dist

ENV=env

PYTHONPATH="."

PG_RESOURCES=""
if [ -n "$database_hostname" ]; then
    PG_RESOURCES="$PG_RESOURCES resource.postgresql.database_hostname=$database_hostname"
fi
if [ -n "$database_username" ]; then
    PG_RESOURCES="$PG_RESOURCES secrets.postgresql.database_username=$database_username"
fi
if [ -n "$database_password" ]; then
    PG_RESOURCES="$PG_RESOURCES secrets.postgresql.database_password=$database_password"
fi
if [ -n "$database_port" ]; then
    PG_RESOURCES="$PG_RESOURCES resource.postgresql.database_port=$database_port"
fi
if [ -n "$database_name" ]; then
    PG_RESOURCES="$PG_RESOURCES resource.postgresql.database_name=$database_name"
fi

RMQ_RESOURCES=""
if [ -n "$rmq_host" ]; then
    RMQ_RESOURCES="$RMQ_RESOURCES resource.rabbitmq.host=$rmq_host"
fi
if [ -n "$rmq_virtual_host" ]; then
    RMQ_RESOURCES="$RMQ_RESOURCES resource.rabbitmq.virtual_host=$rmq_virtual_host"
fi
if [ -n "$rmq_user" ]; then
    RMQ_RESOURCES="$RMQ_RESOURCES secrets.rabbitmq.rabbitmq_user=$rmq_user"
fi
if [ -n "$rmq_password" ]; then
    RMQ_RESOURCES="$RMQ_RESOURCES secrets.rabbitmq.rabbitmq_password=$rmq_password"
fi

ES_RESOURCES=""
if [ -n "$elasticsearch_urls" ]; then
    ES_RESOURCES="$ES_RESOURCES resource.elasticsearch.elasticsearch_urls=$elasticsearch_urls"
fi
if [ -n "$elasticSearchHostname" ]; then
    ES_RESOURCES="$ES_RESOURCES resource.elasticsearch.elasticSearchHostname=$elasticSearchHostname"
fi
if [ -n "$elasticsearch_index" ]; then
    ES_RESOURCES="$ES_RESOURCES resource.elasticsearch.elasticsearch_index=$elasticsearch_index"
fi

# jenkins only settings for the pre-configman components
# can be removed when all tests are updated to use configman
if [ $WORKSPACE ]; then
    pushd socorro/unittest/config
    cp $JENKINS_CONF commonconfig.py
    popd
fi

# setup any unset test configs and databases without overwriting existing files
pushd config
for file in *.ini-dist; do
    if [ ! -f `basename $file -dist` ]; then
        cp $file `basename $file -dist`
    fi
done
popd

PYTHONPATH=$PYTHONPATH $SETUPDB --database_name=socorro_integration_test --database_username=$database_username --database_hostname=$database_hostname --database_password=$database_password --database_port=$database_port --database_superusername=$database_superusername --database_superuserpassword=$database_superuserpassword --dropdb --logging.stderr_error_logging_level=40 --unlogged

PYTHONPATH=$PYTHONPATH $SETUPDB --database_name=socorro_test --database_username=$database_username --database_hostname=$database_hostname --database_password=$database_password --database_port=$database_port --database_superusername=$database_superusername --database_superuserpassword=$database_superuserpassword --dropdb --no_schema --logging.stderr_error_logging_level=40 --unlogged

pushd socorro/unittest/config
for file in *.py.dist; do
    if [ ! -f `basename $file .dist` ]; then
        cp $file `basename $file .dist`
    fi
done
popd

PYTHONPATH=$PYTHONPATH $SETUPDB --database_name=socorro_migration_test --database_username=$database_username --database_hostname=$database_hostname --database_password=$database_password --database_port=$database_port --database_superusername=$database_superusername --database_superuserpassword=$database_superuserpassword --dropdb --logging.stderr_error_logging_level=40 --unlogged

PYTHONPATH=$PYTHONPATH $VIRTUALENV/bin/alembic -c config/alembic.ini downgrade -1
PYTHONPATH=$PYTHONPATH $VIRTUALENV/bin/alembic -c config/alembic.ini upgrade +1

# run tests
$ENV $PG_RESOURCES $RMQ_RESOURCES $ES_RESOURCES PYTHONPATH=$PYTHONPATH $NOSE

# test webapp
cd webapp-django; ./bin/jenkins.sh
