# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman import Namespace
import psycopg2

from socorro.external.postgresql.connection_context import ConnectionContext


_closes = _commits = _rollbacks = 0


class MockConnection(object):

    def __init__(self, dsn):
        self.dsn = dsn
        self.transaction_status = psycopg2.extensions.TRANSACTION_STATUS_IDLE

    def get_transaction_status(self):
        return self.transaction_status

    def close(self):
        global _closes
        _closes += 1

    def rollback(self):
        global _rollbacks
        _rollbacks += 1


class TestConnectionContext(object):
    def setup_method(self, method):
        # reset global variables so each test can run separately
        global _closes, _commits, _rollbacks
        _closes = _commits = _rollbacks = 0

    def test_basic_postgres_usage(self):
        class Sneak(ConnectionContext):

            def connection(self, __=None):
                assert self.dsn
                return MockConnection(self.dsn)

        definition = Namespace()
        local_config = {
            'database_hostname': 'host',
            'database_name': 'name',
            'database_port': 'port',
            'database_username': 'user',
            'database_password': 'password',
        }
        postgres = Sneak(definition, local_config)
        with postgres() as connection:
            assert isinstance(connection, MockConnection)
            assert connection.dsn == 'host=host dbname=name port=port user=user password=password'
            assert _closes == 0
        # exiting the context would lastly call 'connection.close()'
        assert _closes == 1
        assert _commits == 0
        assert _rollbacks == 0

        try:
            with postgres() as connection:
                raise NameError('crap')
        except NameError:
            pass
        finally:
            assert _closes == 2  # second time
            assert _commits == 0
            assert _rollbacks == 0

        try:
            with postgres() as connection:
                connection.transaction_status = psycopg2.extensions.TRANSACTION_STATUS_INTRANS
                raise psycopg2.OperationalError('crap!')
            # OperationalError's aren't bubbled up
        except psycopg2.OperationalError:
            pass

        assert _closes == 3
        assert _commits == 0
        assert _rollbacks == 0
