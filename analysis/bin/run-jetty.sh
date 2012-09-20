#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


function usage() {
  echo "Usage: $0 <jar> <server-port>"
}

# Print usage if incorrect number of args
[[ $# -ne 2 ]] && usage

MAIN_JAR=$1
SERVER_PORT=$2
SERVER_CLASS_NAME="com.mozilla.socorro.web.CorrelationReportServer"
CLASSPATH=$MAIN_JAR

for lib in `ls lib/*.jar`;
do
    CLASSPATH=$CLASSPATH:$lib
done

echo $CLASSPATH

java -Dserver.port=$SERVER_PORT -cp $CLASSPATH $SERVER_CLASS_NAME
