# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
This defines the stage submitter application. It's designed to run as a standalone
service.

It consumes crash ids from the standard topic, determines what to do with them, pulls
the crash data from storage, assembles a payload, and submits them to a destination.

It pulls configuration from socorro.settings reusing processor configuration where
convenient.

To run::

    $ /app/bin/run_submitter.sh

"""

from contextlib import suppress
import dataclasses
from email.header import Header
import gzip
import json
import io
import logging
import pathlib
import random
import sys
import traceback
from typing import Callable

from fillmore.libsentry import set_up_sentry
from fillmore.scrubber import Scrubber, SCRUB_RULES_DEFAULT
import sentry_sdk

from socorro import settings
from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.libmarkus import METRICS, set_up_metrics
from socorro.lib.libdockerflow import get_release_name, get_version_info
from socorro.lib.liblogging import set_up_logging
from socorro.lib.librequests import session_with_retries
from socorro.libclass import build_instance_from_settings


# Default user agent to use when submitting to a destination url
DEFAULT_USER_AGENT = "stage-submitter/2.0"

# Boundary to use. This is the result of uuid.uuid4().hex. We just need a unique string
# to denote the boundary between parts in the payload.
BOUNDARY = "01659896d5dc42cabd7f3d8a3dcdd3bb"


@dataclasses.dataclass
class Crash:
    crash_id: str
    finished_func: Callable[[], None]


@dataclasses.dataclass
class Destination:
    url: str
    sample: int


def get_destinations(value_list):
    """Parse Destination instances from list of strings

    :arg value_list: list of `|` delimited strings

    :returns: list of Destination instances

    """
    destinations = []
    for item in value_list:
        url, sample = item.split("|")
        destinations.append(Destination(url=url, sample=int(sample)))
    return destinations


COLLECTOR_KEYS_TO_REMOVE = [
    "metadata",
    "submitted_timestamp",
    "version",
]


def remove_collector_keys(raw_crash):
    """Given a raw crash, removes keys added by a collector

    :arg raw_crash: dict of annotations and collector-added data

    :returns: mutated raw_crash

    """
    for key in COLLECTOR_KEYS_TO_REMOVE:
        if key in raw_crash:
            del raw_crash[key]

    return raw_crash


def smart_bytes(thing):
    """This converts things to a string representation then to bytes

    :arg thing: the thing to convert to bytes

    :returns: bytes

    """
    if isinstance(thing, bytes):
        return thing

    if isinstance(thing, str):
        return thing.encode("utf-8")

    return repr(thing).encode("utf-8")


def multipart_encode(raw_crash, dumps, payload_type, payload_compressed):
    """Takes a raw_crash and list of (name, dump) and converts to a multipart/form-data

    This returns a tuple of two things:

    1. a ``bytes`` object with the HTTP POST payload
    2. a dict of headers with ``Content-Type`` and ``Content-Length`` in it

    :arg raw_crash: dict of crash annotations
    :arg dumps: list of (name, dump) tuples
    :arg payload_type: either "multipart" or "json"
    :arg payload_compressed: either "1" or "0"

    :returns: tuple of (bytes, headers dict)

    """
    boundary_line = smart_bytes(f"--{BOUNDARY}\r\n")

    # NOTE(willkg): This is the result of uuid.uuid4().hex. We just need a
    # unique string to denote the boundary between parts in the payload.
    output = io.BytesIO()

    # If the payload of the original crash report had the crash annotations in
    # the "extra" field as a JSON blob, we should do the same here
    if payload_type == "json":
        output.write(boundary_line)
        output.write(b'Content-Disposition: form-data; name="extra"\r\n')
        output.write(b"Content-Type: application/json\r\n")
        output.write(b"\r\n")
        extra_data = json.dumps(raw_crash, sort_keys=True, separators=(",", ":"))
        output.write(smart_bytes(extra_data))
        output.write(b"\r\n")

    else:
        # Package up raw crash metadata--sort them so they're stable in the payload
        for key, val in sorted(raw_crash.items()):
            output.write(boundary_line)
            output.write(
                smart_bytes(
                    'Content-Disposition: form-data; name="%s"\r\n'
                    % Header(key).encode()
                )
            )
            output.write(b"Content-Type: text/plain; charset=utf-8\r\n")
            output.write(b"\r\n")
            output.write(smart_bytes(val))
            output.write(b"\r\n")

    # Insert dump data--sort them so they're stable in the payload
    for name, data in sorted(dumps.items()):
        output.write(boundary_line)

        if name == "dump":
            name = "upload_file_minidump"

        # dumps are sent as streams
        output.write(
            smart_bytes(
                'Content-Disposition: form-data; name="%s"; filename="file.dump"\r\n'
                % Header(name).encode()
            )
        )
        output.write(b"Content-Type: application/octet-stream\r\n")
        output.write(b"\r\n")
        output.write(data)
        output.write(b"\r\n")

    # Add end boundary
    output.write(smart_bytes(f"--{BOUNDARY}--\r\n"))
    output = output.getvalue()

    # Generate headers
    headers = {
        "Content-Type": f"multipart/form-data; boundary={BOUNDARY}",
        "Content-Length": str(len(output)),
    }

    # Compress if it we need to
    if payload_compressed == "1":
        bio = io.BytesIO()
        g = gzip.GzipFile(fileobj=bio, mode="w")
        g.write(output)
        g.close()
        output = bio.getbuffer()
        headers["Content-Length"] = str(len(output))
        headers["Content-Encoding"] = "gzip"

    return output, headers


def get_payload_type(raw_crash):
    """Determines payload type from collector metadata in raw crash

    :arg raw_crash: the raw crash data as a Python dict

    :returns: payload type or "unknown"

    """
    if raw_crash.get("metadata", {}).get("payload") is not None:
        return raw_crash["metadata"]["payload"]

    return "unknown"


def get_payload_compressed(raw_crash):
    """Determines whether the payload was compressed from collector metadata in raw crash

    :arg raw_crash: the raw crash data as a Python dict

    :returns: "1" or "0"

    """
    return raw_crash.get("metadata", {}).get("payload_compressed", "0")


def count_sentry_scrub_error(msg):
    """Counts sentry scrub errors"""
    METRICS.incr("submitter.sentry_scrub_error", value=1, tags=["service:submitter"])


def handle_exception(exctype, value, tb):
    """Handles exception that bubbles up to top-level before process exits"""
    logger = logging.getLogger(__name__)
    logger.error(
        "unhandled exception. Exiting. "
        + "".join(traceback.format_exception(exctype, value, tb))
    )


sys.excepthook = handle_exception


class SubmitterApp:
    def __init__(self):
        self.basedir = pathlib.Path(__file__).resolve().parent.parent.parent
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__name__)

    def set_up(self):
        set_up_logging(
            local_dev_env=settings.LOCAL_DEV_ENV,
            logging_level=settings.STAGE_SUBMITTER_LOGGING_LEVEL,
            hostname=settings.HOSTNAME,
        )
        set_up_metrics(
            statsd_host=settings.STATSD_HOST,
            statsd_port=settings.STATSD_PORT,
            hostname=settings.HOSTNAME,
            debug=settings.LOCAL_DEV_ENV,
        )

        scrubber = Scrubber(
            rules=SCRUB_RULES_DEFAULT,
            error_handler=count_sentry_scrub_error,
        )
        set_up_sentry(
            sentry_dsn=settings.SENTRY_DSN,
            release=get_release_name(self.basedir),
            host_id=settings.HOSTNAME,
            before_send=scrubber,
        )

        self.log_config()

        # This uses the same settings as the processor except that it stomps on
        # the priority and reprocessing subscription names so it doesn't pull
        # crash ids from them
        queue_settings = dict(settings.QUEUE)
        queue_settings["options"]["priority_subscription_name"] = None
        queue_settings["options"]["reprocessing_subscription_name"] = None
        self.queue = build_instance_from_settings(queue_settings)
        self.source = build_instance_from_settings(settings.CRASH_SOURCE)

        # Build destinations
        self.destinations = get_destinations(settings.STAGE_SUBMITTER_DESTINATIONS)

        self.logger.info("starting up")

    def log_config(self):
        version_info = get_version_info(self.basedir)
        data = ", ".join(
            [f"{key!r}: {val!r}" for key, val in sorted(version_info.items())]
        )
        data = data or "no version data"
        self.logger.info("version.json: %s", data)

        settings.log_settings(logger=self.logger)

    def source_iterator(self):
        """Iterate yielding crash ids."""
        while True:
            for crash_id, data in self.queue.new_crashes():
                if crash_id is None:
                    continue
                # NOTE(willkg): new_crashes() always returns a tuple of one element for
                # the crash id for whatever reason
                crash_id = crash_id[0]
                finished_func = data["finished_func"]
                yield Crash(crash_id=crash_id, finished_func=finished_func)

    def sample(self, destinations):
        """Applies sampling returning only the destinations we need to send to

        :arg destinations: list of Destination instances

        :returns: list of Destination instances to send to; sometimes an empty list

        """
        return [
            dest
            for dest in destinations
            if dest.sample >= 100 or random.randint(0, 100) > dest.sample
        ]

    def process(self, crash):
        with METRICS.timer("submitter.process"):
            with sentry_sdk.push_scope() as scope:
                crash_id = crash.crash_id
                self.logger.debug(f"processing {crash}")

                scope.set_extra("crash_id", crash)

                # sample and determine destinations
                destinations = []
                for dest in self.destinations:
                    if dest.sample < 100 and random.randint(0, 100) > dest.sample:
                        METRICS.incr("submitter.ignore")
                    else:
                        METRICS.incr("submitter.accept")
                        destinations.append(dest)

                if not destinations:
                    # If there's no where we need to post it to, we just move on--no
                    # need to do more work
                    return

                session = session_with_retries()

                try:
                    raw_crash = self.source.get_raw_crash(crash_id)
                    dumps = self.source.get_dumps(crash_id)
                except CrashIDNotFound:
                    # If the crash data isn't found, we just move on--no need to capture
                    # errors here
                    self.logger.warning(
                        "warning: crash cannot be found in storage: %s", crash_id
                    )
                    return

                # FIXME(willkg): crashstorage converts "upload_file_minidump" to "dump",
                # so we need to convert that back; however, it's not clear this works
                # in _all_ cases
                if "dump" in dumps.keys():
                    dumps["upload_file_minidump"] = dumps["dump"]
                    del dumps["dump"]

                payload_type = get_payload_type(raw_crash)
                payload_compressed = get_payload_compressed(raw_crash)

                # Get the metadata.user_agent if there is one, or use default agent
                user_agent = (
                    raw_crash.get("metadata", {}).get("user_agent")
                    or DEFAULT_USER_AGENT
                )

                # Remove keys created by the collector from the raw crash
                raw_crash = remove_collector_keys(raw_crash)

                # Assemble payload and headers
                payload, headers = multipart_encode(
                    raw_crash=raw_crash,
                    dumps=dumps,
                    payload_type=payload_type,
                    payload_compressed=payload_compressed,
                )

                # Set the User-Agent header so the collector captures this in the metadata
                headers["User-Agent"] = user_agent

                # Post to all destinations
                for destination in destinations:
                    try:
                        # POST crash to new environment
                        session.post(destination.url, headers=headers, data=payload)

                    except Exception:
                        METRICS.incr("submitter.unknown_submit_error", value=1)
                        self.logger.exception(
                            "Error: http post failed for unknown reason: %s", crash_id
                        )

    def run_loop(self, infinite_loop=True):
        """Run cache manager in a loop."""
        crashes = self.source_iterator()
        while True:
            crash = next(crashes)
            try:
                self.process(crash)
            except Exception:
                METRICS.incr("submitter.unknown_process_error", value=1)
                self.logger.exception(
                    "error: processing failed for unknown reason: %s", crash.crash_id
                )
            finally:
                try:
                    crash.finished_func()
                except Exception:
                    METRICS.incr("submitter.unknown_finished_func_error", value=1)
                    self.logger.exception(
                        "error: finished_func failed for unknown reason: %s",
                        crash.crash_id,
                    )

            if not infinite_loop:
                break

        self.shutdown()

    def run_once(self):
        """Runs a nonblocking event generator once."""
        self.run_loop(infinite_loop=False)

    def shutdown(self):
        """Shut down an event generator."""
        with suppress(AttributeError):
            self.queue.close()

        with suppress(AttributeError):
            self.source.close()


def main():
    app = SubmitterApp()
    app.set_up()
    app.run_loop()


if __name__ == "__main__":
    # NOTE(willkg): we need to do this so that the submitter logger isn't `__main__`
    # which causes problems when logging
    from socorro.stage_submitter.submitter import main

    main()
