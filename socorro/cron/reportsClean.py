#!/usr/bin/env python
"""run the 'update_reports_clean' stored procedure"""

from socorro.database.dbtransaction import DBTransactionApp

from datetime import datetime
from datetime import timedelta

class ReportsCleanApp(DBTransactionApp):
    app_name = 'reports_clean'
    app_version = '2.0'
    app_description = __doc__

    def main(self):
        startTime = datetime.now() - timedelta(hours=2)
        with self.config.dbtransaction() as transaction:
            cursor = transaction.cursor()
            cursor.callproc('update_reports_clean', [startTime])
            connection.commit()

if __name__ == "__main__":
    import socorro.app.generic_app as ga
    sys.exit(ga.main(ReportsCleanApp))
