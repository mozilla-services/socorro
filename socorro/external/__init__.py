"""Tools to interact with external resources we use in Socorro. It contains
mainly storage systems. """

class InsertionError(Exception):
    """When an insertion into a storage system failed. """
    pass


class MissingOrBadArgumentError(Exception):
    """When a mandatory argument is missing or has a bad value. """
    pass
