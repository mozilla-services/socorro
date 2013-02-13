$es_version = "0.20.2"

class socorro-elasticsearch inherits socorro-base {

    exec { 'package-oracle-jdk':
        command => '/usr/bin/wget https://github.com/flexiondotorg/oab-java6/raw/0.2.7/oab-java.sh -O oab-java.sh && bash oab-java.sh',
        creates => '/etc/apt/sources.list.d/oab.list',
        cwd => '/home/socorro',
        require => Exec["apt-get-update"],
        timeout => 0
    }

    package { ['sun-java6-jdk']:
        require => Exec['package-oracle-jdk'],
        ensure => latest
    }

    exec { "/usr/bin/wget http://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-${es_version}.deb":
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
