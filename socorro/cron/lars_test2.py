#!/usr/bin/env python
import configman.config_manager as config_man
import socorro.database.dbtransaction as dbt

class MyApp(dbt.DBTransactionApp):

    app_name = 'MyApp'
    app_version = '0.1'
    app_description = 'just a test'

    required_config = config_man.Namespace()
    required_config.add_option('hello',
                               default='world')

    def main(self):
        print self.config.hello

# if you'd rather invoke the app directly with its source file, this will
# allow it.
if __name__ == "__main__":
    import socorro.app.generic_app as ga
    ga.main(MyApp)
