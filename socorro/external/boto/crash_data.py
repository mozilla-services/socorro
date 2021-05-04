# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.lib import external_common, MissingArgumentError, BadArgumentError, ooid
from socorro.external.boto.crashstorage import (
    BotoS3CrashStorage,
    CrashIDNotFound,
    TelemetryBotoS3CrashStorage,
)


class SimplifiedCrashData(BotoS3CrashStorage):
    """Fetches data from BotoS3CrashStorage

    The difference between this and the base CrashData class is that this one
    only makes the get() and if it fails it does NOT try to put the crash ID
    back into the priority jobs queue. Also, it returns a python dict instead
    of a DotDict which makes this easier to work with from the webapp's model
    bridge.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Forcibly set this to override the default in the base
        # crash storage class for boto. We're confident that at this
        # leaf point we want to NOT return a DotDict but just a plain
        # python dict.
        self.config.json_object_hook = dict
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__name__)

    def get(self, **kwargs):
        """Return JSON data of a crash report, given its uuid."""
        filters = [
            ("uuid", None, str),
            ("datatype", None, str),
            ("name", None, str),  # only applicable if datatype == 'raw'
        ]
        params = external_common.parse_arguments(filters, kwargs, modern=True)

        if not params.uuid:
            raise MissingArgumentError("uuid")

        if not ooid.is_crash_id_valid(params.uuid):
            raise BadArgumentError("uuid")

        if not params.datatype:
            raise MissingArgumentError("datatype")

        datatype_method_mapping = {
            # Minidumps
            "raw": "get_raw_dump",
            # Raw Crash
            "meta": "get_raw_crash",
            # Redacted processed crash
            "processed": "get_processed",
            # Unredacted processed crash
            "unredacted": "get_unredacted_processed",
        }
        if params.datatype not in datatype_method_mapping:
            raise BadArgumentError(params.datatype)
        get = self.__getattribute__(datatype_method_mapping[params.datatype])
        try:
            if params.datatype == "raw":
                return get(params.uuid, name=params.name)
            else:
                return get(params.uuid)
        except CrashIDNotFound as cidnf:
            self.logger.warning(
                "%(datatype)s not found: %(exception)s",
                {"datatype": params.datatype, "exception": cidnf},
            )
            # The CrashIDNotFound exception that happens inside the
            # crashstorage is too revealing as exception message
            # contains information about buckets and prefix keys.
            # Re-wrap it here so the message is just the crash ID.
            raise CrashIDNotFound(params.uuid)


class TelemetryCrashData(TelemetryBotoS3CrashStorage):
    """Fetches data from TelemetryBotoS3CrashStorage"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Forcibly set this to override the default in the base crash storage
        # class for boto. We're confident that at this leaf point we want to
        # NOT return a DotDict but just a plain python dict.
        self.config.json_object_hook = dict

    def get(self, **kwargs):
        """Return JSON data of a crash report, given its uuid."""
        filters = [("uuid", None, str)]
        params = external_common.parse_arguments(filters, kwargs, modern=True)

        if not params.uuid:
            raise MissingArgumentError("uuid")

        try:
            return self.get_unredacted_processed(params.uuid)
        except CrashIDNotFound as cidnf:
            self.logger.warning(
                "telemetry crash not found: %(exception)s", {"exception": cidnf}
            )
            # The CrashIDNotFound exception that happens inside the
            # crashstorage is too revealing as exception message contains
            # information about buckets and prefix keys. Re-wrap it here so the
            # message is just the crash ID.
            raise CrashIDNotFound(params.uuid)
