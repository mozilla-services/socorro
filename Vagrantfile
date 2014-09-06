is_jenkins = ENV['USER'] == 'jenkins'

Vagrant.configure("2") do |config|
  config.vm.box = "CentOS 6.4 x86_64 Minimal"
  config.vm.box_url = "http://developer.nrel.gov/downloads/vagrant-boxes/CentOS-6.4-x86_64-v20131103.box"

  config.vm.provider "virtualbox" do |v|
    v.name = "socorro-vm"
    v.memory = 512
  end

  if not is_jenkins
    # Don't share these resources when on Jenkins. We want to be able to
    # parallelize jobs.

    config.vm.network "private_network", ip:"10.11.12.13"
  end

  config.vm.synced_folder ".", "/home/vagrant/socorro"

  config.vm.provision :shell, inline: "if [ ! $(grep single-request-reopen /etc/sysconfig/network) ]; then echo RES_OPTIONS=single-request-reopen >> /etc/sysconfig/network && service network restart; fi"

  config.vm.provision :puppet do |puppet|
    puppet.module_path = "puppet/modules"
    puppet.manifests_path = "puppet/manifests"
    puppet.manifest_file = "vagrant.pp"
    # enable this to see verbose and debug puppet output
    #puppet.options = "--verbose --debug"
  end
end
