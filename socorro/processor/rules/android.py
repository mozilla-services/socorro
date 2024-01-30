# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Processor rules that work on Android_* annotations"""

from socorro.processor.rules.base import Rule


class AndroidCPUInfoRule(Rule):
    """Fill in cpu fields in processed crash using Android_CPU_ABI value

    * cpu_arch
    * cpu_info
    * cpu_count
    * cpu_microcode_version

    """

    # Map of Android_CPU_ABI values to cpu_arch values
    ANDROID_CPU_ABI_MAP = {
        "armeabi-v7a": "arm",
        "arm64-v8a": "arm64",
        "x86_64": "amd64",
    }

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        cpu_arch = processed_crash.get("cpu_arch", "unknown")
        return cpu_arch == "unknown" and "Android_CPU_ABI" in raw_crash

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        android_cpu_abi = raw_crash["Android_CPU_ABI"]
        cpu_arch = self.ANDROID_CPU_ABI_MAP.get(android_cpu_abi, android_cpu_abi)

        processed_crash["cpu_arch"] = cpu_arch


class AndroidOSInfoRule(Rule):
    """Fill in os fields using Android_Version contents

    * os_name
    * os_version

    Note: This rule must run after OSInfoRule.

    """

    def predicate(self, raw_crash, dumps, processed_crash, tmpdir, status):
        os_name = processed_crash.get("os_name", "unknown").lower()
        return os_name in ("unknown", "android") and "Android_Version" in raw_crash

    def action(self, raw_crash, dumps, processed_crash, tmpdir, status):
        processed_crash["os_name"] = "Android"
        # NOTE(willkg): Android_Version holds the sdk version then a space then the
        # release name in parentheses like "23 (REL)". We just want the version part.
        android_sdk_version = raw_crash["Android_Version"].split(" ")[0]

        # Make sure the version is a number, but we want to store it as a string.
        try:
            int(android_sdk_version)
        except ValueError:
            return

        processed_crash["os_version"] = android_sdk_version
