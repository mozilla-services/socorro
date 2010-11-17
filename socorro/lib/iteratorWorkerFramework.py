import datetime
import logging
import signal
import time
import threading
import Queue as queue

import web

#logger = logging.getLogger("base")

import socorro.lib.util as sutil
import socorro.lib.threadlib as thr

#-------------------------------------------------------------------------------
def defaultTaskFunc(jobTuple):
  pass

#-------------------------------------------------------------------------------
def defaultIterator():
  for x in range(10):
    yield x

#-------------------------------------------------------------------------------
def respondToSIGTERM(signalNumber, frame):
  """ these classes are instrumented to respond to a KeyboardInterrupt by
      cleanly shutting down.  This function, when given as a handler to for
      a SIGTERM event, will make the program respond to a SIGTERM as neatly
      as it responds to ^C.
  """
  signame = 'SIGTERM'
  if signalNumber != signal.SIGTERM:
    signame = 'SIGHUP'
  self.logger.info("%s detected", signame)
  raise KeyboardInterrupt

#===============================================================================
class IteratorWorkerFramework(object):
  """ """

  #-----------------------------------------------------------------------------
  def __init__ (self, config, name='mill', jobSourceIterator=defaultIterator,
                taskFunc=defaultTaskFunc):
    """
    """
    super(IteratorWorkerFramework, self).__init__()
    self.config = config
    self.logger = config.logger
    self.name = name
    self.jobSourceIterator = jobSourceIterator
    self.taskFunc = taskFunc
    self.workerPool = thr.TaskManager(self.config.numberOfThreads)
    self.quit = False
    self.logger.debug('finished init')

  #-----------------------------------------------------------------------------
  def quitCheck(self):
    if self.quit:
      raise KeyboardInterrupt

  #-----------------------------------------------------------------------------
  def responsiveSleep (self, seconds):
    for x in xrange(int(seconds)):
      self.quitCheck()
      time.sleep(1.0)

  #-----------------------------------------------------------------------------
  def responsiveJoin(self, thread):
    while True:
      try:
        thread.join(1.0)
        if not thread.isAlive():
          #self.logger.debug('%s is dead', str(thread))
          break
      except KeyboardInterrupt:
        self.logger.debug ('quit detected by responsiveJoin')
        self.quit = True

  #-----------------------------------------------------------------------------
  def start (self):
    self.logger.debug('start')
    self.queuingThread = threading.Thread(name="%sQueuingThread" % self.name,
                                          target=self.queuingThreadFunc)
    self.queuingThread.start()

  #-----------------------------------------------------------------------------
  def waitForCompletion (self):
    self.logger.debug("waiting to join queuingThread")
    self.responsiveJoin(self.queuingThread)

  #-----------------------------------------------------------------------------
  def stop (self):
    self.quit = True
    self.waitForCompletion()

  #-----------------------------------------------------------------------------
  def queuingThreadFunc (self):
    self.logger.debug('queuingThreadFunc start')
    try:
      try:
        for aJob in self.jobSourceIterator(): # never returns StopIteration
          if aJob is None:
            self.logger.info("there is nothing to do.  Sleeping for 7 seconds")
            self.responsiveSleep(7)
            continue
          self.quitCheck()
          try:
            self.logger.debug("queuing standard job %s", aJob)
            self.workerPool.newTask(self.taskFunc, (aJob,))
          except Exception:
            self.logger.warning('%s has failed', aJob)
            sutil.reportExceptionAndContinue(self.logger)
      except Exception:
        self.logger.warning('The jobSourceIterator has failed')
        sutil.reportExceptionAndContinue(self.logger)
      except KeyboardInterrupt:
        self.logger.debug('queuingThread gets quit request')
    finally:
      self.quit = True
      self.logger.debug("we're quitting queuingThread")
      self.logger.debug("waiting for standard worker threads to stop")
      self.workerPool.waitForCompletion()
      self.logger.debug("all worker threads stopped")




