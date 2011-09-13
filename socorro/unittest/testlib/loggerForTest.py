import logging

class TestingLogger:
  """
  Maintains an in-memory buffer of logging levels and log messages.
  Accepts the various methods that send message to logger (log, debug, info, etc)
  If constructed with an external logger, also sends messages to that logger
  As an aid to testing, provides the clear() method
  As an aid to debugging, provides __str__ that puts seperates each message by a newline
  ** BEWARE ** that since this is in-memory, it does not work between threads or processes.
  """
  def __init__(self, logger=None):
    self.levels = []
    self.buffer = []
    self.logger = logger
    self.levelcode =  dict( ((getattr(logging,x),x,) for x in dir(logging) if x == x.upper() and type(0) == type(getattr(logging,x)) ) )

  def log(self, loggingLevel, message, *args):
   self.levels.append(loggingLevel)
   if not message: message = ''
   if args:
     self.buffer.append(message % args)
   else:
     self.buffer.append(str(message))
   if self.logger:
     self.logger.log(loggingLevel, str(message), *args)

  def debug(self, message, *args):
    self.log(logging.DEBUG,message, *args)
  def info(self, message, *args):
    self.log(logging.INFO,message, *args)
  def warning(self, message, *args):
    self.log(logging.WARNING,message, *args)
  def warn(self, message, *args):
    self.log(logging.WARN,message, *args)
  def error(self, message, *args):
    self.log(logging.ERROR,message, *args)
  def critical(self, message, *args):
    self.log(logging.CRITICAL,message, *args)
  def fatal(self, message, *args):
    self.log(logging.FATAL,message, *args)

  def __str__(self):
    return "\n".join( (self.formatOne(i) for i in range(len(self)))  )

  def __len__(self):
    return self.buffer.__len__()

  def clear(self):
    """Remove data from the two in-memory buffers"""
    self.levels = []
    self.buffer = []

  def formatOne(self,index):
    return "%-8s(%2d): %s"%(self.levelcode[self.levels[index]],self.levels[index],self.buffer[index])
