#! /bin/bash -ex

source scripts/defaults

NOSE="$VIRTUAL_ENV/bin/nosetests socorro -s"
SETUPDB="$VIRTUAL_ENV/bin/python ./socorro/external/postgresql/setupdb_app.py"
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

errors=0
while read d
do
  if [ ! -f "$d/__init__.py" ]
  then
    echo "$d is missing an __init__.py file, tests will not run"
    errors=$((errors+1))
  fi
done < <(find socorro/unittest/* -not -name logs -type d)

if [ $errors != 0 ]
then
  exit 1
fi

# jenkins only settings for the pre-configman components
# can be removed when all tests are updated to use configman
pushd socorro/unittest/config
for file in *.py.dist; do
  if [ $WORKSPACE ]; then
    cp $JENKINS_CONF commonconfig.py
    sed -i 's:localhost:jenkins-pg92:' config/alembic.ini-dist
  else
    cp $file `basename $file .dist`
  fi
done
popd

PYTHONPATH=$PYTHONPATH $SETUPDB --database_name=socorro_integration_test --database_username=$database_username --database_hostname=$database_hostname --database_password=$database_password --database_port=$database_port --database_superusername=$database_superusername --database_superuserpassword=$database_superuserpassword --dropdb --logging.stderr_error_logging_level=40 --unlogged --no_staticdata

PYTHONPATH=$PYTHONPATH $SETUPDB --database_name=socorro_test --database_username=$database_username --database_hostname=$database_hostname --database_password=$database_password --database_port=$database_port --database_superusername=$database_superusername --database_superuserpassword=$database_superuserpassword --dropdb --no_schema --logging.stderr_error_logging_level=40 --unlogged --no_staticdata

PYTHONPATH=$PYTHONPATH $SETUPDB --database_name=socorro_migration_test --database_username=$database_username --database_hostname=$database_hostname --database_password=$database_password --database_port=$database_port --database_superusername=$database_superusername --database_superuserpassword=$database_superuserpassword --dropdb --logging.stderr_error_logging_level=40 --unlogged

PYTHONPATH=$PYTHONPATH ${VIRTUAL_ENV}/bin/alembic -c config/alembic.ini downgrade -1
PYTHONPATH=$PYTHONPATH ${VIRTUAL_ENV}/bin/alembic -c config/alembic.ini upgrade heads

# run tests
$ENV $PG_RESOURCES $RMQ_RESOURCES $ES_RESOURCES PYTHONPATH=$PYTHONPATH $NOSE

# test webapp
pushd webapp-django
./bin/ci.sh
popd

# lint puppet manifests; bug 976639
pushd puppet
find . -name '*.pp' -exec puppet parser validate {} \; -exec puppet-lint $puppet_lint_args {} \;
popd
