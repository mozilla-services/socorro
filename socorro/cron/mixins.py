from functools import partial

from configman import RequiredConfig, class_converter


def with_transactional_resource(
    transactional_resource_class,
    resource_name,
    reference_value_from=None
):
    """a class decorator for Crontabber Apps.  This decorator will give access
    to a resource connection source.  Configuration will be automatically set
    up and the cron app can expect to have attributes:
        self.{resource_name}_connection_factory
        self.{resource_name}_transaction_executor
    available to use.
    Within the setup, the RequiredConfig structure gets set up like this:
        config.{resource_name}.{resource_name}_class = \
            transactional_resource_class
        config.{resource_name}.{resource_name}_transaction_executor_class = \
            'socorro.lib.transaction.TransactionExecutor'

    parameters:
        transactional_resource_class - a string representing the full path of
            the class that represents a connection to the resource.  An example
            is "socorro.cron.connection_factory.ConnectionFactory".
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
        new_req = cls.get_required_config()
        new_req.namespace(resource_name)
        new_req[resource_name].add_option(
            '%s_class' % resource_name,
            default=transactional_resource_class,
            from_string_converter=class_converter,
            reference_value_from=reference_value_from,
        )
        new_req[resource_name].add_option(
            '%s_transaction_executor_class' % resource_name,
            default='socorro.lib.transaction.TransactionExecutor',
            doc='a class that will execute transactions',
            from_string_converter=class_converter,
            reference_value_from=reference_value_from
        )
        cls.required_config = new_req

        #------------------------------------------------------------------
        def new__init__(self, *args, **kwargs):
            # instantiate the connection class for the resource
            super(cls, self).__init__(*args, **kwargs)
            setattr(
                self,
                "%s_connection_factory" % resource_name,
                self.config[resource_name]['%s_class' % resource_name](
                    self.config[resource_name]
                )
            )
            # instantiate a transaction executor bound to the
            # resource connection
            setattr(
                self,
                "%s_transaction_executor" % resource_name,
                self.config[resource_name][
                    '%s_transaction_executor_class' % resource_name
                ](
                    self.config[resource_name],
                    getattr(self, "%s_connection_factory" % resource_name)
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


using_postgres = partial(
    with_transactional_resource,
    'socorro.cron.connection_factory.ConnectionFactory',
    'database',
    'resource.postgresql'
)


def with_resource_connection_as_argument(resource_name):
    """a class decorator for Crontabber Apps.  This decorator will a class a
    _run_proxy method that passes a databsase connection as a context manager
    into the CronApp's run method.  The connection will automatically be closed
    when the ConApp's run method ends.

    In order for this dectorator to function properly, it must be used in
    conjunction with previous dectorator, "with_transactional_resource" or
    equivalent.  This decorator depends on the mechanims added by that
    decorator.
    """
    connection_factory_attr_name = '%s_connection_factory' % resource_name

    def class_decorator(cls):
        def _run_proxy(self, *args, **kwargs):
            factory = getattr(self, connection_factory_attr_name)
            with factory() as connection:
                try:
                    self.run(connection, *args, **kwargs)
                finally:
                    factory.close_connection(connection, force=True)
        cls._run_proxy = _run_proxy
        return cls
    return class_decorator


def with_single_transaction(resource_name):
    """a class decorator for Crontabber Apps.  This decorator will give a class
    a _run_proxy method that passes a databsase connection as a context manager
    into the CronApp's 'run' method.  The run method may then use the
    connection at will knowing that after if 'run' exits normally, the
    connection will automatically be commited.  Any abnormal exit from 'run'
    will result in the connnection being rolledback.

    In order for this dectorator to function properly, it must be used in
    conjunction with previous dectorator, "with_transactional_resource" or
    equivalent.  This decorator depends on the mechanims added by that
    decorator.
    """
    transaction_executor_attr_name = "%s_transaction_executor" % resource_name

    def class_decorator(cls):
        def _run_proxy(self, *args, **kwargs):
            getattr(self, transaction_executor_attr_name)(
                self.run,
                *args,
                **kwargs
            )
        cls._run_proxy = _run_proxy
        return cls
    return class_decorator


as_single_postgres_transaction = partial(
    with_single_transaction,
    'database'
)


def as_backfill_cron_app(cls):
    """a class decorator for Crontabber Apps.  This decorator embues a CronApp
    with the parts necessary to be a backfill CronApp.  It adds a main method
    that forces the base class to use a value of False for 'once'.  That means
    it will do the work of a backfilling app.
    """
    def main(self, function=None):
        return super(cls, self).main(
            function=function,
            once=False,
        )
    cls.main = main
    cls._is_backfill_app = True
    return cls


# dedicated rabbitmq mixins
#
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
