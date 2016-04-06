# Set up basic Socorro requirements.
class socorro::vagrant {

  service {
    'iptables':
      ensure => stopped,
      enable => false;

    'sshd':
      ensure  => running,
      enable  => true;

    'httpd':
      ensure  => running,
      enable  => true,
      require => Package['httpd'];

    'memcached':
      ensure  => running,
      enable  => true,
      require => Package['memcached'];

    'rabbitmq-server':
      ensure  => running,
      enable  => true,
      require => Package['rabbitmq-server'];

    'postgresql-9.4':
      ensure  => running,
      enable  => true,
      require => [
        Package['postgresql94-server'],
        Exec['postgres-initdb'],
        File['pg_hba.conf'],
      ];

    'elasticsearch':
      ensure  => running,
      enable  => true,
      require => Package['elasticsearch'];
  }

  yumrepo {
    'elasticsearch':
      baseurl => 'http://packages.elasticsearch.org/elasticsearch/1.4/centos',
      gpgkey  => 'https://packages.elasticsearch.org/GPG-KEY-elasticsearch';
    'PGDG':
      baseurl => 'http://yum.postgresql.org/9.4/redhat/rhel-$releasever-$basearch',
      gpgkey  => 'http://yum.postgresql.org/RPM-GPG-KEY-PGDG';
  }

  Yumrepo['elasticsearch', 'PGDG'] {
    enabled  => 1,
    gpgcheck => 1
  }

  package {
    'fpm':
      ensure   => latest,
      provider => gem,
      require  => Package['ruby-devel'];
  }

  package {
    'ca-certificates':
      ensure => latest
  }

  package {
    'yum-plugin-fastestmirror':
      ensure  => latest,
      require => Package['ca-certificates']
  }

  package {
    [
      'epel-release',
      'gcc-c++',
      'git',
      'httpd',
      'java-1.7.0-openjdk',
      'java-1.7.0-openjdk-devel',
      'libcurl-devel',
      'libffi-devel',
      'libxml2-devel',
      'libxslt-devel',
      'make',
      'memcached',
      'mod_wsgi',
      'nodejs',
      'npm',
      'openldap-devel',
      'openssl-devel',
      'pylint',
      'python-devel',
      'rpm-build',
      'rsync',
      'ruby-devel',
      'rubygem-puppet-lint',
      'subversion',
      'time',
      'unzip',
    ]:
    ensure  => latest,
    require => Package['yum-plugin-fastestmirror']
  }

  package {
    [
      'postgresql94-contrib',
      'postgresql94-devel',
      'postgresql94-plperl',
      'postgresql94-server',
    ]:
    ensure  => latest,
    require => [
      Yumrepo['PGDG'],
      Package['ca-certificates']
    ]
  }

  exec {
    'postgres-initdb':
      command => '/usr/pgsql-9.4/bin/postgresql94-setup initdb'
  }

  exec {
    'postgres-test-role':
      path    => '/usr/bin:/bin',
      cwd     => '/var/lib/pgsql',
      command => 'sudo -u postgres psql template1 -c "create user test with encrypted password \'aPassword\' superuser"',
      unless  => 'sudo -u postgres psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname=\'test\'" | grep -q 1',
      require => [
        Package['postgresql94-server'],
        Exec['postgres-initdb'],
        File['pg_hba.conf'],
        Service['postgresql-9.4']
      ]
  }

  exec {
    'postgres-breakpad-rw-role':
      path    => '/usr/bin:/bin',
      cwd     => '/var/lib/pgsql',
      command => 'sudo -u postgres psql template1 -c "create user breakpad_rw with encrypted password \'aPassword\' superuser"',
      unless  => 'sudo -u postgres psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname=\'breakpad_rw\'" | grep -q 1',
      require => [
        Package['postgresql94-server'],
        Exec['postgres-initdb'],
        File['pg_hba.conf'],
        Service['postgresql-9.4']
      ]
  }

  package {
    [
      'python-virtualenv',
      'supervisor',
      'rabbitmq-server',
      'python-pip',
      'nodejs-less',
    ]:
    ensure  => latest,
    require => Package['epel-release', 'yum-plugin-fastestmirror']
  }

  package {
    'elasticsearch':
      ensure  => latest,
      require => [
        Yumrepo['elasticsearch'],
        Package['java-1.7.0-openjdk']
      ]
  }

  file {
    'motd':
      ensure => file,
      path   => '/etc/motd',
      source => 'puppet:///modules/socorro/motd'
  }

  augeas {
    'sshd_config':
      context => '/files/etc/ssh/sshd_config',
      changes => [
        'set PrintMotd yes',
      ],
      notify  => Service['sshd']
  }

  file {
    '/etc/socorro':
      ensure => directory;

    'pg_hba.conf':
      ensure  => file,
      path    => '/var/lib/pgsql/9.4/data/pg_hba.conf',
      source  => 'puppet:///modules/socorro/var_lib_pgsql_9.4_data/pg_hba.conf',
      owner   => 'postgres',
      group   => 'postgres',
      require => [
        Package['postgresql94-server'],
        Exec['postgres-initdb'],
      ],
      notify  => Service['postgresql-9.4'];

    'pgsql.sh':
      ensure => file,
      path   => '/etc/profile.d/pgsql.sh',
      source => 'puppet:///modules/socorro/etc_profile.d/pgsql.sh',
      owner  => 'root';

    '.bashrc':
      ensure => file,
      path   => '/home/vagrant/.bashrc',
      source => 'puppet:///modules/socorro/home/bashrc',
      owner  => 'vagrant';

    'elasticsearch.yml':
      ensure  => file,
      path    => '/etc/elasticsearch/elasticsearch.yml',
      source  => 'puppet:///modules/socorro/etc_elasticsearch/elasticsearch.yml',
      owner   => 'root',
      require => Package['elasticsearch'],
      notify  => Service['elasticsearch'];
  }

}
