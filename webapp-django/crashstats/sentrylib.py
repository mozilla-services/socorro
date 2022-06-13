# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Provides a before_send callable to sanitize Sentry events."""

import logging
from urllib.parse import parse_qsl, urlencode

import glom
import markus

metrics = markus.get_metrics("webapp.sentry")

# Logger for event processing
SENTRY_LOG_NAME = "crashstats.sentrylib"
logger = logging.getLogger(SENTRY_LOG_NAME)


def run_on(name, sanitizers=None):
    sanitizers = sanitizers or []

    def sanitizer_hook(thing, hint):
        for sanitizer in sanitizers:
            try:
                sanitizer(thing, hint)
            except Exception:
                metrics.incr(f"before_{name}_exception")

                # Make sure the exception is logged because otherwise we have no idea what
                # happened
                logger.exception(f"exception thrown when sanitizing: before_{name}")
                raise

        return thing

    return sanitizer_hook


def build_before_send():
    """Return a before_send sanitizer for the webapp.

    before_send is called before the event (such as an exception or message) is sent to
    Sentry. The webapp uses it to sanitize sensitive PII and security data. For more
    information, see:

    https://docs.sentry.io/platforms/python/configuration/filtering/

    """
    return run_on(
        name="send",
        sanitizers=[
            SanitizeHeaders(("Auth-Token", "X-Forwarded-For", "X-Real-Ip")),
            SanitizePostData(("csrfmiddlewaretoken",)),
            SanitizeQueryString(("code", "state")),
        ],
    )


def build_before_breadcrumb():
    return run_on(
        name="breadcrumb",
        sanitizers=[
            SanitizeSQLQueryCrumb(
                [
                    "email",
                    "username",
                    "password",
                    "session_data",
                    "session_key",
                    "tokens_token.key",
                    "auth_user.id",
                ]
            ),
        ],
    )


class SanitizeSQLQueryCrumb:
    """Filter SQL query breadcrumb containing sensitive keywords.

    This sanitizer expects a breadcrumb of the format:

    .. code-block:: json

       {
           'category': 'query',
           'message': 'SELECT * from...'
       }

    """

    def __init__(self, keywords):
        """Initialize a SanitizeSQLQueryCrumb.

        :param keywords: A sequence of keywords, such as column names, to trigger
            truncation

        """
        self.keywords = keywords
        self.all_keywords = list(keywords)
        for keyword in keywords:
            if "." in keyword:
                # table.column_name could be (PostgreSQL) quoted as well
                self.all_keywords.append(
                    ".".join('"%s"' % part for part in keyword.split("."))
                )

    def __repr__(self):
        return f"{self.__class__.__name__}({self.keywords!r})"

    def __call__(self, crumb, hint):
        """Sanitize SQL queries containing a keyword."""
        if crumb.get("category") != "query" or not crumb.get("message"):
            return

        message = crumb["message"]
        has_keyword = any(keyword in message for keyword in self.all_keywords)
        if has_keyword:
            crumb["message"] = "[filtered]"


class SanitizeSectionByKeyName:
    """Sanitize sensitive keys in a section of a Sentry event.

    This class provides a framework for sanitizing a section of a Sentry event. The
    section is identified by a dotted path, like "request.headers". A section is a dict
    that has values that should be sanitized if the key is sensitive.

    """

    # Set this to the dotted section path in derived classes
    section_path = None

    def __init__(self, names):
        """Initialize a SanitizeSectionByKeyName

        :param section: The dotted path identifying the section
        :param names: A sequence of sensitive names
        """
        assert self.section_path, "Need to set section_path"
        self.names = names

    def __repr__(self):
        return f"{self.__class__.__name__}({self.names!r})"

    def is_sensitive_key(self, key):
        """Return True if the key is a sensitive key."""
        return key in self.names

    def __call__(self, event, hint):
        """Sanitize a section with sensitive keys."""
        try:
            data = glom.glom(event, self.section_path)
        except glom.PathAccessError:
            return

        data_out = {}
        for key, value in data.items():
            if self.is_sensitive_key(key):
                data_out[key] = "[filtered]"
            else:
                data_out[key] = value
        glom.glom(event, glom.Assign(self.section_path, data_out))


class SanitizeHeaders(SanitizeSectionByKeyName):
    """Sanitize sensitive HTTP headers.

    This sanitizer expects an event of the format:

    .. code-block:: json

       {
           "request": {
               "headers": {
                   "Name": "value1",
                   ...
               }
           }
       }

    """

    section_path = "request.headers"

    def __init__(self, names):
        """Initialize a SanitizeHeaders

        :param names: A sequence of Header names (case insensitive) to sanitize
        """
        super().__init__(names)
        self._lower_names = [key.lower() for key in names]

    def is_sensitive_key(self, key):
        """Return True if the key is a case-insensitive match."""
        return key.lower() in self._lower_names


class SanitizePostData(SanitizeSectionByKeyName):
    """Sanitize sensitive POST data.

    This sanitizer expects an event of the format:

    .. code-block:: json

       {
           "request": {
               "data": {
                   "name1": "value1",
                   ...
               }
           }
       }

    """

    section_path = "request.data"


class SanitizeQueryString:
    """Mask sensitive values in the querystring.

    This sanitizer expects an event of the format:

    .. code-block:: json
        {
            "request": {
                "query_string": "foo=1&bar=2",
            }
        }

    The sanitizer will decode and encode the querystring, and some details may change
    outside of sanitization, such as non-canonical and maliciously formed querystrings.

    """

    def __init__(self, names):
        """Initialize an SanitizeQueryString

        :param names: A sequence of query string names to sanitize

        """
        self.names = names

    def __repr__(self):
        return f"{self.__class__.__name__}({self.names!r})"

    def __call__(self, event, hint):
        """Sanitize the querystring."""
        try:
            querystring = glom.glom(event, "request.query_string")
        except glom.PathAccessError:
            return

        out_pairs = []
        for name, value in parse_qsl(querystring, keep_blank_values=True):
            if name in self.names and value:
                value = "[filtered]"
            out_pairs.append((name, value))
        event["request"]["query_string"] = urlencode(out_pairs)
