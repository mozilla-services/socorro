$es_version = "0.20.2"

class socorro-elasticsearch inherits socorro-java {

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
