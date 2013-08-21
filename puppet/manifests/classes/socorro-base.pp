#
# defines the base classes that all servers share
#

class socorro-base {

    file {
        '/etc/profile.d/java.sh':
            owner => root,
            group => root,
            mode => 644,
            ensure => present,
            source => "/home/socorro/dev/socorro/puppet/files/etc_profile.d/java.sh";

        '/etc/hosts':
            owner => root,
            group => root,
            mode => 644,
            ensure => present,
            source => "/home/socorro/dev/socorro/puppet/files/hosts";

        '/data':
            owner => root,
            group => root,
            mode  => 755,
            ensure => directory;

        '/data/socorro':
            owner => socorro,
            group => socorro,
            mode  => 755,
            recurse=> false,
            ensure => directory;

        '/etc/socorro':
            owner => socorro,
            group => socorro,
            mode  => 755,
            recurse=> true,
            ensure => directory,
            source => "/home/socorro/dev/socorro/puppet/files/etc_socorro";

        '/etc/cron.d':
            owner => root,
            group => root,
            ensure => directory,
            recurse => true,
            require => File['/etc/socorro'],
            source => "/home/socorro/dev/socorro/puppet/files/etc_crond";

         '/etc/socorro/socorrorc':
            ensure => link,
            require => Exec['socorro-install'],
            target=> "/data/socorro/application/scripts/crons/socorrorc";

        '/etc/rsyslog.conf':
            require => Package[rsyslog],
            owner => root,
            group => root,
            mode => 644,
            ensure => present,
            notify => Service[rsyslog],
            source => "/home/socorro/dev/socorro/puppet/files/rsyslog.conf";

# FIXME break this out to separate classes
         'etc_supervisor':
            path => "/etc/supervisor/conf.d/",
            recurse => true,
            require => [Package['supervisor'], Exec['socorro-install']],
            #notify => Service[supervisor],
            source => "/home/socorro/dev/socorro/puppet/files/etc_supervisor";

        '/var/log/socorro':
            owner => socorro,
            group => socorro,
            mode  => 644,
            recurse=> true,
            ensure => directory;

        '/home/socorro/persistent':
            owner => socorro,
            group => socorro,
            ensure => directory;

        '/data/socorro/webapp-django/crashstats/settings/local.py':
            alias => 'django-config',
            require => Exec['socorro-reinstall'],
            owner => socorro,
            group => socorro,
            mode => 644,
            ensure => present,
            notify => Service['apache2'],
            source => '/home/socorro/dev/socorro/puppet/files/django/local.py';

        '/data/socorro/webapp-django/static/CACHE':
            owner => socorro,
            group => www-data,
            mode => 777,
            require => Exec['socorro-reinstall'],
            recurse => true,
            ensure => directory;

        '/etc/apt/sources.list':
            ensure => file;
    }

    exec {
        # optimization - touching /tmp/apt-get-update makes re-provisioning
        # faster. /tmp is cleared on boot
        '/usr/bin/apt-get update && touch /tmp/apt-get-update':
            alias => 'apt-get-update',
            creates => '/tmp/apt-get-update';

        'add-deadsnakes-ppa':
            command => '/usr/bin/sudo /usr/bin/add-apt-repository ppa:fkrull/deadsnakes && touch /tmp/add-deadsnakes-ppa',
            require => Package['python-software-properties'],
            creates => '/tmp/add-deadsnakes-ppa';

        'apt-get-update-deadsnakes':
            command => '/usr/bin/apt-get update && touch /tmp/apt-get-update-deadsnakes',
            require => Exec['add-deadsnakes-ppa'],
            creates => '/tmp/apt-get-update-deadsnakes';
    }

    package {
        ['rsyslog', 'libcurl4-openssl-dev', 'libxslt1-dev', 'build-essential',
         'supervisor', 'python-software-properties', 'curl', 'git-core',
         'memcached', 'npm', 'node-less', 'libsasl2-dev']:
            ensure => latest,
            require => Exec['apt-get-update'];
    }

    service {
#        supervisor:
#            enable => true,
#            stop => '/usr/bin/service supervisor force-stop',
#            hasstatus => true,
#            require => [Package['supervisor'], Service['postgresql'],
#                        Exec['setup-schema']],
#            subscribe => Exec['socorro-install'],
#            ensure => running;

        rsyslog:
            enable => true,
            require => Package['rsyslog'],
            ensure => running;

        memcached:
            enable => true,
            require => Package['memcached'],
            subscribe => Exec['socorro-reinstall'],
            ensure => running;
    }


    group { 'puppet':
        ensure => 'present',
    }
}

class socorro-python inherits socorro-base {

    user { 'socorro':
        ensure => 'present',
        uid => '10000',
        shell => '/bin/bash',
        groups => 'admin',
        managehome => true;
    }

    file {
        '/home/socorro':
            require => User[socorro],
            owner => socorro,
            group => socorro,
            mode  => 775,
            recurse=> false,
            ensure => directory;
    }

    file {
        '/home/socorro/dev':
            require => File['/home/socorro'],
            owner => socorro,
            group => socorro,
            mode  => 775,
            recurse=> false,
            ensure => directory;
    }

    file {
        '/etc/mercurial/hgrc':
            require => Package[mercurial],
            alias => 'mercurial-config',
            owner => root,
            group => root,
            mode  => 644,
            ensure => present,
            source => "/home/socorro/dev/socorro/puppet/files/etc_mercurial/hgrc";
    }

    package {
        ['subversion', 'libpq-dev', 'python-virtualenv', 'python2.6-dev',
         'python-pip', 'mercurial']:
            ensure => latest,
            require => [Exec['apt-get-update'],
                        Exec['apt-get-update-deadsnakes']];
    }

    exec {
        '/usr/bin/make minidump_stackwalk':
            alias => 'minidump_stackwalk-install',
            cwd => '/home/socorro/dev/socorro',
            creates => '/home/socorro/dev/socorro/stackwalk',
            timeout => '3600',
            require => [Package['libcurl4-openssl-dev'],
                        File['/data/socorro'], Package['build-essential'],
                        Package['subversion'], File['mercurial-config']],
            environment => ['HOME=/home/socorro',
                            'PWD=/home/socorro/dev/socorro'],
            user => 'socorro';
    }

    exec {
        '/usr/bin/make install VIRTUALENV=socorro-vagrant-virtualenv':
            alias => 'socorro-install',
            cwd => '/home/socorro/dev/socorro',
            timeout => '3600',
            creates => '/data/socorro/revision.txt',
            require => [File['/data/socorro'],
                        Exec['minidump_stackwalk-install']],
            logoutput => on_failure,
            user => 'socorro';
    }

    exec {
        '/usr/bin/make bootstrap VIRTUALENV=socorro-vagrant-virtualenv':
            alias => 'socorro-virtualenv',
            cwd => '/home/socorro/dev/socorro',
            timeout => '3600',
            logoutput => on_failure,
            require => Package['build-essential'],
            user => 'socorro';
    }

    exec { '/usr/bin/make reinstall VIRTUALENV=socorro-vagrant-virtualenv':
            alias => 'socorro-reinstall',
            cwd => '/home/socorro/dev/socorro',
            timeout => '3600',
            require => [Exec['socorro-install'],
                        Package['apache2'],
                        Package['memcached'],
                        Package['npm'],
                        Package['node-less'],
                        Package['libsasl2-dev']],
            logoutput => on_failure,
            user => 'socorro';
    }

}

class socorro-test inherits socorro-base {

    exec { '/usr/bin/make test VIRTUALENV=socorro-vagrant-virtualenv DB_SUPERUSER=socorro':
            alias => 'socorro-unittest',
            cwd => '/home/socorro/dev/socorro',
            timeout => '3600',
            require => [Exec['socorro-reinstall'], Exec['create-roles'],
                        Exec['create-user'], Exec['install-json-enhancements']],
            logoutput => on_failure,
            user => 'socorro';
    }
}

class socorro-web inherits socorro-base {

    package {
        'apache2':
            ensure => latest,
            require => [Exec['apt-get-update']];

        'libapache2-mod-wsgi':
            ensure => latest,
            require => [Exec['apt-get-update'], Package[apache2]];
    }

    service {
        apache2:
            enable => true,
            ensure => running,
            hasstatus => true,
            subscribe => [Exec['socorro-reinstall'],
                          Exec['enable-crash-stats-vhost']],
            require => [Package['apache2'], Package['libapache2-mod-wsgi']];
    }

     file {
        '/etc/apache2/sites-available/crash-stats':
            require => Package['apache2'],
            alias => 'crash-stats-vhost',
            owner => root,
            group => root,
            mode  => 644,
            ensure => present,
            notify => Service[apache2],
            source => "/home/socorro/dev/socorro/puppet/files/etc_apache2_sites-available/crash-stats";
    }

    exec {
        '/usr/sbin/a2ensite crash-stats':
            alias => 'enable-crash-stats-vhost',
            require => File['crash-stats-vhost'],
            creates => '/etc/apache2/sites-enabled/crash-stats';
    }

    exec {
        '/data/socorro/webapp-django/manage.py syncdb --noinput':
            alias => 'django-syncdb',
            timeout => '3600',
            require => [Exec['socorro-reinstall'], File['django-config'],
                        Exec['create-breakpad-db']],
            logoutput => on_failure,
            user => 'socorro';
    }
}
