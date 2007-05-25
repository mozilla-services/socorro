from socorro.models import Branch
from socorro.lib.base import BaseController
from socorro.lib.queryparams import QueryLimit
from pylons import c, session, request
from pylons.templating import render_response
from pylons.database import create_engine

class QueryController(BaseController):
  def query(self):
    c.params = QueryLimit()

    if request.params.get('do_query', None):
      c.params.setFromParams(request.params)
      c.reports = c.params.query().list()

    c.products = Branch.getProducts()
    c.branches = Branch.getBranches()
    c.prodversions = Branch.getProductVersions()

    return render_response('query_form')
