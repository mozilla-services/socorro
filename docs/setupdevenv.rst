.. index:: setupdevenv

.. _setupdevenv-chapter:

Setup a development environment
===============================

The best and easiest way to get started with a complete dev environment is to
use Vagrant and our installation script. You can find all the instructions
here: https://github.com/rhelmer/socorro-vagrant

If you don't want to use a virtual machine, you can install everything in your
own development environment. All steps are described in
:ref:`standalone-chapter`.

Use your own git repo
---------------------

If you forked our mozilla/socorro repository, you will want to make your repo
the origin of the repository inside your VM. Once connected through SSH into
the VM, execute the following commands::

    sudo su - socorro
    cd /home/socorro/dev/socorro
    edit .git/config # change `url = git@github.com:mozilla/socorro.git` with your repo's URL
    git fetch origin

Apply your changes
------------------

After that, whenever you want to see changes you made in one of your branches,
do the following::

    cd /home/socorro/dev/socorro
    git checkout my-dev-branch
    make install
    sudo /etc/init.d/apache restart
    sudo /etc/init.d/supervisor force-stop && sudo /etc/init.d/supervisor start

And then from your browser access http://crash-stats/ for the UI, or
http://socorro-api/bpapi/ for the middleware API directly.

Use a shared folder
-------------------

If you don't like vim or you want to use your favorite IDE, you can easily
create a shared folder between your OS and your VM. You can then work in your
OS and have all your changes automatically passed to the VM.

The best solution is to use NFS. There is a good documentation on Vagrant's
website that explain it all: http://vagrantup.com/docs/nfs.html
