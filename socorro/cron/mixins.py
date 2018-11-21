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
