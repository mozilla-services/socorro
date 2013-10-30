#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import re
import inspect
import logging
import logging.handlers
import functools
import signal


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
        raise NotImplementedError(
          "A definition of 'main' in a derived class is required"
        )


#------------------------------------------------------------------------------
def logging_required_config(app_name):
    lc = Namespace()
    lc.namespace('logging')
    lc.logging.add_option(
      'syslog_host',
      doc='syslog hostname',
      default='localhost'
    )
    lc.logging.add_option(
      'syslog_port',
      doc='syslog port',
      default=514
    )
    lc.logging.add_option(
      'syslog_facility_string',
      doc='syslog facility string ("user", "local0", etc)',
      default='user'
    )
    lc.logging.add_option(
      'syslog_line_format_string',
      doc='python logging system format for syslog entries',
      default='%s (pid {process}): '
              '{asctime} {levelname} - {threadName} - '
              '{message}' % app_name
    )
    lc.logging.add_option(
      'syslog_error_logging_level',
      doc='logging level for the log file (10 - DEBUG, 20 '
          '- INFO, 30 - WARNING, 40 - ERROR, 50 - CRITICAL)',
      default=40
    )
    lc.logging.add_option(
      'stderr_line_format_string',
      doc='python logging system format for logging to stderr',
      default='{asctime} {levelname} - {threadName} - '
              '{message}'
    )
    lc.logging.add_option(
      'stderr_error_logging_level',
      doc='logging level for the logging to stderr (10 - '
          'DEBUG, 20 - INFO, 30 - WARNING, 40 - ERROR, '
          '50 - CRITICAL)',
      default=10
    )
    return lc


#------------------------------------------------------------------------------
def setup_logger(app_name, config, local_unused, args_unused):
    logger = logging.getLogger(app_name)
    # if this is a restart, loggers must be removed before being recreated
    tear_down_logger(app_name)
    logger.setLevel(logging.DEBUG)
    stderr_log = logging.StreamHandler()
    stderr_log.setLevel(config.logging.stderr_error_logging_level)
    stderr_format = config.logging.stderr_line_format_string.replace(
      '{app_name}',
      app_name
    )
    stderr_log_formatter = logging.Formatter(
      _convert_format_string(stderr_format)
    )
    stderr_log.setFormatter(stderr_log_formatter)
    logger.addHandler(stderr_log)

    syslog = logging.handlers.SysLogHandler(
      facility=config.logging.syslog_facility_string
    )
    syslog.setLevel(config.logging.syslog_error_logging_level)
    syslog_format = config.logging.syslog_line_format_string.replace(
      '{app_name}',
      app_name
    )
    syslog_formatter = logging.Formatter(
      _convert_format_string(syslog_format)
    )
    syslog.setFormatter(syslog_formatter)
    logger.addHandler(syslog)
    return logger


#------------------------------------------------------------------------------
def tear_down_logger(app_name):
    logger = logging.getLogger(app_name)
    # must have a copy of the handlers list since we cannot modify the original
    # list while we're deleting items from that list
    handlers = [x for x in logger.handlers]
    for x in handlers:
        logger.removeHandler(x)

#------------------------------------------------------------------------------
def _convert_format_string(s):
    """return '%(foo)s %(bar)s' if the input is '{foo} {bar}'"""
    return re.sub('{(\w+)}', r'%(\1)s', s)


#------------------------------------------------------------------------------
restart = True
#------------------------------------------------------------------------------
def respond_to_SIGHUP(signal_number, frame, logger=None):
    """raise the KeyboardInterrupt which will cause the app to effectively
    shutdown, closing all it resources.  Then, because it sets 'restart' to
    True, the app will reread all the configuration information, rebuild all
    of its structures and resources and start running again"""
    global restart
    restart = True
    if logger:
        logger.info('detected SIGHUP')
    raise KeyboardInterrupt

#------------------------------------------------------------------------------
def main(
    initial_app,
    values_source_list=None,
    config_path=None,
    config_manager_cls=ConfigurationManager
):
    global restart
    restart = True
    while restart:
        app_exit_code = _do_main(
            initial_app,
            values_source_list,
            config_path,
            config_manager_cls
        )
    return app_exit_code

#------------------------------------------------------------------------------
# This _do_main function will load an application object, initialize it and
# then call its 'main' function
def _do_main(
    initial_app,
    values_source_list=None,
    config_path=None,
    config_manager_cls=ConfigurationManager
):
    global restart
    restart = False
    if isinstance(initial_app, basestring):
        initial_app = class_converter(initial_app)

    if config_path is None:
        default = './config'
        config_path = os.environ.get(
            'DEFAULT_SOCORRO_CONFIG_PATH',
            default
        )
        if config_path != default:
            # you tried to set it, then it must be a valid directory
            if not os.path.isdir(config_path):
                raise IOError('%s is not a valid directory' % config_path)

    # the only config parameter is a special one that refers to a class or
    # module that defines an application.  In order to qualify, a class must
    # have a constructor that accepts a DotDict derivative as the sole
    # input parameter.  It must also have a 'main' function that accepts no
    # parameters.  For a module to be acceptable, it must have a main
    # function that accepts a DotDict derivative as its input parameter.
    app_definition = Namespace()
    app_definition.add_option(
      'application',
      doc='the fully qualified module or class of the application',
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

    app_definition.add_aggregation(
      'logger',
      functools.partial(setup_logger, app_name)
    )

    definitions = (
      app_definition,
      logging_required_config(app_name)
    )

    config_manager = config_manager_cls(
      definitions,
      app_name=app_name,
      app_version=app_version,
      app_description=app_description,
      values_source_list=values_source_list,
      config_pathname=config_path
    )

    def fix_exit_code(code):
        # some apps don't return a code so you might get None
        # which isn't good enough to send to sys.exit()
        if code is None:
            return 0
        return code

    with config_manager.context() as config:
        config_manager.log_config(config.logger)

        # install the signal handler for SIGHUP to be the action defined in
        # 'respond_to_SIGHUP'
        respond_to_SIGHUP_with_logging = functools.partial(
            respond_to_SIGHUP,
            logger=config.logger
        )
        signal.signal(signal.SIGHUP, respond_to_SIGHUP_with_logging)


        # get the app class from configman.  Why bother since we have it aleady
        # with the 'initial_app' name?  In most cases initial_app == app,
        # it might not always be that way.  The user always has the ability
        # to specify on the command line a new app class that will override
        # 'initial_app'.
        app = config.application

        if isinstance(app, type):
            # invocation of the app if the app_object was a class
            instance = app(config)
            instance.config_manager = config_manager
            return_code = fix_exit_code(instance.main())
        elif inspect.ismodule(app):
            # invocation of the app if the app_object was a module
            return_code = fix_exit_code(app.main(config))
        elif inspect.isfunction(app):
            # invocation of the app if the app_object was a function
            return_code = fix_exit_code(app(config))
        config.logger.info('done.')
        return return_code

    raise NotImplementedError("The app did not have a callable main function")
