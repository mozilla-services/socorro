# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

$es_version = "0.19.0"

class socorro-elasticsearch inherits socorro-base {
    exec { "/usr/bin/wget https://github.com/downloads/elasticsearch/elasticsearch/elasticsearch-${es_version}.deb":
        alias => "download-elasticsearch",
        creates => "/home/socorro/elasticsearch-${es_version}.deb",
        cwd => "/home/socorro/";
    }

    package { "elasticsearch":
        require => [Package["openjdk-6-jdk"], Exec["download-elasticsearch"]],
        source => "/home/socorro/elasticsearch-${es_version}.deb",
        provider => dpkg,
        ensure => latest;
    }

    service { "elasticsearch":
        require => Package["elasticsearch"],
        ensure => running;
    }
}
