.. index:: vagrant

.. _vagrant-chapter:

Setup a development VM with Vagrant
===============================

Vagrant can be used to build a full Socorro VM.

1. Clone Socorro repository
::
  git clone git://github.com/mozilla/socorro.git
  cd socorro/

2. Install VirtualBox from:
http://www.virtualbox.org/

3. Install Vagrant from:
http://vagrantup.com/

4. Download and copy base box, boot VM and provision it with puppet:
::
 vagrant up

5. Add to /etc/hosts (on the HOST machine!):
::
  10.11.12.13 crash-stats crash-reports socorro-api

If everything works, you'll now have a VM running with all of Socorro's
dependencies installed and ready for you!

Your git checkout will automatically be shared with the VM in
/home/vagrant/src/socorro, you can access it like so:
::
 vagrant ssh
 cd src/socorro

Make sure that you don't already have a ./socorro-virtualenv directory
created with a different architecture! Otherwise you'll get odd errors
about pip not existing, binaries being the wrong architecture and so on.

Now continue in the install docs, starting from: :ref:`settingupenv-chapter`
