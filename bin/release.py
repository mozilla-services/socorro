#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
This script handles releases for this project.

This has two subcommands: ``make-bug`` and ``make-tag``. See the help text for
both.

This requires Python 3 to run.

If you want to use ``pyproject.toml`` and you're using Python <3.11, this also
requires the tomli library.

See https://github.com/willkg/socorro-release/#readme for details.

repo: https://github.com/willkg/socorro-release/
sha: 8c609f3a0934b5f5fc4a954bed4e0c5cce16c429

"""

import argparse
import configparser
import datetime
import json
import os
import re
import shlex
import subprocess
import sys
from urllib.request import urlopen
from urllib.parse import urlencode


DESCRIPTION = """
release.py makes it easier to create deploy bugs and push tags to trigger
deploys.

For help, see: https://github.com/willkg/socorro-release/
"""

GITHUB_API = "https://api.github.com/"
BZ_CREATE_URL = "https://bugzilla.mozilla.org/enter_bug.cgi"
BZ_BUG_JSON_URL = "https://bugzilla.mozilla.org/rest/bug/"

DEFAULT_CONFIG = {
    # Bugzilla product and component to write new bugs in
    "bugzilla_product": "",
    "bugzilla_component": "",
    # GitHub user and project name
    "github_user": "",
    "github_project": "",
    # The name of the main branch
    "main_branch": "",
    # The tag structure using datetime formatting markers
    "tag_name_template": "%Y.%m.%d",
}

LINE = "=" * 80


def get_config():
    """Generates configuration.

    This tries to pull configuration from:

    1. the ``[tool.release]`` table from a ``pyproject.toml`` file, OR
    2. the ``[tool:release]`` section of a ``setup.cfg`` file

    If neither exist, then it uses defaults.

    :returns: configuration dict

    """
    my_config = dict(DEFAULT_CONFIG)

    if os.path.exists("pyproject.toml"):
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            try:
                import tomli as tomllib
            except ImportError:
                print(
                    "For Python <3.11, you need to install tomli to work with pyproject.toml "
                    + "files."
                )
                tomllib = None

        if tomllib is not None:
            with open("pyproject.toml", "rb") as fp:
                data = tomllib.load(fp)

            config_data = data.get("tool", {}).get("release", {})
            if config_data:
                for key, default_val in my_config.items():
                    my_config[key] = config_data.get(key, default_val)
                return my_config

    if os.path.exists("setup.cfg"):
        config = configparser.ConfigParser()
        config.read("setup.cfg")

        if "tool:release" in config:
            config = config["tool:release"]
            for key, default_val in my_config.items():
                my_config[key] = config.get(key, default_val)

            return my_config

    return my_config


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


def fetch_history_from_github(owner, repo, from_rev, main_branch):
    url = f"{GITHUB_API}repos/{owner}/{repo}/compare/{from_rev}...{main_branch}"
    return fetch(url)


def check_output(cmdline, **kwargs):
    args = shlex.split(cmdline)
    return subprocess.check_output(args, **kwargs).decode("utf-8").strip()


def get_remote_name(github_user):
    """Figures out the right remote to use

    People name the git remote differently, so this figures out which one to
    use.

    :arg str github_user: the github user for the remote name to use

    :returns: the name of the remote

    :raises Exception: if it can't figure out the remote name for the specified
        user

    """
    # Figure out remote to push tag to
    remote_output = check_output("git remote -v")

    def check_ssh(github_user, remote_url):
        return f":{github_user}/" in remote_url

    def check_https(github_user, remote_url):
        return f"/{github_user}/" in remote_url

    for line in remote_output.splitlines():
        line = line.split("\t")
        if check_ssh(github_user, line[1]) or check_https(github_user, line[1]):
            return line[0]

    raise Exception(f"Can't figure out remote name for {github_user}.")


def make_tag(bug_number, remote_name, tag_name, commits_since_tag):
    """Tags a release."""
    if bug_number:
        resp = fetch(BZ_BUG_JSON_URL + bug_number, is_json=True)
        bug_summary = resp["bugs"][0]["summary"]

        input(f">>> Using bug {bug_number}: {bug_summary}. Correct? Ctrl-c to cancel")

        message = (
            f"Tag {tag_name} (bug #{bug_number})\n\n"
            + "\n".join(commits_since_tag)
            + f"\n\nDeploy bug #{bug_number}"
        )
    else:
        message = f"Tag {tag_name}\n\n" + "\n".join(commits_since_tag)

    # Print out new tag information
    print(">>> New tag: %s" % tag_name)
    print(">>> Tag message:")
    print(LINE)
    print(message)
    print(LINE)

    # Create tag
    input(f">>> Ready to tag {tag_name}? Ctrl-c to cancel")
    print(">>> Creating tag...")
    subprocess.check_call(["git", "tag", "-s", tag_name, "-m", message])

    # Push tag
    input(f">>> Ready to push to remote {remote_name}? Ctrl-c to cancel")
    print(">>> Pushing...")
    subprocess.check_call(["git", "push", "--tags", remote_name, tag_name])

    if bug_number:
        # Show tag for adding to bug comment
        print(f">>> Show tag... Copy and paste this into bug #{bug_number}.")
        print(">>> %<-----------------------------------------------")
        output = check_output(f"git show {tag_name}")
        # Truncate the output at "diff --git"
        output = output[: output.find("diff --git")].strip()
        print(f"Tagged {tag_name}:")
        print("")
        print("```")
        print(output)
        print("```")
        print(">>> %<-----------------------------------------------")


def make_bug(
    github_project, tag_name, commits_since_tag, bugzilla_product, bugzilla_component
):
    """Creates a bug."""
    summary = f"{github_project} deploy: {tag_name}"
    print(">>> Creating deploy bug...")
    print(">>> Summary")
    print(summary)
    print()

    description = [
        f"We want to do a deploy for `{github_project}` tagged `{tag_name}`.",
        "",
        "It consists of the following:",
        "",
    ]
    description.extend(commits_since_tag)
    description = "\n".join(description)

    print(">>> Description")
    print(description)
    print()

    if bugzilla_product:
        bz_params = {
            "priority": "P2",
            "bug_type": "task",
            "comment": description,
            "form_name": "enter_bug",
            "short_desc": summary,
        }

        bz_params["product"] = bugzilla_product
        if bugzilla_component:
            bz_params["component"] = bugzilla_component

        bugzilla_link = BZ_CREATE_URL + "?" + urlencode(bz_params)
        print(">>> Link to create bug (may not work if it's sufficiently long)")
        print(bugzilla_link)


def run():
    config = get_config()

    parser = argparse.ArgumentParser(description=DESCRIPTION)

    # Add items that can be configured to argparse as configuration options.
    # This makes it possible to specify or override configuration with command
    # line arguments.
    for key, val in config.items():
        key_arg = key.replace("_", "-")
        default_val = val.replace("%", "%%")
        parser.add_argument(
            f"--{key_arg}",
            default=val,
            help=f"override configuration {key}; defaults to {default_val!r}",
        )

    subparsers = parser.add_subparsers(dest="cmd")
    subparsers.required = True

    subparsers.add_parser("make-bug", help="Make a deploy bug")
    make_tag_parser = subparsers.add_parser("make-tag", help="Make a tag and push it")
    make_tag_parser.add_argument(
        "--with-bug", dest="bug", help="Bug for this deploy if any."
    )
    make_tag_parser.add_argument(
        "--with-tag",
        dest="tag",
        help="Tag to use; defaults to figuring out the tag using tag_name_template.",
    )

    args = parser.parse_args()

    github_project = args.github_project
    github_user = args.github_user
    main_branch = args.main_branch
    tag_name_template = args.tag_name_template

    if not github_project or not github_user or not main_branch:
        print("main_branch, github_project, and github_user are required.")
        print(
            "Either set them in pyproject.toml/setup.cfg or specify them as command "
            + "line arguments."
        )
        return 1

    # Let's make sure we're up-to-date and on main branch
    current_branch = check_output("git rev-parse --abbrev-ref HEAD")
    if current_branch != main_branch:
        print(
            f"Must be on the {main_branch} branch to do this; currently on {current_branch}"
        )
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

    remote_name = get_remote_name(github_user)

    # Get existing git tags from remote
    check_output(
        f"git pull {remote_name} {main_branch} --tags", stderr=subprocess.STDOUT
    )

    # Figure out the most recent tag details
    all_tags = check_output("git tag --list --sort=-creatordate").splitlines()
    if all_tags:
        last_tag = all_tags[0]
        last_tag_message = check_output(f'git tag -l --format="%(contents)" {last_tag}')
        print(f">>> Last tag was: {last_tag}")
        print(">>> Message:")
        print(LINE)
        print(last_tag_message)
        print(LINE)

        resp = fetch_history_from_github(
            github_user, github_project, last_tag, main_branch
        )
        if resp["status"] != "ahead":
            print(f"Nothing to deploy! {resp['status']}")
            return
    else:
        first_commit = check_output("git rev-list --max-parents=0 HEAD")
        resp = fetch_history_from_github(github_user, github_project, first_commit)

    commits_since_tag = []
    bug_name_prefix_regexp = re.compile(r"bug-([\d]+)", re.IGNORECASE)
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
        # Bug 1868455: While GitHub autolinking doesn't suport spaces, Bugzilla autolinking
        # doesn't support hyphens.
        if args.cmd == "make-bug":
            summary = bug_name_prefix_regexp.sub(r"bug \1", summary)

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
        tag_name = datetime.datetime.now().strftime(tag_name_template)

    # If there's already a tag, then increment the -N until we find a tag name
    # that doesn't exist, yet
    existing_tags = check_output(f'git tag -l "{tag_name}*"').splitlines()
    if existing_tags:
        tag_name_attempt = tag_name
        index = 2
        while tag_name_attempt in existing_tags:
            tag_name_attempt = f"{tag_name}-{index}"
            index += 1
        tag_name = tag_name_attempt

    if args.cmd == "make-bug":
        make_bug(
            github_project,
            tag_name,
            commits_since_tag,
            args.bugzilla_product,
            args.bugzilla_component,
        )

    elif args.cmd == "make-tag":
        if args.bugzilla_product and args.bugzilla_component and not args.bug:
            print(
                "Bugzilla product and component are specified, but you didn't "
                + "specify a bug number with --with-bug."
            )
            return 1
        make_tag(args.bug, remote_name, tag_name, commits_since_tag)

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(run())
