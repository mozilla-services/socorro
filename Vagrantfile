
Vagrant::Config.run do |config|
  config.vm.box = "CentOS 6.4 x86_64 Minimal"
  config.vm.box_url = "http://developer.nrel.gov/downloads/vagrant-boxes/CentOS-6.4-x86_64-v20131103.box"

  Vagrant.configure("1") do |config|
    config.vm.customize ["modifyvm", :id, "--memory", CONF['memory']]
  end

  Vagrant.configure("2") do |config|
    config.vm.provider "virtualbox" do |v|
      v.name = "Socorro_VM"
      v.customize ["modifyvm", :id, "--memory", CONF['memory']]
    end
  end

  is_jenkins = ENV['USER'] == 'jenkins'

  if not is_jenkins
    # Don't share these resources when on Jenkins. We want to be able to
    # parallelize jobs.

    config.vm.network :hostonly, "10.11.12.13"
  end

  if CONF['boot_mode'] == 'gui'
    config.vm.boot_mode = :gui
  end

  config.vm.synced_folder ".", "/home/vagrant/socorro"

  config.vm.provision :shell, inline: "if [ ! $(grep single-request-reopen /etc/sysconfig/network) ]; then echo RES_OPTIONS=single-request-reopen >> /etc/sysconfig/network && service network restart; fi"

  config.vm.provision :puppet do |puppet|
    puppet.manifests_path = "puppet/manifests"
    puppet.manifest_file = "vagrant.pp"
  end
end
