import contextlib
import sys


@contextlib.contextmanager
def with_scriptname(scriptname):
    """Overrides the sys.argv[0] with specified scriptname"""
    old_scriptname = sys.argv[0]
    sys.argv[0] = scriptname
    try:
        yield
    finally:
        sys.argv[0] = old_scriptname
