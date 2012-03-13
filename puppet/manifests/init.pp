Exec { path => ["/data/jdk1.7.0_03/bin", "/bin", "/sbin", "/usr/bin",
                "/usr/sbin", "/usr/local/bin", "/usr/local/sbin"],
       environment => "JAVA_HOME=/data/jdk1.7.0_03/",
       logoutput => on_failure
}

import "classes/*"
import "nodes/*"
