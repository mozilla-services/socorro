# Whether or not this is jenkins user
IS_JENKINS = ENV['USER'] == 'jenkins'

# Specify how much memory to use
VAGRANT_MEMORY = (ENV['VAGRANT_MEMORY'] || '1024').to_i

# Specify whether or not to enable Puppet debug output
PUPPET_DEBUG = (ENV['VAGRANT_PUPPET_DEBUG'] || '0') == '1'

Vagrant.configure("2") do |config|
  config.vm.box = "puppetlabs/centos-7.0-64-puppet"

  config.vm.provider "virtualbox" do |v|
    v.name = "socorro-vm"
    v.memory = VAGRANT_MEMORY
  end

  if not IS_JENKINS
    # Don't share these resources when on Jenkins. We want to be able to
    # parallelize jobs.

    config.vm.network "private_network", ip:"10.11.12.13"
  end

  config.vm.synced_folder ".", "/home/vagrant/socorro"

  config.vm.provision :shell, inline: "if [ ! $(grep single-request-reopen /etc/sysconfig/network) ]; then echo RES_OPTIONS=single-request-reopen >> /etc/sysconfig/network && service network restart; fi"

  config.vm.provision :puppet do |puppet|
    puppet.environment_path = "puppet"
    puppet.environment = "vagrant"
    puppet.manifests_path = "puppet/vagrant/manifests"
    puppet.manifest_file = "vagrant.pp"

    if PUPPET_DEBUG
      # Enables puppet debug output
      puppet.options = "--verbose --debug"
    end
  end
end
