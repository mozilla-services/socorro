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
          product,
          version,
          id
      from
          productdims
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
              id
          from
              productdims
          where
            product = %s
            and version = %s
          """
      try:
        self.cache[(product, version)] = db.singleValueSql(cursor, sql, (product, version))
      except Exception:
        util.reportExceptionAndContinue(self.config['logger'])
        raise KeyError((product, version))
