# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from functools import cache

from markdown_it import MarkdownIt


def render_add_target_blank(self, tokens, idx, options, env):
    # Sets the target to _blank for all links
    tokens[idx].attrSet("target", "_blank")
    return self.renderToken(tokens, idx, options, env)


@cache
def get_markdown():
    """Returns a markdown parser"""
    md = MarkdownIt().disable("image")
    md.add_render_rule("link_open", render_add_target_blank)
    return md
