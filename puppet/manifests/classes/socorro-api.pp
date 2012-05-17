# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

class socorro-api inherits socorro-web {
     file { 
        '/etc/apache2/sites-available/socorro-api':
            require => Package[apache2],
            alias => 'socorro-api-vhost',
            owner => root,
            group => root,
            mode  => 644,
            ensure => present,
	    notify => Service[apache2],
	    source => "/home/socorro/dev/socorro/puppet/files/etc_apache2_sites-available/socorro-api";

	'/var/run/wsgi':
	    ensure => directory;

    }

    exec {
        '/usr/sbin/a2ensite socorro-api':
            alias => 'enable-socorro-api-vhost',
            require => File['socorro-api-vhost'],
            creates => '/etc/apache2/sites-enabled/socorro-api';
    }

    include socorro-python
}
