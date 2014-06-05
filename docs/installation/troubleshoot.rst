.. index:: troubleshoot

Troubleshooting
---------------

Socorro leaves logs in /var/log/socorro which is a good place to check
for crontabber and backend services like processor.

Socorro supports syslog and raven for application-level logging of all
services (including web services).

If web services are not starting up, /var/log/httpd is a good place to look.
