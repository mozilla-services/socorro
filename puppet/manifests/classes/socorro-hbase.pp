class socorro-hbase {

    file {
	'/etc/apt/sources.list.d/cloudera.list':
            source => '/home/socorro/dev/socorro/puppet/files/etc_apt_sources.list.d/cloudera.list',
            require => Exec['add-cloudera-key'];
    }

    # wish we could use package for this, but we need JAVA_HOME set on first run
    # see http://projects.puppetlabs.com/issues/6400
    exec { '/usr/bin/apt-get install -y hadoop-hbase hadoop-hbase-master hadoop-hbase-thrift liblzo2-dev':
            alias => 'install-hbase',
            logoutput => on_failure,
            require => [Exec['apt-get-update'],Exec['apt-get-update-cloudera']];
    }

    exec { 
        'apt-get-update-cloudera':
            command => '/usr/bin/apt-get update',
            require => [Exec['install-oracle-jdk'],
                        File['/etc/apt/sources.list.d/cloudera.list']];
    }

    exec {
        '/usr/bin/curl -s http://archive.cloudera.com/debian/archive.key | /usr/bin/sudo /usr/bin/apt-key add -':
            alias => 'add-cloudera-key',
            unless => '/usr/bin/apt-key list | grep Cloudera',
            require => Package['curl'];
    }

    # FIXME add real LZO support, remove hack here
    exec {
        '/bin/cat /home/socorro/dev/socorro/analysis/hbase_schema | sed \'s/LZO/NONE/g\' | /usr/bin/hbase shell':
            alias => 'hbase-schema',
            creates => "/var/lib/hbase/crash_reports",
            logoutput => on_failure,
            require => Exec['install-hbase'];
    }
}
