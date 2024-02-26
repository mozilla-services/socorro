#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
This script looks at the ``/__version__`` endpoint information and tells you
how far behind different server environments are from main tip.

This requires Python 3.8+ to run. See help text for more.

See https://github.com/willkg/socorro-release/#readme for details.

Note: If you want to use ``pyproject.toml`` and you're using Python <3.11, this
also requires the tomli library.

repo: https://github.com/willkg/socorro-release/
sha: d19f45bc9eedae34de2905cdd4adf7b9fd03f870

"""

import argparse
import json
import os
import sys
from urllib.parse import urlparse
from urllib.request import urlopen


DESCRIPTION = """
service-status.py tells you how far behind different server environments
are from main tip.

For help, see: https://github.com/willkg/socorro-release/
"""

DEFAULT_CONFIG = {
    # The name of the main branch in the repository
    "main_branch": "main",
    # List of "label=host" for hosts that have a /__version__ to check
    "hosts": [],
}


def get_config():
    """Generates configuration.

    This tries to pull configuration from the ``[tool.service-status]`` table
    from a ``pyproject.toml`` file.

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

            config_data = data.get("tool", {}).get("service-status", {})
            if config_data:
                for key, default_val in my_config.items():
                    my_config[key] = config_data.get(key, default_val)

    return my_config


def fetch(url, is_json=True):
    """Fetch data from a url

    This raises URLError on HTTP request errors. It also raises JSONDecode
    errors if it's not valid JSON.

    """
    fp = urlopen(url, timeout=5)
    data = fp.read()
    if is_json:
        return json.loads(data)
    return data


def fetch_history_from_github(main_branch, user, repo, from_sha):
    return fetch(
        "https://api.github.com/repos/%s/%s/compare/%s...%s"
        % (user, repo, from_sha, main_branch)
    )


class StdoutOutput:
    def section(self, name):
        print("")
        print("%s" % name)
        print("=" * len(name))
        print("")

    def row(self, *args):
        template = "%-13s " * len(args)
        print("  " + template % args)

    def print_delta(self, main_branch, user, repo, sha):
        resp = fetch_history_from_github(main_branch, user, repo, sha)
        # from pprint import pprint
        # pprint(resp)
        if resp["total_commits"] == 0:
            self.row("", "status", "identical")
        else:
            self.row("", "status", "%s commits" % resp["total_commits"])
            self.row()
            self.row(
                "",
                "https://github.com/%s/%s/compare/%s...%s"
                % (
                    user,
                    repo,
                    sha[:8],
                    main_branch,
                ),
            )
            self.row()
            for i, commit in enumerate(resp["commits"]):
                if len(commit["parents"]) > 1:
                    # Skip merge commits
                    continue

                self.row(
                    "",
                    commit["sha"][:8],
                    ("HEAD: " if i == 0 else "")
                    + "%s (%s)"
                    % (
                        commit["commit"]["message"].splitlines()[0][:60],
                        (commit["author"] or {}).get("login", "?")[:10],
                    ),
                )
        self.row()


def main():
    config = get_config()

    parser = argparse.ArgumentParser(description=DESCRIPTION)

    # Add items that can be configured to argparse as configuration options.
    # This makes it possible to specify or override configuration with command
    # line arguments.
    for key, val in config.items():
        key_arg = key.replace("_", "-")
        if isinstance(val, list):
            parser.add_argument(
                f"--{key_arg}",
                default=val,
                nargs="+",
                metavar="VALUE",
                help=f"override configuration {key}; defaults to {val!r}",
            )
        else:
            default_val = val.replace("%", "%%")
            parser.add_argument(
                f"--{key_arg}",
                default=val,
                metavar="VALUE",
                help=f"override configuration {key}; defaults to {default_val!r}",
            )

    args = parser.parse_args()

    main_branch = args.main_branch
    hosts = args.hosts

    out = StdoutOutput()

    if not hosts:
        print("no hosts specified.")
        return 1

    current_section = ""

    for line in hosts:
        parts = line.split("=", 1)
        if len(parts) == 1:
            service = parts[0]
            env_name = "environment"
        else:
            env_name, service = parts

        if current_section != env_name:
            out.section(env_name)
            current_section = env_name

        service = service.rstrip("/")
        resp = fetch(f"{service}/__version__")
        commit = resp["commit"]
        tag = resp.get("version") or "(none)"

        parsed = urlparse(resp["source"])
        _, user, repo = parsed.path.split("/")
        service_name = repo
        out.row(service_name, "version", commit, tag)
        out.print_delta(main_branch, user, repo, commit)


if __name__ == "__main__":
    sys.exit(main())
