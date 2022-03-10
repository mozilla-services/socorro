# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys

from configman import Namespace
from configman.converters import class_converter

from socorro.app.socorro_app import App
from socorro.schemas import TELEMETRY_SOCORRO_CRASH_SCHEMA_AS_STRING


class UploadTelemetrySchema(App):
    """Uploads schema to S3 bucket for Telemetry

    We always send a copy of the crash (mainly processed crash) to a S3 bucket
    meant for Telemetry to ingest. When they ingest, they need a copy of our
    telemetry_socorro_crash.json JSON Schema file.

    They use that not to understand the JSON we store but the underlying
    structure (types, nesting etc.) necessary for storing it in .parquet files
    in S3.

    To get a copy of the telemetry_socorro_crash.json they can take it from the git
    repository but that's fragile since it depends on github.com always being available.

    By uploading it to S3 not only do we bet on S3 being more read-reliable
    that github.com's server but by being in S3 AND unavailable that means the
    whole ingestion process has to halt/pause anyway.

    """

    app_name = "upload-telemetry-schema"
    app_version = "0.1"
    app_description = "Uploads JSON schema to S3 bucket for Telemetry"
    metadata = ""

    required_config = Namespace()
    required_config.namespace("telemetry")
    required_config.telemetry.add_option(
        "resource_class",
        default="socorro.external.boto.connection_context.S3Connection",
        doc="fully qualified dotted Python classname to handle Boto connections",
        from_string_converter=class_converter,
        reference_value_from="resource.boto",
    )
    required_config.telemetry.add_option(
        "json_filename",
        default="telemetry_socorro_crash.json",
        doc="Name of the file/key we're going to upload to",
    )

    def main(self):
        path = self.config.telemetry.json_filename
        conn = self.config.telemetry.resource_class(self.config.telemetry)
        conn.save_file(path, TELEMETRY_SOCORRO_CRASH_SCHEMA_AS_STRING)
        self.logger.info("Success: Schema uploaded!")
        return 0


if __name__ == "__main__":
    sys.exit(UploadTelemetrySchema.run())
