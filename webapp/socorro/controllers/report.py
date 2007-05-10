from socorro.lib.base import *
from socorro.lib.processor import Processor, firefoxHook
import socorro.lib.collect as collect

class ReportController(BaseController):
  def index(self, id):
    c.report = model.Report.get_by(uuid=id)
    if c.report is None:
      abort(404, 'Not found')
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
      
      crash_dump = request.POST['upload_file_minidump']
      if not crash_dump.file:
        #XXXsayrer set a 4xx status
        return Response('Bad request')
      
      # mirror the process used by the standalone collectors
      (dumpID, dumpPath) = collect.storeDump(crash_dump.file)
      collect.storeJSON(dumpID, dumpPath, request.POST)
      processor = Processor(minidump, [symbol_dir], reportHook=firefoxHook)
      processor.process(dumpPath, dumpID)
      return Response(collect.makeResponseForClient(dumpID))

    else:
      h.log('bad request?')
      #XXXsayrer set a 4xx status
      return Response('Bad request')
