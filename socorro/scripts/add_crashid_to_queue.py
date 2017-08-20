# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import os
import os.path

import pika

from socorro.lib.ooid import is_crash_id_valid


EPILOG = """
To use in a docker-based local dev environment:

  $ scripts/add_crashid_to_queue.py socorro.normal <CRASHID>

To use in -prod:

  $ /data/socorro/bin/socorro_env.sh
  (socorro) $ python scripts/add_crashid_to_queue.py socorro.submitter <CRASHID>

Queues:

* socorro.normal - normal processing
* socorro.priority - priority processing
* socorro.submitter (-prod only) - sends crash to -stage environment

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


class WrappedTextHelpFormatter(argparse.HelpFormatter):
    def _fill_text(self, text, width, indent):
        """Wraps text like HelpFormatter, but doesn't squash lines

        This makes it easier to do lists and paragraphs.

        """
        parts = text.split('\n')
        for i, part in enumerate(parts):
            parts[i] = super(WrappedTextHelpFormatter, self)._fill_text(part, width, indent)
        return '\n'.join(parts)


def main(argv):
    parser = argparse.ArgumentParser(
        formatter_class=WrappedTextHelpFormatter,
        prog=os.path.basename(__file__),
        description='Send crash id to rabbitmq queue for processing',
        epilog=EPILOG.strip(),
    )
    parser.add_argument('queue', help='the queue to add the crash id to')
    parser.add_argument('crashid', nargs='+', help='one or more crash ids to add')

    args = parser.parse_args(argv)

    # Verify crash ids first
    for crashid in args.crashid:
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
    print('crashids:     %s' % args.crashid)
    print('')

    conn = build_pika_connection(host, port, virtual_host, user, password)
    props = pika.BasicProperties(delivery_mode=2)
    channel = conn.channel()

    for crashid in args.crashid:
        print('Sending %s to %s....' % (crashid, args.queue))

        channel.basic_publish(
            exchange='',
            routing_key=args.queue,
            body=crashid,
            properties=props
        )

    print('Done!')
    return 0
