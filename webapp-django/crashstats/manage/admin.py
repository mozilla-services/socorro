import requests
from six.moves.urllib.parse import urlparse

from django.conf import settings
from django.db import connection
from django.shortcuts import render

from crashstats.manage.decorators import superuser_required


@superuser_required
def crash_me_now(request):
    # NOTE(willkg): This intentionally throws an error so that we can test
    # unhandled error handling.
    1 / 0  # noqa


@superuser_required
def site_status(request):
    context = {}

    # Get version information for deployed parts
    version_info = {}
    for url in settings.OVERVIEW_VERSION_URLS.split(','):
        hostname = urlparse(url).netloc
        url = url.strip()
        try:
            data = requests.get(url).json()
        except Exception as exc:
            data = {'error': str(exc)}
        version_info[hostname] = data

    context['version_info'] = version_info

    # Get alembic migration data
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT version_num FROM alembic_version')
            alembic_version = cursor.fetchone()[0]
            alembic_error = ''
    except Exception as exc:
        alembic_version = ''
        alembic_error = 'error: %s' % exc
    context['alembic_version'] = alembic_version
    context['alembic_error'] = alembic_error

    # Get Django migration data
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT id, app, name, applied FROM django_migrations')
            cols = [col[0] for col in cursor.description]
            django_db_data = [dict(zip(cols, row)) for row in cursor.fetchall()]
            django_db_error = ''
    except Exception as exc:
        django_db_data = []
        django_db_error = 'error: %s' % exc
    context['django_db_data'] = django_db_data
    context['django_db_error'] = django_db_error

    # Get crontabber data
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT app_name, next_run, last_run, last_success, error_count, last_error '
                'FROM crontabber WHERE error_count > 0'
            )
            cols = [col[0] for col in cursor.description]
            crontabber_data = [dict(zip(cols, row)) for row in cursor.fetchall()]
            crontabber_error = ''
    except Exception as exc:
        crontabber_data = []
        crontabber_error = 'error: %s' % exc
    context['crontabber_data'] = crontabber_data
    context['crontabber_error'] = crontabber_error
    context['title'] = 'Site status'

    return render(request, 'admin/site_status.html', context)
