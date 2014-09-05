# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

""""
these are the rules that transform a raw crash into a processed crash
"""

from socorro.lib.ver_tools import normalize
from socorro.lib.util import DotDict
from socorro.lib.transform_rules import Rule

from sys import maxint


#==============================================================================
class OOMSignature(Rule):
    """To satisfy Bug 1007530, this rule will modify the signature to
    tag OOM (out of memory) crashes"""

    signature_fragments = (
        'NS_ABORT_OOM',
        'mozalloc_handle_oom',
        'CrashAtUnhandlableOOM'
    )

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, raw_dumps, processed_crash, processor):
        if 'OOMAllocationSize' in raw_crash:
            return True
        signature = processed_crash.signature
        for a_signature_fragment in self.signature_fragments:
            if a_signature_fragment in signature:
                return True
        return False

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor):
        processed_crash.original_signature = processed_crash.signature
        try:
            size = int(raw_crash.OOMAllocationSize)
        except (TypeError, AttributeError, KeyError):
            processed_crash.signature = (
                "OOM | unknown | " + processed_crash.signature
            )
            return True

        if size <= 262144:  # 256K
            processed_crash.signature = "OOM | small"
        else:
            processed_crash.signature = (
                "OOM | large | " + processed_crash.signature
            )
        return True


#==============================================================================
class SigTrunc(Rule):
    """ensure that the signature is never longer than 255 characters"""

    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, raw_dumps, processed_crash, processor):
        return len(processed_crash.signature) > 255

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor):
        processed_crash.signature = "%s..." % processed_crash.signature[:252]
        return True


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
