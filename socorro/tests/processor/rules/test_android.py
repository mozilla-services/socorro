# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from socorro.processor.pipeline import Status
from socorro.processor.rules.android import (
    AndroidCPUInfoRule,
    AndroidOSInfoRule,
)


class TestAndroidCPUInfoRule:
    @pytest.mark.parametrize(
        "android_cpu_abi, expected",
        [
            ("x86", "x86"),
            ("arm64-v8a", "arm64"),
            ("x86_64", "amd64"),
            ("value not in map", "value not in map"),
        ],
    )
    def test_cpu_arch_from_android_cpu_abi(self, tmp_path, android_cpu_abi, expected):
        raw_crash = {"Android_CPU_ABI": android_cpu_abi}
        processed_crash = {}
        dumps = {}
        status = Status()

        rule = AndroidCPUInfoRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert processed_crash["cpu_arch"] == expected


class TestAndroidOSInfoRule:
    @pytest.mark.parametrize(
        "os_name, android_version, expected",
        [
            ("Windows", None, False),
            ("Unknown", None, False),
            ("Unknown", "23 (REL)", True),
            ("Android", "23 (REL)", True),
        ],
    )
    def test_predicate(self, tmp_path, os_name, android_version, expected):
        raw_crash = {}
        if android_version is not None:
            raw_crash["Android_Version"] = android_version
        processed_crash = {"os_name": os_name}
        dumps = {}
        status = Status()

        rule = AndroidOSInfoRule()
        result = rule.predicate(
            raw_crash, dumps, processed_crash, str(tmp_path), status
        )
        assert result == expected

    @pytest.mark.parametrize(
        "os_name, android_version, expected_name, expected_version",
        [
            ("Unknown", "23 (REL)", "Android", "23"),
            ("Android", "23 (REL)", "Android", "23"),
            ("Android", "23 (KittyCatUpsideDownSundae)", "Android", "23"),
            ("Unknown", "23", "Android", "23"),
            ("Unknown", "xx", "Android", ""),
        ],
    )
    def test_act(
        self, tmp_path, os_name, android_version, expected_name, expected_version
    ):
        raw_crash = {}
        raw_crash["Android_Version"] = android_version
        processed_crash = {"os_name": os_name}
        dumps = {}
        status = Status()

        rule = AndroidOSInfoRule()
        rule.act(raw_crash, dumps, processed_crash, str(tmp_path), status)
        assert processed_crash["os_name"] == expected_name
        assert processed_crash.get("os_version", "") == expected_version
