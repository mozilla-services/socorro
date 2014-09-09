#!/bin/bash -ex
# Run prelink on virtual env binaries
if [ -n "$(type -p prelink)" ]; then
    prelink -u $BUILD_DIR/`basename ${VIRTUAL_ENV}`/bin/python*
fi
