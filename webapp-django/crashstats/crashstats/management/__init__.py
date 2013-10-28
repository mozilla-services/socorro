from django.contrib.auth.models import Permission, Group
from django.db.models.signals import post_syncdb
from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver
import django.contrib.auth.models
import django.contrib.contenttypes.models


PERMISSIONS = {
    'view_pii': 'View Personal Identifyable Information',
    'view_rawdump': 'View Raw Dumps',
}

GROUPS = (
    ('Hackers', ('view_pii', 'view_rawdump')),
)

_senders_left = [
    django.contrib.auth.models,
    django.contrib.contenttypes.models
]

# global variable that makes it easy for us to exit early when the post_syncdb
# signal is called for every single model possible
_all_set_up = False


@receiver(post_syncdb)
def setup_custom_permissions_and_groups(sender, **kwargs):
    global _all_set_up
    if not _all_set_up:
        if sender in _senders_left:
            _senders_left.remove(sender)

        # All the relevant senders have been sync'ed.
        # We can now use them
        if not _senders_left:
            appname = 'crashstats.crashstats'
            ct, __ = ContentType.objects.get_or_create(
                model='',
                app_label=appname,
                defaults={'name': appname}
            )
            for codename, name in PERMISSIONS.items():
                p, __ = Permission.objects.get_or_create(
                    name=name,
                    codename=codename,
                    content_type=ct
                )

            for name, permissions in GROUPS:
                g, __ = Group.objects.get_or_create(
                    name=name
                )
                for permission in permissions:
                    # The add has a built-in for checking it isn't created
                    # repeatedly.
                    g.permissions.add(
                        Permission.objects.get(codename=permission)
                    )
            _all_set_up = True
