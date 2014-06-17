#!/bin/bash
set -x

# This script is for getting socorro into a working state within the vagrant vm. Do not use this as
# a deploy script for production. Eventually all actions in this script should be moved behind the
# `setup.py install` command (patches welcome).

# If we don't do this we get the following error:
#   not trusting file exploitable/.hg/hgrc from untrusted user vagrant, group vagrant
#   not trusting file /home/vagrant/src/socorro/exploitable/.hg/hgrc from untrusted user vagrant, group vagrant
mkdir /etc/mercurial/
echo "[trusted]
users = vagrant
groups = vagrant" > /etc/mercurial/hgrc

SOCORRO_DIR=/home/vagrant/src/socorro
VIRTUALENV=/home/vagrant/src/socorro/socorro-virtualenv
cd $SOCORRO_DIR

# this will build the virtualenv
make bootstrap-webapp

source $VIRTUALENV/bin/activate

if [ -d build/psycopg2 ]; then
    rm -rf build/psycopg2
fi

export PATH=$PATH:/usr/pgsql-9.3/bin/


# we have to be in the virtualenv because the version of hg we need is there.
scl enable devtoolset-1.1 "source $VIRTUALENV/bin/activate && make stackwalker 2>&1"
