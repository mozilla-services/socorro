# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""This is an extension to configman for Socorro.  It creates a ValueSource
object that is also a 'from_string_converter'.  It is tailored to work with
the Socorro 'application' configuration parameter.  Once configman has made
a final determination as to which application to actually run, this class
allows Configman to go to that application and fetch its preferred defaults
for the rest of options required by that application."""

from configman.converters import str_to_python_object
from configman.dotdict import DotDict


#==============================================================================
class ApplicationDefaultsProxy(object):
    """a placeholder class that will induce configman to query the application
    object for the application's preferred defaults.  """

    def __init__(self):
        self.application_defaults = DotDict()
        self.apps = self.find_all_the_apps()

    #--------------------------------------------------------------------------
    def str_to_application_class(self, an_app_key):
        """a configman compatible str_to_* converter"""
        try:
            app_class = str_to_python_object(self.apps[an_app_key])
        except KeyError:
            app_class = str_to_python_object(an_app_key)
        try:
            self.application_defaults = DotDict(
                app_class.get_application_defaults()
            )
        except AttributeError:
            # no get_application_defaults, skip this step
            pass
        return app_class

    #--------------------------------------------------------------------------
    @staticmethod
    def find_all_the_apps():
        """in the future, re-implement this as an automatic discovery service
        """
        return {
            'collector': 'socorro.collector.collector_app.CollectorApp',
            'collector2015': 'socorro.collector.collector_app.Collector2015App',
            'crashmover': 'socorro.collector.crashmover_app.CrashMoverApp',
            'setupdb': 'socorro.external.postgresql.setupdb_app.SocorroDBApp',
            'submitter': 'socorro.collector.submitter_app.SubmitterApp',
            # crontabber not yet supported in this environment
            #'crontabber': 'socorro.cron.crontabber_app.CronTabberApp',
            'middleware': 'socorro.middleware.middleware_app.MiddlewareApp',
            'processor': 'socorro.processor.processor_app.ProcessorApp',
            'fetch': 'socorro.external.fetch_app.FetchApp',
            'copy_processed':
                'socorro.collector.crashmover_app.ProcessedCrashCopierApp',
            'copy_raw_and_processed':
                'socorro.collector.crashmover_app.RawAndProcessedCopierApp',
            'reprocess_crashlist':
                'socorro.external.rabbitmq.reprocess_crashlist.ReprocessCrashlistApp',
            'purge_rmq':
            'socorro.external.rabbitmq.purge_queue_app.PurgeRabbitMQQueueApp',
            'correlations':
            'socorro.analysis.correlations.correlations_app.CorrelationsApp',
        }


can_handle = (
    ApplicationDefaultsProxy
)


#==============================================================================
class ValueSource(object):
    """This is meant to be used as both a value source and a from string
    converter.  An instance, as a value source, always returns an empty
    dictionary from its 'get_values' method.  However, if it gets used as
    a 'from string' converter, the 'get_values' behavior changes.  Just before
    the 'from string' converter returns the conversion result, this class calls
    the method 'get_application_defaults' on it and saves the result.  That
    saved result becomes the new value for 'get_values' to return.

    The end result is that an app that has a prefered set of defaults can still
    get them loaded and used even if the app was itself loaded through
    Configman.
    """

    #--------------------------------------------------------------------------
    def __init__(self, source, the_config_manager=None):
        self.source = source

    #--------------------------------------------------------------------------
    def get_values(self, config_manager, ignore_mismatches, obj_hook=DotDict):
        if isinstance(self.source.application_defaults, obj_hook):
            return self.source.application_defaults
        return obj_hook(self.source.application_defaults)
