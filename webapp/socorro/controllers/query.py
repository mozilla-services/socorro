from socorro.models import Report, reports_table
from socorro.lib.base import BaseController
from pylons import c, session, request
from pylons.templating import render_response
import formencode
import sqlalchemy
from sqlalchemy import sql, func
from sqlalchemy.databases.postgres import PGInterval

class QueryParams(object):
  """An object representing query conditions for end-user searches."""
  def __init__(self):
    self.signature = ''
    self.signature_type = 'contains'
    self.date = ''
    self.range_value = 1
    self.range_unit = 'weeks'

  def query(self):
    q = Report.query().order_by(sql.desc(reports_table.c.date)).limit(500)
    
    if self.date is None:
      enddate = func.now()
    else:
      enddate = sql.cast(self.date, sqlalchemy.types.DateTime)
    startdate = enddate - sql.cast("%s %s" % (self.range_value, self.range_unit), PGInterval)
    q = q.filter(reports_table.c.date.between(startdate, enddate))

    if self.signature != '':
      if self.signature_type == 'contains':
        pattern = '%' + self.signature.replace('%', '%%') + '%'
        q = q.filter(reports_table.c.signature.like(pattern))
      elif request.params['signature_type'] == 'startswith':
        pattern = self.signature.replace('%', '%%') + '%'
        q = q.filter(reports_table.c.signature.like(pattern))
      else:
        q = q.filter(reports_table.c.signature == self.signature)
    return q

  def __str__(self):
    if self.date is None:
      enddate = 'now'
    else:
      enddate = self.date
      
    str = "Results within %s %s of %s" % (self.range_value, self.range_unit, enddate)

    if self.signature != '':
      sigtype = {'exact': 'is exactly',
                 'startswith': 'starts with',
                 'contains': 'contains'}[self.signature_type]
      
      str += ", where the crash signature %s '%s'" % (sigtype, self.signature)

    str += '.'
    return str

class QueryParamsValidator(formencode.FancyValidator):
  """A custom formvalidator which processes request.params into a QueryParams
  instance."""

  type_validator = formencode.validators.OneOf(['exact', 'startswith', 'contains'])
  datetime_validator = formencode.validators.Regex('^\\d{4}-\\d{2}-\\d{2}( \\d{2}:\\d{2}(:\\d{2})?)?$', strip=True)
  range_unit_validator = formencode.validators.OneOf(['hours', 'days', 'weeks', 'months'])

  def _to_python(self, value, state):
    q = QueryParams()
    q.signature = value.get('signature', '')
    q.signature_type = self.type_validator.to_python(value.get('signature_type', 'exact'))
    q.date = self.datetime_validator.to_python(value.get('date'), '')
    q.range_value = formencode.validators.Int.to_python(value.get('range_value', '1'))
    q.range_unit = self.range_unit_validator.to_python(value.get('range_unit', 'weeks'))
    return q

validator = QueryParamsValidator()

class QueryController(BaseController):
  def query(self):
    if request.params.get('do_query', '') != '':
      c.params = validator.to_python(request.params)
      c.reports = c.params.query().list()
    else:
      c.params = QueryParams()

    return render_response('query_form')
