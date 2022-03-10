#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""This module defines the class hierarchy for all Socorro applications.

The base of the hierarchy is "SocorroApp" which defines the interface and some
of the base methods.

Derived from the base "SocorroApp" is the "App" class.  This class adds logging
configuration requirements to the application.  App is the class from which
all the Socorro Apps derive.

"""

import logging
import logging.config
import logging.handlers
import os
import socket
import sys

from configman import (
    ConfigurationManager,
    Namespace,
    RequiredConfig,
    ConfigFileFutureProxy,
    environment,
    command_line,
)
from configman.converters import (
    py_obj_to_str,
    str_to_boolean,
    str_to_list,
    str_to_python_object,
)
import markus
import sentry_sdk

from socorro.lib.revision_data import get_version, get_version_name


def cls_to_pypath(cls):
    """when a class is defined within the module that is being executed as
    main, the module name will be specified as '__main__' even though the
    module actually had its own real name.  This ends up being very confusing
    to Configman as it tries to refer to a class by its proper module name.
    This function will convert a class into its properly qualified actual
    pathname."""
    if cls.__module__ == "__main__":
        module_path = sys.modules["__main__"].__file__[:-3]
        module_name = ""
        for a_python_path in sys.path:
            tentative_pathname = module_path.replace(a_python_path, "")
            if tentative_pathname != module_path:
                module_name = tentative_pathname.replace("/", ".").strip(".")
                break
        if module_name == "":
            return py_obj_to_str(cls)
    else:
        module_name = cls.__module__
    return "%s.%s" % (module_name, cls.__name__)


class App(RequiredConfig):
    """The base class for all Socorro applications"""

    app_name = "SocorroAppBaseClass"
    app_version = "1.0"
    app_description = "base class for app system"

    #: String containing a module import path. The module is used as a
    #: source for default configuration values. If None, this makes no
    #: changes to the configuration defaults.
    config_defaults = None

    required_config = Namespace()
    required_config.add_option("host_id", doc="host id", default="")
    required_config.namespace("logging")
    required_config.logging.add_option(
        "level",
        doc="logging level: DEBUG, INFO, WARNING, ERROR, or CRITICAL",
        default="INFO",
        reference_value_from="resource.logging",
    )

    required_config.namespace("metricscfg")
    required_config.metricscfg.add_option(
        "statsd_host",
        doc="host for statsd server",
        default="localhost",
        reference_value_from="resource.metrics",
    )
    required_config.metricscfg.add_option(
        "statsd_port",
        doc="port for statsd server",
        default=8125,
        reference_value_from="resource.metrics",
    )
    required_config.metricscfg.add_option(
        "markus_backends",
        doc="comma separated list of Markus backends to use",
        default="markus.backends.datadog.DatadogMetrics",
        reference_value_from="resource.metrics",
        from_string_converter=str_to_list,
    )

    # Sentry handles reporting unhandled exceptions.
    required_config.namespace("sentry")
    required_config.sentry.add_option(
        "dsn",
        doc="DEPRECATED: set SENTRY_DSN in environment instead",
        default="",
        reference_value_from="secrets.sentry",
        secret=True,
    )
    required_config.sentry.add_option(
        "debug",
        doc="Print details of initialization and event processing (true/false)",
        reference_value_from="resource.sentry",
        from_string_converter=str_to_boolean,
        default=False,
    )

    def __init__(self, config):
        self.config = config
        # give a name to this running instance of the program.
        self.app_instance_name = self._app_instance_name()
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__name__)

    def main(self):  # pragma: no cover
        """derived classes must override this function with business logic"""
        raise NotImplementedError(
            "A definition of 'main' in a derived class is required"
        )

    def _app_instance_name(self):
        # originally, only the processors had instance names.  By putting this
        # call here, all the apps have instance names that can be used to
        # tag output that is traceble back to an app/machine/process.
        return "%s_%s_%d" % (
            self.app_name,
            os.uname()[1].replace(".", "_"),
            os.getpid(),
        )

    @classmethod
    def run(cls, config_path=None, values_source_list=None):
        # NOTE(willkg): This is a classmethod, so we need a different logger.
        mylogger = logging.getLogger(__name__ + "." + cls.__name__)
        if config_path is None:
            config_path = os.environ.get("DEFAULT_SOCORRO_CONFIG_PATH", "./config")

        if values_source_list is None:
            values_source_list = [
                # pull in any configuration file
                ConfigFileFutureProxy,
                # get values from the environment
                environment,
                # use the command line to get the final overriding values
                command_line,
            ]

        # Pull base set of defaults from the config module if it is specified
        if cls.config_defaults is not None:
            values_source_list.insert(0, cls.config_defaults)

        config_definition = cls.get_required_config()
        if "application" not in config_definition:
            # FIXME(mkelly): We used to have a SocorroWelcomeApp that defined an
            # "application" option. We no longer have that. This section should
            # get reworked possibly as part of getting rid of application
            # defaults.
            application_config = Namespace()
            application_config.add_option(
                "application",
                doc="the fully qualified classname of the app to run",
                default=cls_to_pypath(cls),
                # the following setting means this option will NOT be
                # commented out when configman generates a config file
                likely_to_be_changed=True,
                from_string_converter=str_to_python_object,
            )
            config_definition = application_config

        config_manager = ConfigurationManager(
            config_definition,
            app_name=cls.app_name,
            app_version=cls.app_version,
            app_description=cls.app_description,
            values_source_list=values_source_list,
            options_banned_from_help=[],
            config_pathname=config_path,
        )

        def fix_exit_code(code):
            # some apps don't return a code so you might get None
            # which isn't good enough to send to sys.exit()
            if code is None:
                return 0
            return code

        with config_manager.context() as config:
            setup_logging(config)
            setup_metrics(config)

            # Log revision information
            version_data = get_version() or {}
            version_items = sorted(version_data.items())
            mylogger.info(
                "version.json: {%s}",
                ", ".join(["%r: %r" % (key, val) for key, val in version_items]),
            )

            config_manager.log_config(mylogger)

            # Add version to crash reports
            version = get_version_name()
            setup_crash_reporting(config, version)

            # we finally know what app to actually run, instantiate it
            app_to_run = cls(config)
            app_to_run.config_manager = config_manager
            # whew, finally run the app that we wanted

            return_code = fix_exit_code(app_to_run.main())
            return return_code


def setup_logging(config):
    """Initialize Python logging."""
    logging_level = config.logging.level

    host_id = config.host_id or socket.gethostname()

    class AddHostID(logging.Filter):
        def filter(self, record):
            record.host_id = host_id
            return True

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {"add_hostid": {"()": AddHostID}},
        "formatters": {
            "socorroapp": {
                "format": "%(asctime)s %(levelname)s - %(name)s - %(threadName)s - %(message)s"
            },
            "mozlog": {
                "()": "dockerflow.logging.JsonLogFormatter",
                "logger_name": "socorro",
            },
        },
        "handlers": {
            "console": {"class": "logging.StreamHandler", "formatter": "socorroapp"},
            "mozlog": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "mozlog",
                "filters": ["add_hostid"],
            },
        },
    }

    if os.environ.get("LOCAL_DEV_ENV") == "True":
        # In a local development environment, we don't want to see mozlog
        # format at all, but we do want to see markus things and py.warnings.
        # So set the logging up that way.
        logging_config["loggers"] = {
            "py.warnings": {"handlers": ["console"]},
            "markus": {"handlers": ["console"], "level": logging.INFO},
            "socorro": {"handlers": ["console"], "level": logging_level},
        }

    else:
        # In a server environment, we want to use mozlog format.
        logging_config["loggers"] = {
            "socorro": {"handlers": ["mozlog"], "level": logging_level}
        }

    logging.config.dictConfig(logging_config)


def setup_metrics(config):
    """Set up Markus."""
    backends = []

    for backend in config.metricscfg.markus_backends:
        if backend == "markus.backends.statsd.StatsdMetrics":
            backends.append(
                {
                    "class": "markus.backends.statsd.StatsdMetrics",
                    "options": {
                        "statsd_host": config.metricscfg.statsd_host,
                        "statsd_port": config.metricscfg.statsd_port,
                    },
                }
            )
        elif backend == "markus.backends.datadog.DatadogMetrics":
            backends.append(
                {
                    "class": "markus.backends.datadog.DatadogMetrics",
                    "options": {
                        "statsd_host": config.metricscfg.statsd_host,
                        "statsd_port": config.metricscfg.statsd_port,
                    },
                }
            )
        elif backend == "markus.backends.logging.LoggingMetrics":
            backends.append({"class": "markus.backends.logging.LoggingMetrics"})
        else:
            raise ValueError('Invalid markus backend "%s"' % backend)

    markus.configure(backends=backends)


def setup_crash_reporting(config, version):
    """Setup Sentry crash reporting."""

    if config.sentry and config.sentry.dsn:
        sentry_dsn = config.sentry.dsn
    else:
        sentry_dsn = os.environ.get("SENTRY_DSN", "")

    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            release=version,
            debug=config.sentry.debug,
            send_default_pii=False,
        )
