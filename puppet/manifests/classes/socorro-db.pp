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
        '/usr/bin/createdb -E \'utf-8\' -T template0 breakpad':
            require => [Package['postgresql'], File['postgres-config']],
            unless => '/usr/bin/psql --list breakpad',
            alias => 'create-breakpad-db',
            user => 'postgres';
    }

    exec {
       'update-postgres-ppa':
            command => '/usr/bin/apt-get update && touch /tmp/update-postgres-ppa',
            require => Exec['add-postgres-ppa'],
            creates => '/tmp/update-postgres-ppa';
    }

    exec {
        '/usr/bin/sudo /usr/bin/add-apt-repository ppa:pitti/postgresql':
            alias => 'add-postgres-ppa',
            creates => '/etc/apt/sources.list.d/pitti-postgresql-lucid.list',
            require => Package['python-software-properties'];

        '/usr/bin/psql -f /home/socorro/dev/socorro/sql/schema/2.4/breakpad_roles.sql breakpad':
            alias => 'create-breakpad-roles',
            user => 'postgres',
            require => Exec['create-breakpad-db'];

        '/usr/bin/psql -f /home/socorro/dev/socorro/sql/schema/2.4/breakpad_schema.sql breakpad':
            alias => 'setup-schema',
            user => 'postgres',
            require => Exec['create-breakpad-roles'],
            onlyif => '/usr/bin/psql breakpad -c "\d reports" 2>&1 | grep "Did not find any relation"';
    }

    exec {
        '/usr/bin/psql -c "grant all on database breakpad to breakpad_rw"':
            alias => 'grant-breakpad-access',
            user => 'postgres',
            unless => '/usr/bin/psql breakpad -c "\z " | grep breakpad',
            require => Exec['create-breakpad-roles'];
    }

    exec {
        '/usr/bin/psql breakpad < /usr/share/postgresql/9.0/contrib/citext.sql':
            user => 'postgres',
            unless => '/usr/bin/psql breakpad -c "\dT" | grep citext',
            require => [Exec['create-breakpad-db'], Package['postgresql-contrib']];
    }

    exec {
        '/usr/bin/psql -c "create language plpgsql" breakpad':
            user => 'postgres',
            unless => '/usr/bin/psql -c "SELECT lanname from pg_language where lanname = \'plpgsql\'" breakpad | grep plpgsql',
            alias => 'create-language-plpgsql',
            require => Exec['create-breakpad-db'];
    }

    exec {
        '/usr/bin/psql -c "create language plperl" breakpad':
            user => 'postgres',
            unless => '/usr/bin/psql -c "SELECT lanname from pg_language where lanname = \'plperl\'" breakpad | grep plperl',
            alias => 'create-language-plperl',
            require => [Exec['create-language-plpgsql'], Package['postgresql-plperl']];
    }

    exec {
        '/bin/bash /home/socorro/dev/socorro/tools/dataload/import.sh':
            alias => 'dataload',
            user => 'postgres',
            cwd => '/home/socorro/dev/socorro/tools/dataload/',
            onlyif => '/usr/bin/psql -xt breakpad -c "SELECT count(*) FROM reports" | grep "count | 0"',
            logoutput => on_failure,
            require => Exec['setup-schema'];
    }

    exec {
        '/usr/bin/psql -c "SELECT backfill_matviews(\'2012-03-02\', \'2012-03-03\'); UPDATE product_versions SET featured_version = true" breakpad':
            alias => 'bootstrap-matviews',
            user => 'postgres',
            onlyif => '/usr/bin/psql -xt breakpad -c "SELECT count(*) FROM product_versions" | grep "count | 0"',
            require => Exec['dataload'];
    }

    exec {
        '/usr/bin/createdb test':
            require => Package['postgresql'],
            unless => '/usr/bin/psql --list test',
            alias => 'create-test-db',
            user => 'postgres';
    }

    exec {
        '/usr/bin/psql -c "create role test login password \'aPassword\'"':
            alias => 'create-test-role',
            unless => '/usr/bin/psql -c "SELECT rolname from pg_roles where rolname = \'test\'" test | grep test',
            user => 'postgres',
            require => Exec['create-test-db'];
    }

    exec {
        '/usr/bin/psql -c "grant all on database test to test"':
            alias => 'grant-test-access',
            user => 'postgres',
            unless => '/usr/bin/psql breakpad -c "\z " | grep test',
            require => Exec['create-test-role'];
    }

    exec {
        '/usr/bin/psql test < /usr/share/postgresql/9.0/contrib/citext.sql':
            user => 'postgres',
            unless => '/usr/bin/psql breakpad -c "\dT" | grep citext',
            require => [Exec['create-test-db'], Package['postgresql-contrib']];
    }

    exec {
        '/usr/bin/psql -c "create language plpgsql" test':
            user => 'postgres',
            unless => '/usr/bin/psql -c "SELECT lanname from pg_language where lanname = \'plpgsql\'" test | grep plpgsql',
            require => Exec['create-test-db'];
    }

    exec {
        '/usr/bin/psql -c "create language plperl" test':
            user => 'postgres',
            unless => '/usr/bin/psql -c "SELECT lanname from pg_language where lanname = \'plperl\'" test | grep plperl',
            require => [Exec['create-test-db'], Package['postgresql-plperl']];
    }

    service { 'postgresql':
            enable => true,
            require => Package['postgresql'],
            ensure => running;
    }

}
