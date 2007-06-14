from socorro.models import Report, reports_table, Branch, branches_table
from socorro.models import getCachedBranchData
from socorro.lib.base import BaseController
from socorro.lib.queryparams import BaseLimit, getCrashesForParams
from socorro.lib.http_cache import responseForKey
from pylons.database import create_engine
from pylons import c, session, request
from pylons.templating import render_response, render
import pylons
import formencode
import re

class TopcrasherController(BaseController):
  """
  The purpose of this controller is to manage incoming Topcrasher report
  requests. Users can request a report by product/version or by product/branch,
  but by default we'll just show everyone a list of what reports are currently
  available.
  """

  def index(self):
    """
    Displays an index of available products, their branches and versions so a
    user can choose which report they want to see.
    """
    (c.products, c.branches, c.product_versions) = getCachedBranchData()
    resp = render_response('topcrasher/index')
    del c.products, c.branches, c.product_versions
    return resp

  def byversion(self, product, version):
    """
    The purpose of this action is to generate topcrasher reports based on
    product and version.
    """
    c.params = BaseLimit(versions=[(product, version)], range=(2, 'weeks'))
    (c.tc, ts) = getCrashesForParams(c.params,"v_%s%s" % (product, version))
    etag = "%s%s%s" % (product, version, ts)
    resp = responseForKey(etag)
    resp.write(render('topcrasher/byversion'))
    del c.params, c.tc
    return resp

  def bybranch(self, branch):
    """
    The purpose of this action is to generate topcrasher reports based on
    branch.
    """
    c.params = BaseLimit(branches=[branch], range=(2, 'weeks'))
    (c.tc, ts) = getCrashesForParams(c.params, "branch_" + branch)
    etag = "%s%s" % (branch, ts)
    resp = responseForKey(etag)
    resp.write(render('topcrasher/bybranch'))
    del c.params, c.tc
    return resp
