import gzip
import ssl
from cStringIO import StringIO

from optparse import make_option

import requests
import boto

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.defaultfilters import filesizeformat
from django.utils import timezone

from crashstats.symbols.models import SymbolsUpload


# Due to a bug in boto, see
# https://github.com/boto/boto/issues/2836
# you can't connect to a S3 bucket, from OSX Python 2.7, if the bucket
# name has a dot in it. To remedy that, on OSX Python 2.7, you can
# override the calling_format parameter when you make the connection
# but doing that will make it impossible for any other environments to
# find the bucket.
# The current solution is this hack below,
# taken from https://github.com/boto/boto/issues/2836#issuecomment-68682573


# Only recent versions of Python 2.7 have this and thus only those
# need this monkey patching.
if hasattr(ssl, 'match_hostname'):

    _old_match_hostname = ssl.match_hostname

    def _new_match_hostname(cert, hostname):
        if hostname.endswith('.s3.amazonaws.com'):
            pos = hostname.find('.s3.amazonaws.com')
            hostname = hostname[:pos].replace('.', '') + hostname[pos:]
        return _old_match_hostname(cert, hostname)

    ssl.match_hostname = _new_match_hostname


class Command(BaseCommand):
    """
    On July 20 2015 we released an improvement to the symbols uploader so
    that all .sym files in the zip archive bundles would be gzipped.
    That makes them smaller.
    However, we made a mistake in that we didn't encode the file correctly,
    just encoding the content.
    To correct this we have this script.
    """

    help = (
        'Run this command to re-encode .sym files that were uploaded '
        'without first being properly encoded with the gzip header signature.'
    )

    option_list = BaseCommand.option_list + (
        make_option(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help='Only find the files to re-encode'
        ),
        make_option(
            '--first-date',
            dest='first_date',
            default='2015-07-20',  # the day we started compressing (132)
            help='Upload date range start (Default 2015-07-20)'
        ),
        make_option(
            '--end-date',
            dest='end_date',
            default='2015-08-05',  # the day the fix was release on prod (134)
            help='Upload date range end (Default 2015-08-05)'
        ),
        make_option(
            '--max-uploads',
            dest='max_uploads',
            default='0',
            help='Max. number of SymbolsUploads to work on (default all)'
        ),
    )

    def _parse_date(self, date):
        year, month, day = [int(x) for x in date.split('-')]
        return timezone.now().replace(
            year=year,
            month=month,
            day=day,
            hour=0,
            minute=0,
            second=0
        )

    def handle(self, *args, **options):
        first_date = self._parse_date(options['first_date'])
        end_date = self._parse_date(options['end_date'])
        max_uploads = int(options['max_uploads'])
        uploads = SymbolsUpload.objects.filter(
            created__gte=first_date,
            created__lt=end_date
        )
        buckets = {}
        conn = boto.connect_s3(
            settings.AWS_ACCESS_KEY,
            settings.AWS_SECRET_ACCESS_KEY,
        )
        if max_uploads > 0:
            uploads = uploads.order_by('?')[:max_uploads]
        valid_bucket_names = [settings.SYMBOLS_BUCKET_DEFAULT_NAME]
        valid_bucket_names += settings.SYMBOLS_BUCKET_EXCEPTIONS.values()

        for upload in uploads:
            print repr(upload)
            for line in upload.content.splitlines():
                if not line.endswith('.sym'):
                    continue
                bucket_name = line.split(',')[0]
                if bucket_name.startswith('+') or bucket_name.startswith('='):
                    bucket_name = bucket_name[1:]

                if bucket_name not in buckets:
                    if bucket_name not in valid_bucket_names:
                        print (
                            "Skipping %r because unrecognized bucket name" % (
                                bucket_name,
                            )
                        )
                        continue
                    buckets[bucket_name] = conn.lookup(bucket_name)

                if not buckets[bucket_name]:
                    print "No bucket called", repr(bucket_name)
                    continue

                key = buckets[bucket_name].get_key(line.split(',')[1])
                if key is not None:
                    assert key.content_type == 'text/plain', key.content_type
                    if key.content_encoding != 'gzip':
                        # then it doesn't need to be fixed
                        continue

                    # Instead of relying on key.generate_url(...)
                    # which will produce a URL like
                    # https://my.bucket.name.s3.amazonaws.com/key/name.ext
                    # which can be troublesome for Python 2.7 on OSX to
                    # GET because of the dots, we instead make our own
                    # URL.
                    url = 'https://s3.amazonaws.com/{}/{}'.format(
                        key.bucket.name,
                        key.name
                    )

                    print filesizeformat(key.size).ljust(10), url
                    if self._correctly_encoded(url):
                        print "CORRECTLY ENCODED"
                    else:
                        print "NOT CORRECT",
                        if not options['dry_run']:
                            downloaded = key.get_contents_as_string()
                            real_content = downloaded.decode('zlib')
                            out = StringIO()
                            with gzip.GzipFile(fileobj=out, mode='w') as f:
                                f.write(real_content)
                            value = out.getvalue()
                            key.set_contents_from_string(value, {
                                'Content-Encoding': 'gzip'
                            })
                            print "FIXED"
                        else:
                            print "DRY-RUN"

    def _correctly_encoded(self, url):
        try:
            requests.get(url)
            return True
        except requests.exceptions.ContentDecodingError:
            return False
