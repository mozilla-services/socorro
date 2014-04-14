from django.db.backends import util

from django_statsd.patches.utils import wrap


def key(db, attr):
    return 'db.%s.%s.%s' % (db.client.executable_name, db.alias, attr)


def __getattr__(self, attr):
    """
    The CursorWrapper is a pretty small wrapper around the cursor.
    If you are NOT in debug mode, this is the wrapper that's used.
    Sadly if it's in debug mode, we get a different wrapper.
    """
    if self.db.is_managed():
        self.db.set_dirty()
    if attr in self.__dict__:
        return self.__dict__[attr]
    else:
        if attr in ['execute', 'executemany']:
            return wrap(getattr(self.cursor, attr), key(self.db, attr))
        return getattr(self.cursor, attr)


def wrap_class(base):
    class Wrapper(base):
        def execute(self, *args, **kw):
            return wrap(super(Wrapper, self).execute,
                        key(self.db, 'execute'))(*args, **kw)

        def executemany(self, *args, **kw):
            return wrap(super(Wrapper, self).executemany,
                        key(self.db, 'executemany'))(*args, **kw)

    return Wrapper


def patch():
    # So that it will work when DEBUG = True.
    util.CursorDebugWrapper = wrap_class(util.CursorDebugWrapper)
    # So that it will work when DEBUG = False.
    util.CursorWrapper.__getattr__ = __getattr__
