from .base import *
# TODO remove this whole try/except when we can safely stop using local.py
try:
    from .local import *
    import warnings
    warnings.warn(
        "Use environment variables or a .env file instead of local.py",
        DeprecationWarning
    )
except ImportError:
    pass
