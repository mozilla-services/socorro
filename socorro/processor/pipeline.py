# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
This file defines the method of converting a raw crash into a processed crash. In this
latest version, all transformations have been reimplemented as sets of loadable rules.
The rules are applied one at a time, each doing some small part of the transformation
process.
"""

import logging
from typing import List

from attrs import define, field
import sentry_sdk

from socorro.libclass import import_class
from socorro.lib.libdatetime import date_to_string, utc_now


@define
class Status:
    notes: List[str] = field(factory=list)

    def add_note(self, note):
        self.notes.append(note)

    def add_notes(self, notes):
        self.notes.extend(notes)


class Pipeline:
    """Processor pipeline for Mozilla crash ingestion."""

    def __init__(self, rulesets, hostname):
        """
        :arg rulesets: either a dict of name -> list of rules or a Python dotted
            string path to a dict of name -> list of rules
        :arg hostname: the id of the host this is running on; used for logging
        """
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__name__)
        self.hostname = hostname

        if isinstance(rulesets, str):
            rulesets = import_class(rulesets)

        self.rulesets = rulesets

        self.log_rulesets()

    def log_rulesets(self):
        for ruleset_name, ruleset in self.rulesets.items():
            self.logger.info("Loading ruleset: %s", ruleset_name)
            for rule in ruleset:
                self.logger.info("Loaded rule: %r", rule)

    def process_crash(self, ruleset_name, raw_crash, dumps, processed_crash, tmpdir):
        """Process a crash

        This takes a raw_crash, associated minidump files, and a pre-existing
        processed_crash if there is one, and processed the crash into a new
        processed_crash.

        If this throws an exception, the crash was not processed correctly.

        """
        # Used for keeping track of processing notes we should save later
        status = Status()

        processed_crash["success"] = False
        start_time = utc_now()
        processed_crash["started_datetime"] = date_to_string(start_time)

        status.add_note(f">>> Start processing: {start_time} ({self.hostname})")

        processed_crash["signature"] = "EMPTY: crash failed to process"

        crash_id = raw_crash["uuid"]

        ruleset = self.rulesets.get(ruleset_name)
        if ruleset is None:
            status.add_note(f"error: no ruleset: {ruleset_name}")
            return processed_crash

        self.logger.info("processing with %s for crash %s", ruleset_name, crash_id)

        # Apply rules; if a rule fails, capture the error and continue onward
        for rule in ruleset:
            with sentry_sdk.push_scope() as scope:
                scope.set_extra("rule", rule.name)

                try:
                    rule.act(
                        raw_crash=raw_crash,
                        dumps=dumps,
                        processed_crash=processed_crash,
                        tmpdir=tmpdir,
                        status=status,
                    )

                except Exception as exc:
                    sentry_sdk.capture_exception(exc)

                    self.logger.exception(
                        "error: crash id %s: rule %s: %r",
                        crash_id,
                        rule.name,
                        exc,
                    )

                    # NOTE(willkg): notes are public, so we can't put exception
                    # messages in them
                    status.add_note(
                        f"ruleset {ruleset_name!r} rule {rule.name!r} failed: "
                        f"{exc.__class__.__name__}"
                    )

        # The crash made it through the processor rules with no exceptions raised, call
        # it a success
        processed_crash["success"] = True

        # Add previous notes to processor history
        processor_history = processed_crash.get("processor_history", [])
        if processed_crash.get("processor_notes"):
            previous_notes = processed_crash["processor_notes"]
            processor_history.insert(0, previous_notes)
        processed_crash["processor_history"] = processor_history

        # Set notes to this processing pass' notes
        processed_crash["processor_notes"] = "\n".join(status.notes)

        # Set completed_datetime
        completed_datetime = utc_now()
        processed_crash["completed_datetime"] = date_to_string(completed_datetime)

        self.logger.info(
            "finishing %s transform for crash: %s",
            "successful" if processed_crash["success"] else "failed",
            crash_id,
        )
        return processed_crash

    def reject_raw_crash(self, crash_id, reason):
        self.logger.warning("%s rejected: %s", crash_id, reason)

    def close(self):
        self.logger.debug("closing rules")
        for rule in self.rules:
            rule.close()
