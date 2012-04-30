class socorro-db inherits socorro-base {
    file {
        '/etc/postgresql/9.0/main/postgresql.conf':
            alias => 'postgres-config',
            owner => postgres,
            group => postgres,
            mode => 644,
            ensure => present,
            require => Package['postgresql-9.0'],
            notify => Service['postgresql'],
            source => "/home/socorro/dev/socorro/puppet/files/etc_postgresql_9.0_main/postgresql.conf";
    }

    package {
	'postgresql-9.0':
            alias => 'postgresql',
	    ensure => latest,
            require => Exec['update-postgres-ppa'];

	'postgresql-plperl-9.0':
            alias => 'postgresql-plperl',
            ensure => latest,
            require => Exec['update-postgres-ppa'];

        'postgresql-contrib-9.0':
            alias => 'postgresql-contrib',
            ensure => latest,
            require => Exec['update-postgres-ppa'];
    }

    exec {
        'add-postgres-ppa':
            command => '/usr/bin/sudo /usr/bin/add-apt-repository ppa:pitti/postgresql',
            creates => '/etc/apt/sources.list.d/pitti-postgresql-lucid.list',
            require => Package['python-software-properties'];

       'update-postgres-ppa':
            command => '/usr/bin/apt-get update && touch /tmp/update-postgres-ppa',
            require => Exec['add-postgres-ppa'],
            creates => '/tmp/update-postgres-ppa';
    }

    exec {
        '/home/socorro/dev/socorro/socorro/external/postgresql/setupdb_app.py --database_name=breakpad':
            require => [Package['postgresql'], File['postgres-config'],
                        Exec['socorro-reinstall']],
            unless => '/usr/bin/psql --list breakpad',
            cwd => '/home/socorro/dev/socorro',
            environment => 'PYTHONPATH=/data/socorro/application',
            alias => 'create-breakpad-db',
            user => 'postgres';
    }

    exec {
        '/usr/bin/createuser -d -r -s socorro':
            require => [Package['postgresql'], File['postgres-config']],
            onlyif => '/usr/bin/psql -xt breakpad -c "SELECT * FROM pg_user WHERE usename = \'socorro\'" | grep "(No rows)"',
            user => 'postgres'
    }

    exec {
        '/bin/bash /home/socorro/dev/socorro/tools/dataload/import.sh':
            alias => 'dataload',
            user => 'postgres',
            cwd => '/home/socorro/dev/socorro/tools/dataload',
            onlyif => '/usr/bin/psql -xt breakpad -c "SELECT count(*) FROM products" | grep "count | 0"',
            logoutput => on_failure,
            require => Exec['create-breakpad-db'];
    }

    service { 'postgresql':
            enable => true,
            require => Package['postgresql'],
            ensure => running;
    }

}
