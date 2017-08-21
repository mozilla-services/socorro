import argparse


class WrappedTextHelpFormatter(argparse.HelpFormatter):
    """Subclass that wraps description and epilog text taking paragraphs into account"""

    def _fill_text(self, text, width, indent):
        """Wraps text like HelpFormatter, but doesn't squash lines

        This makes it easier to do lists and paragraphs.

        """
        parts = text.split('\n')
        for i, part in enumerate(parts):
            parts[i] = super(WrappedTextHelpFormatter, self)._fill_text(part, width, indent)
        return '\n'.join(parts)
