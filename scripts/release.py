#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

"""
This script handles releases for this project.

This has two subcommands: ``make-bug`` and ``make-tag``. See the help text for
both.

This requires Python 3 to run.

repo: https://github.com/willkg/socorro-release/
sha: 90da286263152ca86622b9fd848ee884fe653cf2

"""

import argparse
import datetime
import json
import os
import shlex
import subprocess
import sys
from urllib.request import urlopen
from urllib.parse import urlencode


GITHUB_API = "https://api.github.com/"
GITHUB_USER = "mozilla-services"

BZ_URL = "https://bugzilla.mozilla.org/enter_bug.cgi"


def fetch(url, is_json=True):
    """Fetch data from a url

    This raises URLError on HTTP request errors. It also raises JSONDecode
    errors if it's not valid JSON.

    """
    fp = urlopen(url)
    data = fp.read()
    if is_json:
        return json.loads(data)
    return data


def fetch_history_from_github(owner, repo, from_tag):
    url = f"{GITHUB_API}repos/{owner}/{repo}/compare/{from_tag}...master"
    return fetch(url)


def check_output(cmdline, **kwargs):
    args = shlex.split(cmdline)
    return subprocess.check_output(args, **kwargs).decode("utf-8").strip()


def get_remote_name():
    """Figures out the right remote to use

    People name the git remote differently, so this figures out which one to
    use.

    """
    # Figure out remote to push tag to
    remote_output = check_output("git remote -v")

    for line in remote_output.splitlines():
        line = line.split("\t")
        if "mozilla-services" in line[1]:
            return line[0]

    raise Exception("Can't figure out remote name for mozilla-services.")


def make_tag(bug_number, remote_name, tag_name, commits_since_tag):
    message = "\n".join(commits_since_tag)

    if bug_number:
        # Add bug number to tag
        message = message + f"\n\nDeploy bug #{bug_number}"

    # Print out new tag information
    print(">>> New tag: %s" % tag_name)
    print(">>> Tag message:")
    print("=" * 80)
    print(message)
    print("=" * 80)

    # Create tag
    input('>>> Ready to tag "{}"? Ctrl-c to cancel'.format(tag_name))
    print(">>> Creating tag...")
    subprocess.check_call(["git", "tag", "-s", tag_name, "-m", message])

    # Push tag
    input('>>> Ready to push to remote "{}"? Ctrl-c to cancel'.format(remote_name))
    print(">>> Pushing...")
    subprocess.check_call(["git", "push", "--tags", remote_name, tag_name])


def make_bug(
    remote_name,
    project_name,
    tag_name,
    commits_since_tag,
    bugzilla_product,
    bugzilla_component,
):
    summary = f"{project_name} deploy: {tag_name}"
    print(">>> Creating deploy bug...")
    print(">>> Summary")
    print(summary)
    print()

    description = [
        f"We want to do a deploy for `{project_name}` tagged `{tag_name}`.",
        "",
        "It consists of the following:",
        "",
    ]
    description.extend(commits_since_tag)
    description = "\n".join(description)

    print(">>> Description")
    print(description)
    print()

    bz_params = {
        "bug_type": "task",
        "comment": description,
        "form_name": "enter_bug",
        "short_desc": summary,
    }

    if bugzilla_product:
        bz_params["product"] = bugzilla_product
        if bugzilla_component:
            bz_params["component"] = bugzilla_component

    bugzilla_link = BZ_URL + "?" + urlencode(bz_params)
    print(">>> Link to create bug (may not work if it's sufficiently long)")
    print(bugzilla_link)


def run():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd")
    subparsers.required = True

    make_bug_parser = subparsers.add_parser("make-bug", help="Make a deploy bug")
    make_bug_parser.add_argument(
        "--product", default="", help="The Bugzilla product to set in the bug"
    )
    make_bug_parser.add_argument(
        "--component", default="", help="The Bugzilla component to set in the bug"
    )

    make_tag_parser = subparsers.add_parser("make-tag", help="Make a tag and push it")
    make_tag_parser.add_argument(
        "--with-bug", dest="bug", help="Bug for this deploy if any"
    )
    make_tag_parser.add_argument(
        "--with-tag", dest="tag", help="Tag to use; defaults to figuring out the tag"
    )

    args = parser.parse_args()

    # Let's make sure we're up-to-date and on master branch
    current_branch = check_output("git rev-parse --abbrev-ref HEAD")
    if current_branch != "master":
        print(f"Must be on the master branch to do this (not {current_branch})")
        return 1

    # The current branch can't be dirty
    try:
        subprocess.check_call("git diff --quiet --ignore-submodules HEAD".split())
    except subprocess.CalledProcessError:
        print(
            "Can't be \"git dirty\" when we're about to git pull. "
            "Stash or commit what you're working on."
        )
        return 1

    # Figure out the project name; for now we're cheating and using the
    # current directory
    project_name = os.path.basename(os.getcwd())

    # Figure out the remote name for mozilla-services fork
    remote_name = get_remote_name()

    # Get existing git tags from remote
    check_output(f"git pull {remote_name} master --tags", stderr=subprocess.STDOUT)

    # Figure out the most recent tag details
    last_tag = check_output(
        "git for-each-ref --sort=-taggerdate --count=1 --format %(tag) refs/tags"
    )
    last_tag_message = check_output(f'git tag -l --format="%(contents)" {last_tag}')
    print(f">>> Last tag was: {last_tag}")
    print(">>> Message:")
    print("=" * 80)
    print(last_tag_message)
    print("=" * 80)

    resp = fetch_history_from_github(GITHUB_USER, project_name, last_tag)
    if resp["status"] != "ahead":
        print("Nothing to deploy! (%s)" % resp["status"])
        return

    commits_since_tag = []
    for commit in resp["commits"]:
        # Skip merge commits
        if len(commit["parents"]) > 1:
            continue

        # Use the first 7 characters of the commit sha
        sha = commit["sha"][:7]

        # Use the first line of the commit message which is the summary and
        # truncate it to 80 characters
        summary = commit["commit"]["message"]
        summary = summary.splitlines()[0]
        summary = summary[:80]

        # Figure out who did the commit prefering GitHub usernames
        who = commit["author"]
        if not who:
            who = "?"
        else:
            who = who.get("login", "?")

        commits_since_tag.append("`%s`: %s (%s)" % (sha, summary, who))

    # Use specified tag or figure out next tag name as YYYY.MM.DD format
    if args.cmd == "make-tag" and args.tag:
        tag_name = args.tag
    else:
        tag_name = datetime.datetime.now().strftime("%Y.%m.%d")

    # If it's already taken, append a -N
    existing_tags = check_output(f'git tag -l "{tag_name}*"').splitlines()
    if existing_tags:
        index = len([x for x in existing_tags if x.startswith(tag_name)]) + 1
        tag_name = f"{tag_name}-{index}"

    if args.cmd == "make-bug":
        make_bug(
            remote_name,
            project_name,
            tag_name,
            commits_since_tag,
            args.product,
            args.component,
        )
    elif args.cmd == "make-tag":
        make_tag(args.bug, remote_name, tag_name, commits_since_tag)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(run())
