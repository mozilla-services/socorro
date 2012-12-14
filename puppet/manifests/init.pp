Exec {
    logoutput => on_failure,
    path => ["/usr/local/bin", "/usr/bin", "/bin", "/opt/vagrant_ruby/bin", "/sbin", "/usr/sbin"],
}

import "classes/*"
import "nodes/*"
