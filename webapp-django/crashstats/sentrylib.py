# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Provides a before_send callable to sanitize Sentry events."""

import logging
from urllib.parse import parse_qsl, urlencode

import glom
import markus

metrics = markus.get_metrics("webapp.sentry")

# Logger for event processing
SENTRY_LOG_NAME = "crashstats.sentrylib"
logger = logging.getLogger(SENTRY_LOG_NAME)


def get_before_send():
    """Return a before_send sanitizer for the webapp.

    before_send is called before the event (such as an exception or message) is sent to Sentry.
    The webapp uses it to sanitize sensitive PII and security data. For more information, see:

    https://docs.sentry.io/error-reporting/configuration/filtering/?platform=python
    """
    sanitizers = (
        SanitizeBreadcrumbs(
            (
                SanitizeSQLQueryCrumb(
                    (
                        "email",
                        "username",
                        "password",
                        "session_data",
                        "session_key",
                        "tokens_token.key",
                        "auth_user.id",
                    )
                ),
            )
        ),
        SanitizeHeaders(("Auth-Token", "X-Forwarded-For", "X-Real-Ip")),
        SanitizePostData(("csrfmiddlewaretoken",)),
        SanitizeQueryString(("code", "state")),
    )
    return SentrySanitizer(sanitizers=sanitizers)


class SentrySanitizer:
    """Sanitize Sentry events.

    SentryProcessor applies a series of simple sanitizers to the Sentry event.
    The sanitizers are callables (functions or classes implementing __call__) with the form:

    sanitizer(event, hint)

    Where:
    - event: the event dict, modified in-place
    - hint: the hint dict, which may be empty
    """

    def __init__(self, sanitizers=None):
        """Initialize a SentryProcessor.

        :arg sanitizers: A sequence of functions or callable instances
        """
        self.sanitizers = sanitizers or []

    def __repr__(self):
        return f"{self.__class__.__name__}(sanitizers={self.sanitizers!r})"

    def __call__(self, event, hint):
        """Sanitize a Sentry event.

        :arg event: A event, as a dict, modified in-place
        :arg hint: Context for the event, as a dict
        :return The event after modifications
        """
        logger.debug("sanitizing event=%s hint=%s", event, hint)

        try:
            for sanitizer in self.sanitizers:
                sanitizer(event, hint)
        except Exception:
            metrics.incr("before_send_exception")
            raise

        logger.debug("after sanitizing event=%s", event)
        return event


class SanitizeBreadcrumbs:
    """Process breadcrumbs in an event.

    Breadcrumbs are created as a process is executing, and sent with an event.  A crumb can be
    processed at creation, but most crumbs are discarded since an event isn't usually generated, so
    it makes sense to wait until event processing to sanitize it.  SanitizeBreadcrumbs runs
    breadcrumb sanitizers (that don't need data from the hint) at event processing rather than at
    crumb creation.

    This sanitizer expects an event of the format:

    .. code-block:: json
        {
            "breadcrumbs": [
                { 'category': ... },
            ]
        }
    """

    def __init__(self, crumb_sanitizers):
        """Initialize a SanitizeBreadcrumbs.

        :arg crumb_sanitizers: A sequence of breadcrumb sanitizer functions or callables
        """
        self.crumb_sanitizers = crumb_sanitizers

    def __repr__(self):
        return f"{self.__class__.__name__}({self.crumb_sanitizers!r})"

    def __call__(self, event, hint):
        """Filter each breadcrumb in an event."""
        for crumb in event.get("breadcrumbs", []):
            for crumb_sanitizer in self.crumb_sanitizers:
                # Pass an empty hint rather than the event's hint
                crumb = crumb_sanitizer(crumb, {})


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

        :arg keywords: A sequence of keywords, such as column names, to trigger truncation
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

    This class provides a framework for sanitizing a section of a Sentry event. The section is
    identified by a dotted path, like "request.headers". A section is a dict that has values
    that should be sanitized if the key is sensitive.
    """

    # Set this to the dotted section path in derived classes
    section_path = None

    def __init__(self, names):
        """Initialize a SanitizeSectionByKeyName

        :arg section: The dotted path identifying the section
        :arg names: A sequence of sensitive names
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

        :arg names: A sequence of Header names (case insensitive) to sanitize
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

    The sanitizer will decode and encode the querystring, and some details may change outside
    of sanitization, such as non-canonical and maliciously formed querystrings.
    """

    def __init__(self, names):
        """Initialize an SanitizeQueryString

        :arg names: A sequence of query string names to sanitize
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
