Exec {
  logoutput => 'on_failure'
}

node default {
  include socorro
}
