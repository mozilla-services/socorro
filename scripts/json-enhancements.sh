#! /bin/bash -e

# This is only run manually, as it is a one-time operation
# to be performed at system installation time, rather than
# every time Socorro is built
if [ ! -f `pg_config --pkglibdir`/json_enhancements.so ]; then
    sudo env PATH=$PATH ${VIRTUAL_ENV}/bin/python -c "from pgxnclient import cli; cli.main(['install', 'json_enhancements'])"
fi
