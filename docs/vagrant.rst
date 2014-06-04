.. index:: vagrant

.. _vagrant-chapter:

Set up a VM with Vagrant
=================================

Vagrant can be used to build a VM that supplies the basic dependency stack
required by Socorro. This is an alternative to setting up these services
manually in your local environment.

Requirements
------------

You'll need both VirtualBox (http://www.virtualbox.org/) and
Vagrant (http://vagrantup.com/) set up and ready to go.

Virtualenv warning
------------------

Make sure that you don't already have a ``./socorro-virtualenv`` directory
created with a different architecture, otherwise you'll get odd errors
about pip not existing, binaries being the wrong architecture, and so on.

Instructions
------------

1. Clone the Socorro repository:
::
  git clone git://github.com/mozilla/socorro.git
  cd socorro

2. Provision the VM:
::
 vagrant up

This step will:

* Download the base image if it isn't already present.
* Boot the VM.
* Using Puppet, install and initialise the basic dependencies that Socorro
  needs.

3. Add entries to ``/etc/hosts`` on the **HOST** machine:
::
  10.11.12.13 crash-stats crash-reports socorro-api

That's it!
----------

You can get a shell in the VM as the user "vagrant" by running this
in your Socorro source checkout:
::
  vagrant ssh

Your git checkout on the host will automatically be shared with the VM in
``/home/vagrant/src/socorro`` .

Next you need to install Socorro itself: :ref:`settingupenv-chapter`

.. _Vagrant: https://docs.vagrantup.com/v2/networking/forwarded_ports.html
