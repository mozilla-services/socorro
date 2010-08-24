#! /usr/bin/env python

import subprocess
import os.path
import threading
import time
import re
import collections
import itertools

import logging

logger = logging.getLogger("processor")

import socorro.lib.util as sutil
import socorro.processor.stackwalker as stwk
import socorro.processor.signatureUtilities as sig

import daemon_proc

#-----------------------------------------------------------------------------------------------------------------
def getPart(collection, index, fromStrConversion=str, default=None):
  try:
    return fromStrConversion(collection[index])
  except (IndexError, KeyError, TypeError, ValueError):
    return default

#=================================================================================================================
class ThresholdContainer(collections.Sequence):
  """This container consists of two parts: a list section of with a fixed
  length of 'staticMaxLength' and a deque with a maximum length of 'tailLength'.
  When items are appended to this collection, they first fill the fixed length
  list.  Then items rollover into the deque.  The effect is a list containing
  only the first 'staticMaxLength' items and the last 'tailLength' items.  This
  is used to hold the list of frames in from a thread stack trace.  If the list
  is too long, the editing omission comes from the less interesting middle
  rather than the more significant ends.
  """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, indexableCollection=[], staticMaxLength=100, tailLength=10):
    self.staticMaxLength = staticMaxLength
    self.tailLength = tailLength
    self.parts = (collections.deque(indexableCollection[staticMaxLength:], tailLength),
                  indexableCollection[:staticMaxLength])
    self.numberOfInserts = len(indexableCollection)
  #-----------------------------------------------------------------------------------------------------------------
  def __getitem__(self, index):
    if index < self.staticMaxLength:
      return self.parts[1][index]
    else:
      return self.parts[0][index - self.staticMaxLength]
  #-----------------------------------------------------------------------------------------------------------------
  def __len__(self):
    return len(self.parts[1]) + len(self.parts[0])
    #-----------------------------------------------------------------------------------------------------------------
  def __iter__(self):
    return itertools.chain(iter(self.parts[1]), iter(self.parts[0]))
  #-----------------------------------------------------------------------------------------------------------------
  def __contains__(self, item):
    return item in self.parts[1] or item in self.parts[0]
  #-----------------------------------------------------------------------------------------------------------------
  def append(self, item):
    self.numberOfInserts += 1
    self.parts[len(self.parts[1]) < self.staticMaxLength].append(item)
  #-----------------------------------------------------------------------------------------------------------------
  def isTruncated(self):
    return self.numberOfInserts > self.staticMaxLength + self.tailLength

#=================================================================================================================
class BadBreakpadAnalysisLineException(Exception):
  def __init__(self, reason):
    super(BadBreakpadAnalysisLineException, self).__init__(reason)

#=================================================================================================================
class StreamBreakpadProcessor (daemon_proc.Processor):
  """
  """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, config):
    super(StreamBreakpadProcessor, self).__init__(config)

    #self.logger = config.logger # already done by base class

    assert "generatePipeDump" in config, "generatePipeDump is missing from the configuration"
    assert "generateJDump" in config, "generateJDump is missing from the configuration"
    assert "maximumStackwalkerUses" in config, "maximumStackwalkerUses is missing from the configuration"

    self.logger.debug('Instantiating StreamBreakpadProcessor')

    self.stackWalkerPool = stwk.StackWalkerPool(config)

    self.signatureTool = sig.SignatureUtilities(config)

    # create a dict to dispatch calls to functions that can handle the lines
    # that minidump stactwalk will produce.  The first value on each line will
    # be the key to which handler function to call.  Each line of the frame
    # data starts with an integer.  Since we don't know how many unique ints
    # there will be, we set the default value of the dispatcher dict to the
    # function that handles frame lines.  The default value of a defaultdict
    # must be a callable.  If we were to specify the frame handler function
    # directly as the default, it would get called prematurely without the
    # parameters that we want to pass to it.  Wrapping the bound function with
    # a lambda function solves this problem.  The lambda gets called and returns
    # the bound function that we then call with the contents of the frame line.
    self.analysisDispatcher = collections.defaultdict(lambda : self.lineAnalyzerForStackFrames)
    self.analysisDispatcher.update( { 'OS': self.lineAnalyzerForOS,
                                      'CPU': self.lineAnalyzerForCPU,
                                      'Crash': self.lineAnalyzerForCrash,
                                      'Module': self.lineAnalyzerForModule,
                                    } )
    class ThreadFramesContainer(ThresholdContainer):
      def __init__(self):
        super(ThreadFramesContainer,self).__init__(staticMaxLength=config.threadFrameThreshold,
                                                   tailLength=config.threadTailFrameThreshold)
    self.ThreadFramesContainerClass = ThreadFramesContainer

  #-----------------------------------------------------------------------------------------------------------------
  def orderlyShutdown(self):
    """this must be a cooperative function with all derived classes."""
    super(StreamBreakpadProcessor, self).orderlyShutdown()
    self.stackWalkerPool.cleanup()

  #-----------------------------------------------------------------------------------------------------------------
  def doBreakpadStackDumpAnalysis (self, j_doc, new_jdoc, threadLocalCrashStorage):
    """ This function overrides the base class version of this function.  This function coordinates the six
          steps of running the breakpad_stackdump process and analyzing the textual output for insertion
          into the database.

          returns:
            truncated - boolean: True - due to excessive length the frames of the crashing thread may have been truncated.

          input parameters:
            ooid - the unique string identifier for the crash report
            j_doc - original metadata
            new_jdoc - the dict that will become the processed json, at this
                point, it already has many fields filled out.
            threadLocalCrashStorage -
            err_list -
    """
    #logger.debug('StreamBreakpadProcessor.doBreakpadStackDumpAnalysis')
    localStackWalker = self.stackWalkerPool.stackWalker()
    ooid = new_jdoc.uuid
    crashStorage = self.crashStorePool.crashStorage()
    binaryDump = crashStorage.get_raw_dump(ooid)
    #logger.debug('submitting %s to breakpad_stackwalk', ooid)
    stackIterator = localStackWalker.stackWalk(binaryDump)
    try:
      self.breakpadAnalyzer(stackIterator, j_doc, new_jdoc)
      new_jdoc.success = True
    except IOError, x:
      self.logger.warning('the stackwalk_server is misbehaving - killing and restarting it')
      self.stackWalkerPool.removeStackWalker()
      localStackWalker = self.stackWalkerPool.stackWalker()
      stackIterator = localStackWalker.stackWalk(binaryDump)
      try:
        self.breakpadAnalyzer(stackIterator, j_doc, new_jdoc)
        new_jdoc.success = True
      except Exception:
        sutil.reportExceptionAndContinue(self.logger)
        new_jdoc.success = False
    except Exception, x:
      sutil.reportExceptionAndContinue(self.logger)
      new_jdoc.success = False
    #self.logger.debug('done with %s', new_jdoc.uuid)

  #-----------------------------------------------------------------------------------------------------------------
  def lineAnalyzerForOS (self, line, lineparts, j_dump, new_jdoc):
    j_dump.os_info.os_name = getPart(lineparts, 1)
    new_jdoc.os_name = j_dump.os_info.os_name
    j_dump.os_info.os_version = getPart(lineparts, 2)
    new_jdoc.os_version = j_dump.os_info.os_version
    j_dump.os_info.original_line = line

  #-----------------------------------------------------------------------------------------------------------------
  def lineAnalyzerForCPU (self, line, lineparts, j_dump, new_jdoc):
    j_dump.cpu_info.cpu_name = getPart(lineparts, 1)
    new_jdoc.cpu_name = j_dump.cpu_info.cpu_name
    j_dump.cpu_info.cpu_info = getPart(lineparts, 2)
    new_jdoc.cpu_info = j_dump.cpu_info.cpu_info
    j_dump.cpu_info.cpu_count = getPart(lineparts, 3, int)
    j_dump.cpu_info.original_line = line

  #-----------------------------------------------------------------------------------------------------------------
  def lineAnalyzerForCrash (self, line, lineparts, j_dump, new_jdoc):
    j_dump.crash_info.reason = getPart(lineparts, 1)
    new_jdoc.reason = j_dump.crash_info.reason
    j_dump.crash_info.address = getPart(lineparts, 2)
    new_jdoc.address = j_dump.crash_info.address
    j_dump.crash_info.crashing_thread = getPart(lineparts, 3, int)
    new_jdoc.crashedThread = j_dump.crash_info.crashing_thread
    j_dump.crash_info.original_line = line

  #-----------------------------------------------------------------------------------------------------------------
  flashRE = re.compile(r'NPSWF32\.dll|libflashplayer(.*)\.(.*)|Flash ?Player-?(.*)')
  def getFlashVersion(self, module):
    """If (we recognize this module as Flash and figure out a version): Returns version; else (None or '')"""
    #logger.debug("flash?  %s", module)
    version = module.version
    m = StreamBreakpadProcessor.flashRE.match(module.filename)
    if m:
      if not version:
        version = m.groups()[0]
      if not version:
        version = m.groups()[2]
      if not version and 'knownFlashDebugIdentifiers' in self.config:
        version = self.config.knownFlashDebugIdentifiers.get(debugId) # probably a miss
    else:
      version = None
    return version

  #-----------------------------------------------------------------------------------------------------------------
  def lineAnalyzerForModule (self, line, lineparts, j_dump, new_jdoc):
    module = sutil.DotDict()
    module.filename = getPart(lineparts, 1)
    module.version = getPart(lineparts, 2)
    module.debug_file = getPart(lineparts, 3)
    module.debug_identifier = getPart(lineparts, 4)
    module.base_address = getPart(lineparts, 5)
    module.end_address = getPart(lineparts, 6)
    module.main_module = getPart(lineparts, 7)
    module.original_line = line
    flashVersion = self.getFlashVersion(module)
    if flashVersion:
      new_jdoc.flash_version = flashVersion
    j_dump.modules.append(module)

  #-----------------------------------------------------------------------------------------------------------------
  def lineAnalyzerForStackFrames (self, line, lineparts, j_dump, new_jdoc):
    stack_frame = sutil.DotDict()
    try:
      stack_frame.thread_number = int(lineparts[0])
      stack_frame.frame_number = int(lineparts[1])
    except (TypeError, ValueError, IndexError):
      raise BadBreakpadAnalysisLineException("this looked line a frame line, but it wasn't valid: %s" % line)
    stack_frame.module = getPart(lineparts, 2)
    stack_frame.function = getPart(lineparts, 3)
    stack_frame.file = getPart(lineparts, 4)
    stack_frame.line = getPart(lineparts, 5)
    stack_frame.offset = getPart(lineparts, 6)
    stack_frame.signature = self.signatureTool.normalize_signature(stack_frame.module,
                                                                   stack_frame.function,
                                                                   stack_frame.file,
                                                                   stack_frame.line,
                                                                   stack_frame.offset)
    stack_frame.original_line = line
    j_dump.threads[stack_frame.thread_number].append(stack_frame)

  #-----------------------------------------------------------------------------------------------------------------
  def generatePipeDump(self, j_dump):
    """reconstruct the original pipe delimited breakpad_server output,
    editing out excessive long stacks."""
    output_buffer = []
    try:
      output_buffer.append(j_dump.os_info.original_line)
    except KeyError:
      pass
    try:
      output_buffer.append(j_dump.cpu_info.original_line)
    except KeyError:
      pass
    try:
      output_buffer.append(j_dump.crash_info.original_line)
    except KeyError:
      pass
    for module in j_dump.modules:
      try:
        output_buffer.append(module.original_line)
      except KeyError:
        pass
    output_buffer.append('') # blank line between module section and threads section
    for i in itertools.count(): # this insures a sorted list of threads
      if i not in j_dump.threads:
        break
      output_buffer.extend((x.original_line for x in j_dump.threads[i]))
    return '\n'.join(output_buffer)

  #-----------------------------------------------------------------------------------------------------------------
  def topmostFilenamesAnalysis(self, j_dump, j_doc, new_jdoc):
    try:
      new_jdoc.topmost_filenames = j_dump.threads[j_dump.crash_info.crashing_thread][0].file
    except Exception:
      new_jdoc.topmost_filenames = None
      new_jdoc.processor_notes.append('Unable to determine the topmost_filenames')

  #-----------------------------------------------------------------------------------------------------------------
  def generateSignature(self, j_dump, j_doc, new_jdoc):
    try:
      frameSigList = [x.signature for x in j_dump.threads[j_dump.crash_info.crashing_thread]]
      #self.logger.debug(str(frameSigList))
      if 'process_type' in new_jdoc:
        isHang = new_jdoc.process_type == 'hang'
      else:
        isHang = False
      new_jdoc.signature = self.signatureTool.generateSignatureFromList(frameSigList,
                                                                        isHang)

      #self.logger.debug("new signature: %s", new_jdoc.signature)
    except KeyError, x:
      new_jdoc.signature = ''
      if j_dump.crash_info.crashing_thread:
        new_jdoc.processor_notes.append('No signature could be generated because frame information is missing for thread %d - %s' % (j_dump.crash_info.crashing_thread, str(x)))
      else:
        new_jdoc.processor_notes.append("No signature could be generated because there's no information about which thread crashed")

  #-----------------------------------------------------------------------------------------------------------------
  def buildBreakpadDumpStructure (self, dumpAnalysisLineIterator, j_dump, j_doc, new_jdoc):
    j_dump.os_info = sutil.DotDict()
    j_dump.cpu_info = sutil.DotDict()
    j_dump.crash_info = sutil.DotDict()
    j_dump.crash_info.crashing_thread = None
    j_dump.modules = []
    j_dump.threads = collections.defaultdict(self.ThreadFramesContainerClass)
    new_jdoc.flash_version = None
    j_dump.status = dumpAnalysisLineIterator.next()
    j_dump.bad_breakpad_output = []
    for line in dumpAnalysisLineIterator:
      lineparts = [x.strip() for x in line.split('|')]
      dispatch_key = lineparts[0]
      try:
        self.analysisDispatcher[dispatch_key](line, lineparts, j_dump, new_jdoc)
      except BadBreakpadAnalysisLineException, x:
        j_dump.bad_breakpad_output.append(line)
        new_jdoc.processor_notes.append(str(x))
    #self.logger.debug('no more lines from breakpad')

  #-----------------------------------------------------------------------------------------------------------------
  def detectTruncatedThreadStackFrames(self, j_dump, new_jdoc):
    new_jdoc.truncated_threads = []
    new_jdoc.truncated = False
    for i, aStack in j_dump.threads.iteritems():
      #self.config.logger.debug('examining thread %d' % i)
      if aStack.isTruncated():
        new_jdoc.truncated_threads.append(i)
        if i == j_dump.crash_info.crashing_thread:
          new_jdoc.truncated = True

  #-----------------------------------------------------------------------------------------------------------------
  def breakpadAnalyzer(self, dumpAnalysisLineIterator, j_doc, new_jdoc):
    #self.logger.debug ('starting breakpadAnalyzer');
    # build breakpad output dict structure
    j_dump = sutil.DotDict()
    self.buildBreakpadDumpStructure(dumpAnalysisLineIterator, j_dump, j_doc, new_jdoc)

    # generate analysis notes
    if 'original_line' not in j_dump.os_info:
      new_jdoc.processor_notes.append('No OS information was included in this dump')
    if 'original_line' not in j_dump.cpu_info:
      new_jdoc.processor_notes.append('No CPU information was included in this dump')
    if 'original_line' not in j_dump.os_info:
      new_jdoc.processor_notes.append('No Crash information was included in this dump')
    if j_dump.crash_info.crashing_thread == None:
      new_jdoc.processor_notes.append('No thread was identified as the cause of the crash')
    if not j_dump.modules:
      new_jdoc.processor_notes.append('No modules were listed in this dump')
    if not j_dump.threads:
      new_jdoc.processor_notes.append('No frames were listed in this dump')
    if not new_jdoc.flash_version:
      new_jdoc.processor_notes.append('No module was identified as Flash')

    # additional analysis
    self.generateSignature(j_dump, j_doc, new_jdoc)
    self.topmostFilenamesAnalysis(j_dump, j_doc, new_jdoc)
    self.detectTruncatedThreadStackFrames(j_dump, new_jdoc)

    if self.config.generatePipeDump:
      new_jdoc.dump = self.generatePipeDump(j_dump)
    if self.config.generateJDump:
      new_jdoc.jdump = j_dump

