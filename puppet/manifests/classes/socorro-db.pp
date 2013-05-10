class socorro-db inherits socorro-base {
    file {
        '/etc/postgresql/9.2/main/postgresql.conf':
            alias => 'postgres-config',
            owner => postgres,
            group => postgres,
            mode => 644,
            ensure => present,
            require => Package['postgresql-9.2'],
            notify => Service['postgresql'],
            source => "/home/socorro/dev/socorro/puppet/files/etc_postgresql_9.2_main/postgresql.conf";

        '/etc/apt/sources.list.d/pgdg.list':
            alias => 'pgdg-list',
            owner => root,
            group => root,
            mode => 644,
            ensure => present,
            require => Exec['add-postgres-apt-key'],
            source => '/home/socorro/dev/socorro/puppet/files/etc_postgresql_9.2_main/pgdg.list';

        '/etc/apt/preferences.d/pgpdg.pref':
            alias => 'pgdg-pref',
            owner => 'root',
            group => 'root',
            mode => 644,
            ensure => present,
            require => File['pgdg-list'],
            source => '/home/socorro/dev/socorro/puppet/files/etc_postgresql_9.2_main/pgdg.pref';
    }

    package {
        'postgresql-9.2':
            alias => 'postgresql',
            ensure => latest,
            require => Exec['update-postgres-ppa'];

        'postgresql-plperl-9.2':
            alias => 'postgresql-plperl',
            ensure => latest,
            require => Exec['update-postgres-ppa'];

        'postgresql-contrib-9.2':
            alias => 'postgresql-contrib',
            ensure => latest,
            require => Exec['update-postgres-ppa'];
    }

    exec {
       'update-postgres-ppa':
            command => '/usr/bin/apt-get update && touch /tmp/update-postgres-ppa',
            #require => Exec['add-postgres-ppa'],
            require => File['pgdg-pref'],
            creates => '/tmp/update-postgres-ppa';

        'add-postgres-apt-key':
            command => '/usr/bin/wget -O - http://apt.postgresql.org/pub/repos/apt/ACCC4CF8.asc | /usr/bin/sudo /usr/bin/apt-key add -',
            require => Package['python-software-properties'];
    }

    exec {
        '/usr/bin/psql -f sql/roles.sql && /home/socorro/dev/socorro/socorro-vagrant-virtualenv/bin/python socorro/external/postgresql/setupdb_app.py --database_name=breakpad --fakedata --fakedata_days=15':
            require => [Package['postgresql'], File['postgres-config'],
                        Exec['socorro-virtualenv'], Exec['createuser']],
            unless => '/usr/bin/psql --list breakpad',
            cwd => '/home/socorro/dev/socorro',
            environment => 'PYTHONPATH=/data/socorro/application:/data/socorro/thirdparty',
            alias => 'create-breakpad-db',
            timeout => '3600',
            user => 'postgres';
    }

    exec {
        '/usr/bin/createuser -d -r -s socorro':
            alias => 'createuser',
            require => [Package['postgresql'], File['postgres-config']],
            onlyif => '/usr/bin/psql -xt breakpad -c "SELECT * FROM pg_user WHERE usename = \'socorro\'" | grep "(No rows)"',
            user => 'postgres'
    }

    service { 'postgresql':
            enable => true,
            require => Package['postgresql'],
            ensure => running;
    }

}
