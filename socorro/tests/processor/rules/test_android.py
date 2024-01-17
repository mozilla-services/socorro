# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from socorro.processor.pipeline import Status
from socorro.processor.rules.android import AndroidCPUInfoRule


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
