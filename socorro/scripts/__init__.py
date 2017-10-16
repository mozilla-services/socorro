import argparse


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
        super(FlagAction, self).__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        if option_string.startswith('--no'):
            value = False
        else:
            value = True
        setattr(namespace, self.dest, value)
