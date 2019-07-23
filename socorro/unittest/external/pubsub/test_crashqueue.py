# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import time

from socorro.external.pubsub.crashqueue import PubSubCrashQueue
from socorro.lib.ooid import create_new_ooid
from socorro.unittest.external.pubsub import (
    ACK_DEADLINE,
    get_config_manager,
    PubSubHelper,
)


class TestPubSubCrashQueue:
    def test_iter(self):
        manager = get_config_manager()
        with manager.context() as config:
            pubsub_helper = PubSubHelper(config)

            with pubsub_helper as pubsub:
                standard_crash = create_new_ooid()
                pubsub.publish("standard", standard_crash)

                reprocessing_crash = create_new_ooid()
                pubsub.publish("reprocessing", reprocessing_crash)

                priority_crash = create_new_ooid()
                pubsub.publish("priority", priority_crash)

                crash_queue = PubSubCrashQueue(config)
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

    def test_ack(self):
        original_crash_id = create_new_ooid()

        manager = get_config_manager()
        with manager.context() as config:
            pubsub_helper = PubSubHelper(config)

            with pubsub_helper as pubsub:
                # Publish crash id to the queue
                pubsub.publish("standard", original_crash_id)

                crash_queue = PubSubCrashQueue(config)
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

                # Wait beyond the ack deadline in the grossest way possible
                time.sleep(ACK_DEADLINE + 1)

                # Now call it again and make sure we get nothing back
                new_crashes = list(crash_queue.new_crashes())
                assert new_crashes == []
