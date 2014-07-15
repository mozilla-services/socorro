#! /bin/bash

PREFIX=/data/socorro
VIRTUALENV=$PWD/socorro-virtualenv

# package up the tarball in $PREFIX
# create base directories
mkdir -p $PREFIX/application

# copy to install directory
rsync -a config $PREFIX/application
rsync -a $VIRTUALENV $PREFIX
rsync -a socorro $PREFIX/application
rsync -a scripts $PREFIX/application
rsync -a tools $PREFIX/application
rsync -a sql $PREFIX/application
rsync -a wsgi $PREFIX/application
rsync -a stackwalk $PREFIX/
rsync -a scripts/stackwalk.sh $PREFIX/stackwalk/bin/
rsync -a analysis $PREFIX/
rsync -a alembic $PREFIX/application
rsync -a webapp-django $PREFIX/

# copy default config files
cd $PREFIX/application/scripts/config; for file in *.py.dist; do cp $$file `basename $$file .dist`; done

# record current git revision in install dir
git rev-parse HEAD > $PREFIX/application/socorro/external/postgresql/socorro_revision.txt
cp $PREFIX/stackwalk/revision.txt $PREFIX/application/socorro/external/postgresql/breakpad_revision.txt
