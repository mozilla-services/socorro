#! /bin/bash -e
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Jenkins build script for running tests and packaging build

./scripts/clean.sh

./scripts/bootstrap.sh

./scripts/test.sh

./scripts/integration-test.sh

./scripts/install.sh

./scripts/package.sh
