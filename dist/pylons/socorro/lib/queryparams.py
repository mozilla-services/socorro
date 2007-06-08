from socorro.models import Report, Branch, Frame, reports_table
import formencode
import sqlalchemy
from pylons.database import create_engine
from sqlalchemy import sql, func, select, types
from sqlalchemy.databases.postgres import PGInterval
import re
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

  @staticmethod
  def limit_range(range):
    (num, unit) = range
    num = min(num * rangeTypes[unit], maxSearchHours) / rangeTypes[unit]
    return (num, unit)

  def __init__(self, date=None, range=None,
               products=None, branches=None, versions=None):
    self.date = date
    self.range = range   # _range is a tuple (number, interval)
    self.products = products or []
    self.branches = branches or []
    self.versions = versions or []

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

  def filterByDate(self, q):
    return q.filter(Report.c.date.between(self.getSQLDateStart(),
                                          self.getSQLDateEnd()))

  def filterByProduct(self, q):
    if len(self.products):
      q = q.filter(Report.c.product.in_(*self.products))
    return q

  def filterByBranch(self, q):
    if len(self.branches):
      q = q.filter(sql.and_(Branch.c.branch.in_(*self.branches),
                            Branch.c.product == Report.c.product,
                            Branch.c.version == Report.c.version))
    return q

  def filterByVersion(self, q):
    if len(self.versions):
      q = q.filter(sql.or_(*[sql.and_(Report.c.product == product,
                                      Report.c.version == version)
                             for (product, version) in self.versions]))
    return q

  def filter(self, q):
    q = self.filterByDate(q)
    q = self.filterByProduct(q)
    q = self.filterByBranch(q)
    q = self.filterByVersion(q)
    return q

  def query_reports(self):
    q = Report.query().order_by(sql.desc(Report.c.date)).limit(500)
    return self.filter(q)

  def query_topcrashes(self):
    total = func.count(Report.c.id)
    s = select([Report.c.signature, total],
               group_by=[Report.c.signature],
               order_by=sql.desc(func.count(Report.c.id)),
               limit=100,
               engine=create_engine())

    def FilterToAppend(clause):
      s.append_whereclause(clause)
      return s

    s.filter = FilterToAppend

    s = self.filter(s)
    return s.execute()

class QueryLimit(BaseLimit):
  query_validator = formencode.validators.OneOf(['signature', 'stack'])
  type_validator = formencode.validators.OneOf(['exact', 'contains'])
  signature_validator = formencode.validators.String(strip=True, if_empty=None)
  
  """An object representing query conditions for end-user searches."""
  def __init__(self, signature=None, signature_search=None,
               signature_type=None, **kwargs):
    BaseLimit.__init__(self, **kwargs)
    self.signature = signature
    self.signature_search = signature_search
    self.signature_type = signature_type

  def setFromParams(self, params):
    BaseLimit.setFromParams(self, params)

    self.signature = self.signature_validator.to_python(params.get('signature', None))
    self.signature_search = self.query_validator.to_python(params.get('signature_search', None))
    self.signature_type = self.type_validator.to_python(params.get('signature_type', None))

  def getSignatureSearch(self):
    if self.signature_search is not None:
      return self.signature_search
    return 'signature'

  def getSignatureType(self):
    if self.signature_type is not None:
      return self.signature_type
    return 'contains'

  def filter(self, q):
    q = BaseLimit.filter(self, q)
    if self.signature is not None:
      if self.getSignatureType() == 'contains':
        pattern = '%' + self.signature.replace('%', '%%') + '%'
        if self.getSignatureSearch() == 'signature':
          q = q.filter(Report.c.signature.like(pattern))
        else:
          q = q.filter(
            sql.exists([1],
                       sql.and_(Frame.c.signature.like(pattern),
                                Frame.c.report_id == Report.c.id)))
      else:
        if self.getSignatureSearch() == 'signature':
          q = q.filter(Report.c.signature == self.signature)
        else:
          q = q.filter(
            sql.exists([1],
                       sql.and_(Frame.c.signature == self.signature,
                                Frame.c.report_id == Report.c.id)))

    return q

  def __str__(self):
    if self.date is None:
      enddate = 'now'
    else:
      enddate = self.date
      
    str = "Results within %s %s of %s" % (self.getRange()[0], self.getRange()[1], enddate)

    if self.signature != '':
      sigtype = {'exact': 'is exactly',
                 'contains': 'contains'}[self.getSignatureType()]

      sigquery = {'signature': 'the crash signature',
                  'stack': 'one of the top 10 stack frames'}[self.getSignatureSearch()]
      
      str += ", where %s %s '%s'" % (sigquery, sigtype, self.signature)

    if len(self.products) > 0:
      str += ", and the product is one of %s" % ', '.join(["'%s'" % product for product in self.products])

    if len(self.branches) > 0:
      str += ", and the branch is one of %s" % ', '.join(["'%s'" % branch for branch in self.branches])

    if len(self.versions) > 0:
      str += ", and the version is one of %s" % ', '.join(["'%s %s'" % (product, version) for (product, version) in self.versions])

    str += '.'
    return str

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
      q = q.filter(Report.c.signature == self.signature)
    return q

### XXXcombine the two functions below
def getCrashesForParams(params, key):
  """
  Get a list of top crashes for a BaseLimit and a cache key.
  Returns a tuple of the topcrashers and a timestamp.
  """
  def getCrashers():
    tc = params.query_topcrashes()
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
    ts = time.time()
    return (reports, ts)
  
  rcache = pylons.cache.get_cache('report_data')
  return rcache.get_value(key, createfunc=getList,
                          type="file", expiretime=60)
