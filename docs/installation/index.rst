.. index:: installation

Intro
-----

Socorro is a set of components for collecting, processing and reporting on crashes. It is used by Mozilla for tracking crashes of Firefox, B2G, Thunderbird and other projects. The production Mozilla install is public and hosted at https://crash-stats.mozilla.com/

The components which make up Socorro are:

* Collector - collects breakpad minidump crashes which come in over HTTP POST
* Processor - turn breakpad minidump crashes into stack traces and other info
* Middleware - provide HTTP REST interface for JSON reports and real-time data
* Web UI aka crash-stats - django-based web app for visualizing crash data
