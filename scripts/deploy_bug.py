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
HOST = 'https://crash-stats.mozilla.com'


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


def fetch_current_revision(host):
    # Try /__version__ and fall back to /api/Status/
    resp = fetch(host + '/__version__')
    if 'commit' in resp:
        return resp['commit']

    resp = fetch(host + '/api/Status/')
    return resp['socorro_revision']


def ref_to_tag(ref):
    """Converts a git ref to a socorro tag by plucking off the name

    >>> ref_to_tag('refs/tags/302')
    '302'

    """
    return ref.split('/')[-1]


def get_tags():
    # Figure out and print the current tag and the next tag
    tag_data = fetch_tags_from_github('mozilla-services', 'socorro')
    tags = [ref_to_tag(item['ref']) for item in tag_data]

    # Drop tags that start with "v" since we don't do that anymore
    tags = [tag for tag in tags if not tag.startswith('v')]

    # Convert to int and drop any that don't
    tags = [int(tag) for tag in tags if tag.isdigit()]
    return tags


def main(argv):
    # Fetch tags as numbers (e.g. 309)
    tags = get_tags()

    # The current tag is the max of that
    current_tag = max(tags)

    # The next tag is current_tag + 1
    next_tag = current_tag + 1

    # Figure out the current version
    sha = fetch_current_revision(HOST)

    # Get the commits between the currently deployed version and what's in
    # master tip and if there's nothing to deploy, then we're done!
    resp = fetch_history_from_github('mozilla-services', 'socorro', sha)
    if resp['status'] != 'ahead':
        print('Nothing to deploy!')
        return

    commits = resp['commits']

    print('summary:')
    print('socorro deploy: %s' % next_tag)
    print()
    print('description:')
    print()
    print('We want to do a Socorro -prod deploy today tagged %s.' % next_tag)
    print()
    print('It consists of the following:')
    print()
    print('(current tag: %s - %s)' % (current_tag, sha[:8]))

    # Print the commits out skipping merge commits
    for commit in commits:
        if len(commit['parents']) > 1:
            continue

        print('%s: %s' % (
            commit['sha'][:8],
            commit['commit']['message'].splitlines()[0][:80]
        ))

    print('(next tag: %s - %s)' % (next_tag, commits[-1]['sha'][:8]))
    print()

    # Print all possible post-deploy steps--we winnow the unnecessary ones when
    # writing up the bug
    print('After deploy:')
    print()
    print('* update -prod admin node')
    print('* make configuration changes')
    print('* perform alembic migrations')
    print('* perform Django migrations')
    print('* verify webapp functionality')
    print()

    # Any additional notes
    print('Additional notes:')
    print()
    print('* ')
    print()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
