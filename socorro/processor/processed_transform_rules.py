# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

""""
these are the rules that transform a raw crash into a processed crash
"""

# these symbols were originally defined here, but were moved to the
# signature utilities module.
# these symbols are imported here for backwards compatibility
from socorro.processor.signature_utilities import (
    OOMSignature,
    SigTrunc
)


#------------------------------------------------------------------------------
# the following tuple of tuples is a structure for loading rules into the
# TransformRules system. The tuples take the form:
#   predicate_function, predicate_args, predicate_kwargs,
#   action_function, action_args, action_kwargs.
#
# The args and kwargs components are additional information that a predicate
# or an action might need to have to do its job.  Providing values for args
# or kwargs essentially acts in a manner similar to functools.partial.
# When the predicate or action functions are invoked, these args and kwags
# values will be passed into the function along with the raw_crash,
# processed_crash and processor objects.

default_rules = (
    (OOMSignature, (), {}, OOMSignature, (), {}),
    (SigTrunc, (), {}, SigTrunc, (), {}),
)
