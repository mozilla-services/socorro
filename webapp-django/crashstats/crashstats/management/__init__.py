from django.contrib.auth.models import Permission
from django.db.models.signals import post_migrate
from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver


# Note! When referring to these in code, you'll have to use the
# prefix 'crashstats'. So template code looks like this for example:
#   {% if request.user.has_perm('crashstats.view_pii') %}
PERMISSIONS = {
    'view_pii': 'View Personal Identifiable Information',
    'view_rawdump': 'View Raw Dumps',
    'view_exploitability': 'View Exploitability Results',
    'view_flash_exploitability': 'View Flash Exploitability Results',
    'run_custom_queries': 'Run Custom Queries in Super Search',
    'run_long_queries': 'Run Long Queries',
    'reprocess_crashes': 'Reprocess Crashes',
}


# internal use to know when all interesting models have been synced
_senders_left = [
    'django.contrib.auth',
    'django.contrib.contenttypes'
]


@receiver(post_migrate)
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
        if sender.name in _senders_left:
            _senders_left.remove(sender.name)

        if _senders_left:
            return
        # All the relevant senders have been sync'ed.
        # We can now use them
        appname = 'crashstats'
        ct, __ = ContentType.objects.get_or_create(
            model='',
            app_label=appname,
        )
        for codename, name in PERMISSIONS.items():
            try:
                p = Permission.objects.get(codename=codename, content_type=ct)
                if p.name != name:
                    p.name = name
                    p.save()
            except Permission.DoesNotExist:
                Permission.objects.create(
                    name=name,
                    codename=codename,
                    content_type=ct
                )
