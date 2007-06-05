from socorro.models import Report, reports_table, Branch, branches_table
from socorro.lib.base import BaseController
from socorro.lib.queryparams import BaseLimit
from pylons.database import create_engine
from pylons import c, session, request
from pylons.templating import render_response
import formencode
import sqlalchemy
from sqlalchemy import sql, func, select, desc, and_
from sqlalchemy.databases.postgres import PGInterval
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
  
    c.products = Branch.getProducts()
    c.branches = Branch.getBranches()
    c.product_versions = Branch.getProductVersions()

    return render_response('topcrasher/index')

  def byversion(self, product, version):
    """
    The purpose of this action is to generate topcrasher reports based on
    product and version.
    """

    c.params = BaseLimit(versions=[(product, version)],
                             range=(2, 'weeks'))
    c.tc = c.params.query_topcrashes()

    return render_response('topcrasher/byversion')

  def bybranch(self, branch):
    """
    The purpose of this action is to generate topcrasher reports based on
    branch.
    """

    c.params = BaseLimit(branches=[branch],
                             range=(2, 'weeks'))
    c.tc = c.params.query_topcrashes()

    return render_response('topcrasher/bybranch')
