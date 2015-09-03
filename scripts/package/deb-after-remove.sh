#! /bin/bash
set -e
INSTALL_PREFIX=/data

if [ "$1" = "purge" ] ; then
    if [ -d $INSTALL_PREFIX/socorro ]; then
        rm -r $INSTALL_PREFIX/socorro
    fi

    if type deluser >/dev/null 2>&1; then
        userdel -r socorro 2>&1 > /dev/null
    fi
fi
