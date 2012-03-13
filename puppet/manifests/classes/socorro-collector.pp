class socorro-collector inherits socorro-web {
     file { 

        '/home/socorro/primaryCrashStore':
	    require => User[socorro],
            owner => www-data,
            group => socorro,
            mode  => 2775,
	    recurse=> false,
	    ensure => directory;

        '/home/socorro/fallback':
	    require => User[socorro],
            owner => www-data,
            group => socorro,
            mode  => 2775,
	    recurse=> false,
	    ensure => directory;

        '/var/log/httpd/crash-reports':
            require => Package[apache2],
            owner => root,
            group => root,
            mode  => 755,
            ensure => directory;

        '/etc/apache2/sites-available/crash-reports':
            require => Package[apache2],
            alias => 'crash-reports-vhost',
            owner => root,
            group => root,
            mode  => 644,
            ensure => present,
	    notify => Service[apache2],
	    source => "/home/socorro/dev/socorro/puppet/files/etc_apache2_sites-available/crash-reports";

    }

    exec {
        '/usr/sbin/a2ensite crash-reports':
            alias => 'enable-crash-reports-vhost',
            require => File['crash-reports-vhost'],
            creates => '/etc/apache2/sites-enabled/crash-reports';
    }

    include socorro-python
}
