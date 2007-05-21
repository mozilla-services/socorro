
The Standalone Breakpad Dump Processor
--------------------------------------

Before starting the processor, you MUST set the storageRoot variable:

 - socorro/lib/config.py
   ----------------------- 
   This file contains a number of string constants used by the
   processor script. They are each documented in the file, but the most
   important string is 'storageRoot'. This is the path to the top level
   directory of the storage area.

The processor will run continuously, and can be shut down cleanly with
an interupt. By default, it will DELETE dump files after successfully
processing them.


