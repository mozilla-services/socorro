# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Generates the documentation for metrics."""

import importlib
import sys
import textwrap

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import ViewList


def build_table(table):
    col_size = [0] * len(table[0])
    for row in table:
        for i, col in enumerate(row):
            col_size[i] = max(col_size[i], len(col))

    col_size = [width + 2 for width in col_size]

    yield "  ".join("=" * width for width in col_size)
    yield "  ".join(
        header + (" " * (width - len(header)))
        for header, width in zip(table[0], col_size, strict=True)
    )
    yield "  ".join("=" * width for width in col_size)
    for row in table[1:]:
        yield "  ".join(
            col + (" " * (width - len(col)))
            for col, width in zip(row, col_size, strict=True)
        )
    yield "  ".join("=" * width for width in col_size)


class AutoMetricsDirective(Directive):
    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False

    option_spec = {}

    def add_line(self, line, source, *lineno):
        """Add a line to the result"""
        self.result.append(line, source, *lineno)

    def generate_docs(self, clspath):
        modpath, name = clspath.rsplit(".", 1)
        importlib.import_module(modpath)
        module = sys.modules[modpath]
        metrics = getattr(module, name)

        sourcename = f"metrics of {clspath}"

        # First build a table of metric items
        self.add_line("Table of metrics:", sourcename)
        self.add_line("", sourcename)

        table = []
        table.append(("Key", "Type"))
        for key, metric in metrics.items():
            table.append((f":py:data:`{key}`", metric["type"]))

        for line in build_table(table):
            self.add_line(line, sourcename)

        self.add_line("", sourcename)
        self.add_line("Metrics details:", sourcename)
        self.add_line("", sourcename)

        for key, metric in metrics.items():
            self.add_line(f".. py:data:: {key}", sourcename)
            self.add_line("", sourcename)
            self.add_line("", sourcename)
            self.add_line(f"   **Type**: ``{metric['type']}``", sourcename)
            self.add_line("", sourcename)
            self.add_line("", sourcename)
            for line in textwrap.dedent(metric["description"]).splitlines():
                self.add_line(f"   {line}", sourcename)
            self.add_line("", sourcename)
            self.add_line("", sourcename)

    def run(self):
        self.reporter = self.state.document.reporter
        self.result = ViewList()

        self.generate_docs(self.arguments[0])

        if not self.result:
            return []

        node = nodes.paragraph()
        node.document = self.state.document
        self.state.nested_parse(self.result, 0, node)
        return node.children


def setup(app):
    """Register directive in Sphinx."""
    app.add_directive("autometrics", AutoMetricsDirective)

    return {
        "version": 1.0,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
