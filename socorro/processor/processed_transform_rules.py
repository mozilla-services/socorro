# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

""""
these are the rules that transform a raw crash into a processed crash
"""

from socorro.lib.ver_tools import normalize
from socorro.lib.util import DotDict

from sys import maxint


#==============================================================================
class ProcessedTransformRule(object):
    """the base class for Support Rules.  It provides the framework for the
    rules 'predicate', 'action', and 'version' as well as utilites to help
    rules do their jobs."""

    #--------------------------------------------------------------------------
    def predicate(self, raw_crash, processed_crash, processor):
        """the default predicate for processed_transform invokes any derivied
        _predicate function, trapping any exceptions raised in the process.  We
        are obligated to catch these exceptions to give subsequent rules the
        opportunity act.  An error during the predicate application is a
        failure of the rule, not a failure of the classification system itself
        """
        try:
            return self._predicate(raw_crash, processed_crash, processor)
        except Exception, x:
            processor.config.logger.debug(
                'processed_transform: %s predicate rejection - consideration '
                'of %s failed because of "%s"',
                self.__class__,
                raw_crash.get('uuid', 'unknown uuid'),
                x,
                exc_info=True
            )
            return False

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, processed_crash, processor):
        """"The default processed_transform predicate just returns True.  We
        want all the processed_transform rules to run.

        parameters:
            raw_crash - a mapping representing the raw crash data originally
                        submitted by the client
            processed_crash - the ultimate result of the processor, this is the
                              analyzed version of a crash.  It contains the
                              output of the MDSW program for each of the dumps
                              within the crash.
            processor - a reference to the processor object that is assigned
                        to working on the current crash. This object contains
                        resources that might be useful to a classifier rule.
                        'processor.config' is the configuration for the
                        processor in which database connection paramaters can
                        be found.  'processor.config.logger' is useful for any
                        logging of debug information.
                        'processor.c_signature_tool' or
                        'processor.java_signature_tool' contain utilities that
                        might be useful during classification.

        returns:
            True - this rule should be applied
            False - this rule should not be applied
        """
        return True

    #--------------------------------------------------------------------------
    def action(self, raw_crash, processed_crash, processor):
        """the default action for processed_transform  invokes any derivied
        _action function, trapping any exceptions raised in the process.  We
        are obligated to catch these exceptions to give subsequent rules the
        opportunity act and perhaps (mitigate the error).  An error during the
        action application is a failure of the rule, not a failure of the
        classification system itself."""
        try:
            return self._action(raw_crash, processed_crash, processor)
        except KeyError, x:
            processor.config.logger.debug(
                'processed_transform: %s action failure - %s failed because of '
                '"%s"',
                self.__class__,
                raw_crash.get('uuid', 'unknown uuid'),
                x,
            )
        except Exception, x:
            processor.config.logger.debug(
                'processed_transform: %s action failure - %s failed because of '
                '"%s"',
                self.__class__,
                raw_crash.get('uuid', 'unknown uuid'),
                x,
                exc_info=True
            )
        return False

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, processed_crash, processor):
        """Rules derived from this base class ought to override this method
        with an actual classification rule.  Successful application of this
        method should include a call to '_add_classification'.

        parameters:
            raw_crash - a mapping representing the raw crash data originally
                        submitted by the client
            processed_crash - the ultimate result of the processor, this is the
                              analized version of a crash.  It contains the
                              output of the MDSW program for each of the dumps
                              within the crash.
            processor - a reference to the processor object that is assigned
                        to working on the current crash. This object contains
                        resources that might be useful to a classifier rule.
                        'processor.config' is the configuration for the
                        processor in which database connection paramaters can
                        be found.  'processor.config.logger' is useful for any
                        logging of debug information.
                        'processor.c_signature_tool' or
                        'processor.java_signature_tool' contain utilities that
                        might be useful during classification.

        returns:
            True - this rule was applied successfully and no further rules
                   should be applied
            False - this rule did not succeed and further rules should be
                    tried
        """
        return True

    #--------------------------------------------------------------------------
    def version(self):
        """This method should be overridden in a base class."""
        return '0.0'


#==============================================================================
class OOMSignature(ProcessedTransformRule):
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
    def _predicate(self, raw_crash, processed_crash, processor):
        if 'OOMAllocationSize' in raw_crash:
            return True
        signature = processed_crash.signature
        for a_signature_fragment in self.signature_fragments:
            if a_signature_fragment in signature:
                return True
        return False

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, processed_crash, processor):
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
default_support_classifier_rules = (
    (OOMSignature, (), {}, OOMSignature, (), {}),
)
