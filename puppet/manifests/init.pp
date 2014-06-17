Exec {
  logoutput => true,
  timeout => 0
}

import "socorro"
import "classes/*.pp"

node default {
  include webapp::socorro
  include socorro::socorro_env
  include socorro::python_path
}
