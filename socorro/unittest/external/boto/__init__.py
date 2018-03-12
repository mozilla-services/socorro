from configman import ConfigurationManager
import mock


def get_config(cls, values_source=None):
    """Generates config based on the required config of the cls

    :arg cls: a configman-enhanced class
    :arg values_source: dict of non-default configuration to change

    :returns: a configman config object

    """
    values_source = values_source or {}

    conf = cls.get_required_config()
    conf.add_option('logger', default=mock.Mock())
    conf.add_option('metrics', default=mock.Mock())

    cm = ConfigurationManager(
        [conf],
        app_name='testapp',
        app_version='1.0',
        app_description='',
        values_source_list=[values_source],
        argv_source=[],
    )
    return cm.get_config()
