from django.apps import AppConfig


class CrashstatsConfig(AppConfig):
    name = 'crashstats.crashstats'

    def ready(self):
        # Import signals kicking off signal registration
        from crashstats.crashstats import signals  # noqa
