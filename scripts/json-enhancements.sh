#! /bin/bash

VIRTUALENV=$PWD/socorro-virtualenv

# This is only run manually, as it is a one-time operation
# to be performed at system installation time, rather than
# every time Socorro is built
if [ ! -f `pg_config --pkglibdir`/json_enhancements.so ]; then
    sudo env PATH=$PATH $VIRTUALENV/bin/python -c "from pgxnclient import cli; cli.main(['install', 'json_enhancements'])"
fi
