.. index:: troubleshoot

Troubleshooting
---------------

Socorro Troubleshooting
=======================

journalctl is a good place to look for Socorro logs, especially if services
are not starting up or are crashing.

Socorro supports syslog and raven for application-level logging of all
services (including web services).

Crash-Stats Troubleshooting
===========================

If web services are not starting up, /var/log/nginx/ is a good place to look.

Crash-Stats
===========

If you are not able to log in to the crash-stats UI, try hitting
http://crash-stats/_debug_login

If you are having problems with crontabber jobs, this page shows you the
state of the dependencies: http://crash-stats/crontabber-state/

If you're seeing "Internal Server Error", you can get Django to send you
email with stack traces by adding this to
/data/socorro/webapp-django/crashstats/settings/base.py::

  # Recipients of traceback emails and other notifications.
  ADMINS = ( 
      ('Your Name', 'your_email@domain.com'),
  )
  MANAGERS = ADMINS
