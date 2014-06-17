class socorro::socorro_env (
  $user='vagrant',
  $socorro_dir="/home/vagrant/src/socorro",
  $flag_comment = '# WARNING. DO NOT EDIT: This command is managed by puppet and is used to bootstrap the socorro environment'
) {
  $bash_config = "/home/${user}/.bash_profile"
  $virtualenv_activate = "${socorro_dir}/socorro-virtualenv/bin/activate"

  exec {"activate-venv-on-login":
    path => "/home/${user}",
    unless => "/bin/cat ${bash_config} | /bin/grep '${flag_comment}'",
    command => "/bin/echo 'cd ${socorro_dir} && source ${virtualenv_activate} ${flag_comment}' >> ${bash_config}",
    user => "${user}",
  }
}
