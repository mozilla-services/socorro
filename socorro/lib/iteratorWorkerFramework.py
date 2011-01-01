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
ok = 1
failure = 0

#-------------------------------------------------------------------------------
def defaultTaskFunc(jobTuple):
  pass

#-------------------------------------------------------------------------------
def defaultIterator():
  for x in range(10):
    yield x
  while True:
    yield None

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
    # setup the task manager to a queue size twice the size of the number
    # of threads in use.  Because some mechanisms that feed the queue are
    # are destructive (JsonDumpStorage.destructiveDateWalk), we want to limit
    # the damage in case of error or quit.
    self.workerPool = thr.TaskManager(self.config.numberOfThreads,
                                      self.config.numberOfThreads * 2)
    #self.workerPool = thr.TaskManager(self.config.numberOfThreads,
                                      #10)
    self.quit = False
    self.logger.debug('finished init')

  #-----------------------------------------------------------------------------
  def quitCheck(self):
    if self.quit:
      raise KeyboardInterrupt

  #-----------------------------------------------------------------------------
  def responsiveSleep (self, seconds, waitLogInterval=0, waitReason=''):
    for x in xrange(int(seconds)):
      self.quitCheck()
      if waitLogInterval and not x % waitLogInterval:
        self.logger.info('%s: %dsec of %dsec',
                         waitReason,
                         x,
                         seconds)
      time.sleep(1.0)

  #-----------------------------------------------------------------------------
  def responsiveJoin(self, thread, waitingFunc=None):
    while True:
      try:
        thread.join(1.0)
        if not thread.isAlive():
          #self.logger.debug('%s is dead', str(thread))
          break
        if waitingFunc:
          waitingFunc()
      except KeyboardInterrupt:
        self.logger.debug ('quit detected by responsiveJoin')
        self.quit = True

  #-----------------------------------------------------------------------------
  @staticmethod
  def backoffSecondsGenerator():
    seconds = [10, 30, 60, 120, 300]
    for x in seconds:
      yield x
    while True:
      yield seconds[-1]

  #-----------------------------------------------------------------------------
  def retryTaskFuncWrapper(self, *args):
    backoffGenerator = self.backoffSecondsGenerator()
    try:
      while True:
        result = self.taskFunc(*args)
        if self.quit:
          break
        if result == ok:
          return
        waitInSeconds = backoffGenerator.next()
        self.logger.critical('major failure in crash storage - retry in %s seconds',
                        waitInSeconds)
        self.responsiveSleep(waitInSeconds,
                             10,
                             "waiting for retry after failure in crash storage")
    except KeyboardInterrupt:
      return

  #-----------------------------------------------------------------------------
  def start (self):
    self.logger.debug('start')
    self.queuingThread = threading.Thread(name="%sQueuingThread" % self.name,
                                          target=self.queuingThreadFunc)
    self.queuingThread.start()

  #-----------------------------------------------------------------------------
  def waitForCompletion (self, waitingFunc=None):
    self.logger.debug("waiting to join queuingThread")
    self.responsiveJoin(self.queuingThread, waitingFunc)

  #-----------------------------------------------------------------------------
  def stop (self):
    self.quit = True
    self.waitForCompletion()

  #-----------------------------------------------------------------------------
  def queuingThreadFunc (self):
    self.logger.debug('queuingThreadFunc start')
    try:
      try:
        for aJob in self.jobSourceIterator(): # may never raise StopIteration
          if aJob is None:
            self.logger.info("there is nothing to do.  Sleeping for 7 seconds")
            self.responsiveSleep(7)
            continue
          self.quitCheck()
          try:
            self.logger.debug("queuing standard job %s", aJob)
            self.workerPool.newTask(self.retryTaskFuncWrapper, (aJob,))
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




