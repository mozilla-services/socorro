# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse


from socorro.lib.librequests import session_with_retries
from socorro.scripts import WrappedTextHelpFormatter


DESCRIPTION = """
Fetches crash ids for crash reports that are missing a processed crash
"""

DEFAULT_HOST = "https://crash-stats.mozilla.org"

MAX_PAGE = 1000


def fetch_results(host):
    """Generator that returns results

    :arg str host: the host to query

    :returns: generator of results data

    """
    url = host + "/api/MissingProcessedCrash/"

    session = session_with_retries()

    while True:
        resp = session.get(url)
        if resp.status_code != 200:
            raise Exception("Bad response: %s %s" % (resp.status_code, resp.content))

        data = resp.json()
        results = data["results"]

        for result in results:
            yield result

        url = data["next"]
        if not url:
            return


def main(argv=None):
    parser = argparse.ArgumentParser(
        formatter_class=WrappedTextHelpFormatter, description=DESCRIPTION.strip()
    )
    parser.add_argument(
        "--host", default=DEFAULT_HOST, help="host for system to fetch crashids from"
    )
    parser.add_argument(
        "--print",
        default="crashid",
        choices=["result", "crashid", "stats"],
        help="what to print out",
    )
    parser.add_argument(
        "--is-processed",
        default="all",
        choices=["all", "yes", "no"],
        help="Filter on is_processed value",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="increase verbosity of output"
    )

    if argv is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(argv)

    if args.is_processed == "all":
        is_processed = None
    elif args.is_processed == "yes":
        is_processed = True
    else:
        is_processed = False

    host = args.host.rstrip("/")

    total = 0
    processed = 0
    not_processed = 0

    for result in fetch_results(host):
        total += 1
        if result["is_processed"]:
            processed += 1
        else:
            not_processed += 1

        if is_processed is None or result["is_processed"] == is_processed:
            if args.print == "result":
                print(result)
            elif args.print == "crashid":
                print(result["crash_id"])

    if args.print == "stats":
        print(f"total:         {total}")
        print(f"processed:     {processed} ({processed / total:.2f})")
        print(f"not processed: {not_processed} ({not_processed / total:.2f})")

    return 0
