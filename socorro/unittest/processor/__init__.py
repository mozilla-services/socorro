# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from configman.dotdict import DotDict as DotDict

from socorro.signature.rules import CSignatureTool


csig_config = DotDict()
csig_config.irrelevant_signature_re = ""
csig_config.prefix_signature_re = ""
csig_config.signatures_with_line_numbers_re = ""
csig_config.signature_sentinels = []
csig_config.collapse_arguments = True
c_signature_tool = CSignatureTool()


def create_basic_fake_processor():
    """Create fake processor configuration."""
    fake_processor = DotDict()
    fake_processor.c_signature_tool = c_signature_tool
    fake_processor.config = DotDict()
    fake_processor.processor_notes = []
    return fake_processor


def get_basic_config():
    return DotDict()
