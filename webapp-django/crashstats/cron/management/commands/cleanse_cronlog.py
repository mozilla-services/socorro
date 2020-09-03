import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from crashstats.cron.models import Log


# Number of days to keep records--anything older than this will get
# deleted.
RECORD_AGE_CUTOFF = 180


class Command(BaseCommand):
    """Periodic maintenance task for deleting old cron log records."""

    help = "Cleanse old cron_log records"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="Whether or not to do a dry run."
        )

    def handle(self, *args, **options):
        is_dry_run = options["dry_run"]
        today = timezone.now()
        today.replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = today - datetime.timedelta(days=RECORD_AGE_CUTOFF)

        total_count = Log.objects.all().count()
        records = Log.objects.filter(log_time__lte=cutoff)
        if is_dry_run:
            self.stdout.write("cleanse_cronlog: THIS IS A DRY RUN.")
            count = records.count()
        else:
            count = records.delete()[0]

        self.stdout.write(
            f"cleanse_cronlog: count before cleansing: cron_log={total_count}"
        )
        self.stdout.write(
            f"cleanse_cronlog: cutoff={cutoff.date()}: deleted cron_log={count}"
        )
