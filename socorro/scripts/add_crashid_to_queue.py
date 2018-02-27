#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import os
import os.path
import sys

import pika

from socorro.lib.ooid import is_crash_id_valid
from socorro.scripts import WrappedTextHelpFormatter


EPILOG = """
To use in a docker-based local dev environment:

  $ socorro-cmd add_crashid_to_queue socorro.normal <CRASHID>

Queues:

* socorro.normal - normal processing
* socorro.priority - priority processing
* socorro.stagesubmitter (-prod only) - sends crash to -stage environment

"""


def get_envvar(key, default=None):
    if default is None:
        return os.environ[key]
    return os.environ.get(key, default)


def build_pika_connection(host, port, virtual_host, user, password):
    """Build a pika (rabbitmq) connection"""
    return pika.BlockingConnection(
        pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host=virtual_host,
            connection_attempts=10,
            socket_timeout=10,
            retry_delay=1,
            credentials=pika.credentials.PlainCredentials(
                user,
                password
            )
        )
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        formatter_class=WrappedTextHelpFormatter,
        description='Send crash id to rabbitmq queue for processing',
        epilog=EPILOG.strip(),
    )
    parser.add_argument('queue', help='the queue to add the crash id to')
    parser.add_argument('crashid', nargs='*', help='one or more crash ids to add')

    if argv is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(argv)

    # This will pull crash ids from the command line if specified, or stdin
    crashids_iterable = args.crashid or sys.stdin
    crashids = [crashid.strip() for crashid in crashids_iterable if crashid.strip()]

    # Verify crash ids first
    for crashid in crashids:
        if not is_crash_id_valid(crashid):
            print('Crash id "%s" is not valid. Exiting.' % crashid)
            return 1

    # NOTE(willkg): This matches what's in socorro.external.rabbitmq classes without us having to
    # use configman and ConnectionContext and deal with switching between configured queues
    host = get_envvar('resource.rabbitmq.host')
    port = int(get_envvar('resource.rabbitmq.port', '5672'))
    user = get_envvar('secrets.rabbitmq.rabbitmq_user')
    password = get_envvar('secrets.rabbitmq.rabbitmq_password')

    virtual_host = get_envvar('resource.rabbitmq.virtual_host', '/')

    print('Configuration:')
    print('host:         %s' % host)
    print('port:         %s' % port)
    print('user:         %s' % user)
    print('password:     ********')
    print('virtual_host: %s' % virtual_host)
    print('queue:        %s' % args.queue)
    print('# crashids:   %s' % len(crashids))
    print('')

    conn = build_pika_connection(host, port, virtual_host, user, password)
    props = pika.BasicProperties(delivery_mode=2)
    channel = conn.channel()

    for crashid in crashids:
        print('Sending %s to %s....' % (crashid, args.queue))

        channel.basic_publish(
            exchange='',
            routing_key=args.queue,
            body=crashid,
            properties=props
        )

    print('Done!')
    return 0


if __name__ == '__main__':
    sys.exit(main())
