# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import gzip
import json
import random

from markus.testing import MetricsMock
import pytest

from socorro import settings
from socorro.lib.libooid import create_new_ooid
from socorro.stage_submitter.submitter import (
    get_payload_compressed,
    get_payload_type,
    remove_collector_keys,
    SubmitterApp,
)


# Only run submitter tests in GCP mode
pytestmark = pytest.mark.gcp


def get_app():
    app = SubmitterApp()
    app.set_up()
    return app


def generate_storage_key(kind, crash_id):
    """Generates the key in S3 for this object kind

    :arg kind: the kind of thing to fetch
    :arg crash_id: the crash id

    :returns: the key name

    """
    if kind == "raw_crash":
        return f"v1/raw_crash/20{crash_id[-6:]}/{crash_id}"
    if kind == "dump_names":
        return f"v1/dump_names/{crash_id}"
    if kind in (None, "", "upload_file_minidump"):
        kind = "dump"
    return f"v1/{kind}/{crash_id}"


def jsonify(data):
    return json.dumps(data, sort_keys=True)


def save_crash(gcs_helper, bucket, raw_crash, dumps):
    crash_id = raw_crash["uuid"]

    # Save raw crash
    key = generate_storage_key("raw_crash", crash_id)
    data = jsonify(raw_crash).encode("utf-8")
    gcs_helper.upload(bucket, key, data)

    # Save dump_names
    key = generate_storage_key("dump_names", crash_id)
    data = jsonify(list(dumps.keys())).encode("utf-8")
    gcs_helper.upload(bucket, key, data)

    # Save dumps
    for name, data in dumps.items():
        key = generate_storage_key(name, crash_id)
        data = data.encode("utf-8")
        gcs_helper.upload(bucket, key, data)


@pytest.mark.parametrize(
    "raw_crash, expected",
    [
        ({}, "unknown"),
        ({"metadata": {"payload": "json"}}, "json"),
    ],
)
def test_get_payload_type(raw_crash, expected):
    assert get_payload_type(raw_crash) == expected


@pytest.mark.parametrize(
    "raw_crash, expected",
    [
        ({}, "0"),
        ({"metadata": {"payload_compressed": "1"}}, "1"),
    ],
)
def test_get_payload_compressed(raw_crash, expected):
    assert get_payload_compressed(raw_crash) == expected


@pytest.mark.parametrize(
    "raw_crash, expected",
    [
        ({}, {}),
        (
            {
                "Product": "Firefox",
                "Version": "60.0",
                "metadata": {
                    "collector_notes": [],
                    "dump_checksums": {},
                    "payload_compressed": "0",
                    "payload": "multipart",
                },
                "version": 2,
                "uuid": "de1bb258-cbbf-4589-a673-34f800160918",
                "submitted_timestamp": "2022-09-14T15:45:55.222222",
            },
            {
                "Product": "Firefox",
                "Version": "60.0",
                "uuid": "de1bb258-cbbf-4589-a673-34f800160918",
            },
        ),
    ],
)
def test_remove_collector_keys(raw_crash, expected):
    assert remove_collector_keys(raw_crash) == expected


def test_basic(pubsub_helper, gcs_helper, mock_collector):
    bucket = gcs_helper.get_crashstorage_bucket()
    crash_id = "de1bb258-cbbf-4589-a673-34f800160918"
    save_crash(
        gcs_helper=gcs_helper,
        bucket=bucket,
        raw_crash={
            "Product": "Firefox",
            "uuid": crash_id,
            "Version": "60.0",
            "metadata": {
                "collector_notes": [],
                "dump_checksums": {},
                "payload_compressed": "0",
                "payload": "multipart",
            },
            "version": 2,
        },
        dumps={"upload_file_minidump": "abcdef"},
    )

    # The submitter will only consume and submit from the standard topic
    pubsub_helper.publish("standard", crash_id)
    pubsub_helper.publish("reprocessing", create_new_ooid())
    pubsub_helper.publish("priority", create_new_ooid())

    # Capture logs, make sure it doesn't get sampled by setting sample to 100, and
    # invoke the Lambda function
    with settings.override(
        STAGE_SUBMITTER_DESTINATIONS=["http://antenna:8000/submit|100"]
    ):
        app = get_app()
        with MetricsMock() as metricsmock:
            app.run_once()

    # Verify payload was submitted
    assert len(mock_collector.payloads) == 1
    assert mock_collector.payloads[0].hostname == "antenna"

    # Verify default user agent was used
    headers = mock_collector.payloads[0].headers
    assert headers["User-Agent"] == "stage-submitter/2.0"

    # Stare at some multipart/form-data
    post_payload = mock_collector.payloads[0].text
    assert (
        post_payload == "--01659896d5dc42cabd7f3d8a3dcdd3bb\r\n"
        'Content-Disposition: form-data; name="Product"\r\n'
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        "Firefox\r\n"
        "--01659896d5dc42cabd7f3d8a3dcdd3bb\r\n"
        'Content-Disposition: form-data; name="Version"\r\n'
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        "60.0\r\n"
        "--01659896d5dc42cabd7f3d8a3dcdd3bb\r\n"
        'Content-Disposition: form-data; name="uuid"\r\n'
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        "de1bb258-cbbf-4589-a673-34f800160918\r\n"
        "--01659896d5dc42cabd7f3d8a3dcdd3bb\r\n"
        'Content-Disposition: form-data; name="upload_file_minidump"; filename="file.dump"\r\n'
        "Content-Type: application/octet-stream\r\n"
        "\r\n"
        "abcdef\r\n"
        "--01659896d5dc42cabd7f3d8a3dcdd3bb--\r\n"
    )

    if settings.CLOUD_PROVIDER == "AWS":
        metricsmock.assert_incr("submitter.accept")
    else:
        metricsmock.assert_incr("socorro.submitter.accept")


def test_multiple_destinations(pubsub_helper, gcs_helper, mock_collector):
    bucket = gcs_helper.get_crashstorage_bucket()
    gcs_helper.create_bucket(bucket)
    crash_id = "de1bb258-cbbf-4589-a673-34f800160918"
    save_crash(
        gcs_helper=gcs_helper,
        bucket=bucket,
        raw_crash={
            "Product": "Firefox",
            "uuid": crash_id,
            "Version": "60.0",
            "metadata": {
                "collector_notes": [],
                "dump_checksums": {},
                "payload_compressed": "0",
                "payload": "multipart",
            },
            "version": 2,
        },
        dumps={"upload_file_minidump": "abcdef"},
    )

    pubsub_helper.publish("standard", crash_id)

    # Capture logs, configure to send to two destinations with sample set to 100, and
    # invoke the Lambda function
    with settings.override(
        # NOTE(willkg):antenna and antenna_2 are set up in the collector mock.
        STAGE_SUBMITTER_DESTINATIONS=[
            "http://antenna:8000/submit|100",
            "http://antenna_2:8000/submit|100",
        ],
    ):
        app = get_app()
        app.run_once()

    # Verify payload was submitted
    #
    # We only have one collector mock, but we can distinguish between the destinations
    # by looking at the payload request hostname
    assert len(mock_collector.payloads) == 2
    assert mock_collector.payloads[0].hostname == "antenna"
    assert mock_collector.payloads[1].hostname == "antenna_2"

    # The payloads sent to antenna and antenna_2 should be the same
    assert mock_collector.payloads[0].text == mock_collector.payloads[1].text


def test_annotations_as_json(pubsub_helper, gcs_helper, mock_collector):
    bucket = gcs_helper.get_crashstorage_bucket()
    gcs_helper.create_bucket(bucket)
    crash_id = "de1bb258-cbbf-4589-a673-34f800160918"
    save_crash(
        gcs_helper=gcs_helper,
        bucket=bucket,
        raw_crash={
            "uuid": crash_id,
            "Product": "Firefox",
            "Version": "60.0",
            "metadata": {
                "payload": "json",
            },
            "version": 2,
        },
        dumps={"upload_file_minidump": "abcdef"},
    )

    pubsub_helper.publish("standard", crash_id)

    # Capture logs, make sure it doesn't get sampled, and invoke the Lambda
    # function
    with settings.override(
        STAGE_SUBMITTER_DESTINATIONS=["http://antenna:8000/submit|100"]
    ):
        app = get_app()
        with MetricsMock() as metricsmock:
            app.run_once()

    # Verify payload was submitted
    assert len(mock_collector.payloads) == 1
    post_payload = mock_collector.payloads[0].text

    # Who doesn't like reading raw multipart/form-data? Woo hoo!
    assert (
        post_payload == "--01659896d5dc42cabd7f3d8a3dcdd3bb\r\n"
        'Content-Disposition: form-data; name="extra"\r\n'
        "Content-Type: application/json\r\n"
        "\r\n"
        '{"Product":"Firefox","Version":"60.0","uuid":"de1bb258-cbbf-4589-a673-34f800160918"}\r\n'
        "--01659896d5dc42cabd7f3d8a3dcdd3bb\r\n"
        'Content-Disposition: form-data; name="upload_file_minidump"; filename="file.dump"\r\n'
        "Content-Type: application/octet-stream\r\n"
        "\r\n"
        "abcdef\r\n"
        "--01659896d5dc42cabd7f3d8a3dcdd3bb--\r\n"
    )

    if settings.CLOUD_PROVIDER == "AWS":
        metricsmock.assert_incr("submitter.accept")
    else:
        metricsmock.assert_incr("socorro.submitter.accept")


def test_multiple_dumps(pubsub_helper, gcs_helper, mock_collector):
    bucket = gcs_helper.get_crashstorage_bucket()
    gcs_helper.create_bucket(bucket)
    crash_id = "de1bb258-cbbf-4589-a673-34f800160918"
    save_crash(
        gcs_helper=gcs_helper,
        bucket=bucket,
        raw_crash={
            "uuid": crash_id,
            "Product": "Firefox",
            "Version": "60.0",
        },
        dumps={
            "upload_file_minidump": "abcdef",
            "upload_file_minidump_content": "abcdef2",
        },
    )

    pubsub_helper.publish("standard", crash_id)

    # Capture logs, make sure it doesn't get sampled, and invoke the Lambda
    # function
    with settings.override(
        STAGE_SUBMITTER_DESTINATIONS=["http://antenna:8000/submit|100"]
    ):
        app = get_app()
        with MetricsMock() as metricsmock:
            app.run_once()

    # Verify payload was submitted
    assert len(mock_collector.payloads) == 1
    post_payload = mock_collector.payloads[0].text

    # Who doesn't like reading raw multipart/form-data? Woo hoo!
    assert (
        post_payload == "--01659896d5dc42cabd7f3d8a3dcdd3bb\r\n"
        'Content-Disposition: form-data; name="Product"\r\n'
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        "Firefox\r\n"
        "--01659896d5dc42cabd7f3d8a3dcdd3bb\r\n"
        'Content-Disposition: form-data; name="Version"\r\n'
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        "60.0\r\n"
        "--01659896d5dc42cabd7f3d8a3dcdd3bb\r\n"
        'Content-Disposition: form-data; name="uuid"\r\n'
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        "de1bb258-cbbf-4589-a673-34f800160918\r\n"
        "--01659896d5dc42cabd7f3d8a3dcdd3bb\r\n"
        'Content-Disposition: form-data; name="upload_file_minidump"; filename="file.dump"\r\n'
        "Content-Type: application/octet-stream\r\n"
        "\r\n"
        "abcdef\r\n"
        "--01659896d5dc42cabd7f3d8a3dcdd3bb\r\n"
        'Content-Disposition: form-data; name="upload_file_minidump_content"; '
        'filename="file.dump"\r\n'
        "Content-Type: application/octet-stream\r\n"
        "\r\n"
        "abcdef2\r\n"
        "--01659896d5dc42cabd7f3d8a3dcdd3bb--\r\n"
    )

    if settings.CLOUD_PROVIDER == "AWS":
        metricsmock.assert_incr("submitter.accept")
    else:
        metricsmock.assert_incr("socorro.submitter.accept")


def test_compressed(pubsub_helper, gcs_helper, mock_collector):
    bucket = gcs_helper.get_crashstorage_bucket()
    gcs_helper.create_bucket(bucket)
    crash_id = "de1bb258-cbbf-4589-a673-34f800160918"
    save_crash(
        gcs_helper=gcs_helper,
        bucket=bucket,
        raw_crash={
            "uuid": crash_id,
            "Product": "Firefox",
            "Version": "60.0",
            "metadata": {
                "payload_compressed": "1",
            },
            "version": 2,
        },
        dumps={"upload_file_minidump": "abcdef"},
    )

    pubsub_helper.publish("standard", crash_id)

    # Capture logs, make sure it doesn't get sampled, and invoke the Lambda
    # function
    with settings.override(
        STAGE_SUBMITTER_DESTINATIONS=["http://antenna:8000/submit|100"]
    ):
        app = get_app()
        with MetricsMock() as metricsmock:
            app.run_once()

    # Verify payload was submitted
    assert len(mock_collector.payloads) == 1
    req = mock_collector.payloads[0]

    # Assert the header
    assert req.headers["Content-Encoding"] == "gzip"

    # Assert the length and payload are correct and payload is compressed
    post_payload = req.body
    assert len(post_payload) == int(req.headers["Content-Length"])

    unzipped_payload = gzip.decompress(post_payload)
    assert (
        unzipped_payload == b"--01659896d5dc42cabd7f3d8a3dcdd3bb\r\n"
        b'Content-Disposition: form-data; name="Product"\r\n'
        b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        b"Firefox\r\n"
        b"--01659896d5dc42cabd7f3d8a3dcdd3bb\r\n"
        b'Content-Disposition: form-data; name="Version"\r\n'
        b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        b"60.0\r\n"
        b"--01659896d5dc42cabd7f3d8a3dcdd3bb\r\n"
        b'Content-Disposition: form-data; name="uuid"\r\n'
        b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        b"de1bb258-cbbf-4589-a673-34f800160918\r\n"
        b"--01659896d5dc42cabd7f3d8a3dcdd3bb\r\n"
        b'Content-Disposition: form-data; name="upload_file_minidump"; '
        b'filename="file.dump"\r\n'
        b"Content-Type: application/octet-stream\r\n\r\n"
        b"abcdef\r\n"
        b"--01659896d5dc42cabd7f3d8a3dcdd3bb--\r\n"
    )

    if settings.CLOUD_PROVIDER == "AWS":
        metricsmock.assert_incr("submitter.accept")
    else:
        metricsmock.assert_incr("socorro.submitter.accept")


def test_sample_accepted(pubsub_helper, monkeypatch, gcs_helper, mock_collector):
    def always_20(*args, **kwargs):
        return 20

    monkeypatch.setattr(random, "randint", always_20)

    bucket = gcs_helper.get_crashstorage_bucket()
    gcs_helper.create_bucket(bucket)
    crash_id = "de1bb258-cbbf-4589-a673-34f800160918"
    save_crash(
        gcs_helper=gcs_helper,
        bucket=bucket,
        raw_crash={
            "uuid": crash_id,
            "Product": "Firefox",
            "Version": "60.0",
        },
        dumps={"upload_file_minidump": "abcdef"},
    )

    pubsub_helper.publish("standard", crash_id)

    # Capture the log and set sample value above the mocked randint--this should
    # get submitted
    with settings.override(
        STAGE_SUBMITTER_DESTINATIONS=["http://antenna:8000/submit|30"]
    ):
        app = get_app()
        with MetricsMock() as metricsmock:
            app.run_once()

    # Verify payload was submitted
    assert len(mock_collector.payloads) == 1
    if settings.CLOUD_PROVIDER == "AWS":
        metricsmock.assert_incr("submitter.accept")
    else:
        metricsmock.assert_incr("socorro.submitter.accept")


def test_sample_skipped(pubsub_helper, monkeypatch, gcs_helper, mock_collector):
    def always_20(*args, **kwargs):
        return 20

    monkeypatch.setattr(random, "randint", always_20)

    bucket = gcs_helper.get_crashstorage_bucket()
    gcs_helper.create_bucket(bucket)
    crash_id = "de1bb258-cbbf-4589-a673-34f800160918"
    save_crash(
        gcs_helper=gcs_helper,
        bucket=bucket,
        raw_crash={
            "uuid": crash_id,
            "Product": "Firefox",
            "Version": "60.0",
        },
        dumps={"upload_file_minidump": "abcdef"},
    )

    pubsub_helper.publish("standard", crash_id)

    # Capture the logs and set sample value below the mocked randint--this
    # should get skipped
    with settings.override(
        STAGE_SUBMITTER_DESTINATIONS=["http://antenna:8000/submit|10"]
    ):
        app = get_app()
        with MetricsMock() as metricsmock:
            app.run_once()

    # Verify no payload was submitted
    assert len(mock_collector.payloads) == 0

    if settings.CLOUD_PROVIDER == "AWS":
        metricsmock.assert_not_incr("submitter.accept")
        metricsmock.assert_incr("submitter.ignore")
    else:
        metricsmock.assert_not_incr("socorro.submitter.accept")
        metricsmock.assert_incr("socorro.submitter.ignore")


def test_different_samples(pubsub_helper, monkeypatch, gcs_helper, mock_collector):
    def always_20(*args, **kwargs):
        return 20

    monkeypatch.setattr(random, "randint", always_20)

    bucket = gcs_helper.get_crashstorage_bucket()
    gcs_helper.create_bucket(bucket)
    crash_id = "de1bb258-cbbf-4589-a673-34f800160918"
    save_crash(
        gcs_helper=gcs_helper,
        bucket=bucket,
        raw_crash={
            "Product": "Firefox",
            "uuid": crash_id,
            "Version": "60.0",
            "metadata": {
                "collector_notes": [],
                "dump_checksums": {},
                "payload_compressed": "0",
                "payload": "multipart",
            },
            "version": 2,
        },
        dumps={"upload_file_minidump": "abcdef"},
    )

    pubsub_helper.publish("standard", crash_id)

    # Capture logs and invoke lambda function
    with settings.override(
        STAGE_SUBMITTER_DESTINATIONS=[
            # sampled at 5--will get sampled
            "http://antenna:8000/submit|5",
            # sampled at 30--will get accepted
            "http://antenna_2:8000/submit|30",
        ]
    ):
        app = get_app()
        with MetricsMock() as metricsmock:
            app.run_once()

    # Verify only second destination got a payload
    assert len(mock_collector.payloads) == 1
    assert mock_collector.payloads[0].hostname == "antenna_2"
    if settings.CLOUD_PROVIDER == "AWS":
        metricsmock.assert_incr("submitter.accept")
        metricsmock.assert_incr("submitter.ignore")
    else:
        metricsmock.assert_incr("socorro.submitter.accept")
        metricsmock.assert_incr("socorro.submitter.ignore")


def test_user_agent(pubsub_helper, gcs_helper, mock_collector):
    user_agent = "crash-reporter/1.0"

    bucket = gcs_helper.get_crashstorage_bucket()
    gcs_helper.create_bucket(bucket)
    crash_id = "de1bb258-cbbf-4589-a673-34f800160918"
    save_crash(
        gcs_helper=gcs_helper,
        bucket=bucket,
        raw_crash={
            "Product": "Firefox",
            "uuid": crash_id,
            "Version": "60.0",
            "metadata": {
                "collector_notes": [],
                "dump_checksums": {},
                "payload_compressed": "0",
                "payload": "multipart",
                "user_agent": user_agent,
            },
            "version": 2,
        },
        dumps={"upload_file_minidump": "abcdef"},
    )

    pubsub_helper.publish("standard", crash_id)

    # Capture logs and invoke lambda function
    with settings.override(
        STAGE_SUBMITTER_DESTINATIONS=["http://antenna:8000/submit|100"]
    ):
        app = get_app()
        app.run_once()

    # Verify payload was submitted
    assert len(mock_collector.payloads) == 1

    # Verify user agent is from raw crash
    headers = mock_collector.payloads[0].headers
    assert headers["User-Agent"] == user_agent
