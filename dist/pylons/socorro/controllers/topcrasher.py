from socorro.models import Report, reports_table, Branch, branches_table
from socorro.lib.base import BaseController
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

    end = func.now()
    start = func.now() - sql.cast('2 weeks', PGInterval)

    e = create_engine()
    tc = select([reports_table.c.signature, func.count(reports_table.c.id)],
                and_(reports_table.c.product==product,
                reports_table.c.version==version,
                reports_table.c.date.between(start,end)),
                group_by=[reports_table.c.signature], 
                order_by=desc(func.count(reports_table.c.id)), 
                limit=100, offset=0,
                engine=e).execute()

    c.tc = tc

    return render_response('topcrasher/byversion')

  def bybranch(self, branch):
    """
    The purpose of this action is to generate topcrasher reports based on
    branch.
    """

    end = func.now()
    start = func.now() - sql.cast('2 weeks', PGInterval)

    # Thanks to bsmedberg for his guidance.  Below is the SA equivalent to:
    """
    SELECT reports.signature, count(reports.id) AS count FROM branches JOIN
    reports ON branches.product = reports.product AND branches.version = reports.version 
    WHERE reports.date BETWEEN now() - CAST(%(literal)s AS INTERVAL) AND now() AND 
    branches.branch = %(branches_branch)s GROUP BY reports.signature ORDER BY count DESC
    """
    where = sql.and_(reports_table.c.date.between(start, end),
                     branches_table.c.branch==branch)

    join = branches_table. \
      join(reports_table,
           sql.and_(branches_table.c.product == reports_table.c.product,
                    branches_table.c.version == reports_table.c.version))

    c.tc = \
      sql.select([reports_table.c.signature, func.count(reports_table.c.id).label('count')],
                 where,
                 [join],
                 group_by=[reports_table.c.signature],
                 order_by=[desc('count')],
                 engine=create_engine()).execute()

    return render_response('topcrasher/bybranch')
