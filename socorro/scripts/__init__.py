# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import os


class WrappedTextHelpFormatter(argparse.HelpFormatter):
    """Subclass that wraps description and epilog text taking paragraphs into account"""

    def _fill_text(self, text, width, indent):
        """Wraps text like HelpFormatter, but doesn't squash lines

        This makes it easier to do lists and paragraphs.

        """
        parts = text.split('\n\n')
        for i, part in enumerate(parts):
            # Check to see if it's a bulleted list--if so, then fill each line
            if part.startswith('* '):
                subparts = part.split('\n')
                for j, subpart in enumerate(subparts):
                    subparts[j] = super(WrappedTextHelpFormatter, self)._fill_text(
                        subpart, width, indent
                    )
                parts[i] = '\n'.join(subparts)
            else:
                parts[i] = super(WrappedTextHelpFormatter, self)._fill_text(part, width, indent)

        return '\n\n'.join(parts)


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
        options = [opt.strip('-') for opt in option_strings]

        yes_options = [opt for opt in options if not opt.startswith('no-')]
        no_options = [opt[3:] for opt in options if opt.startswith('no-')]

        if sorted(yes_options) != sorted(no_options):
            raise ValueError('There should be one --no option for every option value.')

        super(FlagAction, self).__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        if option_string.startswith('--no'):
            value = False
        else:
            value = True
        setattr(namespace, self.dest, value)


def get_envvar(key, default=None):
    if default is None:
        return os.environ[key]
    return os.environ.get(key, default)
