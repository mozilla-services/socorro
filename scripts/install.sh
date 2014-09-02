#! /bin/bash -ex

mkdir -p $BUILD_DIR/application

if [ "$BUILD_TYPE" != "tar" ]; then
    # create base directories
    mkdir -p $BUILD_DIR/etc/init.d
    mkdir -p $BUILD_DIR/etc/cron.d
    mkdir -p $BUILD_DIR/etc/httpd/conf.d

    mkdir -p $BUILD_DIR/etc/socorro
    mkdir -p $BUILD_DIR/var/log/socorro
    mkdir -p $BUILD_DIR/var/lock/socorro

    # copy default config files
    for file in scripts/config/*.py.dist; do
      cp $file $BUILD_DIR/etc/socorro/`basename $file .dist`
    done

    for file in config/*.ini-dist; do
      cp $file $BUILD_DIR/etc/socorro/`basename $file -dist`
    done

    cp scripts/crons/socorrorc $BUILD_DIR/etc/socorro/
    for service in processor
    do
        cp scripts/init.d/socorro-${service} $BUILD_DIR/etc/init.d/
    done
    cp config/crontab-dist $BUILD_DIR/etc/cron.d/socorro
    cp webapp-django/crashstats/settings/local.py $BUILD_DIR/etc/socorro/local.py
    cp config/apache.conf-dist $BUILD_DIR/etc/httpd/conf.d/socorro.conf
else
    rsync -a config $BUILD_DIR/application
    pushd $BUILD_DIR/application/scripts/config
    for file in *.py.dist; do cp $file `basename $file .dist`; done
    popd
fi

if [ "$BUILD_TYPE" != "tar" ]; then
    BUILD_DIR=${BUILD_DIR/data/socorro}
    mkdir -p $BUILD_DIR
fi

# copy to install directory
rsync -a ${VIRTUAL_ENV} $BUILD_DIR
rsync -a socorro $BUILD_DIR/application
rsync -a scripts $BUILD_DIR/application
rsync -a tools $BUILD_DIR/application
rsync -a sql $BUILD_DIR/application
rsync -a wsgi $BUILD_DIR/application
rsync -a stackwalk $BUILD_DIR/
rsync -a scripts/stackwalk.sh $BUILD_DIR/stackwalk/bin/
rsync -a analysis $BUILD_DIR/
rsync -a alembic $BUILD_DIR/application
rsync -a webapp-django $BUILD_DIR/

# record current git revision in install dir
git rev-parse HEAD > $BUILD_DIR/application/socorro/external/postgresql/socorro_revision.txt
cp $BUILD_DIR/stackwalk/revision.txt $BUILD_DIR/application/socorro/external/postgresql/breakpad_revision.txt

# Write down build number, if ran by Jenkins
if [ -n "$BUILD_NUMBER" ]
then
  echo "$BUILD_NUMBER" > $BUILD_DIR/JENKINS_BUILD_NUMBER
fi
