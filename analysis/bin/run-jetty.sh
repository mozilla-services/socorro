#!/bin/bash

MAIN_JAR=$1
SERVER_CLASS_NAME="com.mozilla.socorro.web.CorrelationReportServer"
CLASSPATH=$MAIN_JAR

for lib in `ls lib/*.jar`;
do
    CLASSPATH=$CLASSPATH:$lib
done

echo $CLASSPATH

java -cp $CLASSPATH $SERVER_CLASS_NAME
