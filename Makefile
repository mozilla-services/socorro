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

.PHONY: all test test-socorro test-webapp bootstrap install reinstall install-socorro lint clean minidump_stackwalk analysis json_enhancements_pg_extension webapp-django

all:	test

test: test-socorro test-webapp

test-socorro: bootstrap
	# jenkins only settings for the pre-configman components
	# can be removed when all tests are updated to use configman
	if [ $(WORKSPACE) ]; then cd socorro/unittest/config; cp $(JENKINS_CONF) commonconfig.py; fi;
	# setup any unset test configs and databases without overwriting existing files
	cd config; for file in *.ini-dist; do if [ ! -f `basename $$file -dist` ]; then cp $$file `basename $$file -dist`; fi; done
	PYTHONPATH=$(PYTHONPATH) $(SETUPDB) --database_name=socorro_integration_test --database_username=$(DB_USER) --database_hostname=$(DB_HOST) --database_password=$(DB_PASSWORD) --database_port=$(DB_PORT) --database_superusername=$(DB_SUPERUSER) --database_superuserpassword=$(DB_SUPERPASSWORD) --dropdb
	PYTHONPATH=$(PYTHONPATH) $(SETUPDB) --database_name=socorro_test --database_username=$(DB_USER) --database_hostname=$(DB_HOST) --database_password=$(DB_PASSWORD) --database_port=$(DB_PORT) --database_superusername=$(DB_SUPERUSER) --database_superuserpassword=$(DB_SUPERPASSWORD) --dropdb --no_schema
	cd socorro/unittest/config; for file in *.py.dist; do if [ ! -f `basename $$file .dist` ]; then cp $$file `basename $$file .dist`; fi; done
	# run tests with coverage
	rm -f coverage.xml
	PYTHONPATH=$(PYTHONPATH) DB_HOST=$(DB_HOST) $(COVERAGE) run $(NOSE)
	$(COVERAGE) xml

# makes thing semantically consistent (test-{component}) while avoiding
# building the webapp twice to save a little time
test-webapp: webapp-django
	# alias to webapp-django

bootstrap:
	git submodule update --init --recursive
	PATH=$$PATH:node_modules/.bin which lessc || time npm install less
	[ -d $(VIRTUALENV) ] || virtualenv -p python2.6 $(VIRTUALENV)
	# install dev + prod dependencies
	time $(VIRTUALENV)/bin/pip install tools/peep-0.7.tar.gz
	time $(VIRTUALENV)/bin/peep install --download-cache=./pip-cache -r requirements/dev.txt

install: bootstrap reinstall

# this a dev-only option, `make install` needs to be run at least once in the checkout (or after `make clean`)
reinstall: install-socorro
	# record current git revision in install dir
	git rev-parse HEAD > $(PREFIX)/application/socorro/external/postgresql/socorro_revision.txt
	cp $(PREFIX)/stackwalk/revision.txt $(PREFIX)/application/socorro/external/postgresql/breakpad_revision.txt

install-socorro: webapp-django
	# package up the tarball in $(PREFIX)
	# create base directories
	mkdir -p $(PREFIX)/application
	# copy to install directory
	rsync -a config $(PREFIX)/application
	rsync -a $(VIRTUALENV) $(PREFIX)
	rsync -a socorro $(PREFIX)/application
	rsync -a scripts $(PREFIX)/application
	rsync -a tools $(PREFIX)/application
	rsync -a sql $(PREFIX)/application
	rsync -a wsgi $(PREFIX)/application
	rsync -a stackwalk $(PREFIX)/
	rsync -a scripts/stackwalk.sh $(PREFIX)/stackwalk/bin/
	rsync -a analysis $(PREFIX)/
	rsync -a alembic $(PREFIX)/application
	# purge the virtualenv
	[ -d webapp-django/virtualenv ] || rm -rf webapp-django/virtualenv
	rsync -a webapp-django $(PREFIX)/
	# copy default config files
	cd $(PREFIX)/application/scripts/config; for file in *.py.dist; do cp $$file `basename $$file .dist`; done

lint:
	rm -f pylint.txt
	$(PYLINT) -f parseable --rcfile=pylintrc socorro > pylint.txt

clean:
	find ./socorro/ -type f -name "*.pyc" -exec rm {} \;
	rm -rf ./google-breakpad/ ./builds/ ./breakpad/ ./stackwalk ./pip-cache
	rm -rf ./breakpad.tar.gz

minidump_stackwalk:
	PREFIX=`pwd`/stackwalk/ SKIP_TAR=1 ./scripts/build-breakpad.sh

analysis: bootstrap
	git submodule update --init socorro-toolbox akela
	cd akela && mvn package
	cd akela && mvn package
	cd socorro-toolbox && mvn package
	mkdir -p analysis
	rsync socorro-toolbox/target/*.jar analysis/
	rsync akela/target/*.jar analysis/
	rsync -a socorro-toolbox/src/main/pig/ analysis/

json_enhancements_pg_extension: bootstrap
    # This is only run manually, as it is a one-time operation
    # to be performed at system installation time, rather than
    # every time Socorro is built
	if [ ! -f `pg_config --pkglibdir`/json_enhancements.so ]; then sudo env PATH=$$PATH $(VIRTUALENV)/bin/python -c "from pgxnclient import cli; cli.main(['install', 'json_enhancements'])"; fi

webapp-django: bootstrap
	cd webapp-django; ./bin/jenkins.sh
