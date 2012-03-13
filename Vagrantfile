Vagrant::Config.run do |config|
  config.vm.box = "socorro-all"
  config.vm.network :hostonly, "33.33.33.10"
  config.vm.customize ["modifyvm", :id, "--memory", "1024"]
  # enable this to see the GUI if vagrant cannot connect
  #config.vm.boot_mode = :gui
  config.vm.provision :puppet do |puppet|
    puppet.manifests_path = "puppet/manifests"
    puppet.manifest_file = "init.pp"
    # enable this to see verbose and debug puppet output
    #puppet.options = "--verbose --debug"
  end
  Vagrant::Config.run do |config|
    config.vm.share_folder("socorro-code", "/home/socorro/dev/socorro", "./", :nfs => true)
  end
end
