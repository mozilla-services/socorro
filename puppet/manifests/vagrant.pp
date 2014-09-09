Exec {
  logoutput => 'on_failure'
}

node default {
  include webapp::socorro
}

# Set up basic Socorro requirements.
class webapp::socorro {

  service {
    'iptables':
      ensure => stopped,
      enable => false;

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

    'postgresql-9.3':
      ensure  => running,
      enable  => true,
      require => [
          Package['postgresql93-server'],
          Exec['postgres-initdb'],
          File['pg_hba.conf'],
        ];

    'elasticsearch':
      ensure  => running,
      enable  => true,
      require => Package['elasticsearch'];
  }

  exec {
    'postgres-initdb':
      command => '/sbin/service postgresql-9.3 initdb'
  }

  yumrepo {
    'PGDG':
      baseurl  => 'http://yum.postgresql.org/9.3/redhat/rhel-$releasever-$basearch',
      descr    => 'PGDG',
      enabled  => 1,
      gpgcheck => 0;

    'EPEL':
      baseurl  => 'http://dl.fedoraproject.org/pub/epel/$releasever/$basearch',
      descr    => 'EPEL',
      enabled  => 1,
      gpgcheck => 0,
      timeout  => 60;

    'devtools':
      baseurl  => 'http://people.centos.org/tru/devtools-1.1/$releasever/$basearch/RPMS',
      enabled  => 1,
      gpgcheck => 0;

    'elasticsearch':
      baseurl  => 'http://packages.elasticsearch.org/elasticsearch/0.90/centos',
      enabled  => 1,
      gpgcheck => 0;

    'dchen':
      baseurl  => 'https://repos.fedorapeople.org/repos/dchen/apache-maven/epel-$releasever/$basearch/',
      enabled  => 1,
      gpgcheck => 0;
  }

  package {
    [
      'apache-maven',
    ]:
    ensure => latest,
    require => Yumrepo['dchen'];
  }

  package {
    'fpm':
      ensure   => latest,
      provider => gem,
      require  => Package['ruby-devel'];
  }

  package {
    [
      'subversion',
      'make',
      'rsync',
      'ruby-devel',
      'rpm-build',
      'time',
      'gcc-c++',
      'python-devel',
      'git',
      'libxml2-devel',
      'libxslt-devel',
      'openldap-devel',
      'java-1.7.0-openjdk',
      'java-1.7.0-openjdk-devel',
      'yum-plugin-fastestmirror',
      'httpd',
      'mod_wsgi',
      'memcached',
      'daemonize',
      'unzip',
    ]:
    ensure => latest
  }

  package {
    [
      'postgresql93-server',
      'postgresql93-plperl',
      'postgresql93-contrib',
      'postgresql93-devel',
    ]:
    ensure  => latest,
    require => [ Yumrepo['PGDG'], Package['yum-plugin-fastestmirror']]
  }

  exec {
    'postgres-test-role':
      path => '/usr/bin:/bin',
      cwd => '/var/lib/pgsql',
      command => 'sudo -u postgres psql template1 -c "create user test with encrypted password \'aPassword\' superuser"',
      unless => 'sudo -u postgres psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname=\'test\'" | grep -q 1',
      require => [
        Package['postgresql93-server'],
        Exec['postgres-initdb'],
        File['pg_hba.conf'],
        Service['postgresql-9.3']
      ];
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
    require => [ Yumrepo['EPEL'], Package['yum-plugin-fastestmirror']]
  }

  package {
    'elasticsearch':
      ensure  => latest,
      require => [ Yumrepo['elasticsearch'], Package['java-1.7.0-openjdk'] ]
  }

  package {
    'devtoolset-1.1-gcc-c++':
      ensure  => latest,
      require => [ Yumrepo['devtools'], Package['yum-plugin-fastestmirror']]
  }

  file {
    '/etc/socorro':
      ensure => directory;

    'pg_hba.conf':
      path    => '/var/lib/pgsql/9.3/data/pg_hba.conf',
      source  => '/vagrant/puppet/files/var_lib_pgsql_9.3_data/pg_hba.conf',
      owner   => 'postgres',
      group   => 'postgres',
      ensure  => file,
      require => [
        Package['postgresql93-server'],
        Exec['postgres-initdb'],
      ],
      notify  => Service['postgresql-9.3'];

    'pgsql.sh':
      path   => '/etc/profile.d/pgsql.sh',
      source => '/vagrant/puppet/files/etc_profile.d/pgsql.sh',
      owner  => 'root',
      ensure => file;
  }

}
