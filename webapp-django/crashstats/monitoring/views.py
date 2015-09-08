import datetime
import urlparse

import requests

from django.conf import settings

from crashstats.crashstats import utils


@utils.json_view
def crash_analysis_health(request):
    # making sure the files are created properly at
    # https://crash-analysis.mozilla.com/crash_analysis/
    # See https://bugzilla.mozilla.org/show_bug.cgi?id=1202739

    base_url = settings.CRASH_ANALYSIS_URL
    days_back = int(getattr(
        settings,
        'CRASH_ANALYSIS_HEALTH_DAYS',
        3
    ))

    errors = []
    warnings = []

    # We can't expect it to have been built today yet,
    # so if the directory of today hasn't been created yet it's
    # not necessarily a problem
    today = datetime.datetime.utcnow().date()
    for i in range(days_back):
        latest = today - datetime.timedelta(days=i)
        url = urlparse.urljoin(
            base_url, latest.strftime('%Y%m%d/'),
        )
        response = requests.get(url)
        if not i and response.status_code == 404:
            warnings.append(
                "Today's sub-directory has not yet been created (%s)" % (
                    url,
                )
            )
            continue

        if response.status_code != 200:
            errors.append(
                "No sub-directory created for %s" % (
                    url,
                )
            )
            continue  # no point checking its content

        # The output is expected to be something like this:
        # <a href="file.txt">file.txt</a> DD-Mon-YYYY HH:MM    X\r\n
        # where 'X' is an integer that represents the file's size
        good_lines = [
            x for x in response.text.splitlines()
            if x.startswith('<a ') and x.split()[-1].isdigit()
        ]
        for line in good_lines:
            size = int(line.split()[-1])
            if not size:
                errors.append(
                    "%s contains a 0-bytes sized file" % (
                        url,
                    )
                )
                break  # bad enough that 1 file is 0-bytes
        if not good_lines:
            errors.append(
                "%s contains no valid file links that match the "
                "expected pattern" % (
                    url,
                )
            )

    return {
        'status': errors and 'Broken' or 'ALLGOOD',
        'errors': errors,
        'warnings': warnings,
    }
