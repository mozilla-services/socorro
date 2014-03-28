from functools import partial

from crontabber.mixins import (
    with_transactional_resource,
    with_resource_connection_as_argument,
    with_single_transaction
)

#==============================================================================
# dedicated hbase mixins
#------------------------------------------------------------------------------
# this class decorator adds attributes to the class in the form:
#     self.long_term_storage_connection
#     self.long_term_storage_transaction
# when using this definition as a class decorator, it is necessary to use
# parenthesis as it is a function call:
#    @with_postgres_transactions()
#    class MyClass ...
with_hbase_transactions = partial(
    with_transactional_resource,
    'socorro.external.hb.connection_context.ConnectionContext',
    'long_term_storage'
)
#------------------------------------------------------------------------------
# this class decorator adds a _run_proxy method to the class that will
# acquire a database connection and then pass it to the invocation of the
# class' "run" method.  Since the connection is in the form of a
# context manager, the connection will automatically be closed when "run"
# completes.
# when using this definition as a class decorator, it is necessary to use
# parenthesis as it is a function call:
#    @with_postgres_transactions()
#    class MyClass ...
with_hbase_connection_as_argument = partial(
    with_resource_connection_as_argument,
    'long_term_storage'
)
#------------------------------------------------------------------------------
# this class decorator adds a _run_proxy method to the class that will
# call the class' run method in the context of a database transaction.  It
# passes the connection to the "run" function.  When "run" completes without
# raising an exception, the transaction will be commited if the connection
# context class understands transactions. The default HBase connection does not
# do transactions
# when using this definition as a class decorator, it is necessary to use
# parenthesis as it is a function call:
#    @with_postgres_transactions()
#    class MyClass ...
with_single_hb_transaction = partial(
    with_single_transaction,
    'long_term_storage'
)

#==============================================================================
# dedicated rabbitmq mixins
#------------------------------------------------------------------------------
# this class decorator adds attributes to the class in the form:
#     self.queuing_connection
#     self.queuing_transaction
# when using this definition as a class decorator, it is necessary to use
# parenthesis as it is a function call:
#    @with_postgres_transactions()
#    class MyClass ...
with_rabbitmq_transactions = partial(
    with_transactional_resource,
    'socorro.external.rabbitmq.connection_context.ConnectionContext',
    'queuing'
)
#------------------------------------------------------------------------------
# this class decorator adds a _run_proxy method to the class that will
# acquire a database connection and then pass it to the invocation of the
# class' "run" method.  Since the connection is in the form of a
# context manager, the connection will automatically be closed when "run"
# completes.
# when using this definition as a class decorator, it is necessary to use
# parenthesis as it is a function call:
#    @with_postgres_transactions()
#    class MyClass ...
with_rabbitmq_connection_as_argument = partial(
    with_resource_connection_as_argument,
    'queuing'
)
#------------------------------------------------------------------------------
# this class decorator adds a _run_proxy method to the class that will
# call the class' run method in the context of a database transaction.  It
# passes the connection to the "run" function.  When "run" completes without
# raising an exception, the transaction will be commited if the connection
# context class understands transactions. The default RabbitMQ connection does
# not do transactions
# when using this definition as a class decorator, it is necessary to use
# parenthesis as it is a function call:
#    @with_postgres_transactions()
#    class MyClass ...
with_single_rabbitmq_transaction = partial(
    with_single_transaction,
    'queuing'
)
