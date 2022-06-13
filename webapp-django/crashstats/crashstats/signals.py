# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib.auth.models import Permission
from django.db.models.signals import post_migrate
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver


# NOTE(willkg): When referring to these in code, you'll have to use the prefix
# 'crashstats'. For example, in jinja2 templates, use this:
#
#   {% if request.user.has_perm('crashstats.view_pii') %}
#
PERMISSIONS = {
    "view_pii": "View Personal Identifiable Information",
    "view_rawdump": "View Raw Dumps",
    "view_exploitability": "View Exploitability Results",
    "view_flash_exploitability": "View Flash Exploitability Results",
    "run_custom_queries": "Run Custom Queries in Super Search",
    "run_long_queries": "Run Long Queries",
    "reprocess_crashes": "Reprocess Crashes",
}


GROUPS = {
    "Hackers": [
        "reprocess_crashes",
        "run_long_queries",
        "view_exploitability",
        "view_flash_exploitability",
        "view_pii",
        "view_rawdump",
    ],
    "Hackers Plus": [
        "reprocess_crashes",
        "run_custom_queries",
        "run_long_queries",
        "view_exploitability",
        "view_flash_exploitability",
        "view_pii",
        "view_rawdump",
    ],
}


@receiver(post_migrate)
def setup_custom_permissions_and_groups(sender, **kwargs):
    """Set up permissions and groups

    We use this opportunity to create and set up permissions that are NOT
    attached to a specific model. We need this because we want to use
    permissions but not the Django models.

    Note that this needs to run after django.contrib.auth.models have been
    created.

    """
    if sender.name == "django.contrib.auth":
        print("Creating Socorro permissions:")
        appname = "crashstats"
        ct, _ = ContentType.objects.get_or_create(model="", app_label=appname)
        perm_instances = {}
        for codename, name in PERMISSIONS.items():
            perm, created = Permission.objects.get_or_create(
                codename=codename, content_type=ct, name=name
            )
            perm_instances[codename] = perm
            if created:
                print('  Permission: "%s" created.' % name)

        print("Creating Socorro groups:")
        for group_name, perms in GROUPS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            for perm_codename in perms:
                group.permissions.add(perm_instances[perm_codename])
            group.save()
            if created:
                print('  Group: "%s" created.' % group_name)
