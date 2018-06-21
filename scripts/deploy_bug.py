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
    resp = fetch(host + '/__version__')
    return resp['commit']


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
    deployed_sha = fetch_current_revision(HOST)

    # Get the commits between the currently deployed version and what's in
    # master tip and if there's nothing to deploy, then we're done!
    resp = fetch_history_from_github('mozilla-services', 'socorro', deployed_sha)
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
    print('(current tag: %s - %s)' % (current_tag, deployed_sha[:7]))

    # Print the commits out skipping merge commits
    for commit in commits:
        if len(commit['parents']) > 1:
            continue

        # Use the first 7 characters of the commit sha
        sha = commit['sha'][:7]

        # Use the first line of the commit message which is the summary and
        # truncate it to 80 characters
        summary = commit['commit']['message']
        summary = summary.splitlines()[0]
        summary = summary[:80]

        # Figure out who did the commit prefering GitHub usernames
        who = commit['author']
        if not who:
            who = '?'
        else:
            who = who.get('login', '?')

        print('%s: %s (%s)' % (sha, summary, who))

    head_sha = commits[-1]['sha'][:7]
    print('(next tag: %s - %s)' % (next_tag, head_sha))
    print()

    # Any additional things to note
    print('Additional things to note:')
    print()
    print('* ')
    print()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
