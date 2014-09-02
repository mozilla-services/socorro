#! /bin/bash -e

tar -C builds --mode 755 --exclude-vcs --owner 0 --group 0 -zcf socorro.tar.gz socorro/
