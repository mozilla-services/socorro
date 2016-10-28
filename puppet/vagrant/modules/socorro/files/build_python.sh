#!/bin/bash

# This script downloads Python source tarball, builds it and does an altinstall.
# An altinstall installs Python, but doesn't change any of the symlinks in
# /usr/bin, so it doesn't affect anything else on the system that is expecting
# Python 2.7.5.

PYVERSION=2.7.11

cd /tmp
wget "https://www.python.org/ftp/python/${PYVERSION}/Python-${PYVERSION}.tgz"
tar -xzvf Python-${PYVERSION}.tgz
cd Python-${PYVERSION}
./configure
make
make altinstall
