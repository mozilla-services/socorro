#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import signal
import os
import subprocess
import os.path
import re
from socorro.lib.datetimeutil import utc_now
from contextlib import closing

import logging

logger = logging.getLogger("processor")

import socorro.lib.util

import processor

import socorro.database.database as sdb
import socorro.storage.crashstorage as cstore
import socorro.lib.threadlib as sthr


#=================================================================================================================
class ProcessorWithExternalBreakpad (processor.Processor):
  """
  """
#-----------------------------------------------------------------------------------------------------------------
  def __init__(self, config, sdb=sdb, cstore=cstore, signal=signal,
               sthr=sthr, os=os, nowFunc=utc_now):
    super(ProcessorWithExternalBreakpad, self).__init__(
      config,
      sdb,
      cstore,
      signal,
      sthr,
      os,
      nowFunc
    )

    assert "processorSymbolsPathnameList" in config, "processorSymbolsPathnameList is missing from the configuration"
    assert "crashingThreadFrameThreshold" in config, "crashingThreadFrameThreshold is missing from the configuration"
    assert "crashingThreadTailFrameThreshold" in config, "crashingThreadTailFrameThreshold is missing from the configuration"
    assert "stackwalkCommandLine" in config, "stackwalkCommandLine is missing from the configuration"

    #preprocess the breakpad_stackwalk command line
    stripParensRE = re.compile(r'\$(\()(\w+)(\))')
    toPythonRE = re.compile(r'\$(\w+)')
    # Canonical form of $(param) is $param. Convert any that are needed
    tmp = stripParensRE.sub(r'$\2',config.stackwalkCommandLine)
    # Convert canonical $dumpfilePathname to DUMPFILEPATHNAME
    tmp = tmp.replace('$dumpfilePathname','DUMPFILEPATHNAME')
    # Convert canonical $processorSymbolsPathnameList to SYMBOL_PATHS
    tmp = tmp.replace('$processorSymbolsPathnameList','SYMBOL_PATHS')
    # finally, convert any remaining $param to pythonic %(param)s
    tmp = toPythonRE.sub(r'%(\1)s',tmp)
    self.mdsw_command_line = tmp % config

    # Canonical form of $(param) is $param. Convert any that are needed
    tmp = stripParensRE.sub(r'$\2',config.exploitability_tool_command_line)
    # Convert canonical $dumpfilePathname to DUMPFILEPATHNAME
    tmp = tmp.replace('$dumpfilePathname','DUMPFILEPATHNAME')
    # finally, convert any remaining $param to pythonic %(param)s
    tmp = toPythonRE.sub(r'%(\1)s', tmp)
    self.exploitability_command_line = tmp % config

#-----------------------------------------------------------------------------------------------------------------
  def invokeBreakpadStackdump(self, dumpfilePathname):
    """ This function invokes breakpad_stackdump as an external process capturing and returning
          the text output of stdout.  This version represses the stderr output.

          input parameters:
            dumpfilePathname: the complete pathname of the dumpfile to be analyzed
    """
    #logger.debug("analyzing %s", dumpfilePathname)
    if type(self.config.processorSymbolsPathnameList) is list:
      symbol_path = ' '.join(['"%s"' % x for x in self.config.processorSymbolsPathnameList])
    else:
      symbol_path = ' '.join(['"%s"' % x for x in self.config.processorSymbolsPathnameList.split()])
    #commandline = '"%s" %s "%s" %s 2>/dev/null' % (self.config.minidump_stackwalkPathname, "-m", dumpfilePathname, symbol_path)
    newCommandLine = self.mdsw_command_line.replace("DUMPFILEPATHNAME", dumpfilePathname)
    newCommandLine = newCommandLine.replace("SYMBOL_PATHS", symbol_path)
    #logger.info("invoking: %s", newCommandLine)
    subprocessHandle = subprocess.Popen(newCommandLine, shell=True, stdout=subprocess.PIPE)
    return (socorro.lib.util.StrCachingIterator(subprocessHandle.stdout), subprocessHandle)

#-----------------------------------------------------------------------------------------------------------------
  def invoke_exploitability(self, dump_pathname):
    """ This function invokes exploitability tool as an external process
        capturing and returning the text output of stdout.  This version
        represses the stderr output.

          input parameters:
            dump_pathname: the complete pathname of the dumpfile to be analyzed
    """
    command_line = self.exploitability_command_line.replace(
                     "DUMPFILEPATHNAME",
                     dump_pathname
                   )
    subprocessHandle = subprocess.Popen(
                         command_line,
                         shell=True,
                         stdout=subprocess.PIPE
                       )
    return (subprocessHandle.stdout, subprocessHandle)

#-----------------------------------------------------------------------------------------------------------------
  def doBreakpadStackDumpAnalysis (self,
                                   reportId,
                                   uuid,
                                   dumpfilePathname,
                                   isHang,
                                   java_stack_trace,
                                   databaseCursor,
                                   date_processed,
                                   processorErrorMessages):
    """ This function overrides the base class version of this function.  This
    function coordinates the six steps of running the breakpad_stackdump
    process and analyzing the textual output for insertion into the database.

          returns:
            truncated - boolean: True - due to excessive length the frames of
                                        the crashing thread may have been
                                        truncated.

          input parameters:
            reportId - the primary key from the 'reports' table for this report
            uuid - the unique string identifier for the crash report
            dumpfilePathname - the complete pathname for the =crash dump file
            isHang - boolean, is this a hang crash?
            app_notes - a source for java signatures info
            databaseCursor - the cursor to use for insertion into the database
            date_processed
            processorErrorMessages
    """
    #logger.debug('doBreakpadStackDumpAnalysis')
    dumpAnalysisLineIterator, \
      mdsw_subprocess_handle = self.invokeBreakpadStackdump(dumpfilePathname)
    dumpAnalysisLineIterator.secondaryCacheMaximumSize = \
      self.config.crashingThreadTailFrameThreshold + 1
    exploitability_line_iterator, \
      exploitability_subprocess_handle = self.invoke_exploitability(
                                          dumpfilePathname
                                        )
    additionalReportValuesAsDict = self._stackwalk_analysis(
                                     dumpAnalysisLineIterator,
                                     mdsw_subprocess_handle,
                                     reportId,
                                     uuid,
                                     dumpfilePathname,
                                     isHang,
                                     java_stack_trace,
                                     databaseCursor,
                                     date_processed,
                                     processorErrorMessages
                                   )
    additionalReportValuesAsDict['exploitability'] = \
      self._exploitability_analysis(
        exploitability_line_iterator,
        exploitability_subprocess_handle,
        processorErrorMessages
      )
    return additionalReportValuesAsDict

#-----------------------------------------------------------------------------------------------------------------
  def _stackwalk_analysis(self,
                          dumpAnalysisLineIterator,
                          mdsw_subprocess_handle,
                          reportId,
                          uuid,
                          dumpfilePathname,
                          isHang,
                          java_stack_trace,
                          databaseCursor,
                          date_processed,
                          processorErrorMessages):
    try:
      additionalReportValuesAsDict = self.analyzeHeader(reportId, dumpAnalysisLineIterator, databaseCursor, date_processed, processorErrorMessages)
      crashedThread = additionalReportValuesAsDict["crashedThread"]
      try:
        lowercaseModules = additionalReportValuesAsDict['os_name'] in ('Windows NT')
      except KeyError:
        lowercaseModules = True
      evenMoreReportValuesAsDict = self.analyzeFrames(reportId, isHang, java_stack_trace, lowercaseModules, dumpAnalysisLineIterator, databaseCursor, date_processed, crashedThread, processorErrorMessages)
      additionalReportValuesAsDict.update(evenMoreReportValuesAsDict)
      for x in dumpAnalysisLineIterator:
        pass  #need to spool out the rest of the stream so the cache doesn't get truncated
      dumpAnalysisAsString = ('\n'.join(dumpAnalysisLineIterator.cache))
      additionalReportValuesAsDict["dump"] = dumpAnalysisAsString
    finally:
      dumpAnalysisLineIterator.theIterator.close() #this is really a handle to a file-like object - got to close it
    # is the return code from the invocation important?  Uncomment, if it is...
    returncode = mdsw_subprocess_handle.wait()
    if returncode is not None and returncode != 0:
      processorErrorMessages.append("%s failed with return code %s" %(self.config.minidump_stackwalkPathname, mdsw_subprocess_handle.returncode))
      additionalReportValuesAsDict['success'] = False
      if additionalReportValuesAsDict["signature"].startswith("EMPTY"):
        additionalReportValuesAsDict["signature"] += "; corrupt dump"
    return additionalReportValuesAsDict

#-----------------------------------------------------------------------------------------------------------------
  def _exploitability_analysis(self,
                              exploitability_line_iterator,
                              exploitability_subprocess_handle,
                              error_messages):
    exploitability = None
    with closing(exploitability_line_iterator) as the_iter:
      for a_line in the_iter:
        exploitability = a_line.strip().replace('exploitability: ', '')
    returncode = exploitability_subprocess_handle.wait()
    if exploitability is not None and 'ERROR' in exploitability:
      error_messages.append("%s: %s" %
                            (self.config.exploitability_tool_pathname,
                            exploitability))
      exploitability = None
    if returncode is not None and returncode != 0:
      error_messages.append("%s failed with return code %s" %
                               (self.config.exploitability_tool_pathname,
                               returncode))
    return exploitability

#-----------------------------------------------------------------------------------------------------------------
  def analyzeHeader(self, reportId, dumpAnalysisLineIterator, databaseCursor, date_processed, processorErrorMessages):
    """ Scan through the lines of the dump header:
        - # deprecated: extract the information for populating the 'modules' table
        - extract data to update the record for this crash in 'reports', including the id of the crashing thread
        Returns: Dictionary of the various values that were updated in the database
        Side effects: If at least two distinct values are parsed (any of them): the reports table is updated
        Input parameters:
        - reportId - the associated primary key from the 'reports' table for this crash
        - dumpAnalysisLineIterator - an iterator object that feeds lines from crash dump data
        - databaseCursor - for database inserts and updates
        - date_processed
        - processorErrorMessages
    """
    #logger.info("analyzeHeader")
    crashedThread = None
    moduleCounter = 0
    reportUpdateValues = {"id": reportId, "success": True}

    analyzeReturnedLines = False
    reportUpdateSqlParts = []
    flash_version = None
    for lineNumber, line in enumerate(dumpAnalysisLineIterator):
      line = line.strip()
      # empty line separates header data from thread data
      if line == '':
        break
      analyzeReturnedLines = True
      #logger.debug("[%s]", line)
      values = map(lambda x: x.strip(), line.split('|'))
      if len(values) < 3:
        processorErrorMessages.append('Cannot parse header line "%s"'%line)
        continue
      values = map(socorro.lib.util.emptyFilter, values)
      if values[0] == 'OS':
        name = socorro.lib.util.limitStringOrNone(values[1], 100)
        version = socorro.lib.util.limitStringOrNone(values[2], 100)
        reportUpdateValues['os_name']=name
        reportUpdateValues['os_version']=version
        reportUpdateSqlParts.extend(['os_name = %(os_name)s', 'os_version = %(os_version)s'])
      elif values[0] == 'CPU':
        reportUpdateValues['cpu_name'] = socorro.lib.util.limitStringOrNone(values[1], 100)
        reportUpdateValues['cpu_info'] = socorro.lib.util.limitStringOrNone(values[2], 100)
        try:
          reportUpdateValues['cpu_info'] = '%s | %s' % (reportUpdateValues['cpu_info'],
                                                        socorro.lib.util.limitStringOrNone(values[3], 100))
        except IndexError:
          pass
        reportUpdateSqlParts.extend(['cpu_name = %(cpu_name)s','cpu_info = %(cpu_info)s'])
      elif values[0] == 'Crash':
        reportUpdateValues['reason'] = socorro.lib.util.limitStringOrNone(values[1], 255)
        reportUpdateValues['address'] = socorro.lib.util.limitStringOrNone(values[2], 20)
        reportUpdateSqlParts.extend(['reason = %(reason)s','address = %(address)s'])
        try:
          crashedThread = int(values[3])
        except Exception:
          crashedThread = None
      elif values[0] == 'Module':
        # grab only the flash version, which is not quite as easy as it looks
        if not flash_version:
          flash_version = self.getVersionIfFlashModule(values)
        # pass
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
      logger.warning("%s", message)

    #logger.info('reportUpdateValues: %s', str(reportUpdateValues))
    #logger.info('reportUpdateSqlParts: %s', str(reportUpdateSqlParts))
    if len(reportUpdateSqlParts) > 1:
      reportUpdateSQL = """update reports set %s where id=%%(id)s AND date_processed = timestamp with time zone '%s'"""%(",".join(reportUpdateSqlParts),date_processed)
      databaseCursor.execute(reportUpdateSQL, reportUpdateValues)

    if crashedThread is None:
      message = "No thread was identified as the cause of the crash"
      processorErrorMessages.append(message)
      logger.warning("%s", message)
    reportUpdateValues["crashedThread"] = crashedThread
    if not flash_version:
      flash_version = '[blank]'
    reportUpdateValues['flash_version'] = flash_version
    #logger.debug(" updated values  %s", reportUpdateValues)
    return reportUpdateValues

#-----------------------------------------------------------------------------------------------------------------
  flashRE = re.compile(r'NPSWF32_?(.*)\.dll|FlashPlayerPlugin_?(.*)\.exe|libflashplayer(.*)\.(.*)|Flash ?Player-?(.*)')
  def getVersionIfFlashModule(self,moduleData):
    """If (we recognize this module as Flash and figure out a version): Returns version; else (None or '')"""
    #logger.debug(" flash? %s", moduleData)
    try:
      module,filename,version,debugFilename,debugId = moduleData[:5]
    except ValueError:
      logger.debug("bad module line %s", moduleData)
      return None
    m = ProcessorWithExternalBreakpad.flashRE.match(filename)
    if m:
      if not version:
        groups = m.groups()
        if groups[0]:
          version = groups[0].replace('_', '.')
        elif groups[1]:
          version = groups[1].replace('_', '.')
        elif groups[2]:
          version = groups[2]
        elif groups[4]:
          version = groups[4]
        elif 'knownFlashDebugIdentifiers' in self.config:
          version = self.config.knownFlashDebugIdentifiers.get(debugId) # probably a miss
    else:
      version = None
    return version

#-----------------------------------------------------------------------------------------------------------------
  def analyzeFrames(self, reportId, hangType, java_stack_trace, lowercaseModules, dumpAnalysisLineIterator, databaseCursor, date_processed, crashedThread, processorErrorMessages):
    """ After the header information, the dump file consists of just frame information.  This function
          cycles through the frame information looking for frames associated with the crashed thread
          (determined in analyzeHeader).  Each frame from that thread is written to the database until
           it has found a maximum of ten frames.

           returns:
             a dictionary will various values to be used to update report in the database, including:
               truncated - boolean: True - due to excessive length the frames of the crashing thread may have been truncated.
               signature - string: an overall signature calculated for this crash
               processor_notes - string: any errors or warnings that happened during the processing

           input parameters:
             reportId - the primary key from the 'reports' table for this crash report
             hangType -  0: if this is not a hang
                        -1: if "HangID" present in json,but "Hang" was not present
                        "Hang" value: if "Hang" present - probably 1
             java_stack_trace - a source for java lang signature information
             lowerCaseModules - boolean, should modules be forced to lower case for signature generation?
             dumpAnalysisLineIterator - an iterator that cycles through lines from the crash dump
             databaseCursor - for database insertions
             date_processed
             crashedThread - the number of the thread that crashed - we want frames only from the crashed thread
    """
    #logger.info("analyzeFrames")
    frameCounter = 0
    truncated = False
    analyzeReturnedLines = False
    signatureList = []
    topmost_sourcefiles = []
    if hangType == 1:
      thread_for_signature = 0
    else:
      thread_for_signature = crashedThread
    max_topmost_sourcefiles = 1 # Bug 519703 calls for just one. Lets build in some flex
    for line in dumpAnalysisLineIterator:
      analyzeReturnedLines = True
      #logger.debug("  %s", line)
      line = line.strip()
      if line == '':
        processorErrorMessages.append("An unexpected blank line in this dump was ignored")
        continue  #some dumps have unexpected blank lines - ignore them
      (thread_num, frame_num, module_name, function, source, source_line, instruction) = [socorro.lib.util.emptyFilter(x) for x in line.split("|")]
      if len(topmost_sourcefiles) < max_topmost_sourcefiles and source:
        topmost_sourcefiles.append(source)
      if thread_for_signature == int(thread_num):
        if frameCounter < 30:
          if lowercaseModules:
            try:
              module_name = module_name.lower()
            except AttributeError:
              pass
          thisFramesSignature = self.c_signature_tool.normalize_signature(module_name, function, source, source_line, instruction)
          signatureList.append(thisFramesSignature)
          # Bug681476 - stop writing to frames table
          # leaving code in place incase we wish to revert the change
          #if frameCounter < 10:
            #self.framesTable.insert(databaseCursor, (reportId, frame_num, date_processed, thisFramesSignature[:255]), self.databaseConnectionPool.connectionCursorPair, date_processed=date_processed)
        if frameCounter == self.config.crashingThreadFrameThreshold:
          processorErrorMessages.append("This dump is too long and has triggered the automatic truncation routine")
          #logger.debug("starting secondary cache with framecount = %d", frameCounter)
          dumpAnalysisLineIterator.useSecondaryCache()
          truncated = True
        frameCounter += 1
      elif frameCounter:
        break
    dumpAnalysisLineIterator.stopUsingSecondaryCache()
    signature = self.generate_signature(signatureList,
                                        java_stack_trace,
                                        hangType,
                                        crashedThread,
                                        processorErrorMessages)
    #logger.debug("  %s", (signature, '; '.join(processorErrorMessages), reportId, date_processed))
    if not analyzeReturnedLines:
      message = "No frame data available"
      processorErrorMessages.append(message)
      logger.warning("%s", message)
    #processor_notes = '; '.join(processorErrorMessages)
    #databaseCursor.execute("update reports set signature = %%s, processor_notes = %%s where id = %%s and date_processed = timestamp with time zone '%s'" % (date_processed),(signature, processor_notes,reportId))
    #logger.debug ("topmost_sourcefiles  %s", topmost_sourcefiles)
    return { "signature": signature,
             "truncated": truncated,
             "topmost_filenames":topmost_sourcefiles,
           }



  #---------------------------------------------------------------------------
  def generate_signature(self,
                         signature_list,
                         java_stack_trace,
                         hang_type,
                         crashed_thread,
                         processor_notes_list,
                         signature_max_len=255):
    if java_stack_trace:
      # generate a Java signature
      signature, \
        signature_notes = self.java_signature_tool.generate(java_stack_trace,
                                                            delimiter=' ')
      return signature
    else:
      # generate a C signature
      signature, \
        signature_notes = self.c_signature_tool.generate(signature_list,
                                                         hang_type,
                                                         crashed_thread)
    if signature_notes:
      processor_notes_list.extend(signature_notes)

    return signature
