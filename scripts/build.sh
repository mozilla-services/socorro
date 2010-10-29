#!/bin/bash
pushd trunk/webapp-php/tests
phpunit *.php
popd
virtualenv socorro-virtualenv
source socorro-virtualenv/bin/activate
easy_install nose psycopg2 thrift simplejson coverage web.py
easy_install -i 'http://b.pypi.python.org/simple' pylint
pushd trunk/
export PYTHONPATH=.:thirdparty
cp socorro/unittest/config/commonconfig.py.dist socorro/unittest/config/commonconfig.py
rm -f coverage.xml
coverage run ${WORKSPACE}/socorro-virtualenv/bin/nosetests socorro/ --nocapture --with-xunit --cover-package=socorro --cover-inclusive --with-coverage
coverage xml
pylint -f parseable socorro > pylint.txt
popd
