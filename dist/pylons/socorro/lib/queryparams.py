from socorro.models import reports_table as reports, branches_table as branches, frames_table as frames
import formencode
import sqlalchemy
from pylons.database import create_engine
from sqlalchemy import sql, func, select, types
from sqlalchemy.databases.postgres import PGInterval
import re
from socorro.lib.platforms import count_platforms, platformList
import socorro
from pylons import h
import pylons
import time

rangeTypes = {
  'hours': 1,
  'days': 24,
  'weeks': 168,
  'months': 744
  }

# searches shouldn't span more than 3 months
maxSearchHours = 24 * 31 * 3

class ProductVersionValidator(formencode.FancyValidator):
  """A custom validator which processes 'product:version' into (product, version)"""

  pattern = re.compile('^([^:]+):(.+)$')

  def _to_python(self, value, state):
    (product, version) = self.pattern.match(value).groups()
    return (product, version)

class ListValidator(formencode.FancyValidator):
  def __init__(self, validator=None, separator=','):
    self.separator = separator
    if validator:
      self.subvalidator = validator
    else:
      self.subvalidator = formencode.validators.String()
  
  def _to_python(self, value, state):
    return [self.subvalidator.to_python(v)
            for v in str(value).split(self.separator)]

class PlatformValidator(formencode.FancyValidator):
  def _to_python(self, value, state):
    return platformList[str(value)]

class BaseLimit(object):
  """A base class which validates date/branch/product/version conditions for
  multiple searches."""

  datetime_validator = formencode.validators.Regex(
    '^\\d{4}-\\d{2}-\\d{2}( \\d{2}:\\d{2}(:\\d{2})?)?$', strip=True
  )
  range_unit_validator = formencode.validators.OneOf(
    rangeTypes.keys()
  )
  version_validator = ListValidator(ProductVersionValidator())
  stringlist_validator = ListValidator(formencode.validators.String(strip=True))
  platform_validator = ListValidator(PlatformValidator())
  query_validator = formencode.validators.OneOf(['signature', 'stack'])
  type_validator = formencode.validators.OneOf(['exact', 'contains'])
  signature_validator = formencode.validators.String(strip=True, if_empty=None)

  @staticmethod
  def limit_range(range):
    (num, unit) = range
    num = min(num * rangeTypes[unit], maxSearchHours) / rangeTypes[unit]
    return (num, unit)

  def __init__(self, date=None, range=None,
               products=None, branches=None, versions=None, platforms=None,
               query=None, query_search=None, query_type=None):
    self.date = date
    self.range = range   # _range is a tuple (number, interval)
    self.products = products or []
    self.branches = branches or []
    self.versions = versions or []
    self.platforms = platforms or []
    self.query = query
    self.query_search = query_search
    self.query_type = query_type

  def setFromParams(self, params):
    """Set the values of this object from a request.params instance."""

    self.date = self.datetime_validator.to_python(params.get('date'), None)
    
    if 'range_value' in params and 'range_unit' in params:
      self.range = self.limit_range((formencode.validators.Int.to_python(params.get('range_value')),
                                     self.range_unit_validator.to_python(params.get('range_unit'))))
    for products in params.getall('product'):
      self.products.extend(self.stringlist_validator.to_python(products))

    for branches in params.getall('branch'):
      self.branches.extend(self.stringlist_validator.to_python(branches))

    for versions in params.getall('version'):
      self.versions.extend(self.version_validator.to_python(versions))

    for platforms in params.getall('platform'):
      self.platforms.extend(self.platform_validator.to_python(platforms))

    self.query = self.signature_validator.to_python(params.get('query', None))
    self.query_search = self.query_validator.to_python(params.get('query_search', None))
    self.query_type = self.type_validator.to_python(params.get('query_type', None))

  def getURLDict(self):
    d = { }
    if self.date is not None:
      d['date'] = self.date
    if self.range is not None:
      (d['range_value'], d['range_unit']) = self.range
    if len(self.products):
      d['product'] = ','.join(self.products)
    if len(self.branches):
      d['branch'] = ','.join(self.branches)
    if len(self.versions):
      d['version'] = ','.join(['%s:%s' % (product, version) for (product, version) in self.versions])
    if len(self.platforms):
      d['platform'] = ','.join(map(str, self.platforms))
    if self.query is not None:
      d['query'] = self.query
    if self.query_search is not None:
      d['query_search'] = self.query_search
    if self.query_type is not None:
      d['query_type'] = self.query_type
    return d

  def getSQLDateEnd(self):
    if self.date is not None:
      return sql.cast(self.date, types.Date)
    return func.now()

  def getRange(self):
    if self.range:
      return self.range
    return (1, 'weeks')

  def getSQLRange(self):
    return sql.cast('%s %s' % self.getRange(), PGInterval)
    
  def getSQLDateStart(self):
    return self.getSQLDateEnd() - self.getSQLRange()

  def getQuerySearch(self):
    if self.query_search is not None:
      return self.query_search
    return 'signature'

  def getQueryType(self):
    if self.query_type is not None:
      return self.query_type
    return 'contains'

  def filterByDate(self, q):
    return q.filter(reports.c.date.between(self.getSQLDateStart(),
                                          self.getSQLDateEnd()))

  def filterByProduct(self, q):
    if len(self.products):
      q = q.filter(reports.c.product.in_(*self.products))
    return q

  def filterByBranch(self, q):
    if len(self.branches):
      q = q.filter(sql.and_(branches.c.branch.in_(*self.branches),
                            branches.c.product == reports.c.product,
                            branches.c.version == reports.c.version))
    return q

  def filterByVersion(self, q):
    if len(self.versions):
      q = q.filter(sql.or_(*[sql.and_(reports.c.product == product,
                                      reports.c.version == version)
                             for (product, version) in self.versions]))
    return q

  def filterByPlatform(self, q):
    if len(self.platforms):
      q = q.filter(sql.or_(*[platform.condition()
                             for platform in self.platforms]))
    return q
  
  def filterByQuery(self, q):
    if self.query is not None:
      if self.getQueryType() == 'contains':
        pattern = '%' + self.query.replace('%', '%%') + '%'
        if self.getQuerySearch() == 'signature':
          q = q.filter(reports.c.signature.like(pattern))
        else:
          q = q.filter(
            sql.exists([1],
                       sql.and_(frames.c.signature.like(pattern),
                                frames.c.report_id == reports.c.id)))
      else:
        if self.getQuerySearch() == 'signature':
          q = q.filter(reports.c.signature == self.query)
        else:
          q = q.filter(
            sql.exists([1],
                       sql.and_(frames.c.signature == self.query,
                                frames.c.report_id == reports.c.id)))

    return q

  def filter(self, q, use_query=True):
    q = q.filter(reports.c.signature != None)
    q = self.filterByDate(q)
    q = self.filterByProduct(q)
    q = self.filterByBranch(q)
    q = self.filterByVersion(q)
    q = self.filterByPlatform(q)
    if use_query:
      q = self.filterByQuery(q)
    return q

  def query_reports(self):
    selects = [reports.c.date,
               reports.c.date_processed,
               reports.c.comments,
               reports.c.uuid,
               reports.c.product,
               reports.c.version,
               reports.c.build,
               reports.c.signature,
               reports.c.url,
               reports.c.os_name,
               reports.c.os_version,
               reports.c.cpu_name,
               reports.c.cpu_info,
               reports.c.address,
               reports.c.reason,
               reports.c.last_crash,
               reports.c.install_age]
    s = select(selects,
               order_by=sql.desc(reports.c.date),
               limit=500,
               engine=create_engine())

    def FilterToAppend(clause):
      s.append_whereclause(clause)
      return s
      
    s.filter = FilterToAppend
    s = self.filter(s)
    return s.execute()

  def query_frequency(self):
    # The "frequency" of a crash is the number of instances of that crash
    # divided by the number of instances of *any* crash using the specified
    # date/product/branch search criteria.
    crashcount = func.count(sql.case([(reports.c.signature == self.signature, 1)]))
    totalcount = func.count(reports.c.id)
    frequency = sql.cast(crashcount, types.Float) / totalcount
    truncateddate = func.date_trunc('day', reports.c.build_date)

    selects = [truncateddate.label('build_date'),
               crashcount.label('count'),
               frequency.label('frequency'),
               totalcount.label('total')]

    for platform in platformList:
      platform_crashcount = func.count(
        sql.case([(sql.and_(reports.c.signature == self.signature,
                            platform.condition()), 1)])
        )
      platform_totalcount = func.count(
        sql.case([(platform.condition(), 1)])
        )
      platform_frequency = sql.case([(platform_totalcount > 0,
                                      sql.cast(platform_crashcount, types.Float) / platform_totalcount)], else_=0.0)
      selects.extend((platform_crashcount.label('count_%s' % platform.id()),
                      platform_frequency.label('frequency_%s' % platform.id())))

    s = select(selects,
               group_by=[truncateddate],
               order_by=[sql.desc(truncateddate)],
               engine=create_engine())
    s.append_whereclause(reports.c.build_date != None)

    def FilterToAppend(clause):
      s.append_whereclause(clause)
      return s

    s.filter = FilterToAppend
    s = BaseLimit.filter(self, s, False)
    return s.execute()

  def query_topcrashes(self):
    total = func.count(reports.c.id)
    selects = [reports.c.signature, total]
    selects.extend(count_platforms())
    s = select(selects,
               group_by=[reports.c.signature],
               order_by=sql.desc(func.count(reports.c.id)),
               limit=100,
               engine=create_engine())
    s.append_whereclause(reports.c.signature != None)

    def FilterToAppend(clause):
      s.append_whereclause(clause)
      return s

    s.filter = FilterToAppend

    s = self.filter(s)
    return s.execute()

  def __str__(self):
    if self.date is None:
      enddate = 'now'
    else:
      enddate = self.date
      
    msg = "Results within %s %s of %s" % (self.getRange()[0], self.getRange()[1], enddate)

    if self.query is not None:
      sigtype = {'exact': 'is exactly',
                 'contains': 'contains'}[self.getQueryType()]

      sigquery = {'signature': 'the crash signature',
                  'stack': 'one of the top 10 stack frames'}[self.getQuerySearch()]
      
      msg += ", where %s %s '%s'" % (sigquery, sigtype, self.query)

    if len(self.products) > 0:
      msg += ", and the product is one of %s" % ', '.join(["'%s'" % product for product in self.products])

    if len(self.branches) > 0:
      msg += ", and the branch is one of %s" % ', '.join(["'%s'" % branch for branch in self.branches])

    if len(self.versions) > 0:
      msg += ", and the version is one of %s" % ', '.join(["'%s %s'" % (product, version) for (product, version) in self.versions])

    if len(self.platforms) > 0:
      msg += ", and the platform is one of %s" % ', '.join([str(platform) for platform in self.platforms])

    msg += '.'
    return msg

class BySignatureLimit(BaseLimit):
  def __init__(self, signature=None, **kwargs):
    BaseLimit.__init__(self, **kwargs)
    self.signature = signature

  def setFromParams(self, params):
    BaseLimit.setFromParams(self, params)

    self.signature = params.get('signature', None)

  def filter(self, q):
    q = BaseLimit.filter(self, q)
    if self.signature is not None:
      q = q.filter(reports.c.signature == self.signature)
    return q

### XXXcombine the two functions below
def getCrashesForParams(params, key):
  """
  Get a list of top crashes for a BaseLimit and a cache key.
  Returns a tuple of the topcrashers and a timestamp.
  """
  def getCrashers():
    tc = [r for r in params.query_topcrashes()]
    ts = time.time()
    return (tc, ts)

  tccache = pylons.cache.get_cache('tc_data')
  return tccache.get_value(key, createfunc=getCrashers,
                           type="memory", expiretime=60)

def getReportsForParams(params, key):
  """
  Get a list of reports for a set of params. Returns
  a tuple of the reports and a timestamp.
  """
  def getList():
    reports = [r for r in params.query_reports()]
    builds = [b for b in params.query_frequency()]
    ts = time.time()
    return (reports, builds, ts)

  # Disable caching for the moment, because it's causing memory leaks
  return getList()
  
  rcache = pylons.cache.get_cache('report_data')
  return rcache.get_value(key, createfunc=getList,
                          type="file", expiretime=60)
