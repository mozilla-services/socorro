#! /usr/bin/env python

import ConfigParser
import getopt
import os.path
import inspect

import configman as cm
import configman.converters as conv


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

    definitions = (app_definition,
                   lc.required_config(app_name))


    # create an iterable collection of value sources
    # the order is important as these will supply values for the sources
    # defined in the_definition_source. The values will be overlain in turn.
    # First the os.environ values will be applied.  Then any values from an ini
    # file parsed by getopt.  Finally any values supplied on the command line
    # will be applied.
    value_sources = (cm.ConfigFileFutureProxy,  # alias for allowing the user
                                                # to specify a config file on
                                                # the command line
                     cm.environment,  # alias for os.environ
                     cm.command_line) # alias for getopt

    # set up the manager with the definitions and values
    # it isn't necessary to provide the app_name because the
    # app_object passed in or loaded by the ConfigurationManager will alredy
    # have that information.
    config_manager = cm.ConfigurationManager(definitions,
                                             value_sources,
                                             app_name=app_name,
                                             app_version=app_version,
                                             app_description=app_description,
                                            )
    config = config_manager.config

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

if __name__ == '__main__':
    main()


import socorro.lib.config_manager as cm
import socorro.lib.logging_config as lc
import socorro.lib.util as sutil

def main(application_class):
    if isinstance(application_class, str):
        application_class = cm.class_converter(application_class)
    try:
        application_name = application_class.app_name
    except AttributeError:
        application_name = 'Socorro Unknown App'
    try:
        application_version = application_class.version
    except AttributeError:
        application_version = ''
    try:
        application_doc = application_class.doc
    except AttributeError:
        application_doc = ''
    application_main = application_class.main

    app_definition = cm.Namespace()
    app_definition.option('_application',
                          doc='the fully qualified module or '
                              'class of the application',
                          default=application_class,
                          from_string_converter=cm.class_converter
                         )
    definition_list = [ app_definition,
                        lc.required_config(application_name),
                      ]

    config_manager = cm.ConfigurationManager(definition_list,
                                        application_name=application_name,
                                        application_version=application_version,
                                        application_doc=application_doc,
                                             )
    config = config_manager.get_config()

    logger = logging.getLogger(config._application.app_name)
    logger.setLevel(logging.DEBUG)
    lc.setupLoggingHandlers(logger, config)
    config.logger = logger

    config_manager.log_config(logger)

    try:
        application_main(config)
    finally:
        logger.info("done.")

if __name__ == '__main__':
    main()
