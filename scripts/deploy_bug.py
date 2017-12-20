#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
This script generates the summary and description for a Socorro -prod
deploy bug.

Usage:

    python scripts/deploy_bug.py

Then copy and paste the bits it prints out.
"""

from __future__ import print_function

import sys

import requests


GITHUB_API = 'https://api.github.com/'


def fetch(url, is_json=True):
    resp = requests.get(url)
    assert resp.status_code == 200, str(resp.status_code) + ' ' + resp.content
    if is_json:
        return resp.json()
    return resp.content


def fetch_tags_from_github(user, repo):
    return fetch(GITHUB_API + 'repos/%s/%s/git/refs/tags' % (user, repo))


def fetch_history_from_github(user, repo, from_sha):
    return fetch(GITHUB_API + 'repos/%s/%s/compare/%s...master' % (user, repo, from_sha))


def print_row(*args):
    row_template = '%-13s ' * len(args)
    print(row_template % args)


def ref_to_tag(ref):
    """Converts a git ref to a socorro tag by plucking off the name

    >>> ref_to_tag('refs/tags/302')
    '302'

    """
    return ref.split('/')[-1]


def main(argv):
    # Figure out and print the current tag and the next tag
    tag_data = fetch_tags_from_github('mozilla-services', 'socorro')
    tags = [ref_to_tag(item['ref']) for item in tag_data]

    # Drop tags that start with "v" since we don't do that anymore
    tags = [tag for tag in tags if not tag.startswith('v')]

    # Convert to int and drop any that don't
    tags = [int(tag) for tag in tags if tag.isdigit()]

    # The current tag is the max of that
    current_tag = max(tags)

    # The next tag is current_tag + 1
    next_tag = current_tag + 1

    print('summary:')
    print('socorro deploy: %s' % next_tag)
    print()

    print('description:')
    print()

    print('We want to do a Socorro -prod deploy today tagged %s.' % next_tag)
    print()

    print('It consists of the following:')
    print()

    # Figure out and print the version

    # NOTE(willkg): This is the current infrastructure--the new infrastructure
    # uses the /__version__ endpoint. We'll need to update this when we switch
    # over.
    resp = fetch('https://crash-stats.mozilla.com/api/Status/')
    sha = resp['socorro_revision']

    # Figure out and print everything that's going out
    print('(current tag: %s - %s)' % (current_tag, sha[:8]))
    resp = fetch_history_from_github('mozilla-services', 'socorro', sha)
    if resp['status'] == 'ahead':
        # Drop all the merge commits
        commits = [commit for commit in resp['commits'] if len(commit['parents']) == 1]

        # Print the commits out
        for commit in commits:
            print_row(
                commit['sha'][:8],
                commit['commit']['message'].splitlines()[0][:80]
            )
    print('(next tag: %s - %s)' % (next_tag, commits[-1]['sha'][:8]))
    print()

    # Print post-deploy steps
    print('After deploy:')
    print()
    print('* update -prod admin node')
    print('* make configuration changes')
    print('* perform alembic migrations')
    print('* perform django migrations')
    print('* verify webapp functionality')
    print()

    # Any additional notes
    print('Additional notes:')
    print()
    print('* ')
    print()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
