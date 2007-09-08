from socorro.models import getCachedBranchData
from socorro.lib.base import BaseController, h
from socorro.lib.queryparams import BaseLimit
from socorro.lib.http_cache import responseForKey
from pylons import c, session, request
from pylons.templating import render
from pylons.database import create_engine

class QueryController(BaseController):

  def query(self):    
    c.params = BaseLimit()

    (c.products, c.branches, c.prodversions) = getCachedBranchData()

    # make an etag key
    def makeKey(forms):
      k = ""
      for f in forms:
        k += "".join([v for (v,) in f])
      return "%s%s_query" % (request.environ["QUERY_STRING"],k)
    
    key = makeKey([c.products, c.branches,
                   ["%s%s" % (p,v) for (p,v) in c.productsversions]])
    
    if request.params.get('do_query', None):
      c.params.setFromParams(request.params)
      c.reports = c.params.query_topcrashes()
      if c.reports.rowcount == 1:
        h.redirect_to('/report/list', signature=c.reports.fetchone().signature,
                      **c.params.getURLDict())

    resp = responseForKey(key)
    resp.write(render('query_form'))
    return resp
