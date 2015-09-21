# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


def class_with_partial_init(C, *args, **kwargs):
    """
    Return a new subclass of C.

    This function creates a new class W as a subclass of C.  W's __init__ is
    effectively a partial function of C's __init__.  This allows a class to be
    embued with its initialization parameters long before actual instantiation.

    """
    class W(C):
        wrapped_partial = True

        def __init__(self):
            super(W, self).__init__(*args, **kwargs)
    W.__name__ = C.__name__
    return W

classWithPartialInit = class_with_partial_init
