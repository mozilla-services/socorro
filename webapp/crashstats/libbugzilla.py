# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Convenience functions for Bugzilla-related things.
"""


from itertools import islice


# Maximum number of frames to include in bug comment
MAX_FRAMES = 10


def truncate(text, max_length):
    if len(text) > max_length:
        return text[: max_length - 3] + "..."
    return text


def bugzilla_thread_frames(thread):
    """Build frame information for bug creation link

    Extract frame info for the top frames of a crashing thread to be included in the
    Bugzilla summary when reporting the crash.

    :arg thread: dict of thread information including "frames" list

    :returns: list of frame information dicts

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
        if frame.get("line"):
            source += ":{}".format(frame["line"])

        signature = frame.get("signature") or ""

        signature = truncate(signature, 80)

        frames.append(
            {
                "frame": frame.get("frame", "?"),
                "module": frame.get("module") or "?",
                "signature": signature,
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

    # If there's a java_stack_trace, add that; this is a big string blob, so we truncate
    # it at 5,000 characters but don't otherwise format it
    if processed_crash.get("java_stack_trace"):
        lines.append("")
        lines.append("Java stack trace:")
        lines.append("```")
        lines.append(truncate(processed_crash["java_stack_trace"], 5000))
        lines.append("```")

    # Generate frames from the stackwalker output from parsing a minidump
    frames = None
    threads = processed_crash.get("json_dump", {}).get("threads")
    if threads:
        if processed_crash.get("crashing_thread") is None:
            lines.append("")
            lines.append("No crashing thread identified; using thread 0.")

        thread_index = processed_crash.get("crashing_thread") or 0
        frames = bugzilla_thread_frames(threads[thread_index])

        if frames:
            lines.append("")
            lines.append(f"Top {len(frames)} frames of crashing thread:")
            lines.append("```")
            for frame in frames:
                signature = truncate(frame["signature"], 80)
                lines.append(
                    f"{frame['frame']:<2} {frame['module']}  {signature}  {frame['source']}"
                )
            lines.append("```")

        else:
            lines.append("")
            lines.append("No stack.")

    # Remove any trailing white space--we don't want to waste characters
    lines = [line.rstrip() for line in lines]

    return "\n".join(lines)
