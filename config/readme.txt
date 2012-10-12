this directory contains sample ini files for the system.  Puppet will copy the
appropriate files to appropriate locations.

large-scale-dist:
    this directory contians ini files for Socorro configured for maximum
    throughput and maximum storage capacity.  It uses HBase for primary 
    crash storeage.  The ini files are broken up into sections to be 
    managed by separate groups.
        dev-managed: these are the ini values that are set by the dev team.
                     These include  references to pluggable classes that
                     implement the functionality of Socorro.  They are
                     eventually stored in /data/socorro/config
        it-managed: these contain the config values for a specific
                    installation: hostnames and passwords.  They're eventually
                    stored in /etc/socorro

small-scale-dist:
    this directory contains ini files for Socorro configured for a small scale
    installation. It uses the file system for crash storage and stand alone web
    servers rather than Apache. The ini files are all in the dev-managed
    directory rather than broken up to be managed by different groups.
        dev-managed: all ini files live here and will eventually be put into
                     data/socorro/config by puppet
        it-managed: intentionally empty.


