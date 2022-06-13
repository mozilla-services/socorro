# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
import importlib
import re
import sys


DESCRIPTION = """
Generates documentation for the specified signature generation pipeline.
Outputs the documentation in restructured text format.
"""


def import_rules(rules):
    module_path, attr = rules.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, attr)


def indent(text, prefix):
    text = text.replace("\n", "\n" + prefix)
    return text.strip()


LEAD_WHITESPACE = re.compile(r"^[ \t]*")


def dedent_docstring(text):
    text_lines = text.splitlines()

    # Figure out the indentation of all the lines to figure out how much to
    # dedent by
    leads = []
    for line in text_lines:
        if len(line.strip()) == 0:
            continue
        leads.append(LEAD_WHITESPACE.match(line).group(0))

    if leads and len(leads[0]) == 0:
        leads.pop(0)

    if not leads:
        return text

    # Let's use the first non-empty line to dedent the text with. It's
    # possible this isn't a great idea. If that's the case, we can figure
    # out a different way to do it.
    dedent_str = leads[0]
    dedent_amount = len(dedent_str)

    for i, line in enumerate(text_lines):
        if line.startswith(dedent_str):
            text_lines[i] = text_lines[i][dedent_amount:]

    return "\n".join(text_lines)


def get_doc(cls):
    return "**Rule: %s**\n\n%s" % (
        cls.__class__.__name__,
        dedent_docstring(cls.__doc__),
    )


def main(argv=None):
    """Generates documentation for signature generation pipeline"""
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        "pipeline", help="Python dotted path to rules pipeline to document"
    )
    parser.add_argument("output", help="output file")

    if argv is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(argv)

    print("Generating documentation for %s in %s..." % (args.pipeline, args.output))

    rules = import_rules(args.pipeline)

    with open(args.output, "w") as fp:
        fp.write(".. THIS IS AUTOGEMERATED USING:\n")
        fp.write("   \n")
        fp.write("   %s\n" % (" ".join(sys.argv)))
        fp.write("   \n")
        fp.write("Signature generation rules pipeline\n")
        fp.write("===================================\n")
        fp.write("\n")
        fp.write("\n")
        fp.write(
            "This is the signature generation pipeline defined at ``%s``:\n"
            % args.pipeline
        )
        fp.write("\n")

        for i, rule in enumerate(rules):
            li = "%s. " % (i + 1)
            fp.write("%s%s\n" % (li, indent(get_doc(rule), " " * len(li))))
            fp.write("\n")
