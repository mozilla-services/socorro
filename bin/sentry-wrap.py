#!/usr/bin/python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Wraps a command such that if it fails, an error report is sent to the Sentry service
# specified by SENTRY_DSN in the environment.
#
# Usage: python bin/sentry-wrap.py wrap -- [CMD]
#    Wraps a process in error-reporting Sentry goodness.
#
# Usage: python bin/sentry-wrap.py test
#    Tests Sentry configuration and connection.


import os
import shlex
import subprocess
import sys
import time
import traceback

import click
import sentry_sdk
from sentry_sdk import capture_exception, capture_message


@click.command()
@click.option("--timeout", default=300, help="Timeout in seconds to wait for process before giving up.")
@click.argument("cmd", nargs=-1)
@click.pass_context
def wrap_process(ctx, timeout, cmd):
    sentry_dsn = os.environ.get("SENTRY_DSN")

    if not sentry_dsn:
        print("SENTRY_DSN is not defined. Exiting.")
        sys.exit(1)

    if not cmd:
        raise click.UsageError("CMD required")

    start_time = time.time()

    sentry_sdk.init(sentry_dsn)

    cmd = " ".join(cmd)
    cmd_args = shlex.split(cmd)
    print(f"Running: {cmd_args}")

    try:
        ret = subprocess.run(cmd_args, capture_output=True, timeout=timeout)
        if ret.returncode != 0:
            sentry_sdk.set_context(
                "status",
                {
                    "exit_code": ret.returncode,
                    "stdout": ret.stdout.decode("utf-8"),
                    "stderr": ret.stderr.decode("utf-8"),
                },
            )
            capture_message(f"Command {cmd!r} failed.")
            print(ret.stdout.decode("utf-8"))
            print(ret.stderr.decode("utf-8"))
            time_delta = (time.time() - start_time) / 1000
            print(f"Fail. {time_delta:.2f}s")
            ctx.exit(1)

        else:
            print(ret.stdout.decode("utf-8"))
            time_delta = (time.time() - start_time) / 1000
            print(f"Success! {time_delta:.2f}s")

    except click.exceptions.Exit:
        raise

    except Exception as exc:
        capture_exception(exc)
        traceback.print_exc()
        time_delta = (time.time() - start_time) / 1000
        print(f"Fail. {time_delta:.2f}s")
        ctx.exit(1)


if __name__ == "__main__":
    wrap_process()
