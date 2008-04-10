from socorro.models import Report, reports_table as reports, jobs_table as jobs
from socorro.lib.base import BaseController
from sqlalchemy import sql, func, select, types
from pylons.database import create_engine
from pylons import c, session, request
from pylons.templating import render_response, render
import pylons
import re
from time import strftime

class StatusController(BaseController):
  """
  This controller displays system status.
  """

  def index(self):
    """
    Default status dashboard nagios can hit up for data.
    """
    result = select([func.max(jobs.c.completeddatetime),
                     func.avg(jobs.c.completeddatetime - jobs.c.starteddatetime),
                     func.avg(jobs.c.completeddatetime - jobs.c.queueddatetime)
                     ],
                    jobs.c.completeddatetime != None,
                    engine=create_engine()).execute().fetchone().values()

    c.lastProcessedDate = result[0].strftime('%Y-%m-%d %H:%M:%S')
    c.avgProcessTime = result[1]
    c.avgWaitTime = result[2]
    result = select([func.count(jobs.c.id)],
                    jobs.c.completeddatetime == None,
                    engine=create_engine()).execute().fetchone().values()
    c.jobsPending = result[0]
    result = select([jobs.c.queueddatetime],
                    jobs.c.completeddatetime == None,
                    order_by=jobs.c.queueddatetime,
                    limit=1,
                    engine=create_engine()).execute().fetchone()
    if result is not None:
      result = result.values()[0].strftime('%Y-%m-%d %H:%M:%S')
    else:
      result = 'None'
    c.oldestQueuedJob = result
    return render_response('status/index')
