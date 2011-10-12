#!/bin/bash

#please see README

set -e

CURDIR=$(dirname $0)

echo 'alter the releases_raw table so that it can accept nightlies'
psql -f $(CURDIR)/alter_releases_raw.sql breakpad

exit 0
