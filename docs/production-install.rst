.. index:: production-install

.. _production_install-chapter:

Production Install
==================

Currently Socorro is supported on CentOS 7

For any other platform, you must build from source. See
:ref:`development-chapter` for more information.

.. WARNING::

   October 7th, 2016: The RPM contains a ``socorro-virtualenv/`` that's built
   using a local install of Python 2.7.11, so it doesn't work on a standard
   CentOS install.

   This is covered in `bug 1308469
   <https://bugzilla.mozilla.org/show_bug.cgi?id=1308469>`_.


Installing services
-------------------

Install the EPEL repository.
::
  sudo yum install epel-release

Install Elasticsearch 1.4:
http://www.elastic.co/guide/en/elasticsearch/reference/1.4/setup-repositories.html#_yum

Install the Socorro repository.
::
  sudo rpm -ivh https://s3-us-west-2.amazonaws.com/org.mozilla.crash-stats.packages-public/el/7/noarch/socorro-public-repo-1-1.el7.centos.noarch.rpm

Now you can actually install the packages:
::
  sudo yum install java-1.7.0-openjdk python-virtualenv \
    elasticsearch nginx envconsul consul socorro

Enable Nginx and Elasticsearch on startup, and start them now:
::
  sudo systemctl enable nginx elasticsearch
  sudo systemctl start nginx elasticsearch

Disable SELinux
---------------

Socorro currently requires that SELinux is disabled:
::
  sudo vi /etc/sysconfig/selinux

Ensure that SELINUX is set to permissive:
::
  SELINUX=permissive

Reboot the system if the above was changed:
::
  sudo shutdown -r now
