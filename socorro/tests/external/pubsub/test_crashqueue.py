# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# This is tested using test settings (docker/config/test.env) and Pub/Sub emulator.

import time

import pytest

from socorro import settings
from socorro.external.pubsub.crashqueue import CrashIdsFailedToPublish
from socorro.libclass import build_instance_from_settings
from socorro.lib.libooid import create_new_ooid


# Amount of time to sleep between publish and pull so messages are available
PUBSUB_DELAY_PULL = 0.5


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

        # wait for published messages to become available before pulling
        time.sleep(PUBSUB_DELAY_PULL)

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

    def test_pull_max(self, pubsub_helper):
        standard_crashids = []
        for _ in range(10):
            crashid = "000" + create_new_ooid()[3:]
            standard_crashids.append(crashid)

            pubsub_helper.publish("standard", crashid)

        reprocessing_crashids = []
        for _ in range(5):
            crashid = "111" + create_new_ooid()[3:]
            reprocessing_crashids.append(crashid)

            pubsub_helper.publish("reprocessing", crashid)

        # wait for published messages to become available before pulling
        time.sleep(PUBSUB_DELAY_PULL)

        crashqueue = build_instance_from_settings(settings.QUEUE_PUBSUB)
        new_crashes = [item[0][0] for item in crashqueue.new_crashes()]

        # Crash ids may not be in the same order they were published, so we check to see
        # if we get the right balance of crash ids from the standard (000) and
        # reprocessing (111) queues and then check to see if all crash ids were
        # accounted for.
        assert [item[0:3] for item in new_crashes] == [
            "000",
            "000",
            "000",
            "000",
            "000",
            "111",
            "000",
            "000",
            "000",
            "000",
            "000",
            "111",
            "111",
            "111",
            "111",
        ]

        assert list(sorted(new_crashes)) == list(sorted(standard_crashids)) + list(
            sorted(reprocessing_crashids)
        )

    def test_ack(self, pubsub_helper):
        original_crash_id = create_new_ooid()

        # Publish crash id to the queue
        pubsub_helper.publish("standard", original_crash_id)

        # wait for published messages to become available before pulling
        time.sleep(PUBSUB_DELAY_PULL)

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

        # wait for published messages to become available before pulling
        time.sleep(PUBSUB_DELAY_PULL)

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

        # wait for published messages to become available before pulling
        time.sleep(PUBSUB_DELAY_PULL)

        published_crash_ids = pubsub_helper.get_published_crashids(queue)
        assert set(published_crash_ids) == {crash_id_1, crash_id_2, crash_id_3}

    def test_publish_with_error(self, pubsub_helper, sentry_helper):
        queue = "reprocessing"
        crash_id = create_new_ooid()

        crashqueue = build_instance_from_settings(settings.QUEUE_PUBSUB)

        # Run teardown_queues in the helper so there's no queue. That will cause an
        # error to get thrown by PubSub.
        pubsub_helper.teardown_queues()

        with sentry_helper.init() as sentry_client:
            try:
                crashqueue.publish(queue, [crash_id])
            except CrashIdsFailedToPublish as exc:
                print(exc)

            # wait for published messages to become available before pulling
            time.sleep(PUBSUB_DELAY_PULL)

            (envelope,) = sentry_client.envelope_payloads
            errors = [
                f"{error['type']} {error['value']}"
                for error in envelope["exception"]["values"]
            ]

            assert "NotFound Topic not found" in errors
