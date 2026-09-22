# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from crashstats.supersearch.models import SuperSearch, SuperSearchUnredacted
from socorro.lib.libdatetime import utc_now
from socorro.lib.libooid import create_new_ooid


@pytest.mark.parametrize("model", [SuperSearch, SuperSearchUnredacted])
def test_results(model, es_helper):
    now = utc_now()
    crash_ids = {}
    for submission_type in [None, "report", "ping"]:
        crash_id = create_new_ooid(timestamp=now)
        crash_ids[submission_type] = crash_id
        crash = {
            "uuid": crash_id,
            "date_processed": now,
            "signature": "test submission types",
        }
        if submission_type is not None:
            crash["submission_type"] = submission_type
        es_helper.index_crash(processed_crash=crash, refresh=False)
    es_helper.refresh()

    api = model()
    result = api.get(_columns=["uuid"], _facets=["signature"])
    assert result["total"] == 2
    assert {hit["uuid"] for hit in result["hits"]} == {
        crash_ids[None],
        crash_ids["report"],
    }
    assert result["facets"]["signature"] == [
        {"term": "test submission types", "count": 2}
    ]

    result = api.get(submission_type="ping", _columns=["uuid"], _facets=[])
    assert result["total"] == 1
    assert result["hits"] == [{"uuid": crash_ids["ping"]}]
