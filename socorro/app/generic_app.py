#! /usr/bin/env python

import re
import inspect
import logging
import logging.handlers
import functools

from configman import ConfigurationManager, Namespace, RequiredConfig
from configman.converters import class_converter


#==============================================================================
class AppDetailMissingError(AttributeError):
    pass


#==============================================================================
class App(RequiredConfig):
    """The base class from which Socorro apps are based"""
    #--------------------------------------------------------------------------
    def __init__(self, config):
        self.config = config

    #--------------------------------------------------------------------------
    def main(self):  # pragma: no cover
        """derived classes must override this function with business logic"""
        raise NotImplementedError("A definition of 'main' in a derived class"
                                  "is required")


#------------------------------------------------------------------------------
def logging_required_config(app_name):
    lc = Namespace()
    lc.add_option('syslog_host',
              doc='syslog hostname',
              default='localhost')
    lc.add_option('syslog_port',
              doc='syslog port',
              default=514)
    lc.add_option('syslog_facility_string',
              doc='syslog facility string ("user", "local0", etc)',
              default='user')
    lc.add_option('syslog_line_format_string',
              doc='python logging system format for syslog entries',
              default='%s (pid {process}): '
                      '{asctime} {levelname} - {threadName} - '
                      '{message}' % app_name)
    lc.add_option('syslog_error_logging_level',
              doc='logging level for the log file (10 - DEBUG, 20 '
                  '- INFO, 30 - WARNING, 40 - ERROR, 50 - CRITICAL)',
              default=40)
    lc.add_option('stderr_line_format_string',
              doc='python logging system format for logging to stderr',
              default='{asctime} {levelname} - {threadName} - '
                      '{message}')
    lc.add_option('stderr_error_logging_level',
              doc='logging level for the logging to stderr (10 - '
                  'DEBUG, 20 - INFO, 30 - WARNING, 40 - ERROR, '
                  '50 - CRITICAL)',
              default=10)
    return lc


#------------------------------------------------------------------------------

def setup_logger(app_name, config, local_unused, args_unused):
    logger = logging.getLogger(app_name)
    logger.setLevel(logging.DEBUG)
    stderr_log = logging.StreamHandler()
    stderr_log.setLevel(config.stderr_error_logging_level)
    stderr_log_formatter = logging.Formatter(
                      _convert_format_string(config.stderr_line_format_string))
    stderr_log.setFormatter(stderr_log_formatter)
    logger.addHandler(stderr_log)

    syslog = logging.handlers.SysLogHandler(
                                        facility=config.syslog_facility_string)
    syslog.setLevel(config.syslog_error_logging_level)
    syslog_formatter = logging.Formatter(
                      _convert_format_string(config.syslog_line_format_string))
    syslog.setFormatter(syslog_formatter)
    logger.addHandler(syslog)
    return logger


def _convert_format_string(s):
    """return '%(foo)s %(bar)s' if the input is '{foo} {bar}'"""
    return re.sub('{(\w+)}', r'%(\1)s', s)


#------------------------------------------------------------------------------
# This main function will load an application object, initialize it and then
# call its 'main' function
def main(initial_app, values_source_list=None):
    if isinstance(initial_app, basestring):
        initial_app = class_converter(initial_app)

    # the only config parameter is a special one that refers to a class or
    # module that defines an application.  In order to qualify, a class must
    # have a constructor that accepts a DotDict derivative as the sole
    # input parameter.  It must also have a 'main' function that accepts no
    # parameters.  For a module to be acceptable, it must have a main
    # function that accepts a DotDict derivative as its input parameter.
    app_definition = Namespace()
    app_definition.admin = admin = Namespace()
    admin.add_option('application',
                     doc='the fully qualified module or class of the '
                         'application',
                     default=initial_app,
                     from_string_converter=class_converter
                    )
    try:
        app_name = initial_app.app_name  # this will be used as the default
                                         # b
        app_version = initial_app.app_version
        app_description = initial_app.app_description
    except AttributeError, x:
        raise AppDetailMissingError(str(x))

    app_definition.add_aggregation('logger',
                                   functools.partial(setup_logger,
                                                     app_name))

    definitions = (app_definition,
                   logging_required_config(app_name))

    config_manager = ConfigurationManager(definitions,
                                          app_name=app_name,
                                          app_version=app_version,
                                          app_description=app_description,
                                          values_source_list=values_source_list,
                                         )

    with config_manager.context() as config:
        config_manager.log_config(config.logger)

        # get the app class from configman.  Why bother since we have it aleady
        # with the 'initial_app' name?  In most cases initial_app == app,
        # it might not always be that way.  The user always has the ability
        # to specify on the command line a new app class that will override
        # 'initial_app'.
        app = config.admin.application

        if isinstance(app, type):
            # invocation of the app if the app_object was a class
            instance = app(config)
            instance.main()
        elif inspect.ismodule(app):
            # invocation of the app if the app_object was a module
            app.main(config)
        elif inspect.isfunction(app):
            # invocation of the app if the app_object was a function
            app(config)
        return 0
