# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import os
import time

from more_itertools import chunked
from requests.exceptions import ConnectionError, ReadTimeout

from socorro.lib.requestslib import session_with_retries
from socorro.scripts import FallbackToPipeAction, WrappedTextHelpFormatter


DESCRIPTION = """
Sends specified crashes for reprocessing

This requires SOCORRO_REPROCESS_API_TOKEN to be set in the environment to a
valid API token.

Note: If you're processing more than 10,000 crashes, you should use a sleep
value that balances the rate of crash ids being added to the queue and the rate
of crash ids being processed. For example, you could use "--sleep 10" which
will sleep for 10 seconds between submitting groups of crashes.

Also, if you're processing a lot of crashes, you should let ops know and maybe
they should increase the number of processor nodes.

"""

DEFAULT_HOST = "https://crash-stats.mozilla.org"
CHUNK_SIZE = 50
SLEEP_DEFAULT = 1


def main(argv=None):
    parser = argparse.ArgumentParser(
        formatter_class=WrappedTextHelpFormatter, description=DESCRIPTION.strip()
    )
    parser.add_argument(
        "--sleep",
        help="how long in seconds to sleep before submitting the next group",
        type=int,
        default=SLEEP_DEFAULT,
    )
    parser.add_argument(
        "--host", help="host for system to reprocess in", default=DEFAULT_HOST
    )
    parser.add_argument(
        "--ruleset",
        help="name of ruleset to reprocess these crash reports with",
        default="",
    )
    parser.add_argument(
        "crashid",
        help="one or more crash ids to fetch data for",
        nargs="*",
        action=FallbackToPipeAction,
    )

    if argv is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(argv)

    api_token = os.environ.get("SOCORRO_REPROCESS_API_TOKEN")
    if not api_token:
        print("You need to set SOCORRO_REPROCESS_API_TOKEN in the environment")
        return 1

    url = args.host.rstrip("/") + "/api/Reprocessing/"
    print("Sending reprocessing requests to: %s" % url)
    session = session_with_retries()

    ruleset = args.ruleset

    crash_ids = args.crashid
    print(
        "Reprocessing %s crashes sleeping %s seconds between groups..."
        % (len(crash_ids), args.sleep)
    )

    groups = list(chunked(crash_ids, CHUNK_SIZE))
    for i, group in enumerate(groups):
        print(
            "Processing group ending with %s ... (%s/%s)"
            % (group[-1], i + 1, len(groups))
        )

        if ruleset:
            group = [f"{crash_id}:{ruleset}" for crash_id in group]

        keep_trying = True
        while keep_trying:
            try:
                resp = session.post(
                    url, data={"crash_ids": group}, headers={"Auth-Token": api_token}
                )
            except (ConnectionError, ReadTimeout) as exc:
                print(f"{exc} ... waiting 10 seconds and retrying")
                time.sleep(10)
                continue

            if resp.status_code == 200:
                keep_trying = False
                continue

            print(
                "Got back non-200 status code: %s %s" % (resp.status_code, resp.content)
            )

        # NOTE(willkg): We sleep here because the webapp has a bunch of rate limiting and we don't
        # want to trigger that. It'd be nice if we didn't have to do this.
        time.sleep(args.sleep)

    print("Done!")
