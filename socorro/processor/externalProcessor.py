#! /usr/bin/env python

import subprocess
import os.path
import threading
import time
import re

import logging

logger = logging.getLogger("processor")

import socorro.lib.util

import processor

#=================================================================================================================
class ProcessorWithExternalBreakpad (processor.Processor):
  """
  """
#-----------------------------------------------------------------------------------------------------------------
  def __init__(self, config):
    super(ProcessorWithExternalBreakpad, self).__init__(config)

    assert "processorSymbolsPathnameList" in config, "processorSymbolsPathnameList is missing from the configuration"
    assert "crashingThreadFrameThreshold" in config, "crashingThreadFrameThreshold is missing from the configuration"
    assert "crashingThreadTailFrameThreshold" in config, "crashingThreadTailFrameThreshold is missing from the configuration"
    assert "stackwalkCommandLine" in config, "stackwalkCommandLine is missing from the configuration"

    #preprocess the breakpad_stackwalk command line
    # convert parameters of the form "$paramterName" into a python parameter of the form "%(paramterName)s"
    self.commandLine = re.compile(r'(\$(\w+))').sub(r'%(\2)s', config.stackwalkCommandLine)
    # convert parameters of the form "$(paramterName)" into a python parameter of the form "%(paramterName)s"
    self.commandLine = re.compile(r'(\$(\(\w+\)))').sub(r'%(\2)s', self.commandLine)
    # treat the "dumpfilePathname" as a special paramter by changing its syntax
    self.commandLine = self.commandLine.replace('%(dumpfilePathname)s', "DUMPFILEPATHNAME")
    # treat the "processorSymbolsPathnameList" as a special paramter by changing its syntax
    self.commandLine = self.commandLine.replace('%(processorSymbolsPathnameList)s', "SYMBOL_PATHS")
    # finally make the substitutions to make a real command out of the template
    self.commandLine = self.commandLine %  config

#-----------------------------------------------------------------------------------------------------------------
  def invokeBreakpadStackdump(self, dumpfilePathname):
    """ This function invokes breakpad_stackdump as an external process capturing and returning
          the text output of stdout.  This version represses the stderr output.

          input parameters:
            dumpfilePathname: the complete pathname of the dumpfile to be analyzed
    """
    logger.debug("%s - analyzing %s", threading.currentThread().getName(), dumpfilePathname)
    if type(self.config.processorSymbolsPathnameList) is list:
      symbol_path = ' '.join(['"%s"' % x for x in self.config.processorSymbolsPathnameList])
    else:
      symbol_path = ' '.join(['"%s"' % x for x in self.config.processorSymbolsPathnameList.split(' ')])
    #commandline = '"%s" %s "%s" %s 2>/dev/null' % (self.config.minidump_stackwalkPathname, "-m", dumpfilePathname, symbol_path)
    newCommandLine = self.commandLine.replace("DUMPFILEPATHNAME", dumpfilePathname)
    newCommandLine = newCommandLine.replace("SYMBOL_PATHS", symbol_path)
    logger.info("%s - invoking: %s", threading.currentThread().getName(), newCommandLine)
    subprocessHandle = subprocess.Popen(newCommandLine, shell=True, stdout=subprocess.PIPE)
    return (socorro.lib.util.CachingIterator(subprocessHandle.stdout), subprocessHandle)


#-----------------------------------------------------------------------------------------------------------------
  def doBreakpadStackDumpAnalysis (self, reportId, uuid, dumpfilePathname, databaseCursor, date_processed, processorErrorMessages):
    """ This function overrides the base class version of this function.  This function coordinates the six
          steps of running the breakpad_stackdump process and analyzing the textual output for insertion
          into the database.

          returns:
            truncated - boolean: True - due to excessive length the frames of the crashing thread may have been truncated.

          input parameters:
            reportId - the primary key from the 'reports' table for this crash report
            uuid - the unique string identifier for the crash report
            dumpfilePathname - the complete pathname for the =crash dump file
            databaseCursor - the cursor to use for insertion into the database
            date_processed
            processorErrorMessages
    """

    dumpAnalysisLineIterator, subprocessHandle = self.invokeBreakpadStackdump(dumpfilePathname)
    dumpAnalysisLineIterator.secondaryCacheMaximumSize = self.config.crashingThreadTailFrameThreshold + 1
    try:
      crashedThread = self.analyzeHeader(reportId, dumpAnalysisLineIterator, databaseCursor, date_processed, processorErrorMessages)
      truncated = self.analyzeFrames(reportId, dumpAnalysisLineIterator, databaseCursor, date_processed, crashedThread, processorErrorMessages)
      for x in dumpAnalysisLineIterator:
        pass  #need to spool out the rest of the stream so the cache doesn't get truncated
      dumpAnalysis = (''.join(dumpAnalysisLineIterator.cache))
      self.dumpsTable.insert(databaseCursor, (reportId, date_processed, dumpAnalysis), self.databaseConnectionPool.connectToDatabase, date_processed=date_processed)
    finally:
      dumpAnalysisLineIterator.theIterator.close() #this is really a handle to a file-like object - got to close it
    # is the return code from the invocation important?  Uncomment, if it is...
    returncode = subprocessHandle.wait()
    if returncode is not None and returncode != 0:
      raise processor.ErrorInBreakpadStackwalkException("%s failed with return code %s when processing dump %s" %(self.config.minidump_stackwalkPathname, subprocessHandle.returncode, uuid))
    return truncated


#-----------------------------------------------------------------------------------------------------------------
  def analyzeHeader(self, reportId, dumpAnalysisLineIterator, databaseCursor, date_processed, processorErrorMessages):
    """ Scan through the lines of the dump header, extracting the information for population of the
          'modules' table and the update of the record for this crash in 'reports'.  During the analysis
          of the header, the number of the thread that caused the crash is determined and saved.

          returns:
            the number of the thread that crashed

          input parameters:
            reportId - the associated primary key from the 'reports' table for this crash
            dumpAnalysisLineIterator - an iterator object that feeds lines from crash dump data
            databaseCursor - for database inserts and updates
            date_processed
            processorErrorMessages
    """
    logger.info("%s - analyzeHeader", threading.currentThread().getName())
    crashedThread = None
    moduleCounter = 0
    reportUpdateValues = {"id": reportId}
    reportUpdateSQLPhrases = {"osPhrase":"", "cpuPhrase":"", "crashPhrase":""}

    analyzeReturnedLines = False
    for line in dumpAnalysisLineIterator:
      analyzeReturnedLines = True
      #logger.debug("%s -   %s", threading.currentThread().getName(), line)
      line = line.strip()
      # empty line separates header data from thread data
      if line == '':
        break
      values = map(socorro.lib.util.emptyFilter, line.split("|"))
      if values[0] == 'OS':
        reportUpdateValues['os_name'] = socorro.lib.util.limitStringOrNone(values[1], 100)
        reportUpdateValues['os_version'] = socorro.lib.util.limitStringOrNone(values[2], 100)
        reportUpdateSQLPhrases["osPhrase"] = "os_name = %(os_name)s, os_version = %(os_version)s, "
      elif values[0] == 'CPU':
        reportUpdateValues['cpu_name'] = socorro.lib.util.limitStringOrNone(values[1], 100)
        reportUpdateValues['cpu_info'] = socorro.lib.util.limitStringOrNone(values[2], 100)
        reportUpdateSQLPhrases["cpuPhrase"] = "cpu_name = %(cpu_name)s, cpu_info = %(cpu_info)s, "
      elif values[0] == 'Crash':
        reportUpdateValues['reason'] = socorro.lib.util.limitStringOrNone(values[1], 255)
        reportUpdateValues['address'] = socorro.lib.util.limitStringOrNone(values[2], 20)
        try:
          crashedThread = int(values[3])
        except:
          crashedThread = None
        reportUpdateSQLPhrases["crashPhrase"] = "reason = %(reason)s, address = %(address)s"
      elif values[0] == 'Module':
        pass
        # Module|{Filename}|{Version}|{Debug Filename}|{Debug ID}|{Base Address}|Max Address}|{Main}
        # we should ignore modules with no filename
        #if values[1]:
          #filename = socorro.lib.util.limitStringOrNone(values[1], 40)
          #debug_id = socorro.lib.util.limitStringOrNone(values[4], 40)
          #module_version = socorro.lib.util.limitStringOrNone(values[2], 15)
          #debug_filename = socorro.lib.util.limitStringOrNone(values[3], 40)
          #databaseCursor.execute("""insert into modules
                                                     #(report_id, module_key, filename, debug_id, module_version, debug_filename) values
                                                     #(%s, %s, %s, %s, %s, %s)""",
                                                      #(reportId, moduleCounter, filename, debug_id, module_version, debug_filename))
          #moduleCounter += 1

    if not analyzeReturnedLines:
      message = "%s returned no header lines for reportid: %s" % (self.config.minidump_stackwalkPathname, reportId)
      processorErrorMessages.append(message)
      logger.warning("%s - %s", threading.currentThread().getName(), message)

    if len(reportUpdateValues) > 1:
      reportUpdateSQL = ("""update reports set %(osPhrase)s%(cpuPhrase)s%(crashPhrase)s where id = PERCENT(id)s""" % reportUpdateSQLPhrases).replace(", w", " w").replace("PERCENT","%")
      databaseCursor.execute(reportUpdateSQL, reportUpdateValues)

    if crashedThread is None:
      message = "no thread was identified as the cause of the crash"
      processorErrorMessages.append(message)
      logger.warning("%s - %s", threading.currentThread().getName(), message)

    return crashedThread

#-----------------------------------------------------------------------------------------------------------------
  def analyzeFrames(self, reportId, dumpAnalysisLineIterator, databaseCursor, date_processed, crashedThread, processorErrorMessages):
    """ After the header information, the dump file consists of just frame information.  This function
          cycles through the frame information looking for frames associated with the crashed thread
          (determined in analyzeHeader).  Each from from that thread is written to the database until
           it has found a maximum of ten frames.

           returns:
             truncated - boolean: True - due to excessive length the frames of the crashing thread may have been truncated.

           input parameters:
             reportId - the primary key from the 'reports' table for this crash report
             dumpAnalysisLineIterator - an iterator that cycles through lines from the crash dump
             databaseCursor - for database insertions
             date_processed
             crashedThread - the number of the thread that crashed - we want frames only from the crashed thread
    """
    logger.info("%s - analyzeFrames", threading.currentThread().getName())
    frameCounter = 0
    truncated = False
    analyzeReturnedLines = False
    signatureList = []
    for line in dumpAnalysisLineIterator:
      analyzeReturnedLines = True
      #logger.debug("%s -   %s", threading.currentThread().getName(), line)
      line = line.strip()
      if line == '':
        processorErrorMessages.append("An unexpected blank line in this dump was ignored")
        continue  #some dumps have unexpected blank lines - ignore them
      (thread_num, frame_num, module_name, function, source, source_line, instruction) = [socorro.lib.util.emptyFilter(x) for x in line.split("|")]
      if crashedThread == int(thread_num):
        if frameCounter < 30:
          thisFramesSignature = processor.Processor.make_signature(module_name, function, source, source_line, instruction)
          signatureList.append(thisFramesSignature)
          if frameCounter < 10:
            self.framesTable.insert(databaseCursor, (reportId, frame_num, date_processed, thisFramesSignature[:255]), self.databaseConnectionPool.connectToDatabase, date_processed=date_processed)
        if frameCounter == self.config.crashingThreadFrameThreshold:
          processorErrorMessages.append("This dump is too long and has triggered the automatic truncation routine")
          logger.debug("%s - starting secondary cache with framecount = %d", threading.currentThread().getName(), frameCounter)
          dumpAnalysisLineIterator.useSecondaryCache()
          truncated = True
        frameCounter += 1
      elif frameCounter:
        break
    dumpAnalysisLineIterator.stopUsingSecondaryCache()
    signature = self.generateSignatureFromList(signatureList)
    if signature == '' or signature is None:
      if crashedThread is None:
        message = "No signature could be created because we don't know which thread crashed"
      else:
        message = "No proper signature could be created because no good data for the crashing thread (%d) was found" % crashedThread
        try:
          signature = signatureList[0]
        except IndexError:
          pass
      processorErrorMessages.append(message)
      logger.warning("%s - %s", threading.currentThread().getName(), message)
    databaseCursor.execute("update reports set signature = '%s', processor_notes = '%s' where id = %s and date_processed = timestamp without time zone '%s'" % (signature, '; '.join(processorErrorMessages), reportId, date_processed))

    if not analyzeReturnedLines:
      message = "%s returned no frame lines for reportid: %s" % (self.config.minidump_stackwalkPathname, reportId)
      processorErrorMessages.append(message)
      logger.warning("%s - %s", threading.currentThread().getName(), message)

    return truncated

