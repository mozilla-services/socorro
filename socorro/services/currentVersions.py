# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
logger = logging.getLogger("webapi")

import socorro.webapi.webapiService as webapi
import socorro.lib.util as util

import collections as col
import functools as ft
import urllib2

class CurrentVersions(webapi.JsonServiceBase):
    def __init__(self, configContext):
        super(CurrentVersions, self).__init__(configContext)
        logger.debug('CurrentVersions __init__')

    # curl 'http://socorro-api/bpapi/current/versions'
    uri = '/current/versions/'

    def get(self, *args):
        convertedArgs = webapi.typeConversion([str], args)
        parameters = util.DotDict(zip(['orderby'], convertedArgs))
        connection = self.database.connection()
        cursor = connection.cursor()

        # use the last date that we have data for as the end
        currentVersions = """
                        /* socorro.services.CurrentVersions currentVersions */
                       SELECT
                           product_name, product_version_id,
                           version_string, is_featured,
                           start_date, end_date, build_type, throttle
                       FROM product_info
                       ORDER BY
                           product_name, version_sort DESC
                       """
        cursor.execute(currentVersions)

        result = []
        for (product, product_id, version, featured, start,
             end, build_type, throttle) in cursor.fetchall():
            releases = {'id': product_id,
                        'product': product,
                        'version': version,
                        'featured': featured,
                        'start_date': str(start),
                        'end_date': str(end),
                        'release': build_type,
                        'throttle': str(throttle) }

            result.append(releases)

        return {'currentversions': result}
