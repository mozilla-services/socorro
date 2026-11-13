# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Utility functions for parsing and manipulating JavaStackTrace field
contents.
"""

from glom import glom
from more_itertools import peekable


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


def format_exception_class(stacktrace) -> str:
    """
    Build the outermost exception's fully qualified Java class name.

    The client splits the class name at its last ``.`` into ``module`` and ``type``.
    - https://searchfox.org/firefox-main/rev/09b86521110cb23b77f5385a0e02aa4013a41f97/mobile/android/android-components/components/support/base/src/main/java/mozilla/components/support/base/ext/Throwable.kt#58-60
    Kotlin writes nested classes with ``.`` instead of Java's ``$``, so this
    puts the ``$`` back when ``module`` ends in a class name.

    Returns ``""`` if ``module`` or ``type`` is missing.
    """
    exception_module = stacktrace.get("module", "")
    exception_type = stacktrace.get("type", "")

    if not exception_module or not exception_type:
        # We can't build a class name without its components.
        return ""

    # Java naming conventions make packages lowercase (e.g. java.lang, android.view),
    # and classes start with an uppercase letter (e.g. WindowManager).
    # If the last part of `exception_module` starts with an uppercase letter, it's a
    # class, so the exception is nested inside it and needs a $.
    last_segment = exception_module.rsplit(".", 1)[-1]
    separator = "$" if last_segment[:1].isupper() else "."
    return f"{exception_module}{separator}{exception_type}"


def format_frame(frame) -> str:
    """
    Format a ``java_exception`` frame as a Java stack trace line.

    Matches the format of Java's ``StackTraceElement.toString()``, which is what
    crash reports' ``JavaStackTrace`` crash annotation uses:
    * ``at <module>.<function>(<filename>:<lineno>)``
    * ``(Native Method)`` if the method is native (``lineno == -2``)
    * ``(Unknown Source)`` if there's no ``filename``, even if there's a line number.
    * ``(<filename>)`` if there's a ``filename`` but no usable line number.

    See https://developer.android.com/reference/java/lang/StackTraceElement

    :arg frame: a frame dict from ``java_exception`` (keys: ``module``,
        ``function``, ``filename``, ``lineno``; all optional)

    :returns: the stack trace line without the leading tab
    """
    module = frame.get("module", "")
    function = frame.get("function", "")
    if module and function:
        name = f"{module}.{function}"
    elif module:
        name = module
    elif function:
        name = function
    else:
        name = ""

    lineno = frame.get("lineno")
    filename = frame.get("filename")

    if lineno == -2:
        location = "Native Method"
    elif not filename:
        location = "Unknown Source"
    elif lineno is not None and lineno >= 0:
        location = f"{filename}:{lineno}"
    else:
        location = filename

    return f"at {name}({location})"


def java_stack_trace_from_java_exception(java_exception) -> str | None:
    """
    ``JavaSignatureTool`` currently builds the signature from
    ``processed_crash.java_stack_trace``. This helper builds ``java_stack_trace``
    from ``processed_crash.java_exception``.

    Expects ``java_exception`` has been validated against the processed crash
    schema.
    """
    # Get the stacktrace for the outermost exception, since that's what we use to generate
    # signatures for Java crashes:
    # - https://searchfox.org/firefox-main/rev/09b86521110cb23b77f5385a0e02aa4013a41f97/mobile/android/android-components/components/support/base/src/main/java/mozilla/components/support/base/ext/Throwable.kt#20-26
    # - https://github.com/mozilla-services/socorro/blob/c02928fda86ee0aad5eb6e0c68a51ff5bd4ef6a9/socorro/signature/rules.py#L425-L504
    # The outermost exception is the last exception in the list per:
    # - https://searchfox.org/firefox-main/rev/09b86521110cb23b77f5385a0e02aa4013a41f97/mobile/android/android-components/components/support/base/src/main/java/mozilla/components/support/base/ext/Throwable.kt#74-85
    # - https://searchfox.org/firefox-main/rev/09b86521110cb23b77f5385a0e02aa4013a41f97/mobile/android/android-components/components/support/base/src/main/java/mozilla/components/support/base/ext/Throwable.kt#30-72
    stacktrace = glom(java_exception, "exception.values.-1.stacktrace", default=None)
    if not stacktrace:
        return None

    # Line 1 of `java_stack_trace`: the exception's fully qualified class name.
    exception_class = format_exception_class(stacktrace)
    if not exception_class:
        return None

    # Lines 2+ of `java_stack_trace`: one line per frame, with the top frame first.
    # Only the top frame (line 2) affects the signature. The rest are included, so
    # `java_stack_trace` is complete. With no frames, `java_stack_trace` is just the
    # class name.
    frames = stacktrace.get("frames") or []
    frame_lines = [f"\t{format_frame(frame)}" for frame in frames]
    return "\n".join([exception_class, *frame_lines])
