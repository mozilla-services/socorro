class webapp::socorro {

    service {
        'rabbitmq-server':
            ensure => running,
            require => Package['rabbitmq-server'];

        'postgresql-9.2':
            ensure => running,
            require => [
                        Package['postgresql92-server'],
                        Exec['postgres-initdb'],
                       ];
        'elasticsearch':
            ensure => running,
            require => Package['elasticsearch'];
    }

    exec {
        'postgres-initdb':
            command => '/sbin/service postgresql-9.2 initdb';
    }

    yumrepo {
        'PGDG':
            baseurl => 'http://yum.postgresql.org/9.2/redhat/rhel-$releasever-$basearch',
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
         'postgresql92-server',
         'postgresql92-plperl',
         'postgresql92-contrib',
         'postgresql92-devel',
        ]:
        ensure => latest,
        require => Yumrepo['PGDG'];
    }

    package {
        [
         'python-virtualenv',
         'supervisor',
         'rabbitmq-server',
         'python-pip',
        ]:
        ensure => latest,
        require => Yumrepo['EPEL'];
    }

    package {
        [
         'subversion',
         'make',
         'npm',
         'rsync',
         'time',
         'gcc-c++',
         'python-devel',
         'git',
         'libxml2-devel',
         'libxslt-devel',
         'openldap-devel',
         'java-1.7.0-openjdk',
        ]:
        ensure => latest;
    }

    package {
        'elasticsearch':
            provider => rpm,
            source => 'https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-0.90.4.noarch.rpm',
            require => Package['java-1.7.0-openjdk'],
            ensure => 'latest';
    }
}
