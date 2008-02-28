from socorro.models import Report, reports_table as reports
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
    result = select([reports.c.date_processed],
                       order_by=sql.desc(reports.c.date_processed),
                       limit=1,
                       engine=create_engine()).execute().fetchone().values()

    c.lastProcessedDate = result[0].strftime('%Y-%m-%d %H:%M:%S')
    return render_response('status/index')
