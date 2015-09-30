# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


#------------------------------------------------------------------------------
def class_with_partial_init(C, config_local, config_global=None):
    """
    Return a new subclass of C.

    This function creates a new class W as a subclass of C.  W's __init__ is
    effectively a partial function of C's __init__.  This allows a class to be
    embued with its initialization parameters long before actual instantiation.

    """

    #==========================================================================
    class W(C):
        wrapped_partial = True

        # our App object may go out of scope and be garbage collected.  If it
        # does, the config object would be without references and could be
        # garbage collected.  This class variable will hang on to the config
        # object enabling it to live for the entire run of the server process.
        global_config = config_global

        #----------------------------------------------------------------------
        def __init__(self):
            super(W, self).__init__(config_local)

    W.__name__ = C.__name__
    return W
