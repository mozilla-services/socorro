class socorro-java inherits socorro-base {

    exec { 'package-oracle-jdk':
        command => '/usr/bin/wget https://github.com/flexiondotorg/oab-java6/raw/0.2.8/oab-java.sh -O oab-java.sh && chmod +x oab-java.sh && ./oab-java.sh',
        creates => '/etc/apt/sources.list.d/oab.list',
        cwd => '/home/socorro',
        require => Exec["apt-get-update"],
        timeout => 0
    }

    package { ['sun-java6-jdk']:
        require => Exec['package-oracle-jdk'],
        ensure => latest
    }

}

class socorro-hbase inherits socorro-java {

    file {
	'/etc/apt/sources.list.d/cloudera.list':
            source => '/home/socorro/dev/socorro/puppet/files/etc_apt_sources.list.d/cloudera.list',
            require => Exec['add-cloudera-key'];

        'hbase-configs':
            path => "/etc/hbase/conf/",
            recurse => true,
            require => Package['hadoop-hbase'],
            source => "/home/socorro/dev/socorro/puppet/files/etc_hbase_conf"

    }

    package { ['hadoop-hbase', 'hadoop-hbase-master', 'hadoop-hbase-thrift']:
        require => [Exec['apt-get-update'], Exec['apt-get-update-cloudera']],
        ensure => latest
    }

    exec {
        'apt-get-update-cloudera':
            command => '/usr/bin/apt-get update && touch /tmp/apt-get-update-cloudera',
            require => [Exec['package-oracle-jdk'],
                        Package['sun-java6-jdk'],
                        File['/etc/apt/sources.list.d/cloudera.list']],
            creates => '/tmp/apt-get-update-cloudera';
    }

    exec {
        '/usr/bin/curl -s http://archive.cloudera.com/debian/archive.key | /usr/bin/sudo /usr/bin/apt-key add -':
            alias => 'add-cloudera-key',
            unless => '/usr/bin/apt-key list | grep Cloudera',
            require => Package['curl'];
    }

    # FIXME add real LZO support, remove hack here
    exec {
        "/bin/cat /home/socorro/dev/socorro/analysis/hbase_schema | sed 's/LZO/NONE/g' | /usr/bin/hbase shell":
            alias => 'hbase-schema',
            creates => "/var/lib/hbase/crash_reports",
            logoutput => on_failure,
            require => Package['hadoop-hbase-master']
    }

    service {
        ['hadoop-hbase-master', 'hadoop-hbase-thrift']:
            require => [Package['hadoop-hbase-master'],
                        Package['hadoop-hbase-thrift'],
                        File['hbase-configs']],
            ensure => running
    }
}
