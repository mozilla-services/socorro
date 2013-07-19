# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

PREFIX=/data/socorro
ABS_PREFIX = $(shell readlink -f $(PREFIX))
VIRTUALENV=$(CURDIR)/socorro-virtualenv
PYTHONPATH = "."
NOSE = $(VIRTUALENV)/bin/nosetests socorro -s --with-xunit
SETUPDB = $(VIRTUALENV)/bin/python ./socorro/external/postgresql/setupdb_app.py
COVEROPTS = --with-coverage --cover-package=socorro
COVERAGE = $(VIRTUALENV)/bin/coverage
PYLINT = $(VIRTUALENV)/bin/pylint
JENKINS_CONF = jenkins.py.dist

.PHONY: all test submodule-update install reinstall install-socorro virtualenv coverage lint clean minidump_stackwalk analysis thirdparty webapp-django


all:	test

setup-test: virtualenv
	cd config; for file in *.ini-dist; do if [ ! -f `basename $$file -dist` ]; then cp $$file `basename $$file -dist`; fi; done
	PYTHONPATH=$(PYTHONPATH) $(SETUPDB) --database_name=socorro_integration_test --database_username=$(DB_USER) --database_hostname=$(DB_HOST) --database_password=$(DB_PASSWORD) --database_port=$(DB_PORT) --database_superusername=$(DB_SUPERUSER) --database_superuserpassword=$(DB_SUPERPASSWORD) --dropdb
	PYTHONPATH=$(PYTHONPATH) $(SETUPDB) --database_name=socorro_test --database_username=$(DB_USER) --database_hostname=$(DB_HOST) --database_password=$(DB_PASSWORD) --database_port=$(DB_PORT) --database_superusername=$(DB_SUPERUSER) --database_superuserpassword=$(DB_SUPERPASSWORD) --dropdb --no_schema
	cd socorro/unittest/config; for file in *.py.dist; do if [ ! -f `basename $$file .dist` ]; then cp $$file `basename $$file .dist`; fi; done

test: setup-test
	PYTHONPATH=$(PYTHONPATH) $(NOSE)

submodule-update:
	git submodule update --init --recursive

thirdparty:
	[ -d $(VIRTUALENV) ] || virtualenv -p python2.6 $(VIRTUALENV)
	# install production dependencies
	$(VIRTUALENV)/bin/pip install --use-mirrors --download-cache=pip-cache/ --ignore-installed --install-option="--prefix=`pwd`/thirdparty" --install-option="--install-lib=`pwd`/thirdparty" -r requirements/prod.txt

install: thirdparty reinstall

# this a dev-only option, `make install` needs to be run at least once in the checkout (or after `make clean`)
reinstall: install-socorro
	# record current git revision in install dir
	git rev-parse HEAD > $(PREFIX)/revision.txt
	REV=`cat $(PREFIX)/revision.txt` && sed -ibak "s/CURRENT_SOCORRO_REVISION/$$REV/" $(PREFIX)/application/scripts/config/revisionsconfig.py
	REV=`cat $(PREFIX)/stackwalk/revision.txt` && sed -ibak "s/CURRENT_BREAKPAD_REVISION/$$REV/" $(PREFIX)/application/scripts/config/revisionsconfig.py

install-socorro: webapp-django
	# create base directories
	mkdir -p $(PREFIX)/webapp-django
	mkdir -p $(PREFIX)/application
	# copy to install directory
	rsync -a config $(PREFIX)/application
	rsync -a thirdparty $(PREFIX)
	rsync -a socorro $(PREFIX)/application
	rsync -a scripts $(PREFIX)/application
	rsync -a tools $(PREFIX)/application
	rsync -a sql $(PREFIX)/application
	rsync -a wsgi $(PREFIX)/application
	rsync -a stackwalk $(PREFIX)/
	rsync -a scripts/stackwalk.sh $(PREFIX)/stackwalk/bin/
	rsync -a analysis $(PREFIX)/
	rsync -a alembic $(PREFIX)/application
	rsync -a webapp-django/ $(PREFIX)/webapp-django/
	# copy default config files
	cd $(PREFIX)/application/scripts/config; for file in *.py.dist; do cp $$file `basename $$file .dist`; done

virtualenv:
	[ -e $(VIRTUALENV) ] || virtualenv -p python2.6 $(VIRTUALENV)
	$(VIRTUALENV)/bin/pip install --use-mirrors --download-cache=./pip-cache -r requirements/dev.txt

jenkins:
	cd socorro/unittest/config; cp $(JENKINS_CONF) `basename commonconfig.py.dist .dist`

coverage: setup-test
	rm -f coverage.xml
	PYTHONPATH=$(PYTHONPATH) DB_HOST=$(DB_HOST) $(COVERAGE) run $(NOSE)
	$(COVERAGE) xml

lint:
	rm -f pylint.txt
	$(PYLINT) -f parseable --rcfile=pylintrc socorro > pylint.txt

clean:
	find ./socorro/ -type f -name "*.pyc" -exec rm {} \;
	rm -rf ./thirdparty/*
	rm -rf ./google-breakpad/ ./builds/ ./breakpad/ ./stackwalk ./pip-cache
	rm -rf ./breakpad.tar.gz

minidump_stackwalk:
	PREFIX=`pwd`/stackwalk/ SKIP_TAR=1 ./scripts/build-breakpad.sh

analysis:
	git submodule update --init socorro-toolbox akela
	cd akela && mvn package
	cd akela && mvn package
	cd socorro-toolbox && mvn package
	mkdir -p analysis
	rsync socorro-toolbox/target/*.jar analysis/
	rsync akela/target/*.jar analysis/
	rsync -a socorro-toolbox/src/main/pig/ analysis/

json_enhancements_pg_extension: virtualenv
    # This is only run manually, as it is a one-time operation
    # to be performed at system installation time, rather than
    # every time Socorro is built
	if [ ! -f `pg_config --pkglibdir`/json_enhancements.so ]; then sudo $(VIRTUALENV)/bin/python -c "from pgxnclient import cli; cli.main(['install', 'json_enhancements'])"; fi

webapp-django: submodule-update
	#cd webapp-django; ./bin/install.sh
