.. index:: install-binary

.. _install_binary_package-chapter:

Installing from binary package
==============================

If you do not wish to install from source, and are using a RHEL-compatible
64-bit Linux distribution (such as CentOS), then you can install from a package
instead of from source. Both tarball and RPM based installs are
provided.

Installing an RPM:

.. code-block:: bash

  $ curl https://ci.mozilla.org/job/socorro-release/lastSuccessfulBuild/artifact/socorro-latest.x86_64.rpm
  $ sudo rpm -i socorro-latest.x86_64.rpm

Installing a tarball:

.. code-block:: bash

  $ sudo su -
  # mkdir -p "$HOME/socorro-deploy"
  # curl https://raw.githubusercontent.com/mozilla/socorro/master/scripts/deploy.sh \
     -o "$HOME/socorro-deploy/deploy.sh"
  # chmod +x "$HOME/socorro-deploy/deploy.sh"
  # "$HOME/socorro-deploy/deploy.sh" \
     https://ci.mozilla.org/job/socorro-release/lastSuccessfulBuild/artifact/socorro.tar.gz

This will install the very latest development release of Socorro, if you wish
to install a particular release you can select one from the build history
on https://ci.mozilla.org/job/socorro-release/

For example, the Socorro 87 release is
https://ci.mozilla.org/job/socorro-release/1068/

Info for Socorro releases to Mozilla's crash-stats server are available at
https://github.com/mozilla/socorro/releases and the latest git SHA actually
installed on production is available at https://crash-stats.mozilla.com/status/

You can find the git SHAs that went into each build at
https://ci.mozilla.org/job/socorro-release/changes

Note that merge commits do not show up in the Jenkins changelog, so you'll
need to look at the "parent commits" in github to match them up.

You can skip the rest of these instructions, and go to :ref:`systemtest-chapter`
