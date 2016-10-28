from configman import Namespace
from configman.converters import class_converter
from crontabber.base import BaseCronApp

from socorro.schemas import CRASH_REPORT_JSON_SCHEMA_AS_STRING


class UploadCrashReportJSONSchemaCronApp(BaseCronApp):
    app_name = 'upload-crash-report-json-schema'
    app_description = """
    We always send a copy of the crash (mainly processed crash) to a
    S3 bucket meant for Telemetry to ingest.
    When they ingest, they need a copy of our crash_report.json JSON
    Schema file.

    They use that not to understand the JSON we store but the underlying
    structure (types, nesting etc.) necessary for storing it in .parquet
    files in S3.

    To get a copy of the crash_report.json they can take it from the
    git repository but that's fragile since it depends on github.com
    always being available.

    By uploading it to S3 not only do we bet on S3 being more read-reliable
    that github.com's server but by being in S3 AND unavailable that means
    the whole ingestion process has to halt/pause anyway.
    """

    required_config = Namespace()
    required_config.add_option(
        'resource_class',
        default=(
            'socorro.external.boto.connection_context.S3ConnectionContext'
        ),
        doc=(
            'fully qualified dotted Python classname to handle Boto '
            'connections'
        ),
        from_string_converter=class_converter,
        reference_value_from='resource.boto'
    )
    required_config.add_option(
        'json_filename',
        default='crash_report.json',
        doc="Name of the file/key we're going to upload to"
    )

    def run(self):
        connection_context = self.config.resource_class(self.config)
        connection = connection_context._connect()
        bucket = connection_context._get_bucket(
            connection,
            self.config.bucket_name
        )
        key = bucket.get_key(self.config.json_filename)
        if not key:
            key = bucket.new_key(self.config.json_filename)
        key.set_contents_from_string(CRASH_REPORT_JSON_SCHEMA_AS_STRING)
