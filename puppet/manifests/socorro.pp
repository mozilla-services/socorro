# Set up basic Socorro requirements.
class webapp::socorro {

  service {
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
      timeout => 60;

    'devtools':
      baseurl  => 'http://people.centos.org/tru/devtools-1.1/$releasever/$basearch/RPMS',
      enabled  => 1,
      gpgcheck => 0;

    'elasticsearch':
      baseurl  => 'http://packages.elasticsearch.org/elasticsearch/0.90/centos',
      enabled  => 1,
      gpgcheck => 0;
  }

  package {
    [
      'subversion',
      'make',
      'rsync',
      'time',
      'gcc-c++',
      'python-devel',
      'git',
      'libxml2-devel',
      'libxslt-devel',
      'openldap-devel',
      'java-1.7.0-openjdk',
      'yum-plugin-fastestmirror',
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

  package {
    [
      'python-virtualenv',
      'supervisor',
      'rabbitmq-server',
      'python-pip',
      'npm',
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

}
