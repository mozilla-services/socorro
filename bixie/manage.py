#!/usr/bin/env python
import os
import sys
import site

# Edit this if necessary or override the variable in your environment.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bixie.settings')

try:
    # For local development in a virtualenv:
    from funfactory import manage
except ImportError:
    # Production:
    # Add a temporary path so that we can import the funfactory
    tmp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'vendor', 'src', 'funfactory')
    sys.path.append(tmp_path)

    from funfactory import manage

    # Let the path magic happen in setup_environ() !
    sys.path.remove(tmp_path)


manage.setup_environ(__file__, more_pythonic=True)

# We build binary packages on jenkins which installs itself
# in vendor-local/lib64/python
# Add it to sys.path just after vendor-local/lib/python which
# funfactory already added
_new_path = manage.path('vendor-local/lib64/python')
site.addsitedir(
    os.path.abspath(
        _new_path
    )
)
# now re-arrange so the order is right
_other_path = manage.path('vendor-local/lib/python')
sys.path.insert(sys.path.index(_other_path) + 1, _new_path)


if __name__ == "__main__":
    manage.main()
