#!/usr/bin/env python

"""
Fetches normalization data.

Usage:

    python docker/fetch_normalization_data.py

"""

import argparse
import datetime
import os
import sys

import psycopg2
import requests


# NOTE(willkg): These platforms come from the -prod data.
PLATFORMS = ['Mac OS X', 'Linux', 'Windows', 'Unknown']


def fetch_data_from_api(endpoint, product, version, platform, start_date, end_date):
    """Fetches data from API"""
    req = requests.get(endpoint, params={
        'end_date': end_date,
        'start_date': start_date,
        'product': product,
        'platforms': platform,
        'versions': version,
    })
    if req.status_code != 200:
        print('Error retrieving ADI: %s' % req.content)
        return []

    data = req.json()
    return data['hits']


def fetch_versions(conn, product_name):
    """Fetch the version strings for a product from product_versions table"""

    cursor = conn.cursor()
    cursor.execute("""
        SELECT version_string
        FROM product_versions
        WHERE
            product_name=%s
    """, (product_name,))
    # NOTE(willkg): We don't want versions that end with "b" because they're weird.
    versions = set([record[0] for record in cursor if not record[0].endswith('b')])
    return list(versions)


def fetch_product_version_id(conn, product_name, version_string):
    """Given a product name and a version_string, returns a product_version_id"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT product_version_id
        FROM product_versions
        WHERE
            product_name=%s AND
            version_string=%s
    """, (product_name, version_string))
    ret = cursor.fetchone()
    if ret is None:
        return None
    return ret[0]


def insert_adu(conn, adu_count, adu_date, product_name, os_name, version_string):
    """Inserts ADU data into product_adu table"""
    # Fetch the product_version_id we need
    product_version_id = fetch_product_version_id(conn, product_name, version_string)

    if product_version_id is None:
        print('No product_version_id for %s %s' % (product_name, version_string))
        return

    # Insert the data
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO product_adu (adu_count, adu_date, os_name, product_version_id)
            VALUES (%s, %s, %s, %s)
        """, (adu_count, adu_date, os_name, product_version_id))
    except psycopg2.IntegrityError as exc:
        # Hitting an IntegrityError here probably means this data is in the table already, so we
        # just skip it.
        pass
    conn.commit()


def get_connection():
    """Builds a connection using ConnectionContext environment variables

    :returns: postgres connection

    """
    # This uses the same environment variables and defaults as postgres ConnectionContext
    host = os.environ.get('resource.postgresql.database_hostname', 'localhost')
    port = int(os.environ.get('resource.postgresql.database_port', '5432'))
    username = os.environ.get('secrets.postgresql.database_username', 'breakpad_rw')
    password = os.environ.get('secrets.postgresql.database_password', 'aPassword')
    dbname = os.environ.get('resource.postgresql.database_name', 'breakpad')

    local_config = {
        'database_hostname': host,
        'database_port': port,
        'database_username': username,
        'database_password': password,
        'database_name': dbname
    }
    dsn = (
        "host=%(database_hostname)s "
        "dbname=%(database_name)s "
        "port=%(database_port)s "
        "user=%(database_username)s "
        "password=%(database_password)s"
    ) % local_config
    return psycopg2.connect(dsn)


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--products', default='Firefox',
        help='comma separated set of products to fetch ADI for'
    )
    parser.add_argument(
        '--start_date', default='LASTWEEK', help='start date (yyyy-mm-dd)'
    )
    parser.add_argument(
        '--end_date', default='TODAY', help='end date (yyyy-mm-dd)'
    )
    parser.add_argument(
        '--endpoint', default='https://crash-stats.mozilla.com/api/ADI/',
        help='endpoint for ADI API'
    )
    args = parser.parse_args()

    today = datetime.datetime.utcnow()
    last_week = today - datetime.timedelta(days=7)

    start_date = args.start_date
    if start_date == 'LASTWEEK':
        start_date = last_week.strftime('%Y-%m-%d')

    end_date = args.end_date
    if end_date == 'TODAY':
        end_date = today.strftime('%Y-%m-%d')

    if start_date > end_date:
        print('Start date (%s) cannot be after end date (%s). Exiting.' % (start_date, end_date))
        return 1

    conn = get_connection()

    print('Fetching normalization data for %s from %s to %s' % (
        args.products, start_date, end_date)
    )

    for product in args.products.split(','):
        # Fetch versions from the product_versions table that we should pull data for
        versions = fetch_versions(conn, product)

        for version in versions:
            for platform in PLATFORMS:
                # For each (product, version, platform) combo, fetch adu data and insert it
                print('Fetching data for (%s, %s, %s)...' % (product, version, platform))

                adu_data = fetch_data_from_api(
                    endpoint=args.endpoint,
                    product=product,
                    version=version,
                    platform=platform,
                    start_date=start_date,
                    end_date=end_date
                )

                for hit in adu_data:
                    insert_adu(
                        conn=conn,
                        adu_count=hit['adi_count'],
                        adu_date=hit['date'],
                        product_name=product,
                        os_name=platform,
                        version_string=hit['version'],
                    )

    conn.close()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
