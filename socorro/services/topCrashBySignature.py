import logging
logger = logging.getLogger("webapi")

import socorro.database.database as db
import socorro.webapi.webapiService as webapi
import socorro.lib.util as util
import socorro.lib.datetimeutil as dtutil

import psycopg2.extras

class TopCrashBySignature(webapi.JsonServiceBase):

  def __init__(self, configContext):
    super(TopCrashBySignature, self).__init__(configContext)
    logger.debug('TopCrashBySignature __init__')

  # curl 'http://localhost:8085/201106/topcrash/by/sig/p/Firefox/v/5.0/limit/100/start/2011-06-01T00:00:01+0000'
  uri = '/201106/topcrash/by/sig/p/(.*)/v/(.*)/limit/(.*)/start/(.*)'

  def get(self, *args):
    convertedArgs = webapi.typeConversion([str, str, int, dtutil.datetimeFromISOdateString], args)
    parameters = util.DotDict(zip(['product','version','limit','start'], convertedArgs))

    connection = self.database.connection()
    cursor = connection.cursor()

    # use the last date that we have data for as the end
    lastUpdateByVer = """
                      /* socorro.services.topCrashBySignatures lastUpdateByVer */
                     SELECT max(window_end) AS last_updated
                     FROM top_crashes_by_signature tcs
                     JOIN productdims p ON tcs.productdims_id = p.id
                     WHERE p.product = %(product)s AND
                           p.version = %(version)s"""

    cursor.execute(lastUpdateByVer, parameters)
    parameters['end'] = cursor.fetchone()

    tcbsByVersion = """
                    /* socorro.services.topCrashBySignature tcbsByVersion */
                    SELECT p.product AS product,
                      p.version AS version,
                      tcs.signature,
                      sum(tcs.count) as total,
                      sum(case when o.os_name LIKE 'Windows%%' then tcs.count else 0 end) as win,
                      sum(case when o.os_name = 'Mac OS X' then tcs.count else 0 end) as mac,
                      sum(case when o.os_name = 'Linux' then tcs.count else 0 end) as linux
                    FROM top_crashes_by_signature tcs
                    JOIN productdims p ON tcs.productdims_id = p.id
                    JOIN osdims o ON tcs.osdims_id = o.id
                    WHERE p.product = %(product)s AND
                      p.version = %(version)s AND
                      window_end >= %(start)s AND
                      window_end < %(end)s
                    GROUP BY p.product, p.version, tcs.signature
                    HAVING sum(tcs.count) > 0
                    ORDER BY total desc
                    LIMIT %(limit)s"""

    cursor.execute(tcbsByVersion, parameters)

    result = []
    for row in cursor.fetchall():
      rowAsDict = dict(zip(['product','version','signature','total','win','mac','linux'], row))
      result.append(rowAsDict)

    return {'topcrashes': result}
