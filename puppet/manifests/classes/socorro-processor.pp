
class socorro-processor inherits socorro-python {
    file {
        '/home/socorro/temp':
	    require => User[socorro],
            owner => socorro,
            group => socorro,
            mode  => 775,
	    recurse=> false,
	    ensure => directory;

	 "/mnt/socorro":
	    ensure => directory;
	 "/mnt/socorro/symbols":
	    ensure => directory;
	}

    package { "nfs-common": 
        ensure => latest,
        require => Exec['apt-get-update'];
    }   

# FIXME how to fake symbols?
#    mount { 
#	"/mnt/socorro/symbols":
#	    device => $fqdn ? {
#		/nfs_server_here$/ => "nfs_server_ip_here:/vol/socorro/symbols",
#		default => "nfs_server_ip_here:/vol/pio_symbols",
#		},
#	    require => File['/mnt/socorro/symbols'],
#	    ensure => mounted,
#	    fstype => nfs,
#	    options => "ro,noatime,nolock,nfsvers=3,proto=tcp";
#    }
}
