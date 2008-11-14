Socorro Integration tests

= Requierments =
httplib2-0.4.0 - http://code.google.com/p/httplib2/downloads/list

= Notes =
I ran into permissions erros with using 
Postgres COPY FROM '/file'
so switched to STDIN format

= Data =
There is a data set for use with integration tests.

== Use Cases ==
=== Top Crashers ===
Production build - Firefox, 3.0.3
==== JS_RestoreFrameChain ====
2 weeks of JS_RestoreFrameChain for Firefox, 3.0.3, build = 2008092417 ( 1967 records )

Note: Windows crashes only
==== @0x0 ====
2 weeks of @0x0 for Firefox, 3.0.3 ( 2857 records )
cross platform crashes
multiple builds (mac = 2008092414, linux = 2008092416, win = 2008092417)

==== Flash Player@0x49a6be ====
4 'Flash Player@0x49a6be' - data consistent with report table
(report 12 - khan, 840826, 450317, 634030 from load)

Development build - Firefox 3.0.3pre
==== @0x0 ====
4 entries @0x0 for Firefox, 3.0.3pre describing 4 crashes
builds (20081025013618, 20081024020254, 20081023034205, 2008102306)
data consistent with report table ( 13 - 16 )
cross platform crashes

Build values can vary across os...



extensions - empty
modules - only has report_id 12, was empty on stage db

server_status - two hours of data
cron had a hickup between 
id 17 and 18 missing 1 datapoint and time starts on different interval
