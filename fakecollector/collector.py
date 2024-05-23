#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# This is a fake collector that handles incoming HTTP POST requests to /submit and logs
# headers, annotations, and files in the submission.

import json
import logging

import click
from werkzeug.exceptions import HTTPException, MethodNotAllowed
from werkzeug.formparser import parse_form_data
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Request, Response

from socorro.lib.liblogging import set_up_logging
from socorro.lib.libooid import create_new_ooid


def truncate(val, length=80):
    if len(val) > 80:
        val = val[:80-3] + "..."
    return val


class App:
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.App")
        self.url_map = Map([
            Rule("/submit", endpoint="submit"),
        ])

    def __call__(self, environ, start_response):
        request = Request(environ)
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            response = getattr(self, f"on_{endpoint}")(request, **values)
            return response(environ, start_response)
        except HTTPException:
            self.logger.exception("exception in handling")

    def on_submit(self, request):
        """Handle POST /submit requests

        These are crash report submissions, so it parses the payload and then logs
        headers, annotations, and files found in the payload.

        It always returns a CrashID response.

        """
        if request.method != "POST":
            raise MethodNotAllowed(["POST"])

        self.logger.info("handling POST /submit")

        content_length = int(request.headers["Content-Length"])
        self.logger.info("content_length: %s", f"{content_length:,}")

        # "multipart/form-data" or "multipart/mixed"
        content_type = request.headers["Content-Type"]
        self.logger.info("content_type: %s", content_type)

        user_agent = request.headers["User-Agent"]
        self.logger.info("user-agent: %s", user_agent)

        # "gzip" or anything else
        content_encoding = request.headers.get("Content-Encoding", "")
        self.logger.info("content_encoding: %s", content_encoding)

        stream, form, files = parse_form_data(request.environ, max_content_length=content_length)
        crash_id = form.get("uuid") or create_new_ooid()
        for key, val in form.to_dict().items():
            if key == "extra":
                data = json.loads(val)
                for data_key, data_val in data.items():
                    self.logger.info("annotation (extra): %s=%s", data_key, truncate(data_val))
            else:
                self.logger.info("annotation: %s=%s", key, truncate(val))

        for key, filestorage in files.items():
            data = filestorage.stream.read()
            self.logger.info("file: %s %s %s", key, f"{len(data):,}", filestorage.content_type)

        return Response(f"CrashID={crash_id}")


@click.command
@click.option("--host", default="0.0.0.0", help="host to bind to")
@click.option("--port", default=8000, type=int, help="port to listen on")
def main(host, port):
    set_up_logging(local_dev_env=True, hostname="localhost")

    from werkzeug.serving import run_simple
    app = App()
    run_simple(host, port, app, use_debugger=True, use_reloader=True)


if __name__ == '__main__':
    from collector import main
    main()
