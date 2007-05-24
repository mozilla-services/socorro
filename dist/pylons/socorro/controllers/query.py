from socorro.models import Branch
from socorro.lib.base import BaseController
from socorro.lib.queryparams import QueryParamsValidator, QueryParams
from pylons import c, session, request
from pylons.templating import render_response

validator = QueryParamsValidator()

class QueryController(BaseController):
  def query(self):
    if request.params.get('do_query', '') != '':
      c.params = validator.to_python(request.params)
      c.reports = c.params.query().list()
    else:
      c.params = QueryParams()

    c.products = Branch.getProducts()
    c.branches = Branch.getBranches()
    c.prodversions = Branch.getProductVersions()

    return render_response('query_form')
