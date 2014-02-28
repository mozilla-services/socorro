Set up a services VM with Vagrant
=================================

Vagrant can be used to build a VM that supplies the basic services stack
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

2. Provision the VM:
::
 vagrant up

This step will:

* Download the base image if it isn't already present.
* Boot the VM.
* Using Puppet, install and initialise the basic services that Socorro
  needs.

3. Add entries to ``/etc/hosts`` on the **HOST** machine:
::
  10.11.12.13 crash-stats crash-reports socorro-api

That's it!
----------

If everything works, you'll now have a VM running with all of Socorro's
service dependencies installed and ready to go!

Your git checkout will automatically be shared with the VM in
``/home/vagrant/src/socorro`` .
  
You can either hack on the code from within the VM or on the host machine
as normal. Note that, by default, none of the services are available outside
of the VM; see the Vagrant_ documentation for more details on how to modify
this behaviour.

Now continue in the install docs, starting from: :ref:`settingupenv-chapter`

.. _Vagrant: https://docs.vagrantup.com/v2/networking/forwarded_ports.html
