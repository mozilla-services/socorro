# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

.PHONY: all test bootstrap install lint clean breakpad json_enhancements_pg_extension package

all: test

test: bootstrap
	bash ./scripts/test.sh

bootstrap:
	bash ./scripts/bootstrap.sh

install: bootstrap
	bash ./scripts/install.sh

package: install
	bash ./scripts/package.sh

lint:
	bash ./scripts/lint.sh

clean:
	bash ./scripts/clean.sh

breakpad:
	PREFIX=`pwd`/stackwalk/ SKIP_TAR=1 ./scripts/build-breakpad.sh

json_enhancements_pg_extension: bootstrap
	bash ./scripts/json-enhancements.sh
