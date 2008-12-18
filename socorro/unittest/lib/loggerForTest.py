import logging

class TestingLogger:
  def __init__(self):
    self.levels = []
    self.buffer = []

  def log(self, loggingLevel, message, *args):
    self.levels.append(loggingLevel)
    if not message: message = ''
    if args:
      self.buffer.append(message % args)
    else:
      self.buffer.append(message)
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
    return 'levels: %s\nbuffer: %s'%(self.levels,self.buffer)

  def clear(self):
    self.levels = []
    self.buffer = []
