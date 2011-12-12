#!/bin/bash

set -e

CURDIR=$(dirname $0)

# create a dummy performance_check view so that ganglia will stop complaining
psql -f $CURDIR/performance_check_1.sql

# load hang_reports
psql -f $CURDIR/hang_report.sql

#done
exit 0
