# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
This module contains convenience classes for managing "transactions"
that involve doing something and then committing or rolling back
depending on what happened.
"""

from contextlib import contextmanager


@contextmanager
def transaction_context(connection_context):
    """Creates a transaction context

    The connection context must implement the following:

    * ``commit() -> None``

      Commits the transaction.

    * ``rollback() -> None``

      Rolls the transaction back.

    * ``logger``

      Python logger.

    :arg connection_context: the connection context to use

    :yields: the connection the context wraps

    """
    with connection_context() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                conn.logger.exception("cannot rollback")
                raise
            raise
