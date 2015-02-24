#! /bin/bash
INSTALL_PREFIX=/data

if [ -d $INSTALL_PREFIX/socorro ]; then
	rm -r $INSTALL_PREFIX/socorro
fi
