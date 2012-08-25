################################################################################
# This is here solely to support test_middleware_app where it needs to test
# the override of specific classes to be loaded from another implementation.
# See test_overriding_implementation_class()

class Crash(object):

    def __init__(self, config, **kwargs):
        pass

    def get(self, *args, **kwargs):
        return ['all', 'your', 'base']
