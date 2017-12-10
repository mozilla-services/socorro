#! /bin/bash -ex

echo "this is test.sh"

source scripts/defaults

PYTEST="$VIRTUAL_ENV/bin/pytest"
FLAKE8="$VIRTUAL_ENV/bin/flake8"
SETUPDB="$VIRTUAL_ENV/bin/python ./socorro/external/postgresql/setupdb_app.py"
JENKINS_CONF=jenkins.py.dist

ENV=env

PYTHONPATH=.

FS_RESOURCES=""
if [ -n "$fs_root" ]; then
    FS_RESOURCES="$FS_RESOURCES resource.fs.fs_root=$fs_root"
fi

PG_RESOURCES=""
if [ -n "$database_url" ]; then
    echo database_url is present, specifying parameters on the command line is not necessary \( $database_url \)
else
    # This clause is all legacy and can be removed once we switch to use database_url in config
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

errors=0
while read d
do
  if [ ! -f "$d/__init__.py" ]
  then
    if [ "$(ls -A $d/test*py)" ]
    then
        echo "$d is missing an __init__.py file, tests will not run"
        errors=$((errors+1))
    else
        echo "$d has no tests - ignoring it"
    fi
  fi
done < <(find socorro/unittest/* -not -name logs -type d)

if [ $errors != 0 ]
then
  exit 1
fi

# jenkins requires a different alembic default
if [ $WORKSPACE ]; then
    sed -i 's:localhost:jenkins-pg92:' config/alembic.ini
fi


PYTHONPATH=$PYTHONPATH $SETUPDB --database_name=socorro_integration_test --dropdb --logging.stderr_error_logging_level=40 --unlogged --no_staticdata --createdb

PYTHONPATH=$PYTHONPATH $SETUPDB --database_name=socorro_test --dropdb --no_schema --logging.stderr_error_logging_level=40 --unlogged --no_staticdata --createdb

PYTHONPATH=$PYTHONPATH $SETUPDB --database_name=socorro_migration_test --dropdb --logging.stderr_error_logging_level=40 --unlogged --createdb

PYTHONPATH=$PYTHONPATH ${VIRTUAL_ENV}/bin/alembic -c config/alembic.ini downgrade -1
PYTHONPATH=$PYTHONPATH ${VIRTUAL_ENV}/bin/alembic -c config/alembic.ini upgrade heads

# run flake8
$FLAKE8

# run tests
$ENV $FS_RESOURCES $PG_RESOURCES $RMQ_RESOURCES $ES_RESOURCES PYTHONPATH=$PYTHONPATH $PYTEST

# test webapp
pushd webapp-django
PYTHONPATH=.. $PYTEST
popd
