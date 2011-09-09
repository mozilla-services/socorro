PREFIX=/data/socorro
VIRTUALENV=$(CURDIR)/socorro-virtualenv
PYTHONPATH = ".:thirdparty"
NOSE = $(VIRTUALENV)/bin/nosetests socorro -s --with-xunit
COVEROPTS = --with-coverage --cover-package=socorro
COVERAGE = $(VIRTUALENV)/bin/coverage
PYLINT = $(VIRTUALENV)/bin/pylint
DEPS = nose psycopg2 simplejson coverage web.py pylint poster mock

.PHONY: all build install stage coverage hudson-coverage lint test

all:	test

test: virtualenv phpunit
	PYTHONPATH=$(PYTHONPATH) $(NOSE)

phpunit:
	phpunit webapp-php/tests/

install: java_analysis
	mkdir -p $(PREFIX)/htdocs
	mkdir -p $(PREFIX)/application
	git rev-parse HEAD  > $(PREFIX)/revision.txt
	rsync -a --exclude=".svn" thirdparty $(PREFIX)
	rsync -a --exclude=".svn" socorro $(PREFIX)/application
	rsync -a --exclude=".svn" scripts $(PREFIX)/application
	rsync -a --exclude=".svn" tools $(PREFIX)/application
	rsync -a --exclude=".svn" sql $(PREFIX)/application
	rsync -a --exclude=".svn" --exclude="tests" webapp-php/ $(PREFIX)/htdocs
	rsync -a --exclude=".svn" stackwalk $(PREFIX)/
	rsync -a --exclude=".svn" scripts/stackwalk.sh $(PREFIX)/stackwalk/bin/
	rsync -a --exclude=".svn" analysis/build/lib/socorro-analysis-job.jar $(PREFIX)/analysis/
	rsync -a --exclude=".svn" analysis/bin/modulelist.sh $(PREFIX)/analysis/
	cd $(PREFIX)/application/scripts/config; for file in *.py.dist; do cp $$file `basename $$file .dist`; done
	cd $(PREFIX)/htdocs/modules/auth/config/; for file in *.php-dist; do cp $$file `basename $$file -dist`; done
	cd $(PREFIX)/htdocs/modules/recaptcha/config; for file in *.php-dist; do cp $$file `basename $$file -dist`; done
	cd $(PREFIX)/htdocs/application/config; for file in *.php-dist; do cp $$file `basename $$file -dist`; done
	REV=`cat $(PREFIX)/revision.txt` && sed -ibak "s/CURRENT_SOCORRO_REVISION/$$REV/" $(PREFIX)/htdocs/application/config/revision.php
	cd $(PREFIX)/htdocs; cp htaccess-dist .htaccess

virtualenv:
	virtualenv $(VIRTUALENV)
	$(VIRTUALENV)/bin/easy_install $(DEPS)

coverage: virtualenv phpunit
	rm -f coverage.xml
	cd socorro/unittest/config; for file in *.py.dist; do cp $$file `basename $$file .dist`; done
	PYTHONPATH=$(PYTHONPATH) $(COVERAGE) run $(NOSE); $(COVERAGE) xml

lint:
	rm -f pylint.txt
	$(PYLINT) -f parseable --rcfile=pylintrc socorro > pylint.txt

clean:
	find ./socorro/ -type f -name "*.pyc" -exec rm {} \;
	find ./thirdparty/ -type f -name "*.pyc" -exec rm {} \;
	rm -rf ./google-breakpad/
	cd analysis && ant clean

minidump_stackwalk:
	svn co http://google-breakpad.googlecode.com/svn/trunk google-breakpad
	cd google-breakpad && ./configure --prefix=`pwd`/../stackwalk/
	cd google-breakpad && make install

java_analysis:
	cd analysis && ant hadoop-jar
