import logging

from socorro.lib.util import DotDict
from socorro.signature.rules import CSignatureTool


csig_config = DotDict()
csig_config.irrelevant_signature_re = ''
csig_config.prefix_signature_re = ''
csig_config.signatures_with_line_numbers_re = ''
csig_config.signature_sentinels = []
csig_config.collapse_arguments = True
c_signature_tool = CSignatureTool(csig_config)


def create_basic_fake_processor():
    """Creates fake processor configuration"""
    fake_processor = DotDict()
    fake_processor.c_signature_tool = c_signature_tool
    fake_processor.config = DotDict()
    fake_processor.config.logger = logging.getLogger(__name__)
    fake_processor.processor_notes = []
    return fake_processor
