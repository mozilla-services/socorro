require "yaml"

# Load up our vagrant config files -- vagrantconfig.yaml first
_config = YAML.load(File.open(File.join(File.dirname(__FILE__),
                    "vagrantconfig.yaml"), File::RDONLY).read)

# Local-specific/not-git-managed config -- vagrantconfig_local.yaml
begin
    _config.merge!(YAML.load(File.open(File.join(File.dirname(__FILE__),
                   "vagrantconfig_local.yaml"), File::RDONLY).read))
rescue Errno::ENOENT # No vagrantconfig_local.yaml found -- that's OK; just
                     # use the defaults.
end

CONF = _config


Vagrant::Config.run do |config|
  config.vm.box = "socorro-all"
  config.vm.network :hostonly, "33.33.33.10"
  config.vm.customize ["modifyvm", :id, "--memory", CONF['memory']]

  if CONF['boot_mode'] == 'gui'
    config.vm.boot_mode = :gui
  end
  config.vm.provision :puppet do |puppet|
    puppet.manifests_path = "puppet/manifests"
    puppet.manifest_file = "init.pp"
    # enable this to see verbose and debug puppet output
    if CONF['nfs'] == false
      puppet.options = "--verbose --debug"
    end
  end
  Vagrant::Config.run do |config|
    config.vm.share_folder("socorro-code", "/home/socorro/dev/socorro", "./", :nfs => true)
  end
end
