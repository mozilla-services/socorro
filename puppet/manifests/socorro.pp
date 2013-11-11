class webapp::socorro {

    file {
        'pg_hba.conf':
            name => '/var/lib/pgsql/9.3/data/pg_hba.conf',
            source => "/vagrant/puppet/files/pg_hba.conf",
            require => Exec['postgres-initdb'];

        'iptables':
            name => '/etc/sysconfig/iptables',
            source => "/vagrant/puppet/files/iptables",
            notify => Service['iptables'];
    }

    service {
        'rabbitmq-server':
            enable => true,
            ensure => running,
            require => Package['rabbitmq-server'];

        'postgresql-9.3':
            enable => true,
            ensure => running,
            require => [
                        Package['postgresql93-server'],
                        Exec['postgres-initdb'],
                        File['pg_hba.conf'],
                       ];
        'elasticsearch':
            enable => true,
            ensure => running,
            require => Package['elasticsearch'];

        'iptables':
            enable => true,
            ensure => running,
            require => File['iptables'];
    }

    exec {
        'postgres-initdb':
            command => '/sbin/service postgresql-9.3 initdb';
    }

    yumrepo {
        'PGDG':
            baseurl => 'http://yum.postgresql.org/9.3/redhat/rhel-$releasever-$basearch',
            descr => 'PGDG',
            enabled => 1,
            gpgcheck => 0;

        'EPEL':
            baseurl => 'http://download.fedoraproject.org/pub/epel/$releasever/$basearch',
            descr => 'EPEL',
            enabled => 1,
            gpgcheck => 0;
        'devtools':
            baseurl => 'http://people.centos.org/tru/devtools-1.1/$releasever/$basearch/RPMS',
            enabled => 1,
            gpgcheck => 0;
    }

    package {
        [
         'subversion',
         'make',
         'rsync',
         'time',
         'gcc-c++',
         'python-devel',
         'git',
         'libxml2-devel',
         'libxslt-devel',
         'openldap-devel',
         'java-1.7.0-openjdk',
         'yum-plugin-fastestmirror',
        ]:
        ensure => latest;
    }

    package {
        [
         'postgresql93-server',
         'postgresql93-plperl',
         'postgresql93-contrib',
         'postgresql93-devel',
        ]:
        ensure => latest,
        require => [ Yumrepo['PGDG'], Package['yum-plugin-fastestmirror']];
    }

    package {
        [
         'python-virtualenv',
         'supervisor',
         'rabbitmq-server',
         'python-pip',
         'npm',
        ]:
        ensure => latest,
        require => [ Yumrepo['EPEL'], Package['yum-plugin-fastestmirror']];
    }

    package {
        'elasticsearch':
            provider => rpm,
            source => 'https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-0.90.4.noarch.rpm',
            require => Package['java-1.7.0-openjdk'],
            ensure => 'present';
    }

    package {
        'devtoolset-1.1-gcc-c++':
            ensure => latest,
            require => [ Yumrepo['devtools'], Package['yum-plugin-fastestmirror']];
    }

    exec {
        'create-postgres-superuser':
            command  => '/usr/bin/createuser -s vagrant && /usr/bin/psql -q -c "ALTER USER vagrant WITH ENCRYPTED PASSWORD \'aPassword\'"',
            user => postgres,
            unless => '/usr/bin/psql -q -c "SELECT * FROM pg_user where usename = \'vagrant\' and usesuper" | grep vagrant',
            require => Service['postgresql-9.3'];
    }
}
