#! /bin/bash

VIRTUALENV=$CURDIR/socorro-virtualenv

COVERAGE=$VIRTUALENV/bin/coverage
NOSE=$VIRTUALENV/bin/nosetests socorro -s --with-xunit
SETUPDB=$VIRTUALENV/bin/python ./socorro/external/postgresql/setupdb_app.py
JENKINS_CONF=jenkins.py.dist

ENV=env

PYTHONPATH="."

# jenkins only settings for the pre-configman components
# can be removed when all tests are updated to use configman
if [ $WORKSPACE ]; then
    cd socorro/unittest/config
    cp $JENKINS_CONF commonconfig.py
fi

# setup any unset test configs and databases without overwriting existing files
cd config
for file in *.ini-dist; do
    if [ ! -f `basename $file -dist` ]; then
        cp $file `basename $file -dist`
    fi
done

PYTHONPATH=$PYTHONPATH $SETUPDB --database_name=socorro_integration_test --database_username=$database_username --database_hostname=$database_hostname --database_password=$database_password --database_port=$DB_PORT --database_superusername=$database_superusername --database_superuserpassword=$database_superuserpassword --dropdb --logging.stderr_error_logging_level=40 --unlogged

PYTHONPATH=$PYTHONPATH $SETUPDB --database_name=socorro_test --database_username=$database_username --database_hostname=$database_hostname --database_password=$database_password --database_port=$DB_PORT --database_superusername=$database_superusername --database_superuserpassword=$database_superuserpassword --dropdb --no_schema --logging.stderr_error_logging_level=40 --unlogged

cd socorro/unittest/config; for file in *.py.dist; do if [ ! -f `basename $$file .dist` ]; then cp $$file `basename $$file .dist`; fi; done

PYTHONPATH=$PYTHONPATH $SETUPDB --database_name=socorro_migration_test --database_username=$database_username --database_hostname=$database_hostname --database_password=$database_password --database_port=$DB_PORT --database_superusername=$database_superusername --database_superuserpassword=$database_superuserpassword --dropdb --logging.stderr_error_logging_level=40 --unlogged

PYTHONPATH=$PYTHONPATH $VIRTUALENV/bin/alembic -c config/alembic.ini downgrade -1
PYTHONPATH=$PYTHONPATH $VIRTUALENV/bin/alembic -c config/alembic.ini upgrade +1

# run tests with coverage
rm -f coverage.xml
$ENV $PG_RESOURCES $RMQ_RESOURCES $ES_RESOURCES PYTHONPATH=$PYTHONPATH $COVERAGE run $NOSE
$COVERAGE xml

# test webapp
cd webapp-django; ./bin/jenkins.sh
