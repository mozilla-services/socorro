#! /usr/bin/env python

import subprocess
import os.path

import socorro.lib.config as config
import socorro.lib.util

import processor

#==========================================================
class ProcessorWithExternalBreakpad (processor.Processor):
  """
  """
#-----------------------------------------------------------------------------------------------------------------
  def __init__(self):
    super(ProcessorWithExternalBreakpad, self).__init__()
    
#-----------------------------------------------------------------------------------------------------------------
  def invokeBreakpadStackdump(self, dumpfilePathname):
    """ This function invokes breakpad_stackdump as an external process capturing and returning
          the text output of stdout.  This version represses the stderr output.
          
          input parameters:
            dumpfilePathname: the complete pathname of the dumpfile to be analyzed
    """
    symbol_path = ' '.join(['"%s"' % x for x in config.processorSymbols])
    commandline = '"%s" %s "%s" %s 2>/dev/null' % (config.processorMinidump, "-m", dumpfilePathname, symbol_path)
    subprocessHandle = subprocess.Popen(commandline, shell=True, stdout=subprocess.PIPE)
    try:
      return subprocessHandle.stdout.read()
    finally:
      subprocessHandle.stdout.close()
  
#-----------------------------------------------------------------------------------------------------------------
  def doBreakpadStackDumpAnalysis (self, reportId, uuid, dumpfilePathname, databaseCursor):
    """ This function overrides the base class version of this function.  This function coordinates the six
          steps of running the breakpad_stackdump process and analyzing the textual output for insertion
          into the database.
          
          input parameters:
            reportId - the primary key from the 'reports' table for this crash report
            uuid - the unique string identifier for the crash report
            dumpfilePathname - the complete pathname for the =crash dump file
            databaseCursor - the cursor to use for insertion into the database
    """
    dumpAnalysis = self.invokeBreakpadStackdump(dumpfilePathname)
    databaseCursor.execute("insert into dumps (report_id, data) values (%s, %s)", (reportId, dumpAnalysis))
    dumpAnalysisLineiterator = iter(dumpAnalysis.split('\n'))
    crashedThread = self.analyzeHeader(reportId, dumpAnalysisLineiterator, databaseCursor)
    self.analyzeFrames(reportId, dumpAnalysisLineiterator, databaseCursor, crashedThread)
    
#-----------------------------------------------------------------------------------------------------------------
  def analyzeHeader(self, reportId, dumpAnalysisLineiterator, databaseCursor):
    """ Scan through the lines of the dump header, extracting the information for population of the 
          'modules' table and the update of the record for this crash in 'reports'.  During the analysis
          of the header, the number of the thread that caused the crash is determined and saved.
          
          returns:
            the number of the thread that crashed
          
          input parameters:
            reportId - the associated primary key from the 'reports' table for this crash
            dumpAnalysisLineiterator - an iterator object that feeds lines from crash dump data
            databaseCursor - for database inserts and updates
    """
    crashedThread = None
    moduleCounter = 0
    reportUpdateValues = {"id": reportId} 
    reportUpdateSQLPhrases = {"osPhrase":"", "cpuPhrase":"", "crashPhrase":""}

    for line in dumpAnalysisLineiterator:
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
        # Module|{Filename}|{Version}|{Debug Filename}|{Debug ID}|{Base Address}|Max Address}|{Main}
        # we should ignore modules with no filename
        if values[1]:
          filename = socorro.lib.util.limitStringOrNone(values[1], 40)
          debug_id = socorro.lib.util.limitStringOrNone(values[4], 40)
          module_version = socorro.lib.util.limitStringOrNone(values[2], 15)
          debug_filename = socorro.lib.util.limitStringOrNone(values[3], 40)
          databaseCursor.execute("""insert into modules
                                                     (report_id, module_key, filename, debug_id, module_version, debug_filename) values
                                                     (%s, %s, %s, %s, %s, %s)""",
                                                      (reportId, moduleCounter, filename, debug_id, module_version, debug_filename))
          moduleCounter += 1
    
    if len(reportUpdateValues) > 1:
      reportUpdateSQL = ("""update reports set %(osPhrase)s%(cpuPhrase)s%(crashPhrase)s where id = PERCENT(id)s""" % reportUpdateSQLPhrases).replace(", w", " w").replace("PERCENT","%")
      databaseCursor.execute(reportUpdateSQL, reportUpdateValues)
    
    return crashedThread
    
#-----------------------------------------------------------------------------------------------------------------
  def analyzeFrames(self, reportId, dumpAnalysisLineiterator, databaseCursor, crashedThread):
    """ After the header information, the dump file consists of just frame information.  This function
          cycles through the frame information looking for frames associated with the crashed thread
          (determined in analyzeHeader).  Each from from that thread is written to the database until
           it has found a maximum of ten frames.
           
           input parameters:
             reportId - the primary key from the 'reports' table for this crash report
             dumpAnalysisLineiterator - an iterator that cycles through lines from the crash dump
             databaseCursor - for database insertions
             crashedThread - the number of the thread that crashed - we want frames only from the crashed thread
    """
    frameCounter = 0
    for line in dumpAnalysisLineiterator:
      if line == '': continue  #some dumps have unexpected blank lines - ignore them
      if frameCounter == 10:
        break
      (thread_num, frame_num, module_name, function, source, source_line, instruction) = [socorro.lib.util.emptyFilter(x) for x in line.split("|")]
      if crashedThread == int(thread_num):
        signature = processor.Processor.make_signature(module_name, function, source, source_line, instruction)
        databaseCursor.execute("""insert into frames
                                                  (report_id, frame_num, signature) values
                                                  (%s, %s, %s)""",
                                                  (reportId, frame_num, signature[:255]))
        if frameCounter == 0:
          databaseCursor.execute("update reports set signature = %s where id = %s", (signature, reportId))
        frameCounter += 1

  
if __name__ == '__main__':    
  p = ProcessorWithExternalBreakpad()
  p.start()
  print >>config.statusReportStream, "Done."
