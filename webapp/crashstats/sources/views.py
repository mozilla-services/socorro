# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from urllib.parse import urlsplit

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_for_filename, get_lexer_by_name, CppLexer
import requests

from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotFound,
)
from django.utils.html import escape

from crashstats.crashstats.decorators import track_view


# List of hosts that we will fetch source files from that we syntax highlight and return to the
# user in highlight_file view.
ALLOWED_SOURCE_HOSTS = ["gecko-generated-sources.s3.amazonaws.com"]

# List of allowed schemes
ALLOWED_SCHEMES = ["http", "https"]

# Maximum size in bytes before we switch to the TextLexer which is the null lexer
MAX_SIZE = 200_000


@track_view
def highlight_url(request):
    """Retrieves a generated source file and syntax highlights it

    Some stack frames are functions that are generated during the build process. Thus the stack
    frame itself isn't particularly helpful since the generated source file isn't available
    anywhere.

    Bug 1389217 and friends adjust the build process to capture the generated source and push it to
    S3.

    This view takes a URL for the generated source, retrieves it from S3, runs it through syntax
    highlighting, and returns that as an HTML page.

    NOTE(willkg): The output of pygments has CSS in the page, but no JS.

    """
    url = request.GET.get("url")

    if not url:
        return HttpResponseBadRequest("No url specified.")

    try:
        parsed = urlsplit(url)
    except ValueError:
        # If the value can't be parsed as a url, then treat it as if the document
        # doesn't exist. Bug #1902001.
        return HttpResponseNotFound("Document at URL does not exist.")

    # We will only pull urls from allowed hosts
    if parsed.netloc not in ALLOWED_SOURCE_HOSTS:
        return HttpResponseForbidden("Document at disallowed host.")

    if parsed.scheme not in ALLOWED_SCHEMES:
        return HttpResponseForbidden("Document at disallowed scheme.")

    resp = requests.get(url)
    if resp.status_code != 200:
        return HttpResponseNotFound("Document at URL does not exist.")

    filename = parsed.path.split("/")[-1]
    if len(resp.text) > MAX_SIZE:
        # If the file is too big, use the null lexer
        lexer = get_lexer_by_name("text")
    elif filename.endswith(".h"):
        # Pygments will default to C which we don't want, so override it here
        lexer = CppLexer()
    else:
        lexer = get_lexer_for_filename(filename)

    lines = []
    if request.GET.get("line"):
        try:
            lines = [int(request.GET.get("line"))]
        except ValueError:
            pass

    formatter = HtmlFormatter(
        full=True,
        title=escape(parsed.path),
        linenos="table",
        lineanchors="L",
        hl_lines=lines,
    )
    return HttpResponse(
        highlight(resp.text, lexer, formatter), content_type="text/html"
    )
