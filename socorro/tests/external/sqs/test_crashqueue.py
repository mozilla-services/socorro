# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time

import pytest

from socorro.external.sqs.crashqueue import SQSCrashQueue
from socorro.lib.libooid import create_new_ooid
from socorro.tests.external.sqs import get_sqs_config, VISIBILITY_TIMEOUT


class TestSQSCrashQueue:
    def test_iter(self, sqs_helper):
        standard_crash = create_new_ooid()
        sqs_helper.publish("standard", standard_crash)

        reprocessing_crash = create_new_ooid()
        sqs_helper.publish("reprocessing", reprocessing_crash)

        priority_crash = create_new_ooid()
        sqs_helper.publish("priority", priority_crash)

        crash_queue = SQSCrashQueue(get_sqs_config())
        new_crashes = list(crash_queue.new_crashes())

        # Assert the shape of items in new_crashes
        for item in new_crashes:
            assert isinstance(item, tuple)
            assert isinstance(item[0], tuple)  # *args
            assert isinstance(item[1], dict)  # **kwargs
            assert list(item[1].keys()) == ["finished_func"]

        # Assert new_crashes order is the correct order
        crash_ids = [item[0][0] for item in new_crashes]
        assert crash_ids == [priority_crash, standard_crash, reprocessing_crash]

    def test_ack(self, sqs_helper):
        original_crash_id = create_new_ooid()

        # Publish crash id to the queue
        sqs_helper.publish("standard", original_crash_id)

        crash_queue = SQSCrashQueue(get_sqs_config())
        new_crashes = list(crash_queue.new_crashes())

        # Assert original_crash_id is in new_crashes
        crash_ids = [item[0][0] for item in new_crashes]
        assert crash_ids == [original_crash_id]

        # Now call it again; note that we haven't acked the crash_ids
        # nor have the leases expired
        second_new_crashes = list(crash_queue.new_crashes())
        assert second_new_crashes == []

        # Now ack the crash_id and we don't get it again
        for args, kwargs in new_crashes:
            kwargs["finished_func"]()

        time.sleep(VISIBILITY_TIMEOUT + 1)

        # Now call it again and make sure we get nothing back
        new_crashes = list(crash_queue.new_crashes())
        assert new_crashes == []

    @pytest.mark.parametrize("queue", ["standard", "priority", "reprocessing"])
    def test_publish_one(self, sqs_helper, queue):
        crash_id = create_new_ooid()

        crash_queue = SQSCrashQueue(get_sqs_config())
        crash_queue.publish(queue, [crash_id])

        published_crash_ids = sqs_helper.get_published_crashids(queue)
        assert published_crash_ids == [crash_id]

    @pytest.mark.parametrize("queue", ["standard", "priority", "reprocessing"])
    def test_publish_many(self, sqs_helper, queue):
        crash_id_1 = create_new_ooid()
        crash_id_2 = create_new_ooid()
        crash_id_3 = create_new_ooid()

        crash_queue = SQSCrashQueue(get_sqs_config())
        crash_queue.publish(queue, [crash_id_1, crash_id_2])
        crash_queue.publish(queue, [crash_id_3])

        published_crash_ids = sqs_helper.get_published_crashids(queue)
        assert sorted(published_crash_ids) == sorted(
            [crash_id_1, crash_id_2, crash_id_3]
        )
