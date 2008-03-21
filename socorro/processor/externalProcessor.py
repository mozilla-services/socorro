#! /usr/bin/env python

import os
import os.path

import socorro.lib.config as config
import socorro.lib.util

import processor


class ProcessorWithExternalBreakpad (processor.Processor):
  def __init__(self):
    super(ProcessorWithExternalBreakpad, self).__init__()
    self.crashed_thread = None
    
  def invokeBreakpadStackdump(self, dumpfilePathname):
    # now call stackwalk and handle the results
    symbol_path = ' '.join(['"%s"' % x for x in config.processorSymbols])
    commandline = '"%s" %s "%s" %s' % (config.processorMinidump, "-m", dumpfilePathname, symbol_path)
    f = os.popen(commandline)
    try:
      return f.read()
    finally:
      f.close()
  
  def doBreakpadStackDumpAnalysis (self, reportId, uuid, dumpfilePathname, databaseCursor):
    dumpAnalysis = self.invokeBreakpadStackdump(dumpfilePathname)
    databaseCursor.execute("insert into dumps (report_id, data) values (%s, %s)", (reportId, dumpAnalysis))
    dumpAnalysisLineiterator = iter(dumpAnalysis.split('\n'))
    self.analyzeHeader(reportId, dumpAnalysisLineiterator, databaseCursor)
    self.analyzeFrames(reportId, dumpAnalysisLineiterator, databaseCursor)
    
  def analyzeHeader(self, reportId, dumpAnalysisLineiterator, databaseCursor):
    self.crashed_thread = None
    moduleCounter = 0
    reportUpdateValues = {"id": reportId} 

    for line in dumpAnalysisLineiterator:
      # empty line separates header data from thread data
      if line == '':
        break
      values = map(socorro.lib.util.emptyFilter, line.split("|"))
      if values[0] == 'OS':
        reportUpdateValues['os_name'] = values[1]
        reportUpdateValues['os_version'] = values[2]
      elif values[0] == 'CPU':
        reportUpdateValues['cpu_name'] = values[1]
        reportUpdateValues['cpu_info'] = values[2]
      elif values[0] == 'Crash':
        reportUpdateValues['reason'] = values[1]
        reportUpdateValues['address'] = values[2]
        self.crashed_thread = int(values[3])
      elif values[0] == 'Module':
        # Module|{Filename}|{Version}|{Debug Filename}|{Debug ID}|{Base Address}|Max Address}|{Main}
        # we should ignore modules with no filename
        if values[1]:
          databaseCursor.execute("""insert into modules
                                                     (report_id, module_key, filename, debug_id, module_version, debug_filename) values
                                                     (%s, %s, %s, %s, %s, %s)""",
                                                      (reportId, moduleCounter, values[1], values[4], values[2], values[3]))
          moduleCounter += 1
    databaseCursor.execute("""update reports set 
                                                  os_name = %(os_name)s,
                                                  os_version = %(os_version)s,
                                                  cpu_name = %(cpu_name)s,
                                                  cpu_info = %(cpu_info)s,
                                                  reason = %(reason)s,
                                                  address = %(address)s
                                              where id = %(id)s""", reportUpdateValues)
  
  def analyzeFrames(self, reportId, dumpAnalysisLineiterator, databaseCursor):
    frameCounter = 0
    for line in dumpAnalysisLineiterator:
      if frameCounter == 10:
        break
      (thread_num, frame_num, module_name, function, source, source_line, instruction) = map(socorro.lib.util.emptyFilter, line.split("|"))
      if self.crashed_thread == int(thread_num):
        frameCounter += 1
        signature = processor.make_signature(module_name, function, source, source_line, instruction)
        #source_filename = source_link = source_info = None
        #if source is not None:
        #  vcsinfo = source.split(":")
        #  if len(vcsinfo) == 4:
        #    (type, root, source_file, revision) = vcsinfo
        #    source_filename = source_file
        #    if type in config.vcsMappings:
        #      if root in config.vcsMappings[type]:
        #        source_link = config.vcsMappings[type][root] % \
        #                                {'file': source_file,
        #                                 'revision': revision, 
        #                                 'line': source_line} 
        #  else:
        #    source_filename = os.path.split(source)[1]
        #databaseCursor.execute("""insert into frames
        #                                          (report_id, module_name, frame_num, signature, function, source, source_line, instruction, source_filename, source_link, source_info) values
        #                                          (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        #                                          (reportId, module_name, frame_num, signature, function, source, source_line, instruction, source_filename, source_link, source_info))
        databaseCursor.execute("""insert into frames
                                                  (report_id, frame_num, signature) values
                                                  (%s, %s, %s)""",
                                                  (reportId, frame_num, signature))
        
  
if __name__ == '__main__':    
  p = ProcessorWithExternalBreakpad()
  p.start()
  print >>config.statusReportStream, "Done."
