Exec {
    logoutput => on_failure,
}

import "socorro"

node default {
    include webapp::socorro
}
