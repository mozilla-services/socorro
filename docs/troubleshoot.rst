.. index:: troubleshoot

Troubleshooting
---------------

journalctl is a good place to look for Socorro logs.

Socorro supports syslog and raven for application-level logging of all
services (including web services).

If web services are not starting up, /var/log/httpd is a good place to look.

If you are not able to log in to the crash-stats UI, try hitting
http://crash-stats/_debug_login

If you are having problems with crontabber, this page shows some info about
it: http://crash-stats/crontabber-state/
