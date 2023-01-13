#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Creates a shell that loads all the Django ORM models and puts them
in locals.
"""

import code
from importlib import import_module
import inspect
import os

import django
from django.db.models import Model


def load_crashstats_models(apps):
    all_models = {}
    for app in apps:
        if not app.startswith("crashstats"):
            continue

        module_path = app + ".models"
        try:
            module = import_module(module_path)
        except ImportError:
            continue

        names = [name for name in dir(module)]
        models = {}
        for name in names:
            thing = getattr(module, name)
            if inspect.isclass(thing) and issubclass(thing, Model):
                models[name] = thing

        if models:
            print("From %s loading %s" % (module_path, list(models.keys())))

        all_models.update(models)
    return all_models


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crashstats.settings")
    django.setup()
    from django.conf import settings

    all_locals = {}
    all_locals.update(load_crashstats_models(settings.INSTALLED_APPS))

    # Lifted from Lib/site.py in cpython code.
    import readline
    import rlcompleter

    readline_doc = getattr(readline, "__doc__", "")
    if readline_doc is not None and "libedit" in readline_doc:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

    # Add locals to completer
    readline.set_completer(rlcompleter.Completer(all_locals).complete)

    # Kick off interactive prompt
    code.interact(
        banner="Interactive Crash Stats webapp shell. ^D to exit.",
        local=all_locals,
        exitmsg="Be seeing you....",
    )
