from socorro.lib.base import *
from socorro.models import Branch, branches_table, Report, reports_table
from authkit.permissions import RemoteUser
from authkit import authorize
from sqlalchemy import sql, func

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

    # I want to run the following query. I don't know how to construct
    # it and run it against the current session in this
    # context. Please help...

    # SELECT report.product, report.version, count(*)
    # FROM reports OUTER JOIN branches
    #   ON reports.product = branches.product AND
    #      reports.version = branches.version
    # WHERE branches.branch IS NULL
    # GROUP BY reports.product, reports.version

    return render_response('branch_maintenance')

# wrap the controller in authkit protection
AdminController = authorize.middleware(AdminController(), RemoteUser())
