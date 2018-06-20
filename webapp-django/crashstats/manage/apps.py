from django.apps import AppConfig


class ManageConfig(AppConfig):
    name = 'crashstats.manage'

    def ready(self):
        # Import our admin site code so it creates the admin site and
        # monkey-patches things and makes everything right as rain.
        from crashstats.manage import admin_site  # noqa
