#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Opens the specified env file, pulls in configuration, then executes the specified command in that
environment.

Usage:

    build_env.py somefile.env somecmd

Note: This will happily inject environment variables with invalid bash identifiers into the
environment.

"""

import os
import subprocess
import sys


USAGE = 'build_env.py [ENVFILE] [CMD...]'


class ParseException(Exception):
    pass


def parse_env_file(envfile):
    """Parses an env file and returns the env

    :arg str envfile: the path to the env file to open

    :returns: environment as a dict

    """
    env = {}
    with open(envfile, 'r') as fp:
        for lineno, line in enumerate(fp):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                raise ParseException('%d: No = in line' % lineno)
            key, val = line.split('=', 1)
            env[key.strip()] = val.strip()

    return env


def main(argv):
    if not argv:
        print(USAGE)
        print('Error: env file required.')
        return 1

    env_file = argv.pop(0)

    if not argv:
        print(USAGE)
        print('Error: cmd required.')
        return 1

    try:
        env = parse_env_file(env_file)
    except (OSError, IOError) as exc:
        raise ParseException('File error: %s' % exc)

    for key, val in env.items():
        os.environ[key] = val

    print('Running %s in new env' % argv)
    sys.stdout.flush()
    sys.stderr.flush()
    return subprocess.call(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
