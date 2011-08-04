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
  uri = '/201106/current/versions'

  def get(self, *args):
    connection = self.database.connection()
    cursor = connection.cursor()

    # use the last date that we have data for as the end
    currentVersions = """
                      /* socorro.services.CurrentVersions curentVersions */
                     SELECT product_name, version_string
                     FROM product_selector"""

    cursor.execute(currentVersions)

    defaultdict_factory_with_list = ft.partial(col.defaultdict, list)

    result = col.defaultdict(defaultdict_factory_with_list)
    for product, version in cursor.fetchall():
      result[product]['version'].append(version)

    return {'currentversions': result}
