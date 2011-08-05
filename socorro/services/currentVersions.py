import logging
logger = logging.getLogger("webapi")

import socorro.database.database as db
import socorro.webapi.webapiService as webapi
import socorro.lib.util as util
import socorro.lib.datetimeutil as dtutil

import collections as col
import functools as ft

from collections import defaultdict

class CurrentVersions(webapi.JsonServiceBase):
  def __init__(self, configContext):
    super(CurrentVersions, self).__init__(configContext)
    logger.debug('CurrentVersions __init__')

  # curl 'http://localhost:8085/201106/current/versions'
  uri = '/201106/current/versions/(.*)'

  def get(self, *args):

    connection = self.database.connection()
    cursor = connection.cursor()

    featured_only = False
    if 'featured' in args:
      featured_only = True

    # use the last date that we have data for as the end
    currentVersions = """
                      /* socorro.services.CurrentVersions curentVersions */
                     SELECT product_name, version_string, is_featured,
                            start_date, end_date
                     FROM product_info"""

    if featured_only:
      currentVersions += """ WHERE is_featured"""

    cursor.execute(currentVersions)

    defaultdict_factory_with_list = ft.partial(col.defaultdict, list)

    result = col.defaultdict(defaultdict_factory_with_list)
    for product, version, featured, start, end in cursor.fetchall():
      releases = { 'version': version,
                   'start_date': str(start),
                   'end_date': str(end) }

      if not featured_only:
        releases['featured'] = featured

      result[product]['releases'].append(releases)

    return {'currentversions': result}
