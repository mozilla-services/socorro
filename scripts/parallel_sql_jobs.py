#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import sys
import datetime
import threading
import Queue
from optparse import OptionParser, OptionGroup

import psycopg2

usage = "usage: %prog [options] file..."
parser = OptionParser(usage=usage)

parser.add_option('-j', '--jobs', action='store', type='int', dest='jobs', help='Number of parallel jobs (default 6)', default=6)
parser.add_option('', '--stop', action='store_true', dest='stop_on_error', help='Stop on error (default is to continue)', default=False)

conn_opts = OptionGroup(parser, "Database Connection Options")

conn_opts.add_option('', '--host', action='store', type='string', dest='host', help='Database host (default connect via socket)', default='')
conn_opts.add_option('', '--port', action='store', type='int', dest='port', help='Database port (default 5432 for TCP/IP)', default=None)
conn_opts.add_option('', '--username', action='store', type='string', dest='user', help='Database username (default "postgres")', default='postgres')
conn_opts.add_option('', '--dbname', action='store', type='string', dest='dbname', help='Database (default "postgres")', default='postgres')

parser.add_option_group(conn_opts)

(options, args) = parser.parse_args()

terminating = threading.Event()
error_occurred = threading.Event()

stderr_lock = threading.Lock()

def log(message, ordinal=0):
    stderr_lock.acquire()
    sys.stderr.write(str(datetime.datetime.now()) + ' ' + str(ordinal)+ ': ' + message)
    sys.stderr.write('\n')
    stderr_lock.release()

q = Queue.Queue()

class Worker(threading.Thread):

    def __init__(self, ordinal):
        threading.Thread.__init__(self)
        
        self.daemon = True
        self._ordinal = ordinal
        
    def run(self):
        self._connection = None
        
        try:
            connection_string = """
                user=%(user)s
                dbname=%(dbname)s""" %  { 'user': options.user,
                                          'dbname': options.dbname }
            
            if options.host != '':
                connection_string += " host=%(host)s" % { 'host': options.host }
                
            if options.port is not None:
                connection_string += " port=%(port)s" % { 'port': options.port }
                
            self._connection = psycopg2.connect(connection_string)
            
            # We want to run each statement in its own transaction, so there's no reason to pay the
            # overhead of BEGIN/COMMITs.
            
            self._connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            
        except Exception as e:
            log('Exception: ' + str(e), self._ordinal)
            error_occurred.set()
                # If we get a connection error, bail out.
            
        while(not terminating.is_set()):
            work_item = q.get()
            
            # We use the empty string as a flag value to wake up the thread.  If
            # an error has occurred, we flush the queue before terminating so that
            # the q.join() in the main thread will return.
            
            if (work_item == '') or (error_occurred.is_set()):
                q.task_done()
                continue
            
            log('Starting: ' + work_item, self._ordinal)
            try:
                cursor = self._connection.cursor()
                cursor.execute(work_item)
                cursor.close()
                
            except Exception as e:
                log('Exception: ' + str(e), self._ordinal)
                
                if options.stop_on_error:
                    error_occurred.set()
            
            log('Done: ' + work_item, self._ordinal)
            q.task_done()
        
        if self._connection is not None:
            self._connection.close()

log("Started")

workers = [ ]

for worker_number in range(options.jobs):
    th = Worker(worker_number + 1)
    th.start()
    workers.append(th)

if (not args) or (args[0].strip()) == '-':
    for line in sys.stdin.readlines():
        q.put(line.strip())
else:
    for filename in args:
        try:
            with open(filename, 'r') as file:
                log('File: ' + filename, 0)
                for line in file.readlines():
                    q.put(line.strip())
        except Exception as e:
            log('Exception: ' + str(e), 0)
            if options.stop_on_error:
                error_occurred.set()
                break

q.join()
    # Wait until the queue drains before continuing.

terminating.set()

for worker in workers:
    q.put('')
        # Wakes up each worker.  Since each worker will terminate when it comes alive,
        # we know that each worker will get woken up. 

for worker in workers:
    worker.join(0.1)
        # Waits for each worker task to terminate before continuing.  If it doesn't
        # terminate in a 1/10th of a second, we just move on to the next one; they'll
        # all be killed when the program terminates, anyway.
        
log("Finished")

if error_occurred.is_set():
    sys.exit(1)