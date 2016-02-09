# The purpose of this class is to be slightly different from the one in
# socorro.unittest.middleware.fooing


class Fooing(object):

    def __init__(self, config, **kwargs):
        pass

    def get(self, *args, **kwargs):
        return ['one', 'two', 'three']
