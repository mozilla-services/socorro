import logging
logger = logging.getLogger("webapi")

import socorro.lib.util as util
import socorro.webapi.webapiService as webapi
import socorro.database.database as db

class SchedulePriorityJob(webapi.JsonServiceBase):
  def __init__(self, configContext):
    super(SchedulePriorityJob, self).__init__(configContext)

  uri = '/201105/schedule/priority/job/(.*)'

  def post(self, *args):
    convertedArgs = webapi.typeConversion([str], args)
    parameters = util.DotDict(zip(['uuid'], convertedArgs))
    connection = self.database.connection()
    sql = """INSERT INTO priorityjobs (uuid) VALUES (%s)"""
    try:
      connection.cursor().execute(sql, (parameters['uuid'],))
    except Exception:
      connection.rollback()
      util.reportExceptionAndContinue(logger)
      return False
    connection.commit()
    return True
