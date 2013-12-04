from django.contrib.auth.models import Permission
from django.db.models.signals import post_syncdb
from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver

# Import the specific models we need to wait for to have been
# sync'ed by Django
import django.contrib.auth.models
import django.contrib.contenttypes.models

# Note! When referring to these in code, you'll have to use the
# prefix 'crashstats'. So template code looks like this for example:
#   {% if request.user.has_perm('crashstats.view_pii') %}
PERMISSIONS = {
    'view_pii': 'View Personal Identifyable Information',
    'view_rawdump': 'View Raw Dumps',
    'view_exploitability': 'View Exploitability Results',
    'view_flash_exploitability': 'View Flash Exploitability Results',
}


# internal use to know when all interesting models have been synced
_senders_left = [
    django.contrib.auth.models,
    django.contrib.contenttypes.models
]


@receiver(post_syncdb)
def setup_custom_permissions_and_groups(sender, **kwargs):
    """
    When you `./manage.py syncdb` every installed app gets synced.

    We use this opportunity to create and set up permissions that are NOT
    attached to a specific model. We need this because we want to use
    permissions but not the Django models.

    Note that this needs to run after django.contrib.auth.models and
    django.contrib.contenttypes.models have been synced so that we can use
    them in this context.
    """
    if _senders_left:
        if sender in _senders_left:
            _senders_left.remove(sender)

        if _senders_left:
            return
        # All the relevant senders have been sync'ed.
        # We can now use them
        appname = 'crashstats'
        ct, __ = ContentType.objects.get_or_create(
            model='',
            app_label=appname,
            defaults={'name': appname}
        )
        for codename, name in PERMISSIONS.items():
            Permission.objects.get_or_create(
                name=name,
                codename=codename,
                content_type=ct
            )
