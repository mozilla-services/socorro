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
