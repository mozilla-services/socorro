# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
This module creates the classfications.support part of the processed crash. All
the support classifcation rules live here.

{...
    'classifications': {
        'support': {
            'classification': 'some classification',
            'classification_data': 'extra information saved by rule',
            'classificaiton_version': '0.0',
        }
    }

...
}
"""

from socorro.lib.util import DotDict


#==============================================================================
class SupportClassificationRule(object):
    """the base class for Support Rules.  It provides the framework for the
    rules 'predicate', 'action', and 'version' as well as utilites to help
    rules do their jobs."""

    #--------------------------------------------------------------------------
    def predicate(self, raw_crash, processed_crash, processor):
        """the default predicate for Support Classifiers invokes any derivied
        _predicate function, trapping any exceptions raised in the process.  We
        are obligated to catch these exceptions to give subsequent rules the
        opportunity act.  An error during the predicate application is a
        failure of the rule, not a failure of the classification system itself
        """
        try:
            return self._predicate(raw_crash, processed_crash, processor)
        except Exception, x:
            processor.config.logger.debug(
                'support_classifier: %s predicate rejection - consideration of'
                ' %s failed because of "%s"',
                self.__class__,
                raw_crash.get('uuid', 'unknown uuid'),
                x,
                exc_info=True
            )
            return False

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, processed_crash, processor):
        """"The default support classifier predicate just returns True.  We
        want all the support classifiers run.

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
            True - this rule should be applied
            False - this rule should not be applied
        """
        return True

    #--------------------------------------------------------------------------
    def action(self, raw_crash, processed_crash, processor):
        """the default action for Support Classifiers invokes any derivied
        _action function, trapping any exceptions raised in the process.  We
        are obligated to catch these exceptions to give subsequent rules the
        opportunity act and perhaps (mitigate the error).  An error during the
        action application is a failure of the rule, not a failure of the
        classification system itself."""
        try:
            return self._action(raw_crash, processed_crash, processor)
        except Exception, x:
            processor.config.logger.debug(
                'support_classifier: %s action failure - %s failed because of '
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

    #--------------------------------------------------------------------------
    def _add_classification(
        self,
        processed_crash,
        classification,
        classification_data,
        logger=None
    ):
        """This method adds a 'support' classification to a processed
        crash.

        parameters:
            processed_crash - a reference to the processed crash to which the
                              classification is to be added.
            classification - a string that is the classification.
            classification_data - a string of extra data that goes along with a
                                  classification
        """
        if 'classifications' not in processed_crash:
            processed_crash['classifications'] = DotDict()
        if 'support' not in processed_crash['classifications']:
            processed_crash['classifications']['support'] = []
        processed_crash['classifications']['support'].append(DotDict({
            'classification': classification,
            'classification_data': classification_data,
            'classification_version': self.version()
        }))
        if logger and "not classified" not in classification:
            logger.debug(
                'Support classification: %s',
                classification
            )


#==============================================================================
class BitguardClassfier(SupportClassificationRule):
    """To satisfy Bug 931907, this rule will detect 'bitguard.dll' in the
    modules list.  If present, it will add the classification,
    classifications.support.classification.bitguard to the processed crash"""
    #--------------------------------------------------------------------------
    def version(self):
        return '1.0'

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, processed_crash, processor):
        for a_module in processed_crash['json_dump']['modules']:
            if a_module['filename'] == 'bitguard.dll':
                self._add_classification(
                    processed_crash,
                    'bitguard',
                    None,
                    processor.config.logger
                )
                return True
        # bitguard was never found, this rule fails
        return False


#------------------------------------------------------------------------------
default_support_classifier_rules = (
    (BitguardClassfier, (), {}, BitguardClassfier, (), {}),
)
