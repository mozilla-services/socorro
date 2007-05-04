from socorro.lib.base import *
from socorro.lib.processor import Processor, FixupSourcePath, TempFileForData
import socorro.models as model

class ReportController(BaseController):
  def index(self):
    c.report = model.Report.get_by(id=request.params['id'])
    return render_response('report_index')

  def list(self):
    c.reports = model.Report.select()
    return render_response('report_list')

  def add(self):
    if request.environ['REQUEST_METHOD'] == 'POST':
      # get a handle on the situation
      symbol_dir = g.pylons_config.app_conf['socorro.symbol_dir']
      minidump = g.pylons_config.app_conf['socorro.minidump_stackwalk']
      processor = Processor(minidump, [symbol_dir])
      crash_dump = request.POST['upload_file_minidump']
      if not crash_dump.file:
        return Response('Bad request')
      
      # now parse out the data
      try:   
        tempfile = TempFileForData(crash_dump.value)
        fh = processor.breakpad_file(tempfile)

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
	  
      finally:
        tempfile.close()

      return Response(report.id)
    else:
      h.log('bad request?')
      #XXXsayrer set a 4xx status
      return Response('Bad request')
