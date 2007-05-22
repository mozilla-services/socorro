from socorro.lib.base import *
from socorro.models import Branch, branches_table, Report, reports_table
from authkit.permissions import RemoteUser
from authkit import authorize
from sqlalchemy import sql, func, select
from sqlalchemy.databases.postgres import PGInterval
from pylons.database import create_engine

class AdminController(BaseController):
  def index(self):
      return render_response('admin_index')

  def branches(self):
    if 'add_single' in request.params:
      b = Branch(request.params['product'],
                 request.params['version'],
                 request.params['branch'])
      b.flush()
    
    c.branches = Branch.select(order_by=[branches_table.c.product, branches_table.c.version])

    enddate = func.now()
    startdate = enddate - sql.cast('1 week', PGInterval)
    whereclause = sql.and_(branches_table.c.branch == None,
                           reports_table.c.date.between(startdate, enddate),
                           reports_table.c.product != None,
                           reports_table.c.version != None)
    joined = reports_table.outerjoin(
      branches_table,
      sql.and_(reports_table.c.product == branches_table.c.product,
               reports_table.c.version == branches_table.c.version)
    )

    c.missing = sql.select(
      [reports_table.c.product,
       reports_table.c.version,
       func.count(reports_table.c.product).label('total')],
      whereclause,
      [joined],
      group_by=[reports_table.c.product, reports_table.c.version],
      engine=create_engine()
    ).execute()

    return render_response('branch_maintenance')

# wrap the controller in authkit protection
AdminController = authorize.middleware(AdminController(), RemoteUser())
