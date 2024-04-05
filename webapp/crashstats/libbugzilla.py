# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Convenience functions for Bugzilla-related things.
"""


from itertools import islice


# Maximum number of frames to include in bug comment
MAX_FRAMES = 10


def mini_glom(structure, path, default):
    """Returns the value at path in structure or default.

    .. Note::

       We use this instead of glom so we don't have to pull in another dependency in
       this module which might be used externally.

    :arg structure: the Python structure made up of maps, lists, and tuples
    :arg path: a dotted path leading to the item
    :arg default: a default if there is no item at path

    :returns: value

    :raises KeyError: if no default and the path part is a key in a map
    :raises IndexError: if no default and the path part is an index in a list/tuple

    """
    node = structure
    for part in path.split("."):
        if isinstance(node, (tuple, list)):
            part_index = int(part)
            if len(node) >= part_index:
                node = node[part_index]
            else:
                return default

        else:
            if part in node:
                node = node[part]
            else:
                return default

    return node


def truncate(text, max_length):
    if len(text) > max_length:
        return text[: max_length - 3] + "..."
    return text


def minidump_thread_to_frames(thread):
    """Build frame information from minidump output for a thread

    Extract frame info for the top frames of a crashing thread to be included in the
    Bugzilla summary when reporting the crash.

    :arg thread: dict of thread information including "frames" list

    :returns: list of frame information dicts with keys "frame", "module", "signature",
        "source"

    """

    def frame_generator(thread):
        """Yield frames in a thread factoring in inlines"""
        for frame in thread["frames"]:
            for inline in frame.get("inlines") or []:
                yield {
                    "frame": frame.get("frame", "?"),
                    "module": frame.get("module", ""),
                    "signature": inline["function"],
                    "file": inline["file"],
                    "line": inline["line"],
                }

            yield frame

    frames = []
    for frame in islice(frame_generator(thread), MAX_FRAMES):
        # Source is an empty string if data isn't available
        source = frame.get("file") or ""
        if source and frame.get("line") is not None:
            source = f"{source}:{frame['line']}"

        signature = truncate(frame.get("signature") or "", 80)

        frames.append(
            {
                "frame": frame.get("frame", "?"),
                "module": frame.get("module") or "?",
                "signature": signature,
                "source": source,
            }
        )

    return frames


def java_exception_to_frames(stack):
    """Build frame information from java_exception stack

    :arg stack: a java_exception values item

    :returns: list of frame information dicts with keys "frame", "module", "signature",
        "source"

    """
    frames = []
    for i, frame in enumerate(islice(stack, MAX_FRAMES)):
        source = frame.get("filename") or "<nofile>"
        if source and frame.get("lineno") is not None:
            source = f"{source}:{frame['lineno']}"

        frames.append(
            {
                "frame": i,
                "module": frame.get("module") or "?",
                "signature": truncate(frame.get("function") or "?", 80),
                "source": source,
            }
        )

    return frames


def crash_report_to_description(crash_report_url, processed_crash):
    lines = [
        f"Crash report: {crash_report_url}",
    ]
    if processed_crash.get("moz_crash_reason"):
        lines.append("")
        lines.append(f"MOZ_CRASH Reason: ```{processed_crash['moz_crash_reason']}```")
    elif processed_crash.get("reason"):
        lines.append("")
        lines.append(f"Reason: ```{processed_crash['reason']}```")

    frames = None
    if threads := mini_glom(processed_crash, "json_dump.threads", default=None):
        # Generate frames from the stackwalker output from parsing a minidump
        thread_index = processed_crash.get("crashing_thread")
        if thread_index is None:
            lines.append("")
            lines.append("No crashing thread identified; using thread 0.")
        thread_index = thread_index or 0
        frames = minidump_thread_to_frames(threads[thread_index])

    if not frames:
        frames = mini_glom(
            processed_crash,
            "java_exception.exception.values.0.stacktrace.frames",
            default=None,
        )
        # Generate frames from java_exception structure
        if frames:
            frames = java_exception_to_frames(frames)

    if frames:
        lines.append("")
        if len(frames) == 1:
            lines.append(f"Top {len(frames)} frame:")
        else:
            lines.append(f"Top {len(frames)} frames:")
        lines.append("```")
        for frame in frames:
            signature = truncate(frame["signature"], 80)
            lines.append(
                f"{frame['frame']:<2} {frame['module']}  {signature}  {frame['source']}"
            )
        lines.append("```")

    elif processed_crash.get("java_stack_trace"):
        # If there are no frames from a parsed minidump or a java_except value, then use
        # the java_stack_trace if that exists; this is a big string blob, so we convert
        # tabs to spaces, truncate it at 5,000 characters but don't otherwise format it
        java_stack_trace = processed_crash["java_stack_trace"].replace("\t", "    ")
        lines.append("")
        lines.append("Java stack trace:")
        lines.append("```")
        lines.append(truncate(java_stack_trace, 5000))
        lines.append("```")

    else:
        lines.append("")
        lines.append("No stack.")

    # Remove any trailing white space--we don't want to waste characters
    lines = [line.rstrip() for line in lines]

    return "\n".join(lines)
