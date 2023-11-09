# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from socorro.external.crashqueue_base import CrashQueueBase


class TestCrashQueueBase:
    def test_iter(self):
        crashqueue = CrashQueueBase()
        with pytest.raises(NotImplementedError):
            list(crashqueue)

        with pytest.raises(NotImplementedError):
            list(crashqueue())

    def test_publish(self):
        crashqueue = CrashQueueBase()
        crash_id = "0bba929f-8721-460c-dead-a43c20071025"
        with pytest.raises(NotImplementedError):
            crashqueue.publish("standard", [crash_id])
