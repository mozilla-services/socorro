import logging
logger = logging.getLogger("webapi")

import socorro.webapi.webapiService as webapi
import socorro.lib.util as util

import collections as col
import functools as ft
import urllib2

available_columns = {
    "product_version_id": "product_version_id ASC,",
    "product_name": "product_name ASC,",
    "version_string": "version_string ASC,",
    "which_table": "which_table ASC,",
    "start_date": "start_date ASC,",
    "end_date": "end_date ASC,",
    "is_featured": "is_featured ASC,",
    "build_type": "build_type ASC,",
    "throttle": "throttle ASC,",
    "-product_version_id": "product_version_id DESC,",
    "-product_name": "product_name DESC,",
    "-version_string": "version_string DESC,",
    "-which_table": "which_table DESC,",
    "-start_date": "start_date DESC,",
    "-end_date": "end_date DESC,",
    "-is_featured": "is_featured DESC,",
    "-build_type": "build_type DESC,",
    "-throttle": "throttle DESC,", }


def create_order_by(user_input):
    result = ""
    for x in user_input:
        if x in available_columns:
            result += available_columns[x]
    if not result:
        return result
    else:
        return """ ORDER BY %s """ % result.strip(',')


class CurrentVersions(webapi.JsonServiceBase):
    def __init__(self, configContext):
        super(CurrentVersions, self).__init__(configContext)
        logger.debug('CurrentVersions __init__')

    # curl 'http://localhost:8085/current/versions'
    uri = '/current/versions/(.*)'

    def get(self, *args):
        convertedArgs = webapi.typeConversion([str], args)
        parameters = util.DotDict(zip(['orderby'], convertedArgs))
        connection = self.database.connection()
        cursor = connection.cursor()

        featured_only = False
        if 'featured' in args:
            featured_only = True

        # use the last date that we have data for as the end
        currentVersions = """
                        /* socorro.services.CurrentVersions curentVersions */
                       SELECT DISTINCT product_name, product_version_id,
                       version_string, is_featured,
                              start_date, end_date, build_type, throttle
                       FROM product_info"""

        if featured_only:
            currentVersions += """ WHERE is_featured"""

        if parameters['orderby']:
            orderby = parameters['orderby']
            orderby = urllib2.unquote(orderby)
            orderby = orderby.split(',')
            currentVersions += create_order_by(orderby)

        cursor.execute(currentVersions)



        result = []
        for (product, product_id, version, featured, start,
             end, build_type, throttle) in cursor.fetchall():
            releases = {'id': product_id,
                        'product': product,
                        'version': version,
                        'start_date': str(start),
                        'end_date': str(end),
                        'release': build_type,
                        'throttle': str(throttle) }

            if not featured_only:
                releases['featured'] = featured

            result.append(releases)

        return {'currentversions': result}
