class webapp::socorro {

    service {
        'rabbitmq-server':
            ensure => running,
            require => Package['rabbitmq-server'];

        'postgresql-9.3':
            ensure => running,
            require => [
                        Package['postgresql93-server'],
                        Exec['postgres-initdb'],
                       ];
        'elasticsearch':
            ensure => running,
            require => Package['elasticsearch'];
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
}
