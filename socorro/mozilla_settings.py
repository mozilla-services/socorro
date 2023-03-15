# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Settings for Mozilla's crash ingestion pipeline.
"""

import os
import socket
import tempfile

from everett.manager import ConfigManager, ListOf


_config = ConfigManager.basic_config()


def int_or_none(val):
    """If the value is an empty string, then return None"""
    if val.strip() == "":
        return None
    return int(val)


TOOL_ENV = _config(
    "TOOL_ENV",
    default="False",
    parser=bool,
    doc=(
        "Whether or not this is running in a tool environment and should ignore "
        "required configuration."
    ),
)
if TOOL_ENV:
    fake_values = [
        ("ELASTICSEARCH_URL", "http://elasticsearch:9200"),
    ]
    for key, val in fake_values:
        os.environ[key] = val


LOCAL_DEV_ENV = _config(
    "LOCAL_DEV_ENV",
    default="False",
    parser=bool,
    doc="Whether or not this is a local development environment.",
)

HOST_ID = _config(
    "HOST_ID",
    default=socket.gethostname(),
    doc="Name of the host this is running on.",
)

# Sentry DSN--leave as an empty string to disable
SENTRY_DSN = _config(
    "SENTRY_DSN",
    default="",
    doc="Sentry DSN or empty string to disable.",
)

# This has to be a valid level from the Python logging module
LOGGING_LEVEL = _config(
    "LOGGING_LEVEL",
    default="INFO",
    doc="Default logging level. Should be one of INFO, DEBUG, WARNING, ERROR.",
)

# Markus configuration for metrics
MARKUS_BACKENDS = [
    {
        "class": "markus.backends.statsd.StatsdMetrics",
        "options": {
            "statsd_host": _config(
                "STATSD_HOST",
                default="localhost",
                doc="statsd host.",
            ),
            "statsd_port": _config(
                "STATSD_PORT",
                default="8125",
                parser=int,
                doc="statsd port.",
            ),
        },
    },
]
if LOCAL_DEV_ENV:
    MARKUS_BACKENDS.append({"class": "markus.backends.logging.LoggingMetrics"})


# Processor configuration
PROCESSOR = {
    "task_manager": {
        "class": "socorro.lib.threaded_task_manager.ThreadedTaskManager",
        "options": {
            "idle_delay": 7,
            "number_of_threads": _config(
                "PROCESSOR_NUMBER_OF_THREADS",
                default="4",
                parser=int_or_none,
                doc="Number of worker threads for the processor.",
            ),
            "maximum_queue_size": _config(
                "PROCESSOR_MAXIMUM_QUEUE_SIZE",
                default="8",
                parser=int_or_none,
                doc="Number of items to queue up from the processing queues.",
            ),
        },
    },
    "pipeline": {
        "class": "socorro.processor.pipeline.Pipeline",
        "options": {
            "rulesets": "socorro.mozilla_rulesets.RULESETS",
            "host_id": HOST_ID,
        },
    },
    "temporary_path": _config(
        "PROCESSOR_TEMPORARY_PATH",
        default=tempfile.gettempdir(),
        doc="Directory to use as a workspace for crash report processing.",
    ),
}

LOCAL_DEV_AWS_ENDPOINT_URL = _config(
    "LOCAL_DEV_AWS_ENDPOINT_URL",
    default="",
    doc=(
        "Endpoint url for AWS SQS/S3 in the local dev environment. "
        "Don't set this in server environments."
    ),
)

# Crash report processing queue configuration
QUEUE = {
    "class": "socorro.external.sqs.crashqueue.SQSCrashQueue",
    "options": {
        "standard_queue": _config(
            "SQS_STANDARD_QUEUE",
            default="standard-queue",
            doc="Name for the standard processing queue.",
        ),
        "priority_queue": _config(
            "SQS_PRIORITY_QUEUE",
            default="priority-queue",
            doc="Name for the priority processing queue.",
        ),
        "reprocessing_queue": _config(
            "SQS_REPROCESSING_QUEUE",
            default="reprocessing-queue",
            doc="Name for the reprocessing queue.",
        ),
        "access_key": _config("SQS_ACCESS_KEY", default="", doc="SQS access key."),
        "secret_access_key": _config(
            "SQS_SECRET_ACCESS_KEY",
            default="",
            doc="SQS secret access key.",
        ),
        "region": _config("SQS_REGION", default="", doc="SQS region."),
        "endpoint_url": LOCAL_DEV_AWS_ENDPOINT_URL,
    },
}

S3_STORAGE = {
    "class": "socorro.external.boto.crashstorage.BotoS3CrashStorage",
    "options": {
        "metrics_prefix": "processor.s3",
        "bucket": _config(
            "CRASHSTORAGE_S3_BUCKET",
            default="",
            doc="S3 bucket name for crash report data.",
        ),
        "access_key": _config(
            "CRASHSTORAGE_S3_ACCESS_KEY",
            default="",
            doc="S3 access key for crash report data.",
        ),
        "secret_access_key": _config(
            "CRASHSTORAGE_S3_SECRET_ACCESS_KEY",
            default="",
            doc="S3 secret access key for crash report data.",
        ),
        "region": _config(
            "CRASHSTORAGE_S3_REGION",
            default="",
            doc="S3 region for crash report data.",
        ),
        "endpoint_url": LOCAL_DEV_AWS_ENDPOINT_URL,
    },
}

ES_STORAGE = {
    "class": "socorro.external.es.crashstorage.ESCrashStorage",
    "options": {
        "metrics_prefix": "processor.es",
        "index": _config(
            "ELASTICSEARCH_INDEX",
            default="socorro%Y%W",
            doc="Template for Elasticsearch index names.",
        ),
        "index_regex": _config(
            "ELASTICSEARCH_INDEX_REGEX",
            default="^socorro[0-9]{6}$",
            doc="Regex for matching Elasticsearch index names.",
        ),
        "url": _config("ELASTICSEARCH_URL", doc="Elasticsearch url."),
    },
}

TELEMETRY_STORAGE = {
    "class": "socorro.external.boto.crashstorage.TelemetryBotoS3CrashStorage",
    "options": {
        "metrics_prefix": "processor.telemetry",
        "bucket": _config(
            "TELEMETRY_S3_BUCKET",
            default="",
            doc="S3 bucket name for telemetry data export.",
        ),
        "access_key": _config(
            "TELEMETRY_S3_ACCESS_KEY",
            default="",
            doc="S3 access key for telemetry bucket.",
        ),
        "secret_access_key": _config(
            "TELEMETRY_S3_SECRET_ACCESS_KEY",
            default="",
            doc="S3 secret access key for telemetry bucket.",
        ),
        "region": _config("TELEMETRY_S3_REGION", default="", doc="S3 region."),
        "endpoint_url": LOCAL_DEV_AWS_ENDPOINT_URL,
    },
}

# Crash report storage source pulls from S3
CRASH_SOURCE = S3_STORAGE

# Each key in this list corresponds to a key in this dict containing a crash report data
# destination configuration
CRASH_DESTINATIONS_ORDER = ["s3", "es", "telemetry"]
CRASH_DESTINATIONS = {
    "s3": S3_STORAGE,
    "es": ES_STORAGE,
    "telemetry": TELEMETRY_STORAGE,
}


# Disk cache manager configuration
CACHE_MANAGER_LOGGING_LEVEL = _config(
    "CACHE_MANAGER_LOGGING_LEVEL",
    default="INFO",
    doc=(
        "Default logging level for the cache manager. Should be one of INFO, DEBUG, "
        "WARNING, ERROR."
    ),
)
SYMBOLS_CACHE_PATH = _config(
    "SYMBOLS_CACHE_PATH",
    default=os.path.join(tempfile.gettempdir(), "symbols", "cache"),
    doc="Directory to use for the on-disk LRU-cache for symbols files.",
)
SYMBOLS_CACHE_MAX_SIZE = _config(
    "SYMBOLS_CACHE_MAX_SIZE",
    default=str(1024 * 1024 * 1024),
    parser=int_or_none,
    doc=(
        "Max size (bytes) of symbols cache. You can use _ to group digits for "
        "legibility."
    ),
)


# MinidumpStackwalkerRule configuration
STACKWALKER = {
    "command_path": _config(
        "STACKWALKER_COMMAND_PATH",
        default="/stackwalk-rust/minidump-stackwalk",
        doc="Aboslute path to the stackwalker binary.",
    ),
    "command_line": (
        "timeout --signal KILL {kill_timeout} "
        + "{command_path} "
        + "--evil-json={raw_crash_path} "
        + "--symbols-cache={symbol_cache_path} "
        + "--symbols-tmp={symbol_tmp_path} "
        + "--no-color "
        + "{symbols_urls} "
        + "--json "
        + "--verbose=error "
        + "{dump_file_path}"
    ),
    "dump_field": "upload_file_minidump",
    "kill_timeout": _config(
        "STACKWALKER_KILL_TIMEOUT",
        default="120",
        parser=int_or_none,
        doc="Timeout in seconds before the stackwalker is killed.",
    ),
    "symbols_urls": _config(
        "STACKWALKER_SYMBOLS_URLS",
        default="",
        parser=ListOf(str),
        doc="Comma-separated list of urls for symbols suppliers.",
    ),
    "symbol_cache_path": SYMBOLS_CACHE_PATH,
    "symbol_tmp_path": _config(
        "SYMBOLS_TMP_PATH",
        default=os.path.join(tempfile.gettempdir(), "symbols", "tmp"),
        doc="Directory to use for temporary storage of files being downloaded.",
    ),
}


# BetaVersionRule configuration
BETAVERSIONRULE_VERSION_STRING_API = _config(
    "BETAVERSIONRULE_VERSION_STRING_API",
    default="https://crash-stats.mozilla.org/api/VersionString",
    doc="URL for the version string API endpoint in the Crash Stats webapp.",
)
