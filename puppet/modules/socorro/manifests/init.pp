# Set up basic Socorro requirements.
class socorro::vagrant {

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
    'dchen':
      baseurl  => 'https://repos.fedorapeople.org/repos/dchen/apache-maven/epel-$releasever/$basearch/';
    'devtools':
      baseurl  => 'http://people.centos.org/tru/devtools-1.1/$releasever/$basearch/RPMS';
    'elasticsearch':
      baseurl  => 'http://packages.elasticsearch.org/elasticsearch/0.90/centos';
    'EPEL':
      baseurl  => 'http://dl.fedoraproject.org/pub/epel/$releasever/$basearch',
      timeout  => 60;
    'PGDG':
      baseurl  => 'http://yum.postgresql.org/9.3/redhat/rhel-$releasever-$basearch';
  }

  Yumrepo['dchen', 'devtools', 'elasticsearch', 'EPEL', 'PGDG'] {
    enabled  => 1,
    gpgcheck => 0,
    require  => Package['ca-certificates', 'yum-plugin-fastestmirror']
  }

  package {
    [
      'apache-maven',
    ]:
    ensure  => latest,
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
      'ca-certificates',
      'daemonize',
      'gcc-c++',
      'git',
      'httpd',
      'java-1.7.0-openjdk',
      'java-1.7.0-openjdk-devel',
      'libxml2-devel',
      'libxslt-devel',
      'make',
      'memcached',
      'mod_wsgi',
      'openldap-devel',
      'python-devel',
      'rpm-build',
      'rsync',
      'ruby-devel',
      'subversion',
      'time',
      'unzip',
      'yum-plugin-fastestmirror',
    ]:
    ensure => latest
  }

  package {
    [
      'postgresql93-contrib',
      'postgresql93-devel',
      'postgresql93-plperl',
      'postgresql93-server',
    ]:
    ensure  => latest,
    require => Yumrepo['PGDG']
  }

  exec {
    'postgres-test-role':
      path    => '/usr/bin:/bin',
      cwd     => '/var/lib/pgsql',
      command => 'sudo -u postgres psql template1 -c "create user test with encrypted password \'aPassword\' superuser"',
      unless  => 'sudo -u postgres psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname=\'test\'" | grep -q 1',
      require => [
        Package['postgresql93-server'],
        Exec['postgres-initdb'],
        File['pg_hba.conf'],
        Service['postgresql-9.3']
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
    require => Yumrepo['EPEL']
  }

  package {
    'elasticsearch':
      ensure  => latest,
      require => [ Yumrepo['elasticsearch'], Package['java-1.7.0-openjdk'] ]
  }

  package {
    'devtoolset-1.1-gcc-c++':
      ensure  => latest,
      require => Yumrepo['devtools']
  }

  file {
    '/etc/socorro':
      ensure => directory;

    'pg_hba.conf':
      ensure  => file,
      path    => '/var/lib/pgsql/9.3/data/pg_hba.conf',
      source  => 'puppet:///modules/socorro/var_lib_pgsql_9.3_data/pg_hba.conf',
      owner   => 'postgres',
      group   => 'postgres',
      require => [
        Package['postgresql93-server'],
        Exec['postgres-initdb'],
      ],
      notify  => Service['postgresql-9.3'];

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
      ensure => file,
      path   => '/etc/elasticsearch/elasticsearch.yml',
      source => 'puppet:///modules/socorro/etc_elasticsearch/elasticsearch.yml',
      owner  => 'root';
  }

}
