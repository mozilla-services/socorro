"""Default configuration values used by the Socorro Processor."""
from configman.dotdict import DotDict


# Ignore non-config module members like DotDict
always_ignore_mismatches = True


# Inherit config values from FetchTransformSaveApp
from socorro.app.fetch_transform_save_config import * # NOQA


# Crash storage source
source = DotDict({
    'benchmark_tag': 'BotoBenchmarkRead',
    'crashstorage_class': 'socorro.external.crashstorage_base.BenchmarkingCrashStorage',
    'wrapped_crashstore': 'socorro.external.boto.crashstorage.BotoS3CrashStorage',
})


# Crash storage destinations
destination = DotDict({
    'crashstorage_class': 'socorro.external.crashstorage_base.PolyCrashStorage',

    # Each key in this list corresponds to a key in this dict containing
    # a crash storage config.
    'storage_namespaces': ','.join([
        'postgres',
        's3',
        'elasticsearch',
        'statsd',
        'telemetry',
    ]),

    'postgres': {
        'benchmark_tag': 'PGBenchmarkWrite',
        'crashstorage_class': 'socorro.external.statsd.statsd_base.StatsdBenchmarkingWrapper',
        'statsd_prefix': 'processor.postgres',
        'transaction_executor_class': (
            'socorro.database.transaction_executor.TransactionExecutorWithInfiniteBackoff'
        ),
        'wrapped_object_class': 'socorro.external.postgresql.crashstorage.PostgreSQLCrashStorage',
    },
    's3': {
        'active_list': 'save_raw_and_processed',
        'benchmark_tag': 'BotoBenchmarkWrite',
        'crashstorage_class': 'socorro.external.statsd.statsd_base.StatsdBenchmarkingWrapper',
        'statsd_prefix': 'processor.s3',
        'use_mapping_file': 'False',
        'wrapped_object_class': 'socorro.external.boto.crashstorage.BotoS3CrashStorage',
    },
    'elasticsearch': {
        'active_list': 'save_raw_and_processed',
        'benchmark_tag': 'BotoBenchmarkWrite',
        'crashstorage_class': 'socorro.external.statsd.statsd_base.StatsdBenchmarkingWrapper',
        'es_redactor.forbidden_keys': ', '.join([
            'memory_report',
            'upload_file_minidump_browser.json_dump',
            'upload_file_minidump_flash1.json_dump',
            'upload_file_minidump_flash2.json_dump',
        ]),
        'statsd_prefix': 'processor.es',
        'use_mapping_file': 'False',
        'wrapped_object_class': 'socorro.external.es.crashstorage.ESCrashStorageRedactedJsonDump',
    },
    'statsd': {
        'active_list': 'save_raw_and_processed',
        'crashstorage_class': 'socorro.external.statsd.statsd_base.StatsdCounter',
        'statsd_prefix': 'processor',
    },
    'telemetry': {
        'active_list': 'save_raw_and_processed',
        'bucket_name': 'org-mozilla-telemetry-crashes',
        'crashstorage_class': 'socorro.external.statsd.statsd_base.StatsdBenchmarkingWrapper',
        'statsd_prefix': 'processor.telemetry',
        'wrapped_object_class': 'socorro.external.boto.crashstorage.TelemetryBotoS3CrashStorage',
    },
})
