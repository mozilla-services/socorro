#! /usr/bin/env python

import ConfigParser
import getopt
import os.path
import inspect
import logging
import logging.handlers
import functools

import configman as cm
import configman.converters as conv

def logging_required_config(app_name):
    lc = cm.Namespace()
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
              default='%s (pid %%(process)d): '
                      '%%(asctime)s %%(levelname)s - %%(threadName)s - '
                      '%%(message)s' % app_name)
    lc.add_option('syslog_error_logging_level',
              doc='logging level for the log file (10 - DEBUG, 20 '
                  '- INFO, 30 - WARNING, 40 - ERROR, 50 - CRITICAL)',
              default=40)
    lc.add_option('stderr_line_format_string',
              doc='python logging system format for logging to stderr',
              default='%(asctime)s %(levelname)s - %(threadName)s - '
                      '%(message)s')
    lc.add_option('stderr_error_logging_level',
              doc='logging level for the logging to stderr (10 - '
                  'DEBUG, 20 - INFO, 30 - WARNING, 40 - ERROR, '
                  '50 - CRITICAL)',
              default=10)
    return lc


def setup_logger(app_name, config, local_unused, args_unused):
    logger = logging.getLogger(app_name)
    logger.setLevel(logging.DEBUG)
    stderr_log = logging.StreamHandler()
    stderr_log.setLevel(config.stderr_error_logging_level)
    stderr_log_formatter = logging.Formatter(config.stderr_line_format_string)
    stderr_log.setFormatter(stderr_log_formatter)
    logger.addHandler(stderr_log)

    syslog = logging.handlers.SysLogHandler(
                                        facility=config.syslog_facility_string)
    syslog.setLevel(config.syslog_error_logging_level)
    syslog_formatter = logging.Formatter(config.syslog_line_format_string)
    syslog.setFormatter(syslog_formatter)
    logger.addHandler(syslog)
    return logger

# This main function will load an application object, initialize it and then
# call its 'main' function
def main(app_object=None):
    if isinstance(app_object, basestring):
        app_object = conv.class_converter(app_object)

    # the only config parameter is a special one that refers to a class or
    # module that defines an application.  In order to qualify, a class must
    # have a constructor that accepts a DotDict derivative as the sole
    # input parameter.  It must also have a 'main' function that accepts no
    # parameters.  For a module to be acceptable, it must have a main
    # function that accepts a DotDict derivative as its input parameter.
    app_definition = cm.Namespace()
    app_definition.admin = admin = cm.Namespace()
    admin.add_option('application',
                     doc='the fully qualified module or class of the '
                         'application',
                     default=app_object,
                     from_string_converter=conv.class_converter
                    )
    app_name = getattr(app_object, 'app_name', 'unknown')
    app_version = getattr(app_object, 'app_version', '0.0')
    app_description = getattr(app_object, 'app_description', 'no idea')
    app_definition.add_aggregation('logger',
                                   functools.partial(setup_logger,
                                                     app_name))

    definitions = (app_definition,
                   logging_required_config(app_name))

    # set up the manager with the definitions and values
    # it isn't necessary to provide the app_name because the
    # app_object passed in or loaded by the ConfigurationManager will alredy
    # have that information.
    config_manager = cm.ConfigurationManager(definitions,
                                             app_name=app_name,
                                             app_version=app_version,
                                             app_description=app_description,
                                            )

    with config_manager.context() as config:
        config_manager.log_config(config.logger)

        app_object = config.admin.application

        if isinstance(app_object, type):
            # invocation of the app if the app_object was a class
            instance = app_object(config)
            instance.main()
        elif inspect.ismodule(app_object):
            # invocation of the app if the app_object was a module
            app_object.main(config)
        elif inspect.isfunction(app_object):
            # invocation of the app if the app_object was a function
            app_object(config)
        return 0

if __name__ == '__main__':
    main()

