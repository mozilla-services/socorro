#! /bin/bash -e
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Package Socorro for redistribution

source scripts/defaults

DESC="A distributed system for collecting, processing,
 and displaying crash reports from clients using Breakpad"

if [ ! -d "$BUILD_DIR" ]; then
    echo "Socorro has not been built ($BUILD_DIR does not exist)."
    echo "  Please run './scripts/install.sh' before continuing."
    exit 1
fi

echo "> Building Socorro $BUILD_VERSION ..."
if [ "$BUILD_TYPE" != "tar" ]; then
    fpm -s dir -t $BUILD_TYPE \
        -v $BUILD_VERSION \
        -n "socorro" \
        -m "<socorro-dev@mozilla.com>" \
        -C $BUILD_DIR \
        --epoch 1 \
        --license "MPL" \
        --vendor "Mozilla" \
        --url "https://wiki.mozilla.org/Socorro" \
        --description "$DESC" \
        --before-install scripts/package/$BUILD_TYPE-before-install.sh \
        --after-install scripts/package/$BUILD_TYPE-after-install.sh \
        --before-remove scripts/package/$BUILD_TYPE-before-remove.sh \
        --after-remove scripts/package/$BUILD_TYPE-after-remove.sh \
        --config-files /etc/socorro \
        --exclude *.pyc \
        --exclude *.swp \
        --depends 'libc6 > 2.3' \
        --depends 'libgcc1 > 1:4.1.0' \
        --depends 'libsasl2-2 > 2.1.23' \
        --depends 'libssl1.0.0' \
        --depends 'libstdc++6 > 4.4' \
        --depends 'libxml2 > 2.7.3' \
        --depends 'libxslt1.1 > 1.1.25' \
        --depends 'zlib1g > 1:1.1.9' \
        --depends 'nodejs' \
        --depends 'node-less' \
        --deb-suggests 'libpq5' \
        --deb-suggests 'openjdk-7-jre-headless' \
        --deb-suggests 'python-virtualenv' \
        --deb-suggests 'postgresql-9.3' \
        --deb-suggests 'postgresql-plperl-9.3' \
        --deb-suggests 'postgresql-contrib-9.3' \
        --deb-suggests 'rsync' \
        --deb-suggests 'rabbitmq-server' \
        --deb-suggests 'elasticsearch' \
        --deb-suggests 'memcached' \
        --deb-suggests 'apache2' \
        --deb-suggests 'libapache2-mod-wsgi' \
        data etc var
else
    tar -C ${BUILD_DIR%%socorro} --mode 755 --exclude-vcs --owner 0 --group 0 -zcf socorro.tar.gz socorro/
fi

echo "> Build Complete."
