# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import socorro.database.database as db
import socorro.lib.util as util

#=================================================================================================================
class ProductVersionCache(object):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, context):
    super(ProductVersionCache, self).__init__()
    self.config = context
    self.cache = {}
    sql = """
      select
          product_name as product,
          version_string as version,
          product_version_id as id
      from
          product_info
      """
    self.database = db.Database(self.config)
    connection = self.database.connection()
    cursor = connection.cursor()
    for product, version, id in db.execute(cursor, sql):
      self.cache[(product, version)] = id
    connection.close()

  #-----------------------------------------------------------------------------------------------------------------
  def getId(self, product, version):
    try:
      return self.cache[(product, version)]
    except KeyError:
      connection = self.database.connection()
      cursor = connection.cursor()
      sql = """
          select
              product_version_id as id
          from
              product_info
          where
            product_name = %s
            and version_string = %s
          """
      try:
        self.cache[(product, version)] = id = db.singleValueSql(cursor, sql, (product, version))
        return id
      except Exception:
        util.reportExceptionAndContinue(self.config['logger'])
        raise KeyError((product, version))
