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
	    recurse=> false,
	    ensure => directory;

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

	 'hbase-configs':
            path => "/etc/hbase/conf/",
            recurse => true,
            require => Exec['install-hbase'],
            source => "/home/socorro/dev/socorro/puppet/files/etc_hbase_conf";

# FIXME break this out to separate classes
	 'etc_supervisor':
            path => "/etc/supervisor/conf.d/",
            recurse => true,
            require => [Package['supervisor'], Exec['socorro-install']],
	    notify => Service[supervisor],
            source => "/home/socorro/dev/socorro/puppet/files/etc_supervisor";

        '/var/log/socorro':
            mode  => 644,
	    recurse=> true,
	    ensure => directory;

	'/home/socorro/persistent':
	    owner => socorro,
	    group => socorro,
	    ensure => directory;

    }

    file {
        '/etc/apt/sources.list':
            ensure => file;
    }

    exec {
        '/usr/bin/pip install isodate':
            require => Package['python-pip'],
            creates => '/usr/local/lib/python2.6/dist-packages/isodate';
    }

    exec {
        '/usr/bin/apt-get update && touch /tmp/apt-get-update':
            alias => 'apt-get-update',
            creates => '/tmp/apt-get-update';
    }

    exec {
        '/usr/bin/curl http://download.oracle.com/otn-pub/java/jdk/7u3-b04/jdk-7u3-linux-x64.tar.gz | tar -C /data -zxf -':
            alias => 'install-oracle-jdk',
            creates => '/data/jdk1.7.0_03/',
            require => Package['curl'];
    }   

    package {
        ['rsyslog', 'libcurl4-openssl-dev', 'libxslt1-dev', 'build-essential',
         'supervisor', 'ant', 'python-software-properties', 'python-pip',
         'curl', 'git-core', 'openjdk-6-jre-headless']:
            ensure => latest,
            require => Exec['apt-get-update'];
    }

    service {
        supervisor:
            enable => true,
            stop => '/usr/bin/service supervisor force-stop',
            hasstatus => true,
            require => [Package['supervisor'], Service['postgresql'],
                        Exec['setup-schema'], Exec['hbase-schema']],
            subscribe => Exec['socorro-install'],
            ensure => running;

        rsyslog:
            enable => true,
            require => Package['rsyslog'],
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

# FIXME
#        '/etc/logrotate.d/socorro':
#            ensure => present,
#	    source => $fqdn ? {
#		/sjc1.mozilla.com$/ => "puppet://$server/modules/socorro/stage/etc-logrotated/socorro",
#		default => "puppet://$server/modules/socorro/prod/etc-logrotated/socorro",
#		};
    package {
        ['python-psycopg2', 'python-simplejson', 'subversion', 'libpq-dev',
         'python-virtualenv', 'python-dev']:
            ensure => latest,
            require => Exec['apt-get-update'];
    }

    exec {
        '/usr/bin/make minidump_stackwalk':
            alias => 'minidump_stackwalk-install',
            cwd => '/home/socorro/dev/socorro',
            creates => '/home/socorro/dev/socorro/stackwalk',
            timeout => '3600',
            require => [Package['libcurl4-openssl-dev'],
                        File['/data/socorro'], Package['build-essential'],
                        Package['subversion']],
            user => 'socorro';
    }

    exec {
        '/usr/bin/make install':
            alias => 'socorro-install',
            cwd => '/home/socorro/dev/socorro',
            timeout => '3600',
            creates => '/home/socorro/dev/socorro/analysis/build/lib/socorro-analysis-job.jar',
            require => [Package['ant'], File['/data/socorro'],
                        Exec['minidump_stackwalk-install']],
            logoutput => on_failure,
            user => 'socorro';
    }

    exec { '/usr/bin/make reinstall':
            alias => 'socorro-reinstall',
            cwd => '/home/socorro/dev/socorro',
            timeout => '3600',
            require => Exec['socorro-install'],
            logoutput => on_failure,
            notify => [Service['supervisor'], Service['apache2'],
                       Service['memcached']],
            user => 'socorro';
    }
}

class socorro-web inherits socorro-base {

    file { '/var/log/httpd':
        owner => root,
        group => root,
        mode  => 755,
        recurse=> true,
        ensure => directory;
    }

    package {
        'apache2':
            ensure => latest,
            require => [Exec['apt-get-update'], Exec['socorro-install']];

        ['libapache2-mod-php5', 'libapache2-mod-wsgi']:
            ensure => latest,
            require => [Exec['apt-get-update'], Package[apache2]];
    }

    service {
        apache2:
            enable => true,
            ensure => running,
            hasstatus => true,
            subscribe => Exec['socorro-install'],
            require => [Package[apache2], Exec[enable-mod-rewrite], 
                        Exec[enable-mod-headers], Exec[enable-mod-ssl],
                        Exec[enable-mod-php5],
                        Package[libapache2-mod-php5], Exec[enable-mod-proxy]];
    }

}

class socorro-php inherits socorro-web {

     file { 
        '/var/log/httpd/crash-stats':
            require => Package[apache2],
            owner => root,
            group => root,
            mode  => 755,
            ensure => directory;

        '/etc/apache2/sites-available/crash-stats':
            require => Package[apache2],
            alias => 'crash-stats-vhost',
            owner => root,
            group => root,
            mode  => 644,
            ensure => present,
	    notify => Service[apache2],
	    source => "/home/socorro/dev/socorro/puppet/files/etc_apache2_sites-available/crash-stats";

        '/var/log/socorro/kohana':
            require => Package[apache2],
            owner => www-data,
            group => www-data,
            mode  => 755,
            ensure => directory;

	'/etc/php.ini':
            require => Package[apache2],
	    owner => root,
	    group => root,
	    mode => 644,
	    ensure => present,
	    notify => Service[apache2],
	    source => "/home/socorro/dev/socorro/puppet/files/php.ini";

        '/data/socorro/htdocs/application/logs':
            require => Exec['socorro-install'],
            mode => 777,
            ensure => directory;

# FIXME
#        '/etc/logrotate.d/kohana':
#            ensure => present,
#	    source => $fqdn ? {
#		/sjc1.mozilla.com$/ => "puppet://$server/modules/socorro/stage/etc-logrotated/kohana",
#		default => "puppet://$server/modules/socorro/prod/etc-logrotated/kohana",
#		};

    }

    exec {
        '/usr/sbin/a2ensite crash-stats':
            alias => 'enable-crash-stats-vhost',
            require => File['crash-stats-vhost'],
            creates => '/etc/apache2/sites-enabled/crash-stats';
    }

    exec {
        '/usr/sbin/a2enmod rewrite':
            alias => 'enable-mod-rewrite',
            require => File['crash-stats-vhost'],
            creates => '/etc/apache2/mods-enabled/rewrite.load';
    }
    exec {
        '/usr/sbin/a2enmod php5':
            alias => 'enable-mod-php5',
            require => File['crash-stats-vhost'],
            creates => '/etc/apache2/mods-enabled/php5.load';
    }

    exec {
        '/usr/sbin/a2enmod proxy && /usr/sbin/a2enmod proxy_http':
            alias => 'enable-mod-proxy',
            require => File['crash-stats-vhost'],
            creates => '/etc/apache2/mods-enabled/proxy_http.load';
    }

    exec {
        '/usr/sbin/a2enmod ssl':
            alias => 'enable-mod-ssl',
            require => File['crash-stats-vhost'],
            creates => '/etc/apache2/mods-enabled/ssl.load';
    }

    exec {
        '/usr/sbin/a2enmod headers':
            alias => 'enable-mod-headers',
            require => File['crash-stats-vhost'],
            creates => '/etc/apache2/mods-enabled/headers.load';
    }

    service {
        memcached:
            enable => true,
            require => Package['memcached'],
            ensure => running;
    }

    package {
        ['memcached', 'libcrypt-ssleay-perl', 'php5-pgsql', 'php5-curl',
	 'php5-dev', 'php5-tidy', 'php-pear', 'php5-common', 'php5-cli',
	 'php5-memcache', 'php5', 'php5-gd', 'php5-mysql', 'php5-ldap',
         'phpunit']:
            ensure => latest,
            require => Exec['apt-get-update'];
    }
}
