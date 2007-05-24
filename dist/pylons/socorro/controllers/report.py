from socorro.lib.base import *
from socorro.lib.processor import Processor
from socorro.models import Report
import socorro.lib.collect as collect
from sqlalchemy import *
from sqlalchemy.databases.postgres import *

class ReportController(BaseController):
  def index(self, id):
    c.report = Report.get_by(uuid=id)
    if c.report is None:
      abort(404, 'Not found')
    return render_response('report/index')

  def list(self):
    c.signature = request.params['signature']
    c.reports = Report.select(sql.and_(Report.c.signature==c.signature,
                                       Report.c.date > func.now() - sql.cast('2 weeks', PGInterval)),
                              order_by=Report.c.date, limit=100, offset=0)
    return render_response('report/list')

  def add(self):
    #
    # Turn this off for now, until it can be tested again
    #
    if False:
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
      processor = Processor(minidump, [symbol_dir])
      processor.process(dumpPath, dumpID)
      return Response(collect.makeResponseForClient(dumpID))

    else:
      h.log('bad request?')
      #XXXsayrer set a 4xx status
      return Response('Bad request')
