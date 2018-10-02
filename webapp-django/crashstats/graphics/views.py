import datetime
import gzip
from io import BytesIO

from django import http
from django.conf import settings
from django.utils import timezone

from crashstats.graphics.forms import GraphicsReportForm
from crashstats.supersearch.models import SuperSearch
from crashstats.crashstats.utils import UnicodeWriter


GRAPHICS_REPORT_HEADER = (
    'signature',
    'url',
    'crash_id',
    'client_crash_date',
    'date_processed',
    'last_crash',
    'product',
    'version',
    'build',
    'branch',
    'os_name',
    'os_version',
    'cpu_info',
    'address',
    'bug_list',
    'user_comments',
    'uptime_seconds',
    'email',
    'topmost_filenames',
    'addons_checked',
    'flash_version',
    'hangid',
    'reason',
    'process_type',
    'app_notes',
    'install_age',
    'duplicate_of',
    'release_channel',
    'productid',
)


def graphics_report(request):
    """Return a CSV output of all crashes for a specific date for a
    particular day and a particular product."""
    if (
        not request.user.is_active or
        not request.user.has_perm('crashstats.run_long_queries')
    ):
        return http.HttpResponseForbidden(
            "You must have the 'Run long queries' permission"
        )
    form = GraphicsReportForm(request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    batch_size = 1000
    product = form.cleaned_data['product'] or settings.DEFAULT_PRODUCT
    date = form.cleaned_data['date']
    params = {
        'product': product,
        'date': [
            '>={}'.format(date.strftime('%Y-%m-%d')),
            '<{}'.format(
                (date + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
            )
        ],
        '_columns': (
            'signature',
            'uuid',
            'date',
            'product',
            'version',
            'build_id',
            'platform',
            'platform_version',
            'cpu_name',
            'cpu_info',
            'address',
            'uptime',
            'topmost_filenames',
            'reason',
            'app_notes',
            'release_channel',
        ),
        '_results_number': batch_size,
        '_results_offset': 0,
    }
    api = SuperSearch()
    # Do the first query. That'll give us the total and the first page's
    # worth of crashes.
    data = api.get(**params)
    assert 'hits' in data

    accept_gzip = 'gzip' in request.META.get('HTTP_ACCEPT_ENCODING', '')
    response = http.HttpResponse(content_type='text/csv')
    out = BytesIO()
    writer = UnicodeWriter(out, delimiter='\t')
    writer.writerow(GRAPHICS_REPORT_HEADER)
    pages = data['total'] // batch_size
    # if there is a remainder, add one more page
    if data['total'] % batch_size:
        pages += 1
    alias = {
        'crash_id': 'uuid',
        'os_name': 'platform',
        'os_version': 'platform_version',
        'date_processed': 'date',
        'build': 'build_id',
        'uptime_seconds': 'uptime',
    }
    # Make sure that we don't have an alias for a header we don't need
    alias_excess = set(alias.keys()) - set(GRAPHICS_REPORT_HEADER)
    if alias_excess:
        raise ValueError(
            'Not all keys in the map of aliases are in '
            'the header ({!r})'.format(alias_excess)
        )

    def get_value(row, key):
        """Return the appropriate output from the row of data, one key
        at a time. The output is what's used in writing the CSV file.

        The reason for doing these "hacks" is to match what used to be
        done with the SELECT statement in SQL in the ancient, but now
        replaced, report.
        """
        value = row.get(alias.get(key, key))
        if key == 'cpu_info':
            value = '{cpu_name} | {cpu_info}'.format(
                cpu_name=row.get('cpu_name', ''),
                cpu_info=row.get('cpu_info', ''),
            )
        if value is None:
            return ''
        if key == 'date_processed':
            value = timezone.make_aware(datetime.datetime.strptime(
                value.split('.')[0],
                '%Y-%m-%dT%H:%M:%S'
            ))
            value = value.strftime('%Y%m%d%H%M')
        if key == 'uptime_seconds' and value == 0:
            value = ''
        return value

    for page in range(pages):
        if page > 0:
            params['_results_offset'] = batch_size * page
            data = api.get(**params)

        for row in data['hits']:
            # Each row is a dict, we want to turn it into a list of
            # exact order as the `header` tuple above.
            # However, because the csv writer module doesn't "understand"
            # python's None, we'll replace those with '' to make the
            # CSV not have the word 'None' where the data is None.
            writer.writerow([
                get_value(row, x)
                for x in GRAPHICS_REPORT_HEADER
            ])

    payload = out.getvalue()
    if accept_gzip:
        zbuffer = BytesIO()
        zfile = gzip.GzipFile(mode='wb', compresslevel=6, fileobj=zbuffer)
        zfile.write(payload)
        zfile.close()
        compressed_payload = zbuffer.getvalue()
        response.write(compressed_payload)
        response['Content-Length'] = len(compressed_payload)
        response['Content-Encoding'] = 'gzip'
    else:
        response.write(payload)
        response['Content-Length'] = len(payload)
    return response
