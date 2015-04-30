.. index:: production-install

.. _production_install-chapter:

Production Install
==================

Currently Socorro is supported on CentOS 7

For any other platform, you must build from source. See
:ref:`development-chapter` for more information.


.. sidebar:: Breakpad client and symbols

   Socorro aggregates and reports on Breakpad crashes.
   Read more about `getting started with Breakpad <http://code.google.com/p/google-breakpad/wiki/GettingStartedWithBreakpad>`_.

   You will need to `produce symbols for your application <http://code.google.com/p/google-breakpad/wiki/LinuxStarterGuide#Producing_symbols_for_your_application>`_ and make these files available to Socorro.

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
    elasticsearch nginx envconsul consul memcached socorro

Enable Nginx on startup:
::
  sudo systemctl enable nginx memcached elasticsearch

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
