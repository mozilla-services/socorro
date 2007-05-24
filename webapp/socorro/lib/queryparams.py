from socorro.models import Report, Branch, Frame
import formencode
import sqlalchemy
from sqlalchemy import sql, func, select, types
from sqlalchemy.databases.postgres import PGInterval
import re
from pylons import h

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
    ['hours', 'days', 'weeks', 'months']
  )
  version_validator = ListValidator(ProductVersionValidator())
  stringlist_validator = ListValidator(formencode.validators.String(strip=True))

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
      self.range = (formencode.validators.Int.to_python(params.get('range_value')),
                    self.range_unit_validator.to_python(params.get('range_unit')))
    for products in params.getall('product'):
      self.products.extend(self.stringlist_validator.to_python(products))

    for branches in params.getall('branch'):
      self.branches.extend(self.stringlist_validator.to_python(branches))

    for versions in params.getall('version'):
      self.versions.extend(self.version_validator.to_python(versions))

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

class QueryLimit(BaseLimit):
  query_validator = formencode.validators.OneOf(['signature', 'stack'])
  type_validator = formencode.validators.OneOf(['exact', 'contains'])
  
  """An object representing query conditions for end-user searches."""
  def __init__(self, signature=None, signature_search=None,
               signature_type=None, **kwargs):
    BaseLimit.__init__(self, **kwargs)
    self.signature = signature
    self.signature_search = signature_search
    self.signature_type = signature_type

  def setFromParams(self, params):
    BaseLimit.setFromParams(self, params)

    self.signature = params.get('signature', None)
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

  def query(self):
    q = Report.query().order_by(sql.desc(Report.c.date)).limit(500)
    return self.filter(q)

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
