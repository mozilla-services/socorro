#!/usr/bin/env python
import os
import sys

if __name__ == '__main__':
    # Note! If you for some reason change that change the wsgi
    # starting-point script too.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crashstats.settings')

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
