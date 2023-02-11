# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# This is tested using test settings (docker/config/test.env) and localstack.

import os
import time

import pytest

from socorro.libclass import build_instance_from_settings
from socorro.lib.libooid import create_new_ooid


QUEUE_SETTINGS = {
    "class": "socorro.external.sqs.crashqueue.SQSCrashQueue",
    "options": {
        "standard_queue": os.environ["SQS_STANDARD_QUEUE"],
        "priority_queue": os.environ["SQS_PRIORITY_QUEUE"],
        "reprocessing_queue": os.environ["SQS_REPROCESSING_QUEUE"],
        "region": os.environ["SQS_REGION"],
        "access_key": os.environ["SQS_ACCESS_KEY"],
        "secret_access_key": os.environ["SQS_SECRET_ACCESS_KEY"],
        "endpoint_url": os.environ["AWS_ENDPOINT_URL"],
    },
}


class TestSQSCrashQueue:
    def test_iter(self, sqs_helper):
        standard_crash = create_new_ooid()
        sqs_helper.publish("standard", standard_crash)

        reprocessing_crash = create_new_ooid()
        sqs_helper.publish("reprocessing", reprocessing_crash)

        priority_crash = create_new_ooid()
        sqs_helper.publish("priority", priority_crash)

        crashqueue = build_instance_from_settings(QUEUE_SETTINGS)
        new_crashes = list(crashqueue.new_crashes())

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

        crashqueue = build_instance_from_settings(QUEUE_SETTINGS)
        new_crashes = list(crashqueue.new_crashes())

        # Assert original_crash_id is in new_crashes
        crash_ids = [item[0][0] for item in new_crashes]
        assert crash_ids == [original_crash_id]

        # Now call it again; note that we haven't acked the crash_ids
        # nor have the leases expired
        second_new_crashes = list(crashqueue.new_crashes())
        assert second_new_crashes == []

        # Now ack the crash_id and we don't get it again
        for args, kwargs in new_crashes:
            kwargs["finished_func"]()

        time.sleep(sqs_helper.visibility_timeout + 1)

        # Now call it again and make sure we get nothing back
        new_crashes = list(crashqueue.new_crashes())
        assert new_crashes == []

    @pytest.mark.parametrize("queue", ["standard", "priority", "reprocessing"])
    def test_publish_one(self, sqs_helper, queue):
        crash_id = create_new_ooid()

        crashqueue = build_instance_from_settings(QUEUE_SETTINGS)
        crashqueue.publish(queue, [crash_id])

        published_crash_ids = sqs_helper.get_published_crashids(queue)
        assert published_crash_ids == [crash_id]

    @pytest.mark.parametrize("queue", ["standard", "priority", "reprocessing"])
    def test_publish_many(self, sqs_helper, queue):
        crash_id_1 = create_new_ooid()
        crash_id_2 = create_new_ooid()
        crash_id_3 = create_new_ooid()

        crashqueue = build_instance_from_settings(QUEUE_SETTINGS)
        crashqueue.publish(queue, [crash_id_1, crash_id_2])
        crashqueue.publish(queue, [crash_id_3])

        published_crash_ids = sqs_helper.get_published_crashids(queue)
        assert sorted(published_crash_ids) == sorted(
            [crash_id_1, crash_id_2, crash_id_3]
        )
