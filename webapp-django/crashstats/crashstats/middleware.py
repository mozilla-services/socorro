# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.shortcuts import render
from django.utils.encoding import smart_str


class SetRemoteAddrFromRealIP:
    """
    Middleware that sets REMOTE_ADDR based on HTTP_X_REAL_IP, if the
    latter is set. This is useful if you're sitting behind a reverse proxy that
    causes each request's REMOTE_ADDR to be set to 127.0.0.1.

    Note that this does NOT validate HTTP_X_REAL_IP. If you're not behind
    a reverse proxy that sets HTTP_X_REAL_IP automatically, do not use
    this middleware. Anybody can spoof the value of HTTP_X_REAL_IP, and
    because this sets REMOTE_ADDR based on HTTP_X_REAL_IP, that means
    anybody can "fake" their IP address. Only use this when you can absolutely
    trust the value of HTTP_X_REAL_IP.

    """

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        self.process_request(request)
        return self.get_response(request)

    def process_request(self, request):
        real_ip = request.headers.get("X-Real-Ip")
        if real_ip:
            request.META["REMOTE_ADDR"] = real_ip


class Pretty400Errors:
    """Convert HTTP 400 errors to JSON if client doesn't accept html"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
        if (
            response.status_code == 400
            and response["Content-Type"].startswith("text/html")
            and not is_ajax
        ):
            return render(
                request, "400.html", {"error": smart_str(response.content)}, status=400
            )
        return response
