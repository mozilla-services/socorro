import subprocess as sp
import re
import threading
import logging
import struct

import socorro.lib.util as sutil


#=================================================================================================================
class StackWalker(object):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, config):
    """create a stackwalker"""
    self.config = config
    self.server = 'localhost'
    self.logger = config.logger
    self.logger.debug('stackwalker command line: %s', config.commandLine)
    self.fdevnull = open('/dev/null', 'w')
    try:
      self.subprocessHandle = sp.Popen(config.commandLine,
                                       shell=False,
                                       stdout=sp.PIPE,
                                       stderr=self.fdevnull,
                                       stdin=sp.PIPE)
      self.logger.debug('stackwalker started with PID:%d',
                        self.subprocessHandle.pid)
    except Exception, x:
      sutil.reportExceptionAndContinue(self.config.logger,
                                       loggingLevel=logging.CRITICAL)
      raise

  #-----------------------------------------------------------------------------------------------------------------
  def close(self):
    self.fdevnull.close()
    self.subprocessHandle.terminate()

  #-----------------------------------------------------------------------------------------------------------------
  def stackWalk(self, binaryDump):
    header = struct.pack("I", len(binaryDump))
    self.subprocessHandle.stdin.write(header)
    self.subprocessHandle.stdin.write(binaryDump)
    self.subprocessHandle.stdin.flush()
    while True:
      aLine = self.subprocessHandle.stdout.readline().strip()
      if aLine == 'END': break
      if aLine:  #don't serve blank lines
        #self.logger.debug('yielding: %s', aLine)
        yield aLine
    #self.logger.debug('end of stackWalk');

#=================================================================================================================
class StackWalkerPool(dict):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, config):
    super(StackWalkerPool, self).__init__()
    self.config = config
    self.logger = config.logger
    self.logger.debug("creating stackWalkerPool")
    self.config.commandLine = [x for x in self.config.stackwalkCommandLine.split()]

  #-----------------------------------------------------------------------------------------------------------------
  def stackWalker(self, name=None):
    if name is None:
      name = threading.currentThread().getName()
    if name not in self:
      self.logger.debug("creating stackWalker for %s", name)
      self[name] = c = StackWalker(self.config)
      return c
    return self[name]

  #-----------------------------------------------------------------------------------------------------------------
  def removeStackWalker (self, name=None):
    """to be done if a stackwalker misbehaves"""
    if name is None:
      name = threading.currentThread().getName()
    if name in self:
      self[name].close()
      del self[name]

  #-----------------------------------------------------------------------------------------------------------------
  def cleanup (self):
    for name, stackwalker in self.iteritems():
      try:
        stackwalker.close()
        self.logger.debug("stackwalker %s is closed", name)
      except:
        sutil.reportExceptionAndContinue(self.logger)