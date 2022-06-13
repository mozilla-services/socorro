# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Directive for generating an ADR log from a directory of ADRs.

Usage::

    .. adrlog:: PATH

    .. adrlog:: PATH
       :urlroot: https://github.com/mozilla-services/socorro/tree/main/docs/adr

Required parameters:

* PATH: the path relative to the docs/ directory to the ADR directory

Optional parameters:

* urlroot: the absolute url where the ADR files are located

"""

import dataclasses
import os
import os.path
from typing import Dict

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.statemachine import ViewList


@dataclasses.dataclass(order=True)
class ADR:
    adr_id: str
    name: str
    metadata: Dict[str, str]


def fetch_adr(filepath):
    """Parses an ADR at filepath and returns ADR

    :param filepath: path to ADR file in Markdown format

    :returns: ADR

    """
    with open(filepath) as fp:
        source = fp.read()

    # NOTE(willkg): I didn't want to require a markdown parser, so this just looks at
    # Socorro's ADR log structure which is a header followed by a list of meta
    # information

    adr_id = os.path.splitext(os.path.basename(filepath))[0]
    name = ""
    metadata = {}

    STATE_DEFAULT, STATE_LIST = range(2)

    state = STATE_DEFAULT
    for line in source.splitlines():
        line = line.rstrip()

        if state == STATE_DEFAULT:
            if not line:
                continue

            elif line.startswith("# "):
                name = line[2:]

            elif line.startswith("- "):
                state = STATE_LIST
                if ":" not in line:
                    continue

                key, val = line.split(":", 1)
                metadata[key[2:].strip()] = val.strip()

        if state == STATE_LIST:
            if not line:
                # If we hit an empty line while parsing the first list, then we're done
                # and we can stop parsing
                break

            if ":" not in line:
                continue

            key, val = line.split(":", 1)
            metadata[key[2:].strip()] = val.strip()

    return ADR(adr_id=adr_id, name=name, metadata=metadata)


def fetch_adrs(filepath):
    """Given a filepath to an ADRs directory, returns the log

    :param filepath: the filepath to ADR directory

    :returns: list of ADRs

    """
    adrs = []
    for fn in os.listdir(filepath):
        if not fn.endswith(".md"):
            continue
        if fn in ["index.md", "README.md", "template.md"]:
            continue
        fn = os.path.join(filepath, fn)
        adrs.append(fetch_adr(fn))
    return adrs


def build_table(table):
    """Generates reST for a table.

    :param table: a 2d array of rows and columns

    :returns: list of strings

    """
    output = []

    col_size = [0] * len(table[0])
    for row in table:
        for i, col in enumerate(row):
            col_size[i] = max(col_size[i], len(col))

    col_size = [width + 2 for width in col_size]

    # Build header
    output.append("  ".join("=" * width for width in col_size))
    output.append(
        "  ".join(
            header + (" " * (width - len(header)))
            for header, width in zip(table[0], col_size)
        )
    )
    output.append("  ".join("=" * width for width in col_size))

    # Iterate through rows
    for row in table[1:]:
        output.append(
            "  ".join(
                col + (" " * (width - len(col)))
                for col, width in zip(row, col_size)
            )
        )
    output.append("  ".join("=" * width for width in col_size))
    return output


class ADRLogDirective(Directive):
    """Directive for showing an ADR log."""

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False

    option_spec = {
        "urlroot": directives.unchanged_required,
    }

    def add_line(self, line, source, *lineno):
        """Add a line to the result"""
        self.result.append(line, source, *lineno)

    def generate_log(self, filepath, urlroot):
        def linkify(adr_id, urlroot):
            if urlroot:
                return f"`{adr_id} <{urlroot}/{adr_id}.md>`_"
            return adr_id

        adrs = fetch_adrs(filepath)
        adrs.sort(reverse=True)  # key=lambda adr: adr.adr_id, reverse=True)

        table = [["Date", "ADR id", "Status", "Name", "Deciders"]]
        for adr in adrs:
            table.append(
                [
                    adr.metadata.get("Date", "Unknown"),
                    linkify(adr.adr_id, urlroot),
                    adr.metadata.get("Status", "Unknown"),
                    adr.name,
                    adr.metadata.get("Deciders", "Unknown"),
                ]
            )

        sourcename = "adrlog %s" % filepath

        for line in build_table(table):
            self.add_line(line, sourcename)

    def run(self):
        if "urlroot" in self.options:
            urlroot = self.options["urlroot"]
        else:
            urlroot = ""

        self.reporter = self.state.document.reporter
        self.result = ViewList()

        filepath = os.path.abspath(self.arguments[0]).rstrip("/")
        self.generate_log(filepath, urlroot)

        if not self.result:
            return []

        node = nodes.paragraph()
        node.document = self.state.document
        self.state.nested_parse(self.result, 0, node)
        return node.children


def setup(app):
    """Register directive in Sphinx."""
    app.add_directive("adrlog", ADRLogDirective)

    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
