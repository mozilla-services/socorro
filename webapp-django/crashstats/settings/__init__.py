from .base import *
try:
    from .local import *
except ImportError, exc:
    exc.args = tuple(
        [
            '%s (did you rename settings/(dev|prod).py-dist to '
            'settings/local.py?)' % exc.args[0]
        ]
    )
    raise exc
