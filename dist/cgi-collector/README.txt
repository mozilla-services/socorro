
The Standalone Breakpad Dump Collector
--------------------------------------

This version of the collector depends only on Python CGI facilities,
and includes all of its dependencies in neighboring files and directories.

 - collector.py 
   -----------------------
   The collector script. This script is completely stateless, requires
   no database connections, and can write to a root storage folder
   concurrently with other instances of the same script. Depending on your
   configuration, this could be a mod_python handler or a CGI script.

 - standalone_collector.py
   Common collector module.

 - config.py
   ----------------------- 
   This file contains a number of string constants used by the
   collector script. They are each documented in the file, but the most
   important string is 'storageRoot'. This is the path to the top level
   directory of the storage area. The collector script will create child
   directories using dates and non-colliding names to partition
   dumpfiles and prevent collisions.

 - simplejson/
   -----------------------
   Well-tested python module we use to store metadata alongside dump files.

 - uuid.py
   -----------------------
   Ensure non-colliding dump file basenames. Also returned to the
   client as the crash id.
