# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
import os
import sys


class WrappedTextHelpFormatter(argparse.HelpFormatter):
    """Subclass that wraps description and epilog text taking paragraphs into account"""

    def _fill_text(self, text, width, indent):
        """Wraps text like HelpFormatter, but doesn't squash lines

        This makes it easier to do lists and paragraphs.

        """
        parts = text.split("\n\n")
        for i, part in enumerate(parts):
            # Check to see if it's a bulleted list--if so, then fill each line
            if part.startswith("* "):
                subparts = part.split("\n")
                for j, subpart in enumerate(subparts):
                    subparts[j] = super()._fill_text(subpart, width, indent)
                parts[i] = "\n".join(subparts)
            else:
                parts[i] = super()._fill_text(part, width, indent)

        return "\n\n".join(parts)


class FlagAction(argparse.Action):
    """Facilitates --flag, --no-flag arguments

    Usage::

        parser.add_argument(
            '--flag', '--no-flag', action=FlagAction, default=True,
            help='whether to enable flag'
        )


    Which allows you to do::

        $ command
        $ command --flag
        $ command --no-flag


    And the help works nicely, too::

        $ command --help
        ...
        optional arguments:
           --flag, --no-flag  whether to enable flag

    """

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        # Validate option strings--we should have a no- option for every option
        options = [opt.strip("-") for opt in option_strings]

        yes_options = [opt for opt in options if not opt.startswith("no-")]
        no_options = [opt[3:] for opt in options if opt.startswith("no-")]

        if sorted(yes_options) != sorted(no_options):
            raise ValueError("There should be one --no option for every option value.")

        super().__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        if option_string.startswith("--no"):
            value = False
        else:
            value = True
        setattr(namespace, self.dest, value)


class FallbackToPipeAction(argparse.Action):
    """Fallback to load strings piped from stdin

    This action reads from stdin when the positional arguments were omitted. It
    expects one value per line, and at least one value.

    This does not work with named arguments, since the action is not called
    when a named argument is omitted.

    To use this as a fallback for positional arguments:
    > parser.add_argument('name', nargs='*', action=FallbackToPipeAction)
    """

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        """Initialize the FallbackToPipeAction.

        :param option_strings: Names for non-positional arguments.
        :param dest: The destination attribute on the parser
        :param nargs: The number of arguments, must be '*' for zero or more
        :param kwargs: Additional parameters for the parser argument
        """
        if option_strings:
            raise ValueError("This action does not work with named arguments")
        if nargs != "*":
            # For nargs='*', the action is called with an empty list.
            # For other values ('?', '+', 1), the action isn't called, so we
            # can't fallback to reading from stdin.
            raise ValueError("nargs should be '*'")
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        """Call the FallbackToPipeAction.

        If the arguments were set on the command line, use them. Otherwise,
        try reading from stdin (the pipe). If a pipe was not provided or was
        empty, parser.error is called to print usage and exit early.

        :param parser: The argument parser
        :param namespace: The destination namespace
        :param values: The parsed values, an empty list if omitted
        :param option_string: The option name, or None for positional arguments
        """

        if not values:
            if sys.stdin.isatty():
                # There is no data being piped to the script, but instead it
                # is an interactive TTY. Instead of blocking while waiting
                # for input, exit on the missing parameter
                parser.error(
                    'argument "%s" was omitted and stdin is not a pipe.' % self.dest
                )
            else:
                # Data is being piped to this script. Remove trailing newlines
                # from reading sys.stdin as line iterator.
                type_func = self.type or str
                values = [type_func(item.rstrip()) for item in sys.stdin]
                if not values:
                    parser.error(
                        'argument "%s" was omitted and stdin was empty.' % self.dest
                    )

        setattr(namespace, self.dest, values)


def get_envvar(key, default=None):
    if default is None:
        return os.environ[key]
    return os.environ.get(key, default)
