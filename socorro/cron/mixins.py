from functools import partial
import subprocess

from configman import RequiredConfig, Namespace, class_converter


#==============================================================================
#  mixin decorators
#
#  the functions found in this section are for modifying the BaseCronApp base
#  class by adding features and/or behaviors.  This replaces the previous
#  technique of using multiple inheritance for mixins.
#==============================================================================
def as_backfill_cron_app(cls):
    """a class decorator for Crontabber Apps.  This decorator embues a CronApp
    with the parts necessary to be a backfill CronApp.  It adds a main method
    that forces the base class to use a value of False for 'once'.  That means
    it will do the work of a backfilling app.
    """
    #----------------------------------------------------------------------
    def main(self, function=None):
        return super(cls, self).main(
            function=function,
            once=False,
        )
    cls.main = main
    cls._is_backfill_app = True
    return cls


#==============================================================================
def with_transactional_resource(transactional_resource_class, resource_name):
    """a class decorator for Crontabber Apps.  This decorator will give access
    to a resource connection source.  Configuration will be automatically set
    up and the cron app can expect to have attributes:
        self.{resource_name}_connection
        self.{resource_name}_transaction
    available to use.
    Within the setup, the RequiredConfig structure gets set up like this:
        config.{resource_name}.{resource_name}_class = \
            transactional_resource_class
        config.{resource_name}.{resource_name}_transaction_executor_class = \
            'socorro.database.transaction_executor.TransactionExecutor'

    parameters:
        transactional_resource_class - a string representing the full path of
            the class that represents a connection to the resource.  An example
            is "socorro.external.postgresql.connection_context
            .ConnectionContext.
        resource_name - a string that will serve as an identifier for this
            resource within the mixin. For example, if the resource is
            'database' we'll see configman namespace in the cron job section
            of "...class-SomeCronJob.database.database_connection_class" and
            "...class-SomeCronJob.database.transaction_executor_class"
    """
    def class_decorator(cls):
        if not issubclass(cls, RequiredConfig):
            raise Exception(
                '%s must have RequiredConfig as a base class' % cls
            )
        if not hasattr(cls, 'required_config'):
            cls.requried_config = Namespace()
        cls.required_config.namespace(resource_name)
        cls.required_config[resource_name].add_option(
            '%s_class' % resource_name,
            default=transactional_resource_class,
            from_string_converter=class_converter,
        )
        cls.required_config[resource_name].add_option(
            '%s_transaction_executor_class' % resource_name,
            default=
            'socorro.database.transaction_executor.TransactionExecutor',
            doc='a class that will execute transactions',
            from_string_converter=class_converter,
        )

        #------------------------------------------------------------------
        def new__init__(self, *args, **kwargs):
            # instantiate the connection class for the resource
            super(cls, self).__init__(*args, **kwargs)
            setattr(
                self,
                "%s_connection" % resource_name,
                self.config[resource_name]['%s_class' % resource_name](
                    self.config[resource_name]
                )
            )
            # instantiate a transaction executor bound to the
            # resource connection
            setattr(
                self,
                "%s_transaction" % resource_name,
                self.config[resource_name][
                    '%s_transaction_executor_class' % resource_name
                ](
                    self.config[resource_name],
                    getattr(self, "%s_connection" % resource_name)
                )
            )
        if hasattr(cls, '__init__'):
            original_init = cls.__init__

            def both_inits(self, *args, **kwargs):
                new__init__(self, *args, **kwargs)
                return original_init(self, *args, **kwargs)
            cls.__init__ = both_inits
        else:
            cls.__init__ = new__init__
        return cls
    return class_decorator


#==============================================================================
def with_resource_connection_as_argument(resource_name):
    """a class decorator for Crontabber Apps.  This decorator will a class a
    _run_proxy method that passes a databsase connection as a context manager
    into the CronApp's run method.  The connection will automaticall be close
    when the ConApp's run method ends.
    """
    connection_name = '%s_connection' % resource_name

    def class_decorator(cls):
        def _run_proxy(self, *args, **kwargs):
            with getattr(self, connection_name)() as connection:
                self.run(connection, *args, **kwargs)
        cls._run_proxy = _run_proxy
        return cls
    return class_decorator


#==============================================================================
def with_single_transaction(resource_name):
    """a class decorator for Crontabber Apps.  This decorator will give a class
    a _run_proxy method that passes a databsase connection as a context manager
    into the CronApp's run method.  The connection will automatically be closed
    when the ConApp's run method ends.
    """
    transaction_name = "%s_transaction" % resource_name

    def class_decorator(cls):
        def _run_proxy(self, *args, **kwargs):
            getattr(self, transaction_name)(self.run, *args, **kwargs)
        cls._run_proxy = _run_proxy
        return cls
    return class_decorator


#==============================================================================
def with_subprocess(cls):
    """a class decorator for Crontabber Apps.  This decorator gives the CronApp
    a _run_proxy method that will execute the cron app as a single PG
    transaction.  Commit and Rollback are automatic.  The cron app should do
    no transaction management of its own.  The cron app should be short so that
    the transaction is not held open too long.
    """

    def run_process(self, command, input=None):
        """
        Run the command and return a tuple of three things.

        1. exit code - an integer number
        2. stdout - all output that was sent to stdout
        2. stderr - all output that was sent to stderr
        """
        if isinstance(command, (tuple, list)):
            command = ' '.join('"%s"' % x for x in command)

        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, err = proc.communicate(input=input)
        return proc.returncode, out.strip(), err.strip()
    cls.run_process = run_process
    return cls


#==============================================================================
# dedicated postgresql mixins
#------------------------------------------------------------------------------
# this class decorator adds attributes to the class in the form:
#     self.database_connection
#     self.database_transaction
# when using this definition as a class decorator, it is necessary to use
# parenthesis as it is a function call:
#    @with_postgres_transactions()
#    class MyClass ...
with_postgres_transactions = partial(
    with_transactional_resource,
    'socorro.external.postgresql.connection_context.ConnectionContext',
    'database'
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
with_postgres_connection_as_argument = partial(
    with_resource_connection_as_argument,
    'database'
)
#------------------------------------------------------------------------------
# this class decorator adds a _run_proxy method to the class that will
# call the class' run method in the context of a database transaction.  It
# passes the connection to the "run" function.  When "run" completes without
# raising an exception, the transaction will be commited.  An exception
# escaping the run function will result in a "rollback"
# when using this definition as a class decorator, it is necessary to use
# parenthesis as it is a function call:
#    @with_postgres_transactions()
#    class MyClass ...
with_single_postgres_transaction = partial(
    with_single_transaction,
    'database'
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
