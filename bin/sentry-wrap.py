# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Wraps a command such that if it fails, an error report is sent to the Sentry service
# specified by SENTRY_DSN in the environment.
#
# Usage: python bin/sentry-wrap.py -- [CMD]


import argparse
import os
import shlex
import subprocess
import sys

import sentry_sdk
from sentry_sdk import capture_exception, capture_message


def main():
    parser = argparse.ArgumentParser(
        description="Python-based cli for sentry error reporting."
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout to wait for process before giving up.",
    )
    parser.add_argument("cmd", nargs="+", help="The process to run.")

    args = parser.parse_args()

    sentry_dsn = os.environ.get("SENTRY_DSN")

    if not sentry_dsn:
        print("SENTRY_DSN is not defined. Exiting.")
        sys.exit(1)

    sentry_sdk.init(sentry_dsn)

    cmd = " ".join(args.cmd)
    cmd_args = shlex.split(cmd)
    print(f"Running: {cmd_args}")

    try:
        ret = subprocess.run(cmd_args, capture_output=True, timeout=args.timeout)
        if ret.returncode != 0:
            sentry_sdk.set_context(
                "status",
                {
                    "exit_code": ret.returncode,
                    "stdout": ret.stdout.decode("utf-8"),
                    "stderr": ret.stderr.decode("utf-8"),
                },
            )
            capture_message(f"Command {args.cmd} failed.")

        else:
            print(ret.stdout.decode("utf-8"))
            print("Success!")

    except Exception as exc:
        capture_exception(exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
