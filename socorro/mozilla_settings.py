# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Settings for Mozilla's crash ingestion pipeline.
"""

import functools
import os
import socket
import tempfile

from everett.manager import ConfigManager, ListOf, parse_data_size, parse_time_period


_config = ConfigManager.basic_config()


def or_none(parser):
    """If the value is an empty string, then return None"""

    @functools.wraps(parser)
    def _or_none(val):
        if val.strip() == "":
            return None
        return parser(val)

    return _or_none


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

HOSTNAME = _config(
    "HOSTNAME",
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
    doc="Default logging level. Should be one of DEBUG, INFO, WARNING, ERROR.",
)


STATSD_HOST = _config("STATSD_HOST", default="localhost", doc="statsd host.")
STATSD_PORT = _config("STATSD_PORT", default="8125", parser=int, doc="statsd port.")


# Processor configuration
PROCESSOR = {
    "task_manager": {
        "class": "socorro.lib.threaded_task_manager.ThreadedTaskManager",
        "options": {
            "idle_delay": 7,
            "number_of_threads": _config(
                "PROCESSOR_NUMBER_OF_THREADS",
                default="4",
                parser=or_none(int),
                doc="Number of worker threads for the processor.",
            ),
            "maximum_queue_size": _config(
                "PROCESSOR_MAXIMUM_QUEUE_SIZE",
                default="8",
                parser=or_none(int),
                doc="Number of items to queue up from the processing queues.",
            ),
        },
    },
    "pipeline": {
        "class": "socorro.processor.pipeline.Pipeline",
        "options": {
            "rulesets": "socorro.mozilla_rulesets.RULESETS",
            "hostname": HOSTNAME,
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

# Crash report processing queue configuration if CLOUD_PROVIDER == AWS
QUEUE_SQS = {
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
# Crash report processing queue configuration if CLOUD_PROVIDER == GCP
QUEUE_PUBSUB = {
    "class": "socorro.external.pubsub.crashqueue.PubSubCrashQueue",
    "options": {
        "project_id": _config(
            "PUBSUB_PROJECT_ID",
            default="test",
            doc="Google Compute Platform project_id.",
        ),
        "standard_topic_name": _config(
            "PUBSUB_STANDARD_TOPIC_NAME",
            default="standard-queue",
            doc="Topic name for the standard processing queue.",
        ),
        "standard_subscription_name": _config(
            "PUBSUB_STANDARD_SUBSCRIPTION_NAME",
            default="standard-queue",
            doc="Subscription name for the standard processing queue.",
        ),
        "priority_topic_name": _config(
            "PUBSUB_PRIORITY_TOPIC_NAME",
            default="priority-queue",
            doc="Topic name for the priority processing queue.",
        ),
        "priority_subscription_name": _config(
            "PUBSUB_PRIORITY_SUBSCRIPTION_NAME",
            default="priority-queue",
            doc="Subscription name for the priority processing queue.",
        ),
        "reprocessing_topic_name": _config(
            "PUBSUB_REPROCESSING_TOPIC_NAME",
            default="reprocessing-queue",
            doc="Topic name for the reprocessing queue.",
        ),
        "reprocessing_subscription_name": _config(
            "PUBSUB_REPROCESSING_SUBSCRIPTION_NAME",
            default="reprocessing-queue",
            doc="Subscription name for the reprocessing queue.",
        ),
    },
}

# Crash report storage configuration if CLOUD_PROVIDER == AWS
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
# Crash report storage configuration if CLOUD_PROVIDER == GCP
GCS_STORAGE = {
    "class": "socorro.external.gcs.crashstorage.GcsCrashStorage",
    "options": {
        "metrics_prefix": "processor.gcs",
        "bucket": _config(
            "CRASHSTORAGE_GCS_BUCKET",
            default="",
            doc="GCS bucket name for crash report data.",
        ),
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

# Telemetry crash report storage configuration if CLOUD_PROVIDER == AWS
TELEMETRY_S3_STORAGE = {
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
# Telemetry crash report storage configuration if CLOUD_PROVIDER == GCP
TELEMETRY_GCS_STORAGE = {
    "class": "socorro.external.gcs.crashstorage.TelemetryGcsCrashStorage",
    "options": {
        "metrics_prefix": "processor.telemetry",
        "bucket": _config(
            "TELEMETRY_GCS_BUCKET",
            default="",
            doc="GCS bucket name for telemetry data export.",
        ),
    },
}


def cloud_provider_parser(val):
    """Return 'AWS' or 'GCP'."""
    normalized = val.strip().upper()
    if normalized in ("AWS", "GCP"):
        return normalized
    raise ValueError(f"cloud provider not supported, must be AWS or GCP: {val}")


# Cloud provider specific configuration
CLOUD_PROVIDER = _config(
    "CLOUD_PROVIDER",
    default="AWS",
    parser=cloud_provider_parser,
    doc="The cloud provider to use for queueing and blob storage. Must be AWS or GCP.",
)
if CLOUD_PROVIDER == "AWS":
    QUEUE = QUEUE_SQS
    STORAGE = S3_STORAGE
    TELEMETRY_STORAGE = TELEMETRY_S3_STORAGE
elif CLOUD_PROVIDER == "GCP":
    QUEUE = QUEUE_PUBSUB
    STORAGE = GCS_STORAGE
    TELEMETRY_STORAGE = TELEMETRY_GCS_STORAGE

# Crash report storage source pulls from S3 or GCS
CRASH_SOURCE = STORAGE

# Each key in this list corresponds to a key in this dict containing a crash report data
# destination configuration
CRASH_DESTINATIONS_ORDER = ["storage", "es", "telemetry"]
CRASH_DESTINATIONS = {
    "storage": STORAGE,
    "es": ES_STORAGE,
    "telemetry": TELEMETRY_STORAGE,
}


# Disk cache manager configuration
CACHE_MANAGER_LOGGING_LEVEL = _config(
    "CACHE_MANAGER_LOGGING_LEVEL",
    default="INFO",
    doc=(
        "Default logging level for the cache manager. Should be one of DEBUG, INFO, "
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
    # default="4gb",
    default="40gb",  # temporary until we set it in infra configuration
    parser=or_none(parse_data_size),
    doc=(
        "Max size (bytes) of symbols cache. You can use _ to group digits for "
        "legibility. You can use units like kb, mb, gb, tb, etc."
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
        "{command_path} "
        + "--evil-json={raw_crash_path} "
        + "--symbols-cache={symbol_cache_path} "
        + "--symbols-tmp={symbol_tmp_path} "
        + "--no-color "
        + "--output-file={output_path} "
        + "--log-file={log_path} "
        + "{symbols_urls} "
        + "--json "
        + "--verbose=error "
        + "{dump_file_path}"
    ),
    "dump_field": "upload_file_minidump",
    "kill_timeout": _config(
        "STACKWALKER_KILL_TIMEOUT",
        default="2m",
        parser=or_none(parse_time_period),
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


# Stage submitter configuration
STAGE_SUBMITTER_LOGGING_LEVEL = _config(
    "STAGE_SUBMITTER_LOGGING_LEVEL",
    default="INFO",
    doc=(
        "Default logging level for the stage submitter. Should be one of DEBUG, INFO, "
        "WARNING, ERROR."
    ),
)

STAGE_SUBMITTER_DESTINATIONS = _config(
    "STAGE_SUBMITTER_DESTINATIONS",
    default="",
    doc=(
        "Comma-separated pairs of ``DESTINATION_URL|SAMPLE`` where the "
        "``DESTINATION_URL`` is an https url to submit the crash report to "
        "and ``SAMPLE`` is a number between 0 and 100 representing the sample "
        "rate. For example:\n"
        "\n"
        "* ``https://example.com|20``\n"
        "* ``https://example.com|30,https://example2.com|100``"
    ),
    parser=ListOf(str),
)
