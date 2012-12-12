#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys

try:
    import config.processorconfig as configModule
except ImportError:
    import processorconfig as configModule

import socorro.lib.ConfigurationManager as configurationManager

try:
    config = configurationManager.newConfiguration(
        configurationModule=configModule,
        applicationName="Socorro Processor 2.9"
    )
except configurationManager.NotAnOptionError, x:
    print >>sys.stderr, x
    print >>sys.stderr, "for usage, try --help"
    sys.exit()

def processor2008(config):
    import sys
    import logging
    import logging.handlers

    import socorro.lib.util as sutil
    import socorro.processor.externalProcessor as processor

    logger = logging.getLogger("processor")
    logger.setLevel(logging.DEBUG)

    sutil.setupLoggingHandlers(logger, config)
    sutil.echoConfig(logger, config)

    config['logger'] = logger

    try:
        try:
            p = processor.ProcessorWithExternalBreakpad(config)
            p.start()
        except:
            sutil.reportExceptionAndContinue(logger)
    finally:
        logger.info("done.")

def processor2012(config):
    from configman.dotdict import DotDict

    # the following section is a translation of old-style configuration into
    # the new style configuration.  It lets a new style app run without leaving
    # the old configuration system.

    trans_config = DotDict()

    #--------------------------------------------------------------------------
    # destination -
    trans_config.destination = DotDict()

    # name: destination.crashstorage_class
    # doc: the destination storage class
    # converter: configman.converters.class_converter
    import socorro.external.crashstorage_base
    trans_config.destination.crashstorage_class = \
        socorro.external.crashstorage_base.PolyCrashStorage

    # name: destination.storage_classes
    # doc: a comma delimited list of storage classes
    # converter: configman.converters.class_list_converter
    import socorro.external.postgresql.crashstorage
    import socorro.external.hbase.crashstorage
    import socorro.external.elasticsearch.crashstorage
    trans_config.destination.storage_classes = '''
        socorro.external.postgresql.crashstorage.PostgreSQLCrashStorage,
        socorro.external.hbase.crashstorage.HBaseCrashStorage,
        socorro.external.elasticsearch.crashstorage.ElasticSearchCrashStorage
    '''

    #--------------------------------------------------------------------------
    # storage0 -
    trans_config.destination.storage0 = DotDict()

    # name: destination.storage0.backoff_delays
    # doc: delays in seconds between retries
    # converter: eval
    trans_config.destination.storage0.backoff_delays = [10, 30, 60, 120, 300,
                                                        300, 300, 300, 300,
                                                        300]

    # name: destination.storage0.crashstorage_class
    # doc: None
    # converter: configman.converters.class_converter
    trans_config.destination.storage0.crashstorage_class = \
        socorro.external.postgresql.crashstorage.PostgreSQLCrashStorage

    # name: destination.storage0.database_class
    # doc: the class responsible for connecting toPostgres
    # converter: configman.converters.class_converter
    import socorro.external.postgresql.connection_context
    trans_config.destination.storage0.database_class = \
        socorro.external.postgresql.connection_context.ConnectionContext

    # name: destination.storage0.database_host
    # doc: the hostname of the database
    # converter: str
    trans_config.destination.storage0.database_host = config.databaseHost

    # name: destination.storage0.database_name
    # doc: the name of the database
    # converter: str
    trans_config.destination.storage0.database_name = config.databaseName

    # name: destination.storage0.database_password
    # doc: the user's database password
    # converter: str
    trans_config.destination.storage0.database_password = \
        config.databasePassword

    # name: destination.storage0.database_port
    # doc: the port for the database
    # converter: int
    trans_config.destination.storage0.database_port = config.databasePort

    # name: destination.storage0.database_user
    # doc: the name of the user within the database
    # converter: str
    trans_config.destination.storage0.database_user = config.databaseUserName

    # name: destination.storage0.transaction_executor_class
    # doc: a class that will manage transactions
    # converter: configman.converters.class_converter
    import socorro.database.transaction_executor
    trans_config.destination.storage0.transaction_executor_class = (
        socorro.database.transaction_executor
               .TransactionExecutorWithLimitedBackoff
    )

    # name: destination.storage0.wait_log_interval
    # doc: seconds between log during retries
    # converter: int
    trans_config.destination.storage0.wait_log_interval = 5

    #--------------------------------------------------------------------------
    # storage1 -
    trans_config.destination.storage1 = DotDict()

    # name: destination.storage1.backoff_delays
    # doc: delays in seconds between retries
    # converter: eval
    trans_config.destination.storage1.backoff_delays = [10, 30, 60, 120, 300,
                                                        300, 300, 300, 300,
                                                        300]

    # name: destination.storage1.crashstorage_class
    # doc: None
    # converter: configman.converters.class_converter
    trans_config.destination.storage1.crashstorage_class = \
        socorro.external.hbase.crashstorage.HBaseCrashStorage

    # name: destination.storage1.forbidden_keys
    # doc: a comma delimited list of keys banned from the processed crash in
    # HBase
    # converter: socorro.external.hbase.crashstorage.<lambda>
    trans_config.destination.storage1.forbidden_keys = \
        ['email', 'url', 'user_id', 'exploitability']

    # name: destination.storage1.hbase_host
    # doc: Host to HBase server
    # converter: str
    trans_config.destination.storage1.hbase_host = config.hbaseHost

    # name: destination.storage1.hbase_port
    # doc: Port to HBase server
    # converter: int
    trans_config.destination.storage1.hbase_port = config.hbasePort

    # name: destination.storage1.hbase_timeout
    # doc: timeout in milliseconds for an HBase connection
    # converter: int
    trans_config.destination.storage1.hbase_timeout = config.hbaseTimeout

    # name: destination.storage1.number_of_retries
    # doc: Max. number of retries when fetching from hbaseClient
    # converter: int
    trans_config.destination.storage1.number_of_retries = 2

    # name: destination.storage1.transaction_executor_class
    # doc: a class that will execute transactions
    # converter: configman.converters.class_converter
    trans_config.destination.storage1.transaction_executor_class = (
        socorro.database.transaction_executor
               .TransactionExecutorWithLimitedBackoff
    )

    # name: destination.storage1.wait_log_interval
    # doc: seconds between log during retries
    # converter: int
    trans_config.destination.storage1.wait_log_interval = 5

    # name: destination.storage1.temporary_file_system_storage_path
    # doc: a local filesystem path dumps can be temporarily written
    #      for processing
    # converter: str
    trans_config.destination.storage1.temporary_file_system_storage_path = \
        config.temporaryFileSystemStoragePath

    # name: destination.storage1.dump_file_suffix
    # doc: the suffix used to identify a dump file (for use in temp files)
    # converter: str
    trans_config.destination.storage1.dump_file_suffix = \
        config.dumpFileSuffix

    #--------------------------------------------------------------------------
    # storage2 -
    trans_config.destination.storage2 = DotDict()

    # name: destination.storage2.crashstorage_class
    # doc: None
    # converter: configman.converters.class_converter
    trans_config.destination.storage2.crashstorage_class = \
        socorro.external.elasticsearch.crashstorage.ElasticSearchCrashStorage

    # name: destination.storage2.submission_url
    # doc: a url to submit crash_ids for Elastic Search (use %s in place of the
    #      crash_id) (leave blank to disable)
    # converter: str
    trans_config.destination.storage2.submission_url = \
        config.elasticSearchOoidSubmissionUrl

    # name: destination.storage2.timeout
    # doc: how long to wait in seconds for confirmation of a submission
    # converter: int
    trans_config.destination.storage2.timeout = 2

    # name: destination.storage2.transaction_executor_class
    # doc: a class that will manage transactions
    # converter: configman.converters.class_converter
    import socorro.database.transaction_executor
    trans_config.destination.storage2.transaction_executor_class = \
        socorro.database.transaction_executor.TransactionExecutor

    #--------------------------------------------------------------------------
    # logging -
    trans_config.logging = DotDict()

    # name: logging.stderr_error_logging_level
    # doc: logging level for the logging to stderr (10 - DEBUG, 20 - INFO, 30 -
    #      WARNING, 40 - ERROR, 50 - CRITICAL)
    # converter: int
    trans_config.logging.stderr_error_logging_level = \
        config.stderrErrorLoggingLevel

    # name: logging.stderr_line_format_string
    # doc: python logging system format for logging to stderr
    # converter: str
    trans_config.logging.stderr_line_format_string = \
        config.stderrLineFormatString

    # name: logging.syslog_error_logging_level
    # doc: logging level for the log file (10 - DEBUG, 20 - INFO, 30 - WARNING,
    #      40 - ERROR, 50 - CRITICAL)
    # converter: int
    trans_config.logging.syslog_error_logging_level = \
        config.syslogErrorLoggingLevel

    # name: logging.syslog_facility_string
    # doc: syslog facility string ("user", "local0", etc)
    # converter: str
    trans_config.logging.syslog_facility_string = config.syslogFacilityString

    # name: logging.syslog_host
    # doc: syslog hostname
    # converter: str
    trans_config.logging.syslog_host = config.syslogHost

    # name: logging.syslog_line_format_string
    # doc: python logging system format for syslog entries
    # converter: str
    # NOTE: the old and new systems use very differet formats for
    # the logging template.  In the entire history of the project
    # the template has not changed.  Rather than spending the effort
    # to translate the format, this hard coding will do.  Since this
    # chimera processor is  transintional, this will go away in the
    # not too distant future.
    trans_config.logging.syslog_line_format_string = \
        '{app_name} (pid {process}): ' \
        '{asctime} {levelname} - {threadName} - ' \
        '{message}'

    # name: logging.syslog_port
    # doc: syslog port
    # converter: int
    trans_config.logging.syslog_port = config.syslogPort

    #--------------------------------------------------------------------------
    # new_crash_source -
    trans_config.new_crash_source = DotDict()

    # name: new_crash_source.backoff_delays
    # doc: delays in seconds between retries
    # converter: eval
    trans_config.new_crash_source.backoff_delays = [10, 30, 60, 120, 300, 300,
                                                    300, 300, 300, 300]

    # name: new_crash_source.batchJobLimit
    # doc: the number of jobs to pull in a time
    # converter: int
    trans_config.new_crash_source.batchJobLimit = config.batchJobLimit

    # name: new_crash_source.database_class
    # doc: the class of the database
    # converter: configman.converters.class_converter
    trans_config.new_crash_source.database_class = \
        socorro.external.postgresql.connection_context.ConnectionContext

    # name: new_crash_source.database_host
    # doc: the hostname of the database
    # converter: str
    trans_config.new_crash_source.database_host = config.databaseHost

    # name: new_crash_source.database_name
    # doc: the name of the database
    # converter: str
    trans_config.new_crash_source.database_name = config.databaseName

    # name: new_crash_source.database_password
    # doc: the user's database password
    # converter: str
    trans_config.new_crash_source.database_password = config.databasePassword

    # name: new_crash_source.database_port
    # doc: the port for the database
    # converter: int
    trans_config.new_crash_source.database_port = config.databasePort

    # name: new_crash_source.database_user
    # doc: the name of the user within the database
    # converter: str
    trans_config.new_crash_source.database_user = config.databaseUserName

    # name: new_crash_source.new_crash_source_class
    # doc: an iterable that will stream crash_ids needing processing
    # converter: configman.converters.class_converter
    import socorro.processor.legacy_new_crash_source
    trans_config.new_crash_source.new_crash_source_class = \
        socorro.processor.legacy_new_crash_source.LegacyNewCrashSource

    # name: new_crash_source.transaction_executor_class
    # doc: a class that will manage transactions
    # converter: configman.converters.class_converter
    trans_config.new_crash_source.transaction_executor_class = (
        socorro.database.transaction_executor
               .TransactionExecutorWithLimitedBackoff
    )

    # name: new_crash_source.wait_log_interval
    # doc: seconds between log during retries
    # converter: int
    trans_config.new_crash_source.wait_log_interval = 5

    #--------------------------------------------------------------------------
    # processor -
    trans_config.processor = DotDict()

    # name: processor.backoff_delays
    # doc: delays in seconds between retries
    # converter: eval
    trans_config.processor.backoff_delays = [10, 30, 60, 120, 300, 300, 300,
                                             300, 300, 300]

    # name: processor.collect_addon
    # doc: boolean indictating if information about add-ons should be collected
    # converter: configman.converters.boolean_converter
    trans_config.processor.collect_addon = config.collectAddon

    # name: processor.collect_crash_process
    # doc: boolean indictating if information about process type should be
    #      collected
    # converter: configman.converters.boolean_converter
    trans_config.processor.collect_crash_process = config.collectCrashProcess

    # name: processor.crashing_thread_frame_threshold
    # doc: the number of frames to keep in the raw dump for the crashing thread
    # converter: int
    trans_config.processor.crashing_thread_frame_threshold = \
        config.crashingThreadFrameThreshold

    # name: processor.crashing_thread_tail_frame_threshold
    # doc: the number of frames to keep in the raw dump at the tail of the
    #      frame
    #      list
    # converter: int
    trans_config.processor.crashing_thread_tail_frame_threshold = \
        config.crashingThreadTailFrameThreshold

    # name: processor.database_class
    # doc: the class of the database
    # converter: configman.converters.class_converter
    trans_config.processor.database_class = \
        socorro.external.postgresql.connection_context.ConnectionContext

    # name: processor.database_host
    # doc: the hostname of the database
    # converter: str
    trans_config.processor.database_host = config.databaseHost

    # name: processor.database_name
    # doc: the name of the database
    # converter: str
    trans_config.processor.database_name = config.databaseName

    # name: processor.database_password
    # doc: the user's database password
    # converter: str
    trans_config.processor.database_password = config.databasePassword

    # name: processor.database_port
    # doc: the port for the database
    # converter: int
    trans_config.processor.database_port = config.databasePort

    # name: processor.database_user
    # doc: the name of the user within the database
    # converter: str
    trans_config.processor.database_user = config.databaseUserName

    # name: processor.known_flash_identifiers
    # doc: A subset of the known "debug identifiers" for flash versions,
    #      associated to the version
    # converter: json.loads
    trans_config.processor.known_flash_identifiers = \
        config.knownFlashIdentifiers

    # name: processor.minidump_stackwalk_pathname
    # doc: the full pathname of the extern program minidump_stackwalk (quote
    #      path with embedded spaces)
    # converter: str
    trans_config.processor.minidump_stackwalk_pathname = \
        config.minidump_stackwalkPathname

    # name: processor.processor_class
    # doc: the class that transforms raw crashes into processed crashes
    # converter: configman.converters.class_converter
    import socorro.processor.legacy_processor
    trans_config.processor.processor_class = \
        socorro.processor.legacy_processor.LegacyCrashProcessor

    # name: processor.processor_symbols_pathname_list
    # doc: comma or space separated list of symbol files for minidump_stackwalk
    #      (quote paths with embedded spaces)
    # converter: socorro.processor.legacy_processor.create_symbol_path_str
    trans_config.processor.processor_symbols_pathname_list = \
        config.processorSymbolsPathnameList

    # name: processor.stackwalk_command_line
    # doc: the template for the command to invoke minidump_stackwalk
    # converter: str
    trans_config.processor.stackwalk_command_line = \
        config.stackwalkCommandLine.replace(
        'minidump_stackwalkPathname',
        'minidump_stackwalk_pathname'
    ).replace(
        'processorSymbolsPathnameList',
        'processor_symbols_pathname_list'
    )

    # name: exploitability_tool_command_line
    # doc: the template for the command to invoke the exploitability tool
    # converter: str
    trans_config.processor.exploitability_tool_command_line = \
        config.exploitability_tool_command_line

    # name: exploitability_tool_pathname
    # doc: the full pathname of the extern program exploitability tool
    #      (quote path with embedded spaces)
    # converter: str
    trans_config.processor.exploitability_tool_pathname = \
        config.exploitability_tool_pathname

    # name: processor.symbol_cache_path
    # doc: the path where the symbol cache is found (quote path with embedded
    #      spaces)
    # converter: str
    trans_config.processor.symbol_cache_path = config.symbolCachePath

    # name: processor.transaction_executor_class
    # doc: a class that will manage transactions
    # converter: configman.converters.class_converter
    trans_config.processor.transaction_executor_class = (
        socorro.database.transaction_executor
               .TransactionExecutorWithLimitedBackoff
    )

    # name: processor.wait_log_interval
    # doc: seconds between log during retries
    # converter: int
    trans_config.processor.wait_log_interval = 5

    #--------------------------------------------------------------------------
    # c_signature -
    trans_config.processor.c_signature = DotDict()

    # name: processor.c_signature.c_signature_tool_class
    # doc: the class that can generate a C signature
    # converter: configman.converters.class_converter
    import socorro.processor.signature_utilities
    trans_config.processor.c_signature.c_signature_tool_class = \
        socorro.processor.signature_utilities.CSignatureTool

    # name: processor.c_signature.irrelevant_signature_re
    # doc: a regular expression matching frame signatures that should be
    #      ignored when generating an overall signature
    # converter: str
    trans_config.processor.c_signature.irrelevant_signature_re = \
        config.irrelevantSignatureRegEx

    # name: processor.c_signature.prefix_signature_re
    # doc: a regular expression matching frame signatures that should always be
    #      coupled with the following frame signature when generating an
    #      overall signature
    # converter: str
    trans_config.processor.c_signature.prefix_signature_re = \
        config.prefixSignatureRegEx

    # name: processor.c_signature.signature_sentinels
    # doc: a list of frame signatures that should always be considered top of
    #      the stack if present in the stack
    # converter: eval
    trans_config.processor.c_signature.signature_sentinels = \
        config.signatureSentinels

    # name: processor.c_signature.signatures_with_line_numbers_re
    # doc: any signatures that match this list should be combined with their
    #      associated source code line numbers
    # converter: str
    trans_config.processor.c_signature.signatures_with_line_numbers_re = \
        config.signaturesWithLineNumbersRegEx

    #--------------------------------------------------------------------------
    # java_signature -
    trans_config.processor.java_signature = DotDict()

    # name: processor.java_signature.java_signature_tool_class
    # doc: the class that can generate a Java signature
    # converter: configman.converters.class_converter
    trans_config.processor.java_signature.java_signature_tool_class = \
        socorro.processor.signature_utilities.JavaSignatureTool

    #--------------------------------------------------------------------------
    # producer_consumer -
    trans_config.producer_consumer = DotDict()

    # name: producer_consumer.idle_delay
    # doc: the delay in seconds if no job is found
    # converter: int
    trans_config.producer_consumer.idle_delay = \
        config.processorLoopTime.seconds

    # name: producer_consumer.maximum_queue_size
    # doc: the maximum size of the internal queue
    # converter: int
    trans_config.producer_consumer.maximum_queue_size = \
        config.numberOfThreads * 2

    # name: producer_consumer.number_of_threads
    # doc: the number of threads
    # converter: int
    trans_config.producer_consumer.number_of_threads = config.numberOfThreads

    # name: producer_consumer.producer_consumer_class
    # doc: the class implements a threaded producer consumer queue
    # converter: configman.converters.class_converter
    import socorro.lib.threaded_task_manager
    trans_config.producer_consumer.producer_consumer_class = \
        socorro.lib.threaded_task_manager.ThreadedTaskManager

    #--------------------------------------------------------------------------
    # registrar -
    trans_config.registrar = DotDict()

    # name: registrar.backoff_delays
    # doc: delays in seconds between retries
    # converter: eval
    trans_config.registrar.backoff_delays = [10, 30, 60, 120, 300, 300, 300,
                                             300, 300, 300]

    # name: registrar.check_in_frequency
    # doc: how often the processor is required to reregister (hh:mm:ss)
    # converter: configman.converters.timedelta_converter
    trans_config.registrar.check_in_frequency = \
        config.processorCheckInFrequency

    # name: registrar.database
    # doc: the class of the registrar's database
    # converter: configman.converters.class_converter
    trans_config.registrar.database = \
        socorro.external.postgresql.connection_context.ConnectionContext

    # name: registrar.database_host
    # doc: the hostname of the database
    # converter: str
    trans_config.registrar.database_host = config.databaseHost

    # name: registrar.database_name
    # doc: the name of the database
    # converter: str
    trans_config.registrar.database_name = config.databaseName

    # name: registrar.database_password
    # doc: the user's database password
    # converter: str
    trans_config.registrar.database_password = config.databasePassword

    # name: registrar.database_port
    # doc: the port for the database
    # converter: int
    trans_config.registrar.database_port = config.databasePort

    # name: registrar.database_user
    # doc: the name of the user within the database
    # converter: str
    trans_config.registrar.database_user = config.databaseUserName

    # name: registrar.processor_id
    # doc: the id number for the processor (must already exist) (0 for create
    #      new Id, "auto" for autodetection, "host" for same host)
    # converter: str
    trans_config.registrar.processor_id = config.processorId

    # name: registrar.registrar_class
    # doc: the class that registers and tracks processors
    # converter: configman.converters.class_converter
    import socorro.processor.registration_client
    trans_config.registrar.registrar_class = \
        socorro.processor.registration_client.ProcessorAppRegistrationClient

    # name: registrar.transaction_executor_class
    # doc: a class that will manage transactions
    # converter: configman.converters.class_converter
    trans_config.registrar.transaction_executor_class = (
        socorro.database.transaction_executor
               .TransactionExecutorWithLimitedBackoff
    )

    # name: registrar.wait_log_interval
    # doc: seconds between log during retries
    # converter: int
    trans_config.registrar.wait_log_interval = 5

    #--------------------------------------------------------------------------
    # source -
    trans_config.source = DotDict()

    # name: source.backoff_delays
    # doc: delays in seconds between retries
    # converter: eval
    trans_config.source.backoff_delays = [10, 30, 60, 120, 300, 300, 300, 300,
                                          300, 300]

    # name: source.crashstorage_class
    # doc: the source storage class
    # converter: configman.converters.class_converter
    trans_config.source.crashstorage_class = \
        socorro.external.hbase.crashstorage.HBaseCrashStorage

    # name: source.forbidden_keys
    # doc: a comma delimited list of keys banned from the processed crash in
    #      HBase
    # converter: socorro.external.hbase.crashstorage.<lambda>
    trans_config.source.forbidden_keys = \
        ['email', 'url', 'user_id', 'exploitability']
    # name: source.hbase_host
    # doc: Host to HBase server
    # converter: str
    trans_config.source.hbase_host = config.hbaseHost

    # name: source.hbase_port
    # doc: Port to HBase server
    # converter: int
    trans_config.source.hbase_port = config.hbasePort

    # name: source.hbase_timeout
    # doc: timeout in milliseconds for an HBase connection
    # converter: int
    trans_config.source.hbase_timeout = config.hbaseTimeout

    # name: source.number_of_retries
    # doc: Max. number of retries when fetching from hbaseClient
    # converter: int
    trans_config.source.number_of_retries = 2

    # name: source.transaction_executor_class
    # doc: a class that will execute transactions
    # converter: configman.converters.class_converter
    trans_config.source.transaction_executor_class = (
        socorro.database.transaction_executor
               .TransactionExecutorWithLimitedBackoff
        )

    # name: source.wait_log_interval
    # doc: seconds between log during retries
    # converter: int
    trans_config.source.wait_log_interval = 5

    # name: destination.storage1.temporary_file_system_storage_path
    # doc: a local filesystem path dumps can be temporarily written
    #      for processing
    # converter: str
    trans_config.source.temporary_file_system_storage_path = \
        config.temporaryFileSystemStoragePath

    # name: destination.storage1.dump_file_suffix
    # doc: the suffix used to identify a dump file (for use in temp files)
    # converter: str
    trans_config.source.dump_file_suffix = config.dumpFileSuffix

    #--------------------------------------------------------------------------

    from socorro.app.generic_app import main
    from socorro.processor.processor_app import ProcessorApp

    main(ProcessorApp, [trans_config])

#==============================================================================

if config.processor_implementation == 2008:
    processor2008(config)
else:
    processor2012(config)

