from socorro.lib.base import *
from socorro.lib.processor import Processor, FixupSourcePath
import socorro.lib.collect as collect
import socorro.models as model
import socorro.lib.simplejson as simplejson

class ReportController(BaseController):
  def index(self):
    c.report = model.Report.get_by(id=request.params['id'])
    return render_response('report_index')

  def list(self):
    c.reports = model.Report.select()
    return render_response('report_list')

  def add(self):
    if request.environ['REQUEST_METHOD'] == 'POST':
      #
      # xx fix this
      symbol_dir = g.pylons_config.app_conf['socorro.symbol_dir']
      minidump = g.pylons_config.app_conf['socorro.minidump_stackwalk']
      
      processor = Processor(minidump, [symbol_dir])
      crash_dump = request.POST['upload_file_minidump']
      if not crash_dump.file:
        #XXXsayrer set a 4xx status
        return Response('Bad request')
      
      # mirror the process used by the standalone collectors
      (dumpID, dumpPath) = collect.storeDump(crash_dump.file)
      collect.storeJSON(dumpID, dumpPath, request.POST)
      
      # now parse out the data
      fh = processor.breakpad_file(dumpPath)

      # read report headers
      report = model.Report()
      report.read_header(fh)
      report.flush()
      
      # record each stack frame of the crash
      #XXXsayrer probably not real fast to flush after each one
      frame_num = 0
      for line in fh:
        frame = model.Frame()
        frame.readline(line[:-1])
        if frame.thread_num is 0:
          if frame.source is not None:
            frame.source = FixupSourcePath(frame.source)
          frame.report_id = report.id
          frame.frame_num = frame_num
          report.frames.append(frame)
          frame.flush()
          frame_num += 1


      return Response(collect.makeResponseForClient(dumpID))
    else:
      h.log('bad request?')
      #XXXsayrer set a 4xx status
      return Response('Bad request')
