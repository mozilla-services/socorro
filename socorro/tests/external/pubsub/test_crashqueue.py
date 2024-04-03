# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# This is tested using test settings (docker/config/test.env) and Pub/Sub emulator.

import time

import pytest

from socorro.libclass import build_instance_from_settings
from socorro.lib.libooid import create_new_ooid
from socorro import settings


class TestPubSubCrashQueue:
    def test_iter(self, pubsub_helper):
        standard_crash = create_new_ooid()
        pubsub_helper.publish("standard", standard_crash)
        # intentionally simulate pubsub double-delivering a message
        pubsub_helper.publish("standard", standard_crash)

        reprocessing_crash = create_new_ooid()
        pubsub_helper.publish("reprocessing", reprocessing_crash)

        priority_crash = create_new_ooid()
        pubsub_helper.publish("priority", priority_crash)

        crashqueue = build_instance_from_settings(settings.QUEUE_PUBSUB)
        new_crashes = list(crashqueue.new_crashes())

        # Assert the shape of items in new_crashes
        for item in new_crashes:
            assert isinstance(item, tuple)
            assert isinstance(item[0], tuple)  # *args
            assert isinstance(item[1], dict)  # **kwargs
            assert list(item[1].keys()) == ["finished_func"]

        new_crash_args = {item[0] for item in new_crashes}
        # Assert new_crashes order is the correct order
        assert new_crash_args == {
            (priority_crash,),
            (standard_crash,),
            (reprocessing_crash,),
        }

    def test_ack(self, pubsub_helper):
        original_crash_id = create_new_ooid()

        # Publish crash id to the queue
        pubsub_helper.publish("standard", original_crash_id)

        crashqueue = build_instance_from_settings(settings.QUEUE_PUBSUB)
        new_crashes = list(crashqueue.new_crashes())

        # Assert original_crash_id is in new_crashes
        assert {item[0] for item in new_crashes} == {(original_crash_id,)}

        # Now call it again; note that we haven't acked the crash_ids
        # nor have the leases expired
        second_new_crashes = list(crashqueue.new_crashes())
        assert second_new_crashes == []

        # Now ack the crash_id and we don't get it again
        for _, kwargs in new_crashes:
            kwargs["finished_func"]()

        time.sleep(pubsub_helper.ack_deadline_seconds + 1)

        # Now call it again and make sure we get nothing back
        new_crashes = list(crashqueue.new_crashes())
        assert new_crashes == []

    @pytest.mark.parametrize("queue", ["standard", "priority", "reprocessing"])
    def test_publish_one(self, pubsub_helper, queue):
        crash_id = create_new_ooid()

        crashqueue = build_instance_from_settings(settings.QUEUE_PUBSUB)
        crashqueue.publish(queue, [crash_id])

        published_crash_ids = pubsub_helper.get_published_crashids(queue)
        assert set(published_crash_ids) == {crash_id}

    @pytest.mark.parametrize("queue", ["standard", "priority", "reprocessing"])
    def test_publish_many(self, pubsub_helper, queue):
        crash_id_1 = create_new_ooid()
        crash_id_2 = create_new_ooid()
        crash_id_3 = create_new_ooid()

        crashqueue = build_instance_from_settings(settings.QUEUE_PUBSUB)
        crashqueue.publish(queue, [crash_id_1, crash_id_2])
        crashqueue.publish(queue, [crash_id_3])

        published_crash_ids = pubsub_helper.get_published_crashids(queue)
        assert set(published_crash_ids) == {crash_id_1, crash_id_2, crash_id_3}
