# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re

from glom import glom
import markus

from socorro.processor.rules.base import Rule


METRICS = markus.get_metrics("processor")


class DeNullRule(Rule):
    """Removes nulls from keys and values

    Sometimes crash reports come in with junk data. This removes the egregious
    junk that causes downstream processing and storage problems.

    """

    def de_null(self, s):
        """Remove nulls from bytes and str values

        :arg str/bytes value: The str or bytes to remove nulls from

        :returns: str or bytes without nulls

        """
        if isinstance(s, bytes) and b"\0" in s:
            return s.replace(b"\0", b"")

        if isinstance(s, str) and "\0" in s:
            return s.replace("\0", "")

        # If it's not a bytes or a str, it's something else and we should
        # return it as is
        return s

    def action(self, raw_crash, dumps, processed_crash, processor_meta_data):
        had_nulls = False

        # Go through the raw crash and de-null keys and values
        for key, val in list(raw_crash.items()):
            new_key = self.de_null(key)
            if key != new_key:
                had_nulls = True
                del raw_crash[key]

            new_val = self.de_null(val)
            if val != new_val:
                had_nulls = True
                raw_crash[new_key] = new_val

        if had_nulls:
            METRICS.incr("denullrule.has_nulls")


class DeNoneRule(Rule):
    """Removes keys that have None values

    Sometimes crash reports can have None values. That's unhelpful and usually
    a bug in the crash reporter. This removes keys have None values.

    """

    def action(self, raw_crash, dumps, processed_crash, processor_meta_data):
        had_nones = False

        # Remove keys that have None values
        for key, val in list(raw_crash.items()):
            if val is None:
                had_nones = True
                del raw_crash[key]

        if had_nones:
            METRICS.incr("denonerule.had_nones")


class IdentifierRule(Rule):
    def action(self, raw_crash, dumps, processed_crash, processor_meta_data):
        if "uuid" in raw_crash:
            processed_crash["crash_id"] = raw_crash["uuid"]
            processed_crash["uuid"] = raw_crash["uuid"]


class CPUInfoRule(Rule):
    """Fill in cpu_arch, cpu_info, and cpu_count fields in processed crash"""

    # Map of Android_CPU_ABI values to cpu_arch values
    ANDROID_CPU_ABI_MAP = {
        "armeabi-v7a": "arm",
        "arm64-v8a": "arm64",
        "x86_64": "amd64",
    }

    def action(self, raw_crash, dumps, processed_crash, processor_meta_data):
        # This is the CPU info of the machine the product was running on
        processed_crash["cpu_info"] = glom(
            processed_crash, "json_dump.system_info.cpu_info", default="unknown"
        )
        processed_crash["cpu_count"] = glom(
            processed_crash, "json_dump.system_info.cpu_count", default=0
        )

        # This is the CPU that the product was built for. We look at the
        # minidump-stackwalk output first and if there's nothing there, look at
        # annotations.
        cpu_arch = glom(
            processed_crash, "json_dump.system_info.cpu_arch", default="unknown"
        )
        if cpu_arch == "unknown" and "Android_CPU_ABI" in raw_crash:
            android_cpu_abi = raw_crash["Android_CPU_ABI"]
            cpu_arch = self.ANDROID_CPU_ABI_MAP.get(android_cpu_abi, android_cpu_abi)

        processed_crash["cpu_arch"] = cpu_arch


class OSInfoRule(Rule):
    def action(self, raw_crash, dumps, processed_crash, processor_meta_data):
        os_name = glom(
            processed_crash, "json_dump.system_info.os", default="Unknown"
        ).strip()
        processed_crash["os_name"] = os_name

        os_ver = glom(
            processed_crash, "json_dump.system_info.os_ver", default=""
        ).strip()
        processed_crash["os_version"] = os_ver


class CollectorInfoRule(Rule):
    """Copy keys from the raw crash related to the collector

    Note: These are not validated or normalized. It's assumed the collector is
    generating this data correctly.

    """

    KEYS = [
        "collector_notes",
    ]

    def action(self, raw_crash, dumps, processed_crash, processor_meta_data):
        for key in self.KEYS:
            processed_crash[key] = raw_crash.get(key, None)


class CrashReportKeysRule(Rule):
    """Extracts a list of all keys and dump names and saves it as crash_report_keys"""

    # At least one alphanumeric plus underscore and dash
    VALID_KEY = re.compile(r"^[a-zA-Z0-9_-]+$")

    def sanitize(self, key):
        # If the key isn't alphanumeric with underscores, then it's not valid
        if not self.VALID_KEY.match(key):
            return None

        # Truncate
        key = key[:100]

        return key

    def action(self, raw_crash, dumps, processed_crash, processor_meta_data):
        all_keys = set(raw_crash.keys()) | set(dumps.keys())

        # Go through and remove obviously invalid keys
        sanitized_keys = [self.sanitize(key) for key in all_keys]
        sanitized_keys = {key for key in sanitized_keys if key}

        processed_crash["crash_report_keys"] = list(sorted(sanitized_keys))

        # Figure out the set of keys that are in one set or the other, but
        # not both
        diff = all_keys.symmetric_difference(sanitized_keys)
        if diff:
            processor_meta_data["processor_notes"].append(
                "invalidkeys: Crash report contains invalid keys"
            )
