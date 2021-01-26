# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Utility functions for parsing and manipulating JavaStackTrace field
contents.
"""

import copy

import jsonschema
from more_itertools import peekable

from socorro.schemas import JAVA_EXCEPTION_SCHEMA


class JavaStackTrace:
    def __init__(self, exception_class, exception_message, stack, additional):
        self.exception_class = exception_class
        self.exception_message = exception_message
        self.stack = stack
        self.additional = additional

    def to_public_string(self):
        """Builds stack trace with parts of the exception that don't contain PII

        Currently, this skips the exception message which can contain data
        related to the exception and might have PII in it.

        It also skips the "Suppressed" and "Caused by" sections because those
        can have exception messages, too.

        """
        text = "%s\n%s" % (
            self.exception_class,
            "\n".join(["\t%s" % line for line in self.stack]),
        )
        return text


class MalformedJavaStackTrace(Exception):
    pass


CLASS_MESSAGE, STACK, ADDITIONAL = range(3)


def parse_java_stack_trace(text):
    """Parses a ``JavaStackTrace`` text blob value into a JavaStackTrace instance

    :arg str text: the ``JavaStackTrace`` blob value

    :returns: a JavaStackTrace instance

    :raises MalformedJavaStackTrace: if there's a parsing error

    """
    if not text:
        raise MalformedJavaStackTrace("no text blob")

    stage = CLASS_MESSAGE
    lines = peekable(text.splitlines())

    new_exc = JavaStackTrace(
        exception_class="", exception_message="", stack=[], additional=[]
    )

    for line in lines:
        if not line.strip():
            continue

        if stage is CLASS_MESSAGE:
            if ":" in line:
                cls, msg = line.split(":", 1)
            else:
                cls, msg = line, ""

            # Append lines to the message until one of them starts with
            # a tab.
            next_line = lines.peek(None)
            while next_line is not None and not next_line.startswith("\tat "):
                msg = msg + "\n" + next(lines)
                next_line = lines.peek(None)

            new_exc.exception_class = cls.strip()
            new_exc.exception_message = msg.strip()

            stage = STACK

        elif stage is STACK:
            # Verify this has a tab at the beginning of the line
            if line[0] != "\t":
                raise MalformedJavaStackTrace("stack line missing tab")

            # Drop first tab from the line
            new_exc.stack.append(line[1:])

            next_line = lines.peek(None)
            if next_line and next_line.strip().startswith(
                ("Suppressed:", "Caused by:")
            ):
                stage = ADDITIONAL

        elif stage is ADDITIONAL:
            # Append all the rest of the stack trace as is
            new_exc.additional.append(line)

    return new_exc


class MalformedJavaException(Exception):
    pass


def validate_java_exception(data):
    """Validates a JavaException value

    :arg dict data: the JavaException value

    :raises MalformedJavaException: if the structure is malformed in some way

    """
    try:
        jsonschema.validate(data, JAVA_EXCEPTION_SCHEMA)
        return True
    except jsonschema.ValidationError as exc:
        raise MalformedJavaException(exc)


def sanitize_java_exception(data):
    """Removes PII from a JavaException value

    :arg dict data: the JavaException value

    :returns: a deep-copied copy of the data with PII redacted

    """
    data = copy.deepcopy(data)

    # NOTE(willkg): If we ever change this code, then we should think about reprocessing
    # all the Java crashes.
    for item in data["exception"]["values"]:
        stacktrace = item["stacktrace"]
        if "value" in stacktrace:
            stacktrace["value"] = "REDACTED"
    return data
