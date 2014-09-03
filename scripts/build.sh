#! /bin/bash -e
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Jenkins build script for running tests and packaging build

export JAVA_HOME=${JAVA_HOME:-"/usr/lib/jvm/jre-openjdk"}

if [ -z "$WORKSPACE" -o -z "$CI" ]; then
  export PATH=$JAVA_HOME/bin:$PATH
fi

export BUILD_TYPE=${BUILD_TYPE:-"tar"}
export BUILD_DIR=${BUILD_DIR:-"builds/$BUILD_TYPE/socorro"}
export BUILD_VERSION=${BUILD_NUMBER:-$(git describe --tags | cut -d'-' -f1)}

export database_hostname=${database_hostname:-"localhost"}
export database_username=${database_username:-"test"}
export database_port=${database_port:-"5432"}
export database_password=${database_password:-"aPassword"}
export database_superusername=${database_superusername:-"test"}
export database_superuserpassword=${database_superuserpassword:-"aPassword"}

export rmq_host=${rmq_host:-"localhost"}
export rmq_user=${rmq_user:-"guest"}
export rmq_password=${rmq_password:-"guest"}
export rmq_virtual_host=${rmq_virtual_host:-"/"}

export elasticSearchHostname=${elasticSearchHostname:-"localhost"}
export elasticsearch_urls=${elasticsearch_urls:-"http://localhost:9200"}


source scripts/clean.sh

source scripts/bootstrap.sh

source scripts/test.sh

source scripts/integration-test.sh

source scripts/analysis.sh

source scripts/install.sh

source scripts/package.sh
