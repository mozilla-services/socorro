#!/usr/bin/python

import sys
import datetime
import threading
import Queue
from optparse import OptionParser

import psycopg2

parser = OptionParser()

parser.add_option('-j', '--jobs', action='store', type='int', dest='jobs', help='Number of parallel jobs (default 6)', default=6)
parser.add_option('', '--host', action='store', type='string', dest='host', help='Database host (default localhost)', default='localhost')
parser.add_option('', '--port', action='store', type='int', dest='port', help='Database port (default 5432)', default=5432)
parser.add_option('', '--username', action='store', type='string', dest='user', help='Database username (default "postgres")', default='postgres')
parser.add_option('', '--dbname', action='store', type='string', dest='dbname', help='Database (default "postgres")', default='postgres')
parser.add_option('', '--stop', action='store_true', dest='stop_on_error', help='Stop on error (default is to continue)', default=False)

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
        try:
            self._connection = psycopg2.connect(
                """host=%(host)s
                   port=%(port)s
                   user=%(user)s
                   dbname=%(dbname)s""" % { 'host': options.host,
                                            'port': options.port,
                                            'user': options.user,
                                            'dbname': options.dbname } )
            
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


log("Started")

workers = [ ]

for worker_number in range(options.jobs):
    th = Worker(worker_number + 1)
    th.start()
    workers.append(th)
    
for line in sys.stdin.readlines():
    q.put(line.strip())

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
