#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import sys


def main(argv):
    # Note! If you for some reason change that change the wsgi
    # starting-point script too.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crashstats.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(argv)


if __name__ == "__main__":
    main(sys.argv)
