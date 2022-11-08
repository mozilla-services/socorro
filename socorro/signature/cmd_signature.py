# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
import csv
import os
import sys

import requests

from .generator import SignatureGenerator
from .utils import convert_to_crash_data, parse_crashid


DESCRIPTION = """
Given one or more crash ids via command line or stdin (one per line), pulls down information from
Socorro, generates signatures, and prints signature information.
"""

# FIXME(willkg): This hits production. We might want it configurable.
API_URL = "https://crash-stats.mozilla.org/api"


class OutputBase:
    """Base class for outputter classes

    Outputter classes are context managers. If they require start/top or begin/end semantics, they
    should implement ``__enter__`` and ``__exit__``.

    Otherwise they can just implement ``data`` and should be fine.

    """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def warning(self, line):
        """Prints out a warning line to stderr

        :arg str line: the line to print to stderr

        """
        print(f"WARNING: {line}", file=sys.stderr)

    def separator(self):
        """Output a separator between two crash signature generations"""
        pass

    def data(self, crash_id, old_sig, result, verbose):
        """Outputs a data point

        :arg str crash_id: the crash id for the signature generated
        :arg str old_sig: the old signature retrieved in the processed crash
        :arg Result result: the signature result
        :arg boolean verbose: whether or not to be verbose

        """
        pass


class TextOutput(OutputBase):
    def data(self, crash_id, old_sig, result, verbose):
        print(f"Crash id: {crash_id}")
        print(f"Original: {old_sig}")
        print(f"New:      {result.signature}")
        print(f"Same?:    {old_sig == result.signature}")

        if result.notes:
            print(f"Notes:    ({len(result.notes)})")
            for note in result.notes:
                print(f"          {note}")
        if verbose:
            if result.debug_log:
                print(f"Debug:    ({len(result.debug_log)})")
                for item in result.debug_log:
                    print(f"          {item}")

            extra_items = list(sorted(result.extra.items()))
            if extra_items:
                print("Extra:")
                for key, val in extra_items:
                    if isinstance(val, list):
                        print(f"          {key}:")
                        for item in val:
                            print(f"          - {item}")
                    else:
                        print(f"          {key}: {val}")

    def separator(self):
        print("")


class CSVOutput(OutputBase):
    def __enter__(self):
        self.out = csv.writer(sys.stdout, quoting=csv.QUOTE_ALL)
        self.out.writerow(["crashid", "old", "new", "same?", "notes"])
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.out = None

    def data(self, crash_id, old_sig, result, verbose):
        self.out.writerow(
            [
                crash_id,
                old_sig,
                result.signature,
                str(old_sig == result.signature),
                result.notes,
            ]
        )


class MarkdownOutput(OutputBase):
    """Output in Markdown for use in Bugzilla and GitHub"""

    def data(self, crash_id, old_sig, result, verbose):
        def fix(s):
            return s.replace("`", "\\`")

        print(
            "**Crash id:** [%s](https://crash-stats.mozilla.org/report/index/%s)"
            % (crash_id, crash_id)
        )
        print(f"**Original:** `{fix(old_sig)}`")
        print(f"**New:** `{fix(result.signature)}`")
        print(f"**Same?:** {old_sig == result.signature}")
        print(f"**Notes:** ({len(result.notes)})")
        print("")
        if result.notes:
            for note in result.notes:
                print(f"* {note}")
            print("")
        if verbose and result.debug_log:
            print(f"**Debug:** ({len(result.debug_log)})")
            print("")
            for note in result.debug_log:
                print(f"* {note}")

    def separator(self):
        print("")


def fetch(endpoint, crash_id, api_token=None):
    kwargs = {"params": {"crash_id": crash_id}}
    if api_token:
        kwargs["headers"] = {"Auth-Token": api_token}

    return requests.get(API_URL + endpoint, **kwargs)


def main(argv=None):
    """Takes crash data via args and generates a Socorro signature"""
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "-v", "--verbose", help="increase output verbosity", action="store_true"
    )
    parser.add_argument(
        "--format", help="specify output format: csv, markdown, text (default)"
    )
    parser.add_argument(
        "--different-only",
        dest="different",
        action="store_true",
        help="limit output to just the signatures that changed",
    )
    parser.add_argument(
        "--signature-list-dir",
        required=False,
        help=(
            "directory of signature list files to use; if not specified, uses the "
            + "included signature list files"
        ),
    )
    parser.add_argument(
        "crashids",
        metavar="crashid",
        nargs="*",
        help="crash id to generate signatures for",
    )

    if argv is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(argv)

    if args.format == "csv":
        outputter = CSVOutput
    elif args.format == "markdown":
        outputter = MarkdownOutput
    else:
        outputter = TextOutput

    api_token = os.environ.get("SOCORRO_API_TOKEN", "")

    generator_kwargs = {}
    if args.signature_list_dir:
        generator_kwargs = {
            "signature_list_dir": args.signature_list_dir,
        }
    generator = SignatureGenerator(**generator_kwargs)

    if args.crashids:
        crashids_iterable = args.crashids
    elif not sys.stdin.isatty():
        # If a script is piping to this script, then isatty() returns False. If
        # there is no script piping to this script, then isatty() returns True
        # and if we do list(sys.stdin), it'll block waiting for input.
        crashids_iterable = list(sys.stdin)
    else:
        crashids_iterable = []

    if not crashids_iterable:
        parser.print_help()
        return 0

    with outputter() as out:
        for index, crash_id in enumerate(crashids_iterable):
            if index > 0:
                out.separator()

            crash_id = crash_id.strip()
            parsed_crash_id = parse_crashid(crash_id)
            if not parsed_crash_id:
                out.warning(f"Error: {crash_id} is not a valid crash id")
                continue

            crash_id = parsed_crash_id

            resp = fetch("/ProcessedCrash/", crash_id, api_token)
            if resp.status_code == 404:
                out.warning(f"{crash_id}: does not have processed crash.")
                continue
            if resp.status_code == 429:
                out.warning(f"API rate limit reached. {resp.content}")
                # FIXME(willkg): Maybe there's something better we could do here. Like maybe wait a
                # few minutes.
                return 1
            if resp.status_code == 500:
                out.warning(f"HTTP 500: {resp.content}")
                continue

            processed_crash = resp.json()

            # If there's an error in the processed crash, then something is wrong--probably with the
            # API token. So print that out and exit.
            if "error" in processed_crash:
                out.warning(
                    f"Error fetching processed crash: {processed_crash['error']}"
                )
                return 1

            old_signature = processed_crash["signature"]
            crash_data = convert_to_crash_data(processed_crash)

            result = generator.generate(crash_data)

            if not args.different or old_signature != result.signature:
                out.data(crash_id, old_signature, result, args.verbose)
