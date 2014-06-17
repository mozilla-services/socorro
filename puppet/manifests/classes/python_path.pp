class socorro::python_path (
  $user='vagrant',
  $flag_comment = '# WARNING. DO NOT EDIT: This command is managed by puppet and is used to set the default PYTHONPATH'
) {
  $bash_config = "/home/${user}/.bash_profile"
  $extra_path_export = 'export PYTHONPATH=.:$PYTHONPATH'

  exec {"add-cwd-to-default-python-path":
    path => "/bin/",
    unless => "cat ${bash_config} | grep '${flag_comment}'",
    command => "echo '${extra_path_export} ${flag_comment}' >> ${bash_config}",
    user => "${user}",
  }
}
