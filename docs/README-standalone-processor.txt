
The Standalone Breakpad Dump Processor
--------------------------------------

1.) Before starting the processor, you MUST set the storageRoot variable:

 - socorro/lib/config.py
   -----------------------
   This file contains a number of string constants used by the
   processor script. They are each documented in the file, but the most
   important string is 'storageRoot'. This is the path to the top level
   directory of the storage area.

The processor will run continuously, and can be shut down cleanly with
an interupt. By default, it will DELETE dump files after successfully
processing them.

The processor will print to stdout and stderr, so you may want to
redirect its output to a file.

Dependencies
------------

   SQLAlchemy>=0.3.5
   Psycopg2

   and the big one...

   Gamin
   <http://www.gnome.org/~veillard/gamin/>

   This is Linux-only, and is used to monitor the filesystem for
   changes. Your linux package manager probably has it.

Sample Usage
------------

First, see step 1.

   %prompt> python start-processor.py
   starting Socorro dump file monitor

   ...

   [ctrl-C]

   stopping Socorro dump file monitor
   %prompt>
