#!/usr/bin/env python
"""run the 'update_reports_clean' stored procedure"""

from socorro.database.dbtransaction import DBTransactionApp

from datetime import datetime
from datetime import timedelta

#==============================================================================
class ReportsCleanApp(StoredProcedureApp):
    #--------------------------------------------------------------------------
    # configman app definition section
    app_name = 'reports_clean'
    app_version = '2.0'
    app_description = __doc__

    #--------------------------------------------------------------------------
    # configman parameter definition section
    required_config = cm.Namespace()
    required_config.add_option(
      name='hours',
      default=2,
      doc='the number of hours into the past',
    )

    #--------------------------------------------------------------------------
    stored_procedure_name = 'update_reports_clean'

    #--------------------------------------------------------------------------
    def stored_procedure_parameters(self):
        return (datetime.now() - timedelta(hours=self.config.hours),)

#------------------------------------------------------------------------------
if __name__ == "__main__":
    import socorro.app.generic_app as ga
    sys.exit(ga.main(ReportsCleanApp))
